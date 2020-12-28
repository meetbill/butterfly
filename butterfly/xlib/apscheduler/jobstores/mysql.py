#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-12-27 10:54:26

# File Name: mysql.py
# Description:
    Stores jobs in a database table using peewee.
"""
from __future__ import absolute_import

from xlib.apscheduler.jobstores.base import BaseJobStore, JobLookupError, ConflictingIdError
from xlib.apscheduler.util import datetime_to_timestamp, timestamp_to_datetime
from xlib.apscheduler.job import Job
from xlib.apscheduler.triggers import date
from xlib.apscheduler.triggers import interval
from xlib.apscheduler.triggers import cron
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
    job_state = PickleField()
    job_lock = BooleanField(default=False, index=True)
    job_name = CharField(max_length=64, index=True, null=True)
    job_rule = CharField(max_length=64, null=True)
    u_time = DateTimeField(column_name="u_time", default=datetime.datetime.now)
    c_time = DateTimeField(column_name="c_time", default=datetime.datetime.now)

    class Meta(object):
        table_name = 'ruqi_jobs'


class MySQLJobStore(BaseJobStore):
    """
    Stores jobs in a database table using peewee.
    The table will be created if it doesn't exist in the database.

    Plugin alias: ``mysql``
    """

    def __init__(self, ha=True):
        super(MySQLJobStore, self).__init__()

        # 191 = max key length in MySQL for InnoDB/utf8mb4 tables,
        # 25 = precision that translates to an 8-byte float
        self.jobs_t = RuqiJobs
        # 设置为 true 时，从 MySQL 中取任务时会进行加锁，下次取任务时会将超过 20s 的 job 进行解锁
        self.ha = ha

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
        取已经到期的 job

        Scheduler 根据此方法获取需要执行的任务
        """
        timestamp = datetime_to_timestamp(now)
        if not self.ha:
            return self._get_jobs(self.jobs_t.next_run_time <= timestamp, self.jobs_t.job_lock == False)

        # 解锁 20s 前的任务
        old_datetime = now - datetime.timedelta(seconds=20)
        old_timestamp = datetime_to_timestamp(old_datetime)
        data = {
            "job_lock": False,
            "u_time": datetime.datetime.now()
        }
        update = self.jobs_t.update(data).where(
            self.jobs_t.next_run_time <= old_timestamp,
            self.jobs_t.job_lock == True)
        result = update.execute()
        if result > 0:
            self._logger.info("[apscheduler]: Unlock expired jobs, hvae {num} job unlock".format(num=result))

        return self._get_jobs_with_lock(self.jobs_t.next_run_time <= timestamp, self.jobs_t.job_lock == False)

    def get_next_run_time(self):
        """
        获取最近的下次执行时间, 排除掉加锁的任务
        """
        row = self.jobs_t.select(self.jobs_t.next_run_time).where(
            self.jobs_t.next_run_time is not None).order_by(self.jobs_t.next_run_time).limit(1).execute()
        if len(row) == 1:
            result_dict = shortcuts.model_to_dict(row[0])
            return timestamp_to_datetime(result_dict["next_run_time"])
        else:
            return None

    def get_all_jobs(self):
        """
        获取所有任务
        """
        jobs = self._get_jobs()
        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        job_state = job.__getstate__()
        job_rule = ""
        if isinstance(job_state["trigger"], cron.CronTrigger):
            fields = job_state["trigger"].fields
            field_dict = {}
            for field in fields:
                field_dict[field.name] = str(field)
            job_rule = "{second} {minute} {hour} {day} {month} {day_of_week}".format(
                second=field_dict['second'],
                minute=field_dict['minute'],
                hour=field_dict['hour'],
                day=field_dict['day'],
                month=field_dict['month'],
                day_of_week=field_dict["day_of_week"]
            )

        if isinstance(job_state["trigger"], interval.IntervalTrigger):
            job_rule = str(job_state["trigger"].interval_length) + "s"

        if isinstance(job_state["trigger"], date.DateTrigger):
            job_rule = str(job_state["trigger"].run_date)

        values = {
            'id': job.id,
            'next_run_time': datetime_to_timestamp(job.next_run_time),
            'job_state': job_state,
            'job_name': job_state["name"],
            'job_rule': job_rule
        }
        try:
            self.jobs_t.create(**values)
        except BaseException:
            raise ConflictingIdError(job.id)

    def update_job(self, job):
        data = {
            "next_run_time": datetime_to_timestamp(job.next_run_time),
            "job_state": job.__getstate__(),
            "job_lock": False,
            "u_time": datetime.datetime.now()
        }
        update = self.jobs_t.update(data).where(self.jobs_t.id == job.id)
        result = update.execute()
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

    def _add_lock(self, job_id, next_run_time_timestamp, next_run_time_datetime):
        """
        对 job 加锁

        Args:
            job_id: (Str) job id
            next_run_time_timestamp: (Str) next_run_time 时间戳
            next_run_time_datetime: (DateTime)
        Returns:
            bool
        """
        data = {
            "job_lock": True,
            "u_time": datetime.datetime.now()
        }
        update = self.jobs_t.update(data).where(self.jobs_t.id == job_id,
                                                self.jobs_t.next_run_time == next_run_time_timestamp,
                                                self.jobs_t.job_lock == False)
        result = update.execute()
        if result == 0:
            self._logger.info(
                "[apscheduler]: id={id} run_time={run_time} add lock failed".format(
                    id=job_id, run_time=next_run_time_datetime))
            return False
        else:
            self._logger.info(
                "[apscheduler]: id={id} run_time={run_time} add lock success".format(
                    id=job_id, run_time=next_run_time_datetime))
            return True

    def _get_jobs_with_lock(self, *conditions):
        jobs = []
        query_cmd = self.jobs_t.select(
            self.jobs_t.id,
            self.jobs_t.next_run_time,
            self.jobs_t.job_state).order_by(
            self.jobs_t.next_run_time)
        selectable = query_cmd.where(*conditions) if conditions else query_cmd
        failed_job_ids = set()
        for row in selectable:
            row_dict = shortcuts.model_to_dict(row)
            # 对任务加锁
            if not self._add_lock(row_dict["id"], row_dict["next_run_time"], row_dict["job_state"]["next_run_time"]):
                continue
            try:
                jobs.append(self._reconstitute_job(row_dict["job_state"]))
            except BaseException:
                self._logger.exception('Unable to restore job "%s" -- removing it', row.id)
                failed_job_ids.add(row.id)

        # Remove all the jobs we failed to restore
        if failed_job_ids:
            delete = self.jobs_t.delete().where(self.jobs_t.id.in_(failed_job_ids))
            delete.execute()

        return jobs

    def _get_jobs(self, *conditions):
        jobs = []
        query_cmd = self.jobs_t.select(self.jobs_t.id, self.jobs_t.job_state).order_by(self.jobs_t.next_run_time)
        selectable = query_cmd.where(*conditions) if conditions else query_cmd
        failed_job_ids = set()
        for row in selectable:
            row_dict = shortcuts.model_to_dict(row)
            try:
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
