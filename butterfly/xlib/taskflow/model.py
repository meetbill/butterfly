#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-03-22 22:52:08

# File Name: job_model.py
# Description:

"""
from datetime import datetime

from xlib.db.peewee import CharField
from xlib.db.peewee import IntegerField
from xlib.db.peewee import DateTimeField
from xlib.db.peewee import BigAutoField
from xlib.db.peewee import BigIntegerField
from xlib.db.peewee import DoubleField
from xlib.db.peewee import TextField
from xlib.db.peewee import BooleanField
import xlib.db


# Define a model class
class Job(xlib.db.BaseModel):
    """
    Job 表结构
    job_status: started --> finished
                    |
                    V
                  failed
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    job_id = BigAutoField(primary_key=True)
    job_namespace = CharField(max_length=64, default="", index=True)
    job_reqid = CharField(max_length=64, default="none", index=True)
    job_name = CharField(max_length=64, unique=True)
    job_status = CharField(max_length=64, index=True, default="started")
    # 记录 workflow class name
    job_type = CharField(max_length=64, default="", index=True)
    ret_stat = CharField(max_length=64, index=True, default="OK")
    ret_data = TextField(null=True)
    job_cost = DoubleField(default=0, index=True)
    job_extra = CharField(max_length=2048, default="{}")
    # job超时(s)
    job_timeout = IntegerField(default=0)
    # operator user
    operator = CharField(max_length=64, default="", index=True)
    # 是否有效
    is_valid = BooleanField(default=False, index=True)
    # create time
    c_time = DateTimeField(column_name="c_time", default=datetime.now)
    # start time
    s_time = DateTimeField(column_name="s_time", default=datetime.now)
    # end time
    e_time = DateTimeField(column_name="e_time", default=datetime.now)

    class Meta(object):
        """
        meta
        """
        table_name = 'workflow_job'


# Define a model class
class Task(xlib.db.BaseModel):
    """
    Task 表结构

    task_status: waiting --> pending --> started --> finished
                    |           |           |
                    |           |           V
                    +-----------+-------->failed
    """
    # task 唯一 id, 创建时生成
    task_id = BigAutoField(primary_key=True)
    # job id, 创建时生成
    job_id = BigIntegerField(index=True)
    # task 的任务 label, 创建时生成
    task_label = CharField(max_length=64, index=True)
    # task 的 reqid
    task_reqid = CharField(max_length=64, default="", index=True)
    # 请求的 handler
    task_cmd = CharField(max_length=128, index=True)
    # 参数
    task_params = CharField(max_length=1024, null=True)
    # 参数: 即 arg1,arg2
    task_requires = CharField(max_length=1024, default="")
    # 结果: 即 result1,result2
    task_provides = CharField(max_length=1024, default="")
    # 依赖: 即 label1,label2
    task_dependencies = CharField(max_length=1024, default="")
    # 状态
    task_status = CharField(max_length=64, default="waiting", index=True)
    # 耗时
    task_cost = DoubleField(default=0, index=True)
    # 额外信息
    task_extra = CharField(max_length=2048, default="{}")
    # 是否保存数据到 job 中
    task_is_save = BooleanField(default=False)
    # 任务结果返回码
    ret_stat = CharField(max_length=64, default="OK", index=True)
    # 任务结果返回信息
    ret_data = TextField(null=True)
    # 最多重试次数
    task_retrymax = IntegerField(default=0)
    # 重试次数
    task_retrycount = IntegerField(default=0)
    # 任务超时(s)
    task_timeout = IntegerField(default=0)
    # 创建时间
    c_time = DateTimeField(column_name="c_time", default=datetime.now)
    # 更新时间
    u_time = DateTimeField(column_name="u_time", default=datetime.now)

    class Meta(object):
        """
        meta
        """
        table_name = 'workflow_task'


if __name__ == "__main__":
    xlib.db.my_databases["default"].connect()
    xlib.db.my_databases["default"].drop_tables([Job, Task])
    xlib.db.my_databases["default"].create_tables([Job, Task])
