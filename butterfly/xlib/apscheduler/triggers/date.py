#!/usr/bin/python
# coding=utf8
"""
# File Name: date.py
# Description:
    一次性延迟执行任务
"""
from datetime import datetime

from xlib.apscheduler.triggers.base import BaseTrigger
from xlib.apscheduler.util import convert_to_datetime, datetime_repr


class DateTrigger(BaseTrigger):
    """
    Triggers once on the given datetime. If ``run_date`` is left empty, current time is used.

    :param datetime|str run_date: the date/time to run the job at
    """

    __slots__ = 'run_date'

    def __init__(self, run_date=None):
        if run_date is not None:
            self.run_date = convert_to_datetime(run_date)
        else:
            self.run_date = datetime.now()

    def get_next_fire_time(self, previous_fire_time, now):
        """
        计算任务对象下次要运行的时间。

        Args:
            previous_fire_time: 上次运行时间
            now: 当前时间
        Returns:
            下次要运行的时间
        """
        return self.run_date if previous_fire_time is None else None

    def __getstate__(self):
        return {
            'version': 1,
            'run_date': self.run_date
        }

    def __setstate__(self, state):
        # This is for compatibility with APScheduler 3.0.x
        if isinstance(state, tuple):
            state = state[1]

        if state.get('version', 1) > 1:
            raise ValueError(
                'Got serialized data for version %s of %s, but only version 1 can be handled' %
                (state['version'], self.__class__.__name__))

        self.run_date = state['run_date']

    def __str__(self):
        return 'date[%s]' % datetime_repr(self.run_date)

    def __repr__(self):
        return "<%s (run_date='%s')>" % (self.__class__.__name__, datetime_repr(self.run_date))
