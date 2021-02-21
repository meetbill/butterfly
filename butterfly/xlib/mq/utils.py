# -*- coding: utf-8 -*-
"""
Miscellaneous helper functions.

The formatter for ANSI colored console output is heavily based on Pygments
terminal colorizing code, originally by Georg Brandl.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import calendar
import datetime
import importlib
import numbers
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from .compat import as_text, string_types
from .exceptions import TimeoutFormatError


def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def utcnow():
    return datetime.datetime.utcnow()


_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def utcformat(dt):
    return dt.strftime(as_text(_TIMESTAMP_FORMAT))


def utcparse(string):
    try:
        return datetime.datetime.strptime(string, _TIMESTAMP_FORMAT)
    except ValueError:
        # This catches any msgs remain with old datetime format
        return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%SZ')


def first(iterable, default=None, key=None):
    """
    Return first element of `iterable` that evaluates true, else return None
    (or an optional default value).

    >>> first([0, False, None, [], (), 42])
    42

    >>> first([0, False, None, [], ()]) is None
    True

    >>> first([0, False, None, [], ()], default='ohai')
    'ohai'

    >>> import re
    >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
    >>> m.group(1)
    'bc'

    The optional `key` argument specifies a one-argument predicate function
    like that used for `filter()`.  The `key` argument, if supplied, must be
    in keyword form.  For example:

    >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
    4

    """
    if key is None:
        for el in iterable:
            if el:
                return el
    else:
        for el in iterable:
            if key(el):
                return el

    return default


def is_nonstring_iterable(obj):
    """Returns whether the obj is an iterable, but not a string"""
    return isinstance(obj, Iterable) and not isinstance(obj, string_types)


def ensure_list(obj):
    """
    When passed an iterable of objects, does nothing, otherwise, it returns
    a list with just that object in it.
    """
    return obj if is_nonstring_iterable(obj) else [obj]


def current_timestamp():
    """Returns current UTC timestamp"""
    return calendar.timegm(datetime.datetime.utcnow().utctimetuple())


def enum(name, *sequential, **named):
    values = dict(zip(sequential, range(len(sequential))), **named)

    # NOTE: Yes, we *really* want to cast using str() here.
    # On Python 2 type() requires a byte string (which is str() on Python 2).
    # On Python 3 it does not matter, so we'll use str(), which acts as
    # a no-op.
    return type(str(name), (), values)


def backend_class(holder, default_name, override=None):
    """Get a backend class using its default attribute name or an override"""
    if override is None:
        return getattr(holder, default_name)
    elif isinstance(override, string_types):
        return import_attribute(override)
    else:
        return override


def str_to_date(date_str):
    if date_str is None:
        return
    else:
        return utcparse(as_text(date_str))


def parse_timeout(timeout):
    """Transfer all kinds of timeout format to an integer representing seconds"""
    if not isinstance(timeout, numbers.Integral) and timeout is not None:
        try:
            timeout = int(timeout)
        except ValueError:
            digit, unit = timeout[:-1], (timeout[-1:]).lower()
            unit_second = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
            try:
                timeout = int(digit) * unit_second[unit]
            except (ValueError, KeyError):
                raise TimeoutFormatError('Timeout must be an integer or a string representing an integer, or '
                                         'a string with format: digits + unit, unit can be "d", "h", "m", "s", '
                                         'such as "1h", "23m".')

    return timeout
