#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-06-18 17:39:32

# File Name: demo_api.py
# Description:

"""
from xlib.taskflow.taskflow import WorkflowRunner

class Ping(WorkflowRunner):
    """
    a workflow is defined by overloading the WorkflowRunner.workflow() method:
    """

    def workflow(self):
        """
        先执行 task1, 再执行 task2
        """
        self.add_task("task1", "/demo_api/ping")
        # 通过 dependencies 描述依赖关系
        self.add_task("task2", "/demo_api/ping", dependencies=["task1"])

def setup(app):
    """
    插件注册函数
    """
    app.register_formatter('ping', Ping)
