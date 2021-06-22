# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-06-18 20:52:08

# File Name: exceptions.py
# Description:

"""


class TaskWaiting(Exception):
    """
    等待下次重试
    """
    pass


class TaskError(Exception):
    """
    任务异常
    """
    pass
