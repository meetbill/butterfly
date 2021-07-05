#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-06-18 17:39:32

# File Name: helloworld.py
# Description:

"""
from xlib.taskflow.taskflow import WorkflowRunner


class Hello(WorkflowRunner):
    """
    a workflow is defined by overloading the WorkflowRunner.workflow() method:
    """

    def params_check(self):
        """
        params_check, self.job_extra
        """
        if "str_info" not in self.job_extra.keys():
            raise Exception("job_extra not have str_info")

    def workflow(self):
        """
        学习点:
            (1) 参数传入
                * 普通参数:  参数的 value 会从任务依赖的 task 中获取，或者从 job_extra 中获取
                * 参数名为 all_taskdata 的参数：此时会将此任务依赖的 task 的 ret_data 放到一个列表中,
                  以 all_taskdata 传给此 task
            (2) 保存结果到 job ret_data 中
                场景：工作流的场景分为操作型和数据型，如果是操作型，我们仅仅需要知道执行结果即可
                      如果是数据型，我们需要获取整个任务的结果，此时我们可以在最后的一个任务中 设置 is_save 为 True
                      在此 task 中进行汇聚下结果，然后进行保存数据

        执行顺序:
            执行 task1, task1 需要 str_info 参数, 参数的 value 会从任务依赖的 task 中获取，或者从 job_extra 中获取
            task1 执行完成后，执行 task2
            task1 和 task2 都执行完成后，执行 task3, task3 将结果保存到 job ret_data 中
        """
        self.add_task("task1", "/demo_api/hello", requires=["str_info"])
        self.add_task("task2", "/demo_api/ping", dependencies=["task1"])
        self.add_task(
            "task3",
            "/demo_api/collect",
            requires=["all_taskdata"],
            dependencies=[
                "task1",
                "task2"],
            is_save=True)


def setup(app):
    """
    插件注册函数
    """
    app.register_formatter('hello', Hello)
