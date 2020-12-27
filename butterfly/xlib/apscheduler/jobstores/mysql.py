#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-12-27 10:54:26

# File Name: mysql.py
# Description:

"""
from __future__ import absolute_import

from xlib.apscheduler.jobstores.base import BaseJobStore, JobLookupError, ConflictingIdError
from xlib.apscheduler.util import datetime_to_timestamp, timestamp_to_datetime
from xlib.apscheduler.job import Job
from datetime import datetime

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle


import xlib.db
from xlib.db.peewee import DoubleField
from xlib.db.peewee import BlobField
from xlib.db.peewee import CharField
from xlib.db.peewee import DateTimeField
from xlib.db import shortcuts

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
    id = CharField(primary_key=True)
    next_run_time = DoubleField(index=True)
    job_state=PickleField()
    u_time = DateTimeField(column_name="u_time", default=datetime.now)
    c_time = DateTimeField(column_name="c_time", default=datetime.now)

    class Meta(object):
        table_name = 'ruqi_jobs'

class MySQLJobStore(BaseJobStore):
    """
    Stores jobs in a database table using peewee.
    The table will be created if it doesn't exist in the database.

    Plugin alias: ``mysql``
    """

    def __init__(self):
        super(MySQLJobStore, self).__init__()

        # 191 = max key length in MySQL for InnoDB/utf8mb4 tables,
        # 25 = precision that translates to an 8-byte float
        self.jobs_t = RuqiJobs

    def start(self, scheduler, alias):
        """
        The table will be created if it doesn't exist in the database.
        """
        super(MySQLJobStore, self).start(scheduler, alias)
        xlib.db.my_database.create_tables([self.jobs_t])

    def lookup_job(self, job_id):
        """
        根据 job_id 查询 job
        """
        row = self.jobs_t.select(self.jobs_t.job_state).where(self.jobs_t.id == job_id).get()
        row_dict = shortcuts.model_to_dict(row)
        return self._reconstitute_job(row_dict["job_state"]) if row_dict["job_state"] else None

    def get_due_jobs(self, now):
        """
        获取已经到期的 job

        Scheduler 根据此方法获取需要执行的任务
        """
        timestamp = datetime_to_timestamp(now)
        return self._get_jobs(self.jobs_t.next_run_time <= timestamp)

    def get_next_run_time(self):
        """
        获取最近的下次执行时间
        """
        row = self.jobs_t.select(self.jobs_t.next_run_time).where(self.jobs_t.next_run_time != None).order_by(self.jobs_t.next_run_time).limit(1).execute()
        if len(row) == 1:
            result_dict = shortcuts.model_to_dict(row[0])
            return timestamp_to_datetime(result_dict["next_run_time"])
        else:
            return None

    def get_all_jobs(self):
        jobs = self._get_jobs()
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        values = {
            'id': job.id,
            'next_run_time': datetime_to_timestamp(job.next_run_time),
            'job_state': job.__getstate__()
            }
        self._logger.info(str(values))
        try:
            self.jobs_t.create(**values)
        except:
            raise ConflictingIdError(job.id)

    def update_job(self, job):
        data = {
                    "next_run_time": datetime_to_timestamp(job.next_run_time),
                    "job_state": job.__getstate__(),
                    "u_time": datetime.now()
                }
        update = self.jobs_t.update(data).where(self.jobs_t.id == job.id)
        result = update.execute()
        self._logger.info(str(data))
        if result == 0:
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        delete = self.jobs_t.delete().where(self.jobs_t.id == job_id)
        result = delete.execute()
        if result == 0:
            raise JobLookupError(job_id)

    def remove_all_jobs(self):
        delete = self.jobs_t.delete()
        delete.execute()

    def shutdown(self):
        pass

    def _reconstitute_job(self, job_state):
        job_state['jobstore'] = self
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, *conditions):
        jobs = []
        query_cmd = self.jobs_t.select(self.jobs_t.id, self.jobs_t.job_state).order_by(self.jobs_t.next_run_time)
        selectable = query_cmd.where(*conditions) if conditions else query_cmd
        failed_job_ids = set()
        for row in selectable:
            try:
                row_dict = shortcuts.model_to_dict(row)
                jobs.append(self._reconstitute_job(row_dict["job_state"]))
            except BaseException:
                self._logger.exception('Unable to restore job "%s" -- removing it', row.id)
                failed_job_ids.add(row.id)

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            delete = self.jobs_t.delete().where(self.jobs_t.id.in_(failed_job_ids))
            delete.execute()

        return jobs

    def __repr__(self):
        return '<%s (url=%s)>' % (self.__class__.__name__, self.engine.url)
