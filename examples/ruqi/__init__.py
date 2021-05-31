# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-01-08 11:42:53

# File Name: ruqi.py
# Description:
    如期而至，定时执行
    用于管理定时任务, 需要在配置文件中开启定时任务

# Version
    1.0.1: 2021-01-08
    1.0.2: 2021-04-12
        增加修改任务接口
    1.0.3: 2021-04-14
        增加 get_job 接口, 用于获取 job 详情
"""

from xlib.middleware import funcattr
from xlib.httpgateway import Request
from xlib import retstat
from xlib.apscheduler.models.apscheduler_model import RuqiJobsHistory
from xlib.db import peewee
from xlib.db import shortcuts
from xlib.apscheduler import manager

__info = "ruqi"
__version = "1.0.3"


@funcattr.api
def get_jobs(req, job_id=None, job_name=None, page_index=None, page_size=15):
    """
    获取定期任务列表
    """
    isinstance(req, Request)
    jobs_result = {}
    jobs = manager.scheduler.get_jobs(job_id, job_name, page_index, page_size)
    jobs_result["data"] = jobs
    return retstat.OK, jobs_result, [(__info, __version)]


@funcattr.api
def get_job(req, job_id):
    """
    获取定期任务详情

    Args:
        job_id: (String) job_id
    Returns:
        job_info
        {
            "job_id"        : "xxx",
            "job_name"      : "xxx",
            "job_trigger"   : "cron/interval/date",
            "cmd"           : "xxx",
            "rule"          : "xxx",
            "nexttime"      : "xxx"
        }
    备注:
        使用 test_handler.py 时，因为 test_handler.py 未启动 scheduler，故直接返回 None
    """
    isinstance(req, Request)
    is_success, job_info = manager.scheduler.get_job(job_id)
    if is_success:
        return retstat.OK, {"data": job_info}, [(__info, __version)]
    else:
        req.error_str = job_info
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def add_job(req, job_trigger, job_id, job_name, cmd, rule):
    """
    添加定时任务

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
        status, content, headers
    """
    isinstance(req, Request)
    is_success, err_msg = manager.scheduler.add_job(job_trigger, job_id, job_name, cmd, rule)
    if is_success:
        return retstat.OK, {}, [(__info, __version)]
    else:
        req.error_str = err_msg
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def modify_job(req, job_trigger, job_id, job_name, cmd, rule):
    """
    添加定时任务

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
        status, content, headers
    """
    isinstance(req, Request)
    is_success, err_msg = manager.scheduler.modify_job(job_trigger, job_id, job_name, cmd, rule)
    if is_success:
        return retstat.OK, {}, [(__info, __version)]
    else:
        req.error_str = err_msg
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def remove_job(req, job_id):
    """
    删除定时任务

    Args:
        name: (str) job name
    Returns:
        status, content, headers
    """
    isinstance(req, Request)
    is_success, err_msg = manager.scheduler.remove_job(job_id)
    if is_success:
        return retstat.OK, {}, [(__info, __version)]
    else:
        req.error_str = err_msg
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def pause_job(req, job_id):
    """
    暂停定时任务

    Args:
        name: (str) job name
    Returns:
        status, content, headers
    """
    isinstance(req, Request)
    is_success, err_msg = manager.scheduler.pause_job(job_id)
    if is_success:
        return retstat.OK, {}, [(__info, __version)]
    else:
        req.error_str = err_msg
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def resume_job(req, job_id):
    """
    继续定时任务

    Args:
        name: (str) job name
    Returns:
        status, content, headers
    """
    isinstance(req, Request)
    is_success, err_msg = manager.scheduler.resume_job(job_id)
    if is_success:
        return retstat.OK, {}, [(__info, __version)]
    else:
        req.error_str = err_msg
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def get_history(req, job_id=None, job_name=None, page_index=None, page_size=15):
    """
    获取定期任务列表
    """
    data = {}
    # 如下方式以分页数据返回
    model = RuqiJobsHistory
    query_cmd = model.select()
    expressions = []
    if job_id is not None:
        expressions.append(peewee.NodeList((model.job_id, peewee.SQL('='), job_id)))

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
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def status(req):
    """
    获取 status 状态

    Args:
    Returns:
        status, content, headers
    """
    isinstance(req, Request)
    data = manager.scheduler.status()
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def wakeup(req):
    """
    获取 status 状态

    Args:
    Returns:
        status, content, headers
    """
    isinstance(req, Request)
    manager.scheduler.wakeup()
    return retstat.OK, {}, [(__info, __version)]
