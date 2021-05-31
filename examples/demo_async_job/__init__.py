#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-01-21 16:32:27

# File Name: __init__.py
# Description:

    async_job --发起异步任务，由单独线程进行处理

    1.0.1: async_job 1.0.1 版本，用于简易创建异步任务，异步任务进行执行本地 Shell/Python 脚本
"""

import os
import logging

from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr
from xlib.util import concurrent
from xlib.util import shell_util


__info = "async_job"
__version = "1.0.1"

executor = concurrent.ThreadPoolExecutor(max_workers=10)


def run_cmd(reqid, cmd):
    """
    执行本地命令
    Args:
        job_id  : (Str) job_id
        job_name: (Str) job_name
        cmd     : (Str) "python/bash file_path args"
        errlog  : (object) errlog logger
    """
    # 设置 1 小时超时
    cmd_result = shell_util.run(cmd, timeout=3600, reqid=reqid)


def _check_cmd(cmd):
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


def executor_callback(worker):
    """
    记录 worker 执行异常
    """
    logging.info("called worker callback function")
    worker_exception = worker.exception()
    if worker_exception:
        logging.exception("Worker return exception: {}".format(worker_exception))


@funcattr.api
def add_job(req, cmd):
    """
    添加任务

    cmd: (str) bash xxx.sh/python xxx.py  本地需要有此脚本
    """
    isinstance(req, Request)

    if not _check_cmd(cmd):
        return retstat.ERR, {}, [(__info, __version)]

    task = executor.submit(run_cmd, reqid=req.reqid, cmd=cmd)
    task.add_done_callback(executor_callback)

    return retstat.OK, {}, [(__info, __version)]
