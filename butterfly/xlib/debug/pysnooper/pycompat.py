# coding=utf8
"""
Python 2/3 compatibility
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.
"""

import abc
import os
import inspect
import sys
import datetime as datetime_module

PY3 = (sys.version_info[0] == 3)
PY2 = not PY3

if hasattr(abc, 'ABC'):
    ABC = abc.ABC
else:
    class ABC(object):
        """Helper class that provides a standard way to create an ABC using
        inheritance.
        """
        __metaclass__ = abc.ABCMeta
        __slots__ = ()


if hasattr(os, 'PathLike'):
    PathLike = os.PathLike
else:
    class PathLike(ABC):
        """Abstract base class for implementing the file system path protocol."""

        @abc.abstractmethod
        def _fspath_(self):
            """Return the file system path representation of the object."""
            raise NotImplementedError

        @classmethod
        def __subclasshook__(cls, subclass):
            return (
                hasattr(subclass, '_fspath_') or
                # Make a concession for older `pathlib` versions:g
                (hasattr(subclass, 'open') and
                 'path' in subclass.__name__.lower())
            )


try:
    iscoroutinefunction = inspect.iscoroutinefunction
except AttributeError:
    iscoroutinefunction = lambda whatever: False # Lolz

try:
    isasyncgenfunction = inspect.isasyncgenfunction
except AttributeError:
    isasyncgenfunction = lambda whatever: False # Lolz


if PY3:
    string_types = (str,)
    text_type = str
else:
    string_types = (basestring,)
    text_type = unicode

try:
    from collections import abc as collections_abc
except ImportError: # Python 2.7
    import collections as collections_abc

if sys.version_info[:2] >= (3, 6):
    time_isoformat = datetime_module.time.isoformat
else:
    def time_isoformat(time, timespec='microseconds'):
        """
        返回表示 ISO 8601 格式的时间的字符串
        """
        assert isinstance(time, datetime_module.time)
        if timespec != 'microseconds':
            raise NotImplementedError
        result = '{:02d}:{:02d}:{:02d}.{:06d}'.format(
            time.hour, time.minute, time.second, time.microsecond
        )
        assert len(result) == 15
        return result


def timedelta_format(timedelta):
    """
    返回 iso 时间格式
    """
    time = (datetime_module.datetime.min + timedelta).time()
    return time_isoformat(time, timespec='microseconds')


def timedelta_parse(s):
    """
    返回时间差, timedelta 格式
    """
    hours, minutes, seconds, microseconds = map(
        int,
        s.replace('.', ':').split(':')
    )
    return datetime_module.timedelta(hours=hours, minutes=minutes,
                                     seconds=seconds,
                                     microseconds=microseconds)

