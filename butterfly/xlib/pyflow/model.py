#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2020-03-22 22:52:08

# File Name: job_model.py
# Description:

"""
from datetime import datetime

from xlib.db.peewee import CharField
from xlib.db.peewee import IntegerField
from xlib.db.peewee import DateTimeField
from xlib.db.peewee import PrimaryKeyField
from xlib.db.peewee import DoubleField
from xlib.db.peewee import TextField
import xlib.db


# Define a model class
class Job(xlib.db.BaseModel):
    """
    Job 表结构
    job_status: waiting --> started --> finished
                                |
                                V
                              failed
               同步 job 状态从 started 开始，异步 job 状态从 waiting 开始
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    job_id = PrimaryKeyField()
    job_runner = CharField(max_length=64, null=True, index=True)
    job_reqid = CharField(max_length=64, default="none", index=True)
    job_name = CharField(max_length=64, index=True)
    job_status = CharField(max_length=64, index=True, default="started")
    # 记录 workflow class name
    job_type = CharField(max_length=64, default="", index=True)
    job_retcode = IntegerField(default=0, index=True)
    job_retinfo = TextField(null=True)
    job_cost = DoubleField(null=True, index=True)
    job_extra = CharField(max_length=2048, default="{}")
    c_time = DateTimeField(column_name="c_time", default=datetime.now)
    u_time = DateTimeField(column_name="u_time", default=datetime.now)

    class Meta(object):
        """
        meta
        """
        table_name = 'xinggui_job'


# Define a model class
class Task(xlib.db.BaseModel):
    """
    Task 表结构

    task_status: waiting --> started --> finished
                                |
                                V
                              failed
    """
    # task 唯一 id, 创建时生成
    task_id = PrimaryKeyField()
    # job id, 创建时生成
    job_id = IntegerField(index=True)
    # task 的任务 cmd, 创建时生成
    task_label = CharField(max_length=64, index=True)
    task_namespace = CharField(max_length=64, default="", index=True)
    task_core_count = IntegerField(default=1, index=True)
    # mb
    task_mem = IntegerField(default=2048, index=True)
    task_priority = IntegerField(default=0, index=True)
    task_dependencies = CharField(max_length=1024, default="")
    task_cmd = CharField(max_length=128, index=True)
    task_status = CharField(max_length=64, default="waiting", index=True)
    # 耗时
    task_cost = IntegerField(default=0, index=True)
    # 额外信息
    task_extra = CharField(max_length=2048, default="{}")
    # 任务结果返回码
    ret_code = IntegerField(default=0, index=True)
    # 任务结果返回信息
    ret_info = TextField(null=True)
    # 创建时间
    c_time = DateTimeField(column_name="c_time", default=datetime.now)
    # 更新时间
    u_time = DateTimeField(column_name="u_time", default=datetime.now)

    class Meta(object):
        """
        meta
        """
        table_name = 'xinggui_task'


if __name__ == "__main__":
    xlib.db.my_databases["default"].connect()
    xlib.db.my_databases["default"].drop_tables([Job, Task])
    xlib.db.my_databases["default"].create_tables([Job, Task])
