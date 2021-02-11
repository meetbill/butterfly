#!/usr/bin/python
# coding=utf8
"""
# File Name: date.py
# Description:
    基于间隔的执行
"""
from datetime import timedelta, datetime
from math import ceil

from xlib.apscheduler.triggers.base import BaseTrigger
from xlib.apscheduler.util import convert_to_datetime, timedelta_seconds, datetime_repr


class IntervalTrigger(BaseTrigger):
    """
    Triggers on specified intervals, starting on ``start_date`` if specified, ``datetime.now()`` +
    interval otherwise.

    :param int weeks: number of weeks to wait
    :param int days: number of days to wait
    :param int hours: number of hours to wait
    :param int minutes: number of minutes to wait
    :param int seconds: number of seconds to wait
    :param datetime|str start_date: starting point for the interval calculation
    :param datetime|str end_date: latest possible date/time to trigger on
    :param int|None jitter: advance or delay the job execution by ``jitter`` seconds at most.
    """

    __slots__ = 'start_date', 'end_date', 'interval', 'interval_length', 'jitter'

    def __init__(self, weeks=0, days=0, hours=0, minutes=0, seconds=0, start_date=None,
                 end_date=None, jitter=None):
        self.interval = timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes,
                                  seconds=seconds)
        self.interval_length = timedelta_seconds(self.interval)
        if self.interval_length == 0:
            self.interval = timedelta(seconds=1)
            self.interval_length = 1

        start_date = start_date or (datetime.now() + self.interval)
        self.start_date = convert_to_datetime(start_date)
        self.end_date = convert_to_datetime(end_date)

        self.jitter = jitter

    def get_next_fire_time(self, previous_fire_time, now):
        """
        计算任务对象下次要运行的时间。

        Args:
            previous_fire_time: 上次运行时间
            now: 当前时间
        Returns:
            下次要运行的时间
        """
        if previous_fire_time:
            next_fire_time = previous_fire_time + self.interval
        elif self.start_date > now:
            next_fire_time = self.start_date
        else:
            timediff_seconds = timedelta_seconds(now - self.start_date)
            next_interval_num = int(ceil(timediff_seconds / self.interval_length))
            next_fire_time = self.start_date + self.interval * next_interval_num

        if self.jitter is not None:
            next_fire_time = self._apply_jitter(next_fire_time, self.jitter, now)

        if not self.end_date or next_fire_time <= self.end_date:
            return next_fire_time

    def __getstate__(self):
        return {
            'version': 2,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'interval': self.interval,
            'jitter': self.jitter,
        }

    def __setstate__(self, state):
        # This is for compatibility with APScheduler 3.0.x
        if isinstance(state, tuple):
            state = state[1]

        if state.get('version', 1) > 2:
            raise ValueError(
                'Got serialized data for version %s of %s, but only versions up to 2 can be '
                'handled' % (state['version'], self.__class__.__name__))

        self.start_date = state['start_date']
        self.end_date = state['end_date']
        self.interval = state['interval']
        self.interval_length = timedelta_seconds(self.interval)
        self.jitter = state.get('jitter')

    def __str__(self):
        return 'interval[%s]' % str(self.interval)

    def __repr__(self):
        options = ['interval=%r' % self.interval, 'start_date=%r' % datetime_repr(self.start_date)]
        if self.end_date:
            options.append("end_date=%r" % datetime_repr(self.end_date))
        if self.jitter:
            options.append('jitter=%s' % self.jitter)

        return "<%s (%s)>" % (
            self.__class__.__name__, ', '.join(options))
