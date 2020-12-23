#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-12-23 13:35:16

# File Name: peewee_store.py
# Description:
    Stores jobs in a database table using Peewee.

"""
import logging
import pickle
from datetime import datetime


from xlib.apscheduler.jobstores.base import JobStore
from xlib.apscheduler.job import Job

import xlib.db
from xlib.db.peewee import CharField
from xlib.db.peewee import IntegerField
from xlib.db.peewee import BlobField
from xlib.db.peewee import BigIntegerField
from xlib.db.peewee import DateTimeField
from xlib.db.peewee import BooleanField
from xlib.db.peewee import PrimaryKeyField
from xlib.db import shortcuts

logger = logging.getLogger(__name__)

class PickleField(BlobField):

     def __init__(self, *args, **kwargs):
         super(PickleField, self).__init__(*args, **kwargs)

     def db_value(self, value):
         return pickle.dumps(value)

     def python_value(self, value):
         return pickle.loads(value)

# Define a model class
class RuqiJobs(xlib.db.BaseModel):
    """
    如期表结构
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    id = PrimaryKeyField()
    trigger = PickleField()
    func_ref = CharField(max_length=1024)
    args = PickleField()
    kwargs = PickleField()
    name =CharField(max_length=1024)
    misfire_grace_time = IntegerField()
    coalesce = BooleanField()
    max_runs = IntegerField(null=True)
    max_instances = IntegerField()
    next_run_time = DateTimeField()
    runs = BigIntegerField()
    c_time = DateTimeField(column_name="c_time", default=datetime.now)

    class Meta(object):
        table_name = 'ruqi_jobs'


class PeeweeJobStore(JobStore):
    def __init__(self):
        self.jobs = []

    def add_job(self, job):
        job_dict = job.__getstate__()
        result = RuqiJobs.create(**job_dict)
        job.id = result.id
        self.jobs.append(job)

    def remove_job(self, job):
        RuqiJobs.delete().where(RuqiJobs.id == job.id).execute()
        self.jobs.remove(job)

    def load_jobs(self):
        jobs = []
        record_list = RuqiJobs.select()
        for row in record_list:
            try:
                job = Job.__new__(Job)
                job_dict = row.__dict__
                job_dict = shortcuts.model_to_dict(row)
                job.__setstate__(job_dict)
                jobs.append(job)
            except Exception:
                job_name = job_dict.get('name', '(unknown)')
                logger.exception('Unable to restore job "%s"', job_name)
        self.jobs = jobs

    def update_job(self, job):
        job_dict = job.__getstate__()
        query = RuqiJobs.update(next_run_time=job_dict['next_run_time'], runs=job_dict['runs']).where(RuqiJobs.id == job.id)
        query.execute()

    def close(self):
        pass

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)


if __name__ == "__main__":
    xlib.db.my_database.connect()
    xlib.db.my_database.create_tables([RuqiJobs])
