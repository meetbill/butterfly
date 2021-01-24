#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-12-27 10:54:26

# File Name: apscheduler_model.py
# Description:
    Stores jobs in a database table using peewee.
"""
from __future__ import absolute_import

import datetime

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle


import xlib.db
from xlib.db.peewee import DoubleField
from xlib.db.peewee import BlobField
from xlib.db.peewee import CharField
from xlib.db.peewee import DateTimeField
from xlib.db.peewee import BooleanField


class PickleField(BlobField):
    """
    PickleField
    """

    def __init__(self, *args, **kwargs):
        super(PickleField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        """
        save value to db
        """
        return pickle.dumps(value)

    def python_value(self, value):
        """
        get value from db
        """
        return pickle.loads(value)

# Define a model class


class RuqiJobs(xlib.db.BaseModel):
    """
    如期表结构
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    id = CharField(primary_key=True)
    # 通过设置 null 来标记此 job 为暂停中任务
    next_run_time = DoubleField(index=True, null=True)
    job_state = PickleField()
    job_lock = BooleanField(default=False, index=True)
    job_name = CharField(max_length=64, index=True, null=True)
    job_trigger = CharField(max_length=16, null=True)
    job_rule = CharField(max_length=64, null=True)
    u_time = DateTimeField(column_name="u_time", default=datetime.datetime.now)
    c_time = DateTimeField(column_name="c_time", default=datetime.datetime.now)

    class Meta(object):
        """
        RuqiJobs meta
        """
        table_name = 'ruqi_jobs'


class RuqiJobsHistory(xlib.db.BaseModel):
    """
    如期操作历史表
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    job_id = CharField(index=True)
    job_name = CharField(index=True)
    cmd = CharField(max_length=64)
    cmd_is_success=BooleanField(default=False, index=True)
    cmd_output = CharField(max_length=4096)
    cmd_cost = DoubleField(index=True)
    scheduler_name = CharField(max_length=64)
    c_time = DateTimeField(column_name="c_time", default=datetime.datetime.now)

    class Meta(object):
        """
        RuqiJobsHistory meta
        """
        table_name = 'ruqi_jobs_history'
