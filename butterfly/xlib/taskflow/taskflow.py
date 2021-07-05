#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-06-13 10:13:30

# File Name: taskflow.py
# Description:

"""
import json
import logging
import traceback
from datetime import datetime

from xlib.taskflow import model
from xlib.db import shortcuts
from xlib.taskflow import task_fsm
from xlib.taskflow import exceptions


class WorkflowRunner(object):
    """
    This object is designed to be inherited by a class in
    client code. This inheriting class can override the
    L{workflow()<WorkflowRunner.workflow>} method to define the
    tasks that need to be run and their dependencies.
    """

    def create(self, job_reqid, job_namespace, job_name, job_type, job_extra=None, job_timeout=None):
        """
        Create workflow
        """
        if job_extra is None:
            job_extra = {}

        if job_timeout is None:
            # 1h
            job_timeout = 3600

        self.job_extra = job_extra
        self.params_check()
        job_extra_json = json.dumps(job_extra)

        job_id = model.Job.insert(
            job_reqid=job_reqid,
            job_namespace=job_namespace,
            job_name=job_name,
            job_type=job_type,
            job_extra=job_extra_json,
            job_timeout=job_timeout
        ).execute()
        self._job_id = job_id
        self.workflow()
        return self._job_id

    def params_check(self):
        """
        Parameter check
        """
        pass

    def workflow(self):
        """
        Workflow definition defined in child class

        This method should be overridden in the class derived from
        L{WorkflowRunner} to specify the actual workflow logic. Client
        code should not call this method directly.
        """
        pass

    def add_task(self,
                 label,
                 cmd,
                 params=None,
                 requires=None,
                 provides=None,
                 dependencies=None,
                 retrymax=0,
                 is_save=False,
                 timeout=None
                 ):
        """
        Args:
            label: (string) A string used to identify each task. The label must
                 be composed of only ascii letters, digits,
                 underscores and dashes (ie. /[A-Za-z0-9_-]+/). The
                 label must also be unique within the workflow, and
                 non-empty.
            cmd: (string) The task command.
            requires: (list).
            provides: (list).
            dependencies: (list) A task label or container of task labels specifying all dependent
                        tasks. Dependent tasks must already exist in the workflow.
            retrymax: (int).
            is_save: (bool) Save the results to the job at the same time.
        """
        if params is not None:
            assert isinstance(params, dict)
            params = json.dumps(params)

        if requires is None:
            requires_str = ""
        else:
            assert isinstance(requires, list)
            requires_str = ",".join(requires)

        if provides is None:
            provides_str = ""
        else:
            assert isinstance(provides, list)
            provides_str = ",".join(provides)

        if dependencies is None:
            dependencies_str = ""
        else:
            assert isinstance(dependencies, list)
            dependencies_str = ",".join(dependencies)

        if timeout is None:
            timeout = 0

        self._task_id = model.Task.insert(
            job_id=self._job_id,
            task_label=label,
            task_cmd=cmd,
            task_params=params,
            task_requires=requires_str,
            task_provides=provides_str,
            task_dependencies=dependencies_str,
            task_retrymax=retrymax,
            task_is_save=is_save,
            task_timeout=timeout
        ).execute()


def is_job_end(job_id):
    """
    发起任务, 需要加锁
    """

    task_model = model.Task
    job_model = model.Job
    job_obj = job_model.get(job_model.job_id == job_id)
    # 获取所有字段
    record_list = task_model.select().where(task_model.job_id == job_id)

    task_status_dict = {}
    task_status_dict["waiting_count"] = 0
    task_status_dict["pending_count"] = 0
    task_status_dict["started_count"] = 0
    task_status_dict["finished_count"] = 0
    task_status_dict["failed_count"] = 0
    for record in record_list:
        record_dict = shortcuts.model_to_dict(record)
        try:
            if record_dict["task_status"] == "waiting":
                task_status_dict["waiting_count"] = task_status_dict["waiting_count"] + 1
                task = task_fsm.TaskMachine(model=record, state_field="task_status")
                task.go_pending()
            if record_dict["task_status"] == "pending":
                task_status_dict["pending_count"] = task_status_dict["pending_count"] + 1
                task = task_fsm.TaskMachine(model=record, state_field="task_status")
                task.go_running()
            if record_dict["task_status"] == "started":
                task_status_dict["started_count"] = task_status_dict["started_count"] + 1
                task = task_fsm.TaskMachine(model=record, state_field="task_status")
                task.go_success()
            if record_dict["task_status"] == "finished":
                task_status_dict["finished_count"] = task_status_dict["finished_count"] + 1
                task = task_fsm.TaskMachine(model=record, state_field="task_status")
                # 检查是否需要保存数据到 job
                if record_dict["task_is_save"]:
                    ret_data = record_dict["ret_data"]
                    ret_data_dict = json.loads(ret_data)
                    if "data" in ret_data_dict.keys():
                        job_obj.ret_data = json.dumps(ret_data_dict["data"])
                    else:
                        ret_data_dict.pop("stat", None)
                        job_obj.ret_data = json.dumps(ret_data_dict)

            if record_dict["task_status"] == "failed":
                task_status_dict["failed_count"] = task_status_dict["failed_count"] + 1

        except exceptions.TaskWaiting:
            logging.info(traceback.format_exc())
        except BaseException:
            log_msg = ("job_id={job_id} task_id={task_id} task_reqid={task_reqid} task_cmd={task_cmd} "
                       "err_info={err_info}".format(
                           job_id=record_dict["job_id"],
                           task_id=record_dict["task_id"],
                           task_reqid=record_dict["task_reqid"],
                           task_cmd=record_dict["task_cmd"],
                           err_info=traceback.format_exc()
                       ))
            logging.error(log_msg)
            # 设置任务失败
            task.go_failure()

    job_obj.u_time = datetime.now()
    job_obj.job_cost = (job_obj.u_time - job_obj.c_time).total_seconds()
    if job_obj.job_cost > job_obj.job_timeout:
        job_obj.job_status = "failed"
        job_obj.ret_stat = "ERR_JOB_TIMEOUT"
        job_obj.save()
        return True, task_status_dict

    if task_status_dict["failed_count"] > 0:
        job_obj.job_status = "failed"
        job_obj.save()
        return True, task_status_dict

    if task_status_dict["finished_count"] == len(record_list):
        job_obj.job_status = "finished"
        job_obj.save()
        return True, task_status_dict

    return False, task_status_dict
