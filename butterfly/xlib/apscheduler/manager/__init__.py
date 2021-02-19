# coding=utf8
import os
import re
import json
import traceback

# schedulers
from xlib.apscheduler.schedulers import background
# triggers
from xlib.apscheduler.triggers.interval import IntervalTrigger
from xlib.apscheduler.triggers.cron import CronTrigger
from xlib.apscheduler.triggers.date import DateTrigger
# jobstores
from xlib.apscheduler.jobstores.base import ConflictingIdError
from xlib.apscheduler.jobstores.mysql import MySQLJobStore
from xlib.apscheduler.jobstores.memory import MemoryJobStore
# models
from xlib.apscheduler.models.apscheduler_model import RuqiJobsHistory
from xlib.apscheduler.models.apscheduler_model import RuqiJobs
# executors
from xlib.apscheduler.executors.pool import ThreadPoolExecutor

from xlib.util import shell_util
from xlib.util import http_util
from xlib.db import peewee
from xlib.db import shortcuts
from conf import config
from conf import logger_conf


def run_cmd(job_id, job_name, cmd, errlog):
    """
    执行本地命令
    Args:
        job_id  : (Str) job_id
        job_name: (Str) job_name
        cmd     : (Str) "python/bash file_path args"
        errlog  : (object) errlog logger
    """
    # 设置 1 小时超时
    cmd_result = shell_util.run(cmd, timeout=3600)
    values = {
        "job_id": job_id,
        "job_name": job_name,
        "cmd": cmd,
        "cmd_is_success": cmd_result.success(),
        # 设置的在数据库中最多存储 4096 字节
        "cmd_output": cmd_result.output()[:4096],
        "scheduler_name": config.scheduler_name,
        "cmd_cost": float(cmd_result.cost)
    }
    try:
        RuqiJobsHistory.create(**values)
    except BaseException:
        errlog.log("[module=run_scheduler_job  job_id=job_id exception_info={exception_info}]".format(
            job_id=job_id, exception_info=traceback.format_exc()))


def run_http(job_id, job_name, cmd, errlog):
    """
    执行 HTTP 请求
    Args:
        job_id  : (Str) job_id
        job_name: (Str) job_name
        cmd     : (Str) 'python/bash file_path args'
                : 'http://127.0.0.1:8585/demo_api/hello#{"str_info":"hello"}'
                : 'http://127.0.0.1:8585/demo_api/ping'
        errlog  : (object) errlog logger
    """
    # 请求体数据
    data = {}

    # cmd
    cmd_list = cmd.split("#")
    if len(cmd_list) == 1:
        url = cmd_list[0]
    else:
        url = cmd_list[0]
        data = json.loads(cmd_list[1])

    cmd_result = http_util.post_json(url, data=data)

    values = {
        "job_id": job_id,
        "job_name": job_name,
        "cmd": cmd,
        "cmd_is_success": cmd_result.success(),
        # 设置的在数据库中最多存储 4096 字节
        # http_util 默认会将 json 转为 dict
        "cmd_output": str(cmd_result.output())[:4096],
        "scheduler_name": config.scheduler_name,
        "cmd_cost": float(cmd_result.cost)
    }
    try:
        RuqiJobsHistory.create(**values)
    except BaseException:
        errlog.log("[module=run_scheduler_job  job_id=job_id exception_info={exception_info}]".format(
            job_id=job_id, exception_info=traceback.format_exc()))


class Scheduler(object):
    """
    Scheduler class
    """

    def __init__(self, initlog, errlog, jobstore_alias="memory"):
        if jobstore_alias == "mysql":
            self._jobstore = MySQLJobStore()
        else:
            self._jobstore = MemoryJobStore()

        # -----------------------------------------------------------------
        # config
        # -----------------------------------------------------------------
        jobstores = {
            'default': self._jobstore,
            'memory': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        scheduler_config = {
            'default_wait_seconds': 300  # 单位:s 假如检测到无 job 时，将会在 default_wait_seconds 后进行唤醒
        }
        # -----------------------------------------------------------------end
        self._initlog = initlog
        self._errlog = errlog
        self._scheduler = background.BackgroundScheduler(jobstores=jobstores,
                                                         executors=executors, job_defaults=job_defaults, scheduler_config=scheduler_config)

    def _check_cmd(self, cmd):
        """
        检查 cmd 命令合法性, 仅支持执行 Python/Shell 脚本
        Args:
            cmd: (Str)
                example: "python/bash file_path args"
        Returns:
            bool
        """
        if ";" in cmd or "&&" in cmd or "||" in cmd:
            return False

        cmd_list = cmd.split()
        if len(cmd_list) < 2:
            return False

        file_type = cmd_list[0]
        file_path = cmd_list[1]
        if file_type not in ["python", "bash"]:
            return False

        if not os.path.exists(file_path):
            return False

        return True

    def _add_cron_job(self, func, job_id, job_name, cmd, rule):
        """
        创建 cron 任务, 有同名任务时则失败
        Args:
            func    : func
            job_id  : job id(唯一索引)
            job_name: 用作分类
            cmd     : job cmd
            rule    : "* * * * * *"
        Returns:
            (Bool, Str)
        """
        cron_rule_list = rule.split(' ')
        if len(cron_rule_list) != 6:
            return (False, "Rule check failed")

        kwargs = {}
        kwargs["cmd"] = cmd
        kwargs["job_id"] = job_id
        kwargs["job_name"] = job_name
        kwargs["errlog"] = self._errlog

        cron_trigger = CronTrigger(
            second=cron_rule_list[0],
            minute=cron_rule_list[1],
            hour=cron_rule_list[2],
            day=cron_rule_list[3],
            month=cron_rule_list[4],
            day_of_week=cron_rule_list[5])

        self._scheduler.add_job(
            func=func,
            trigger=cron_trigger,
            kwargs=kwargs,
            id=job_id,
            name=job_name,
            # 允许调度 30s 前未调度的任务
            misfire_grace_time=30,
        )
        return (True, "OK")

    def _add_interval_job(self, func, job_id, job_name, cmd, rule):
        """
        添加间隔任务
        Args:
            func    : func
            job_id  : job id(唯一索引)
            job_name: 用作分类
            cmd     : job cmd
            rule    : Xs/Xm/Xh/Xd
        Returns:
            (Bool, Str)
        """
        interval_cron_dict = {}
        interval_cron_dict["days"] = 0
        interval_cron_dict["hours"] = 0
        interval_cron_dict["minutes"] = 0
        interval_cron_dict["seconds"] = 0

        rule_list = re.findall(r"[0-9]+|[a-z]+", rule)
        if len(rule_list) != 2:
            return (False, "Rule check failed")

        if rule_list[1] not in ["s", "m", "h", "d"]:
            return (False, "Rule check failed")

        if rule_list[1] == "s":
            interval_cron_dict["seconds"] = int(rule_list[0])
        elif rule_list[1] == "m":
            interval_cron_dict["minutes"] = int(rule_list[0])
        elif rule_list[1] == "h":
            interval_cron_dict["hours"] = int(rule_list[0])
        elif rule_list[1] == "d":
            interval_cron_dict["days"] = int(rule_list[0])

        kwargs = {}
        kwargs["cmd"] = cmd
        kwargs["job_id"] = job_id
        kwargs["job_name"] = job_name
        kwargs["errlog"] = self._errlog

        interval_trigger = IntervalTrigger(
            days=interval_cron_dict["days"],
            hours=interval_cron_dict["hours"],
            minutes=interval_cron_dict["minutes"],
            seconds=interval_cron_dict["seconds"],
        )

        self._scheduler.add_job(
            func=func,
            trigger=interval_trigger,
            kwargs=kwargs,
            id=job_id,
            name=job_name,
            # 允许调度 30s 前未调度的任务
            misfire_grace_time=30,
        )
        return (True, "OK")

    def _add_date_job(self, func, job_id, job_name, cmd, rule):
        """
        添加一次任务
        Args:
            func    : func
            job_id  : job id(唯一索引)
            job_name: 用作分类
            cmd     : job cmd
            rule    : "2020-12-16 18:03:17"/"2020-12-16 18:05:17.682862"/"now"
        Returns:
            (Bool, Str)
        """

        if rule == "now":
            date_trigger = DateTrigger()
        else:
            date_trigger = DateTrigger(run_date=rule)

        kwargs = {}
        kwargs["cmd"] = cmd
        kwargs["job_id"] = job_id
        kwargs["job_name"] = job_name
        kwargs["errlog"] = self._errlog

        self._scheduler.add_job(
            func=func,
            trigger=date_trigger,
            kwargs=kwargs,
            id=job_id,
            name=job_name,
            # 允许调度 30s 前未调度的任务
            misfire_grace_time=30,
        )

        return (True, "OK")

    def add_job(self, job_trigger, job_id, job_name, cmd, rule):
        """
        Args:
            job_trigger: job_trigger(cron/interval/date)
            job_id     : job id(唯一索引)
            job_name   : 用作分类
            cmd        : job cmd
            rule       :
                   date: "2020-12-16 18:03:17"/"2020-12-16 18:05:17.682862"/"now"
                   cron: "* * * * * *"
               interval: Xs/Xm/Xh/Xd
        Returns:
            (Bool, Str)
        """
        jobs_map = {
            "cron": self._add_cron_job,
            "interval": self._add_interval_job,
            "date": self._add_date_job
        }

        if job_trigger not in jobs_map.keys():
            return (False, "Job_trigger not in jobs_map")

        if cmd.startswith("http"):
            func = run_http
        else:
            if not self._check_cmd(cmd):
                return (False, "(scripts) Cmd does not meet expectations")
            func = run_cmd

        try:
            is_success, err_msg = jobs_map[job_trigger](func, job_id, job_name, cmd, rule)
        except ConflictingIdError as e:
            is_success, err_msg = False, str(e)
        except BaseException as e:
            is_success, err_msg = False, str(e)

        return (is_success, err_msg)

    def start(self):
        """
        启动 scheduler
        """
        is_success = False
        try:
            self._scheduler.start()
            is_success = True
        except BaseException:
            self._errlog.log(
                "[module=start_scheduler  exception_info={exception_info}]".format(
                    exception_info=traceback.format_exc()))

        self._initlog.log("[module=start_scheduler jobstore={jobstore} is_success={is_success}]".format(
            jobstore=self._jobstore,
            is_success=is_success
        ))

    def status(self):
        """
        Scheduler 状态
        """
        return self._scheduler.status()

    def wakeup(self):
        """
        唤醒 scheduler
        """
        self._scheduler.wakeup()

    def _get_jobs_in_memory(self):
        """
        获取所有任务

        job.__dict__
        {
            'runs': 0,
            'args': [],
            'name': u'test_name',
            'misfire_grace_time': 1,
            'instances': 0,
            '_lock': <thread.lock object at 0x10241c5d0>,
            'next_run_time': datetime.datetime(2020, 12, 15, 19, 48),
            'max_instances': 1,
            'max_runs': None,
            'coalesce': True,
            'trigger': <CronTrigger (month='*', day='*', day_of_week='*', hour='*', minute='*/4', second='*/3')>,
            'func': <function run_cmd at 0x102676140>,
            'kwargs': {'cmd': 'cc'},
            'id': '512965'
        }
        """
        data = {}
        jobs = []
        for job in self._scheduler.get_jobs():
            # cron_rule
            jobinfo = {}

            rule = ""
            trigger = ""
            if isinstance(job.trigger, CronTrigger):
                trigger = "cron"
                fields = job.trigger.fields
                cron = {}
                for field in fields:
                    cron[field.name] = str(field)
                rule = "{second} {minute} {hour} {day} {month} {day_of_week}".format(
                    second=cron['second'],
                    minute=cron['minute'],
                    hour=cron['hour'],
                    day=cron['day'],
                    month=cron['month'],
                    day_of_week=cron["day_of_week"]
                )

            if isinstance(job.trigger, IntervalTrigger):
                trigger = "interval"
                rule = str(job.trigger.interval_length) + "s"

            if isinstance(job.trigger, DateTrigger):
                trigger = "date"
                rule = str(job.trigger.run_date)

            jobinfo["job_id"] = job.id
            jobinfo["job_name"] = job.name
            jobinfo["job_trigger"] = trigger
            jobinfo["cmd"] = job.kwargs["cmd"]
            jobinfo["rule"] = rule
            jobinfo["nexttime"] = str(job.next_run_time)
            jobs.append(jobinfo)

        data["total"] = len(jobs)
        data["list"] = jobs
        return data

    def _get_jobs_in_mysql(self, job_id=None, job_name=None, page_index=None, page_size=10):
        """
        mysql jobstore 时, 获取 job 列表
        """
        data = {}
        # 如下方式以分页数据返回
        model = RuqiJobs
        query_cmd = RuqiJobs.select()
        expressions = []
        if job_id is not None:
            expressions.append(peewee.NodeList((model.id, peewee.SQL('='), job_id)))

        if job_name is not None:
            expressions.append(peewee.NodeList((model.job_name, peewee.SQL('='), job_name)))

        if len(expressions):
            query_cmd = query_cmd.where(*expressions)

        record_count = query_cmd.count()
        if page_index is None:
            record_list = query_cmd.order_by(model.c_time.desc())
        else:
            record_list = query_cmd.order_by(model.c_time.desc()).paginate(int(page_index), int(page_size))

        data_list = []
        for record in record_list:
            record_dict = shortcuts.model_to_dict(record)
            record_select_dict = {}
            record_select_dict["job_id"] = record_dict["id"]
            record_select_dict["job_name"] = record_dict["job_name"]
            record_select_dict["Job_trigger"] = record_dict["job_trigger"]
            record_select_dict["cmd"] = record_dict["job_state"]["kwargs"]["cmd"]
            record_select_dict["rule"] = record_dict["job_rule"]
            record_select_dict["next_run_time"] = record_dict["job_state"]["next_run_time"]
            data_list.append(record_select_dict)

        data["total"] = record_count
        data["list"] = data_list
        return data

    def get_jobs(self, job_id=None, job_name=None, page_index=None, page_size=10):
        """
        Returns:
            data: (dict)
                total: 总个数
                list : 数据列表
        """
        if isinstance(self._jobstore, MySQLJobStore):
            return self._get_jobs_in_mysql(job_id, job_name, page_index, page_size)
        else:
            return self._get_jobs_in_memory()

    def remove_job(self, job_id):
        """
        移除 job
        """
        is_success = True
        err_msg = "OK"
        try:
            self._scheduler.remove_job(job_id)
        except BaseException as e:
            is_success, err_msg = False, str(e)
        return (is_success, err_msg)

    def pause_job(self, job_id):
        """
        暂停 job
        """
        is_success = True
        err_msg = "OK"
        try:
            self._scheduler.pause_job(job_id)
        except BaseException as e:
            is_success, err_msg = False, str(e)
        return (is_success, err_msg)

    def resume_job(self, job_id):
        """
        继续 job
        """
        is_success = True
        err_msg = "OK"
        try:
            self._scheduler.resume_job(job_id)
        except BaseException as e:
            is_success, err_msg = False, str(e)
        return (is_success, err_msg)

scheduler = Scheduler(logger_conf.initlog, logger_conf.errlog, jobstore_alias=config.scheduler_store)
scheduler.start()

original_scheduler = scheduler._scheduler

if __name__ == "__main__":
    """
    # 使用原生 scheduler 进行添加任务, 用于启动时设置某些任务定时执行, 比如定时执行发送心跳任务
    interval_cron_dict = {}
    interval_cron_dict["seconds"] = 900
    interval_trigger = IntervalTrigger(seconds=interval_cron_dict["seconds"],)
    original_scheduler.add_job(
            func=func,
            trigger=interval_trigger,
            jobstore = "memory"
            )
    """
    import time

    cmd = "bash test_scripts.sh"

    scheduler.add_job("cron", "test_cron1", "scripts", cmd, "*/3 */4 * * * *")
    scheduler.add_job("cron", "test_cron2", "scripts", cmd, "*/3 */4 * * * *")
    scheduler.add_job("cron", "test_cron3", "scripts", cmd, "*/3 */4 * * * *")
    scheduler.add_job("interval", "test_interval1", "scripts", cmd, "10s")
    scheduler.add_job("date", "test_date1", "scripts", cmd, "now")

    for job in scheduler.get_jobs():
        print job

    # crontab.remove_job("test_name")

    while True:
        time.sleep(2)
