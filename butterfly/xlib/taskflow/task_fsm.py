#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-06-14 13:11:16

# File Name: task_fsm.py
# Description:

"""
import json
import logging
import traceback

from xlib.statemachine import StateMachine
from xlib.statemachine import State
from xlib.taskflow import model
from xlib.taskflow import exceptions
from xlib.db import shortcuts
from xlib import db
from xlib.mq import Queue
from xlib.mq import msg
from xlib.mq import exceptions as mq_exceptions

log = logging.getLogger("butterfly")
baichuan_connection = db.my_caches["baichuan"]

__info = "xingqiao"
__version = "1.0.1"


class TaskMachine(StateMachine):
    """
    +------------+------------+---------+----------+---------+
    |   Start    |   Event    |   End   | On Enter | On Exit |
    +------------+------------+---------+----------+---------+
    |  failed[$] |     .      |    .    |    .     |    .    |
    |  pending   | go_failure |  failed |    .     |    .    |
    |  pending   | go_running | started |    .     |    .    |
    |  started   | go_failure |  failed |    .     |    .    |
    |  started   | go_success |finished |    .     |    .    |
    | finished[$]|     .      |    .    |    .     |    .    |
    | waiting[^] | go_failure | failed  |    .     |    .    |
    | waiting[^] | go_pending | pending |    .     |    .    |
    +------------+------------+---------+----------+---------+

    [^] 表示初始状态
    [$] 表示终止状态
                                      检查依赖      准备参数       结果校验
                                    (go_pending)   (go_running)  (go_success)
    即 taskflow 的状态正常流程为 waiting ---> pending ---> started ---> finished
                                    |           |           |
                                    |           |           V
                                    +-----------+-------> failed
                                        (go_failure)
    """
    waiting = State(name="waiting", initial=True)
    pending = State(name="pending")
    started = State(name="started")
    finished = State(name="finished")
    failed = State(name="failed")

    go_pending = waiting.to(pending)
    go_running = pending.to(started)
    go_success = started.to(finished)
    go_failure = waiting.to(failed) | pending.to(failed) | started.to(failed)

    def on_go_pending(self):
        """
        检测依赖任务是否已完成
        > * (1) 无依赖任务
        > * (2) 有依赖任务，且依赖任务均已完成
        """
        log_msg = "task_id={task_id} task_cmd={task_cmd} task_dependencies={task_dependencies}".format(
            task_id=self.model.task_id,
            task_cmd=self.model.task_cmd,
            task_dependencies=self.model.task_dependencies
        )
        logging.info(log_msg)
        if self.model.task_dependencies:
            job_id = self.model.job_id
            task_model = model.Task
            task_dependencies = self.model.task_dependencies
            task_dependencies_list = task_dependencies.split(",")
            task_dependencies_set = set(task_dependencies_list)
            record_list = task_model.select(task_model.task_id, task_model.task_status).where(
                task_model.job_id == job_id, task_model.task_label.in_(task_dependencies_set)
            )
            finished_count = 0
            for record in record_list:
                record_dict = shortcuts.model_to_dict(record)
                if record_dict["task_status"] == "finished":
                    finished_count = finished_count + 1

            if finished_count != len(task_dependencies_list):
                log_msg = "[task_id={task_id} dependencies is not finished]".format(task_id=self.model.task_id)
                raise exceptions.TaskWaiting(log_msg)

    def on_go_running(self):
        self.task_requires_dict = {}
        all_taskdata_key = "all_taskdata"

        # 检查是否已设置 params, 若有，则直接跳过
        if self.model.task_params is not None:
            params_dict = json.loads(self.model.task_params)
            self.task_requires_dict = params_dict
            return

        # 无需传参
        if not self.model.task_requires:
            return

        task_requires_list = self.model.task_requires.split(",")
        # 在依赖的 task 的 ret_data 中获取参数数据
        job_id = self.model.job_id
        if self.model.task_dependencies:
            all_taskdata_list = []
            task_model = model.Task
            task_dependencies = self.model.task_dependencies
            task_dependencies_list = task_dependencies.split(",")
            task_dependencies_set = set(task_dependencies_list)
            record_list = task_model.select(task_model.task_id, task_model.ret_data).where(
                task_model.job_id == job_id, task_model.task_label.in_(task_dependencies_set)
            )
            for record in record_list:
                record_dict = shortcuts.model_to_dict(record)
                ret_data = json.loads(record_dict["ret_data"])
                all_taskdata_list.append(ret_data)
                for key in ret_data.keys():
                    if key in task_requires_list:
                        self.task_requires_dict[key] = ret_data[key]

        job_model = model.Job
        # 在 job_extra 中获取参数数据
        job_obj = job_model.select().where(job_model.job_id == job_id).get()
        job_extra_json = job_obj.job_extra
        job_extra = json.loads(job_extra_json)
        for key in job_extra.keys():
            if key in task_requires_list:
                self.task_requires_dict[key] = job_extra[key]

        # 检查是否需要所有依赖的 task data
        if all_taskdata_key in task_requires_list:
            self.task_requires_dict[all_taskdata_key] = all_taskdata_list

        # 检查参数是否准备 Ok
        task_requires_list.sort()
        task_requires_list_cur = sorted(self.task_requires_dict.keys())
        if task_requires_list != task_requires_list_cur:
            log_msg = ("event=go_running job_id={job_id} task_id={task_id} cmd={cmd} "
                       "requires={requires} params={params} job_extra={job_extra} "
                       "task_requires_list={task_requires_list} task_requires_list_cur={task_requires_list_cur} "
                       "err_info={err_info} ".format(
                           job_id=self.model.job_id,
                           task_id=self.model.task_id,
                           cmd=self.model.task_cmd,
                           requires=self.model.task_requires,
                           params=str(self.task_requires_dict),
                           job_extra=job_extra_json,
                           task_requires_list=str(task_requires_list),
                           task_requires_list_cur=str(task_requires_list_cur),
                           err_info="params not match"
                       ))
            raise exceptions.TaskError(log_msg)

    def on_go_success(self):
        """
        检查状态
        """
        msg_status = "none"
        msg_id = self.model.task_reqid
        provides_str = self.model.task_provides
        if provides_str:
            provides_list = provides_str.split(",")
        else:
            provides_list = []

        try:
            msg_obj = msg.Msg.fetch(msg_id, connection=baichuan_connection)
        except mq_exceptions.NoSuchMsgError:
            log_msg = "task_id={task_id} task_reqid={task_reqid} msg_status={msg_status} err_info={err_info}".format(
                task_id=self.model.task_id, task_reqid=msg_id, msg_status=msg_status, err_info="msg not exists")
            raise exceptions.TaskError(log_msg)
        except BaseException:
            logging.warning(
                "msg_id={msg_id} err_info={err_info}".format(
                    msg_id=msg_id,
                    err_info=traceback.format_exc()))
            raise exceptions.TaskWaiting(log_msg)

        # status
        msg_status = msg_obj.get_status()
        # cost
        self.model.task_cost = float(getattr(msg_obj, "cost", "-1"))

        if msg_status == "failed":
            log_msg = "task_id={task_id} task_reqid={task_reqid} msg_status={msg_status} err_info={err_info}".format(
                task_id=self.model.task_id, task_reqid=msg_id, msg_status=msg_status, err_info="msg exe failed")
            raise exceptions.TaskError(log_msg)

        if msg_status == "finished":
            msg_result = json.loads(msg_obj.result)
            # 检查状态
            if msg_result["stat"] != "OK":
                log_msg = ("task_id={task_id} task_reqid={task_reqid} msg_status={msg_status} "
                           "err_info={err_info}".format(
                               task_id=self.model.task_id, task_reqid=msg_id,
                               msg_status=msg_status, err_info="msg exe failed, stat error"))
                raise exceptions.TaskError(log_msg)

            self.model.ret_data = msg_obj.result
            if provides_str:
                msg_result_key = msg_result.keys()
                intersection = list(set(provides_list).intersection(set(msg_result_key)))
                if intersection != provides_list:
                    log_msg = ("task_id={task_id} task_reqid={task_reqid} msg_status={msg_status} "
                               "provides={provides} result_key={result_key} err_info={err_info}".format(
                                   task_id=self.model.task_id, task_reqid=msg_id,
                                   provides=provides_str, result_key=",".join(msg_result_key),
                                   msg_status=msg_status, err_info="msg exe failed, data error"))
                    raise exceptions.TaskError(log_msg)

            # 执行 OK
            return

        log_msg = "task_id={task_id} task_reqid={task_reqid} msg_status={msg_status} err_info={err_info}".format(
            task_id=self.model.task_id, task_reqid=msg_id, msg_status=msg_status, err_info="waiting")
        raise exceptions.TaskWaiting(log_msg)

    def on_go_failure(self):
        pass

    def on_exit_waiting(self):
        pass

    def on_exit_pending(self):
        """
        解析参数
        """
        pass

    def on_enter_pending(self):
        """
        保存数据到数据库
        """
        self.model.save()

    def on_enter_started(self):
        # 发起请求
        mq_queue = Queue(self.model.task_cmd, connection=baichuan_connection)
        msg_data = json.dumps(self.task_requires_dict)
        # 消息队列中结果保留 1 天
        msg_obj = mq_queue.enqueue(msg_data, result_ttl=86400)
        self.model.task_reqid = msg_obj.id
        self.model.save()

    def on_enter_finished(self):
        """
        """
        self.model.save()

    def on_enter_failed(self):
        """
        """
        self.model.save()
