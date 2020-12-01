# -*- coding: utf-8 -*-
import calendar
import string
import random
import datetime

from .compat import xrange


def random_string(len, corpus=None):
    """
    Return random string with given len
    """
    if not corpus:
        corpus = string.ascii_letters + string.digits
    return ''.join(random.choice(corpus) for _ in xrange(len))


def expire_to_datetime(expire):
    """
    Convert datetime(), timedelta() or number of seconds to datetime object

    :param expire: the expiration mark (None, seconds, datetime or timedelta)
    :returns: datetime object, which is "naive" but considered as having UTC
              timezone
    """
    if expire is None:
        return None
    if isinstance(expire, datetime.datetime):
        return expire
    ts = utcnow()
    if isinstance(expire, datetime.timedelta):
        return ts + expire
    return ts + datetime.timedelta(seconds=expire)


def datetime_to_timestamp(dt):
    """
    Convert datetime objects to correct timestamps

    Consider naive datetimes as UTC ones
    """
    if dt is None:
        return None
    micro = dt.microsecond / 1e6
    ts = calendar.timegm(dt.timetuple())
    return ts + micro


def timestamp_to_datetime(ts):
    """
    Convert timestamps to datetime objects
    """
    if ts is None:
        return None
    if isinstance(ts, (str, bytes)):
        ts = float(ts)
    return datetime.datetime.utcfromtimestamp(ts)


def utcnow():
    # see http://www.redhotchilipython.com/en_posts/2012-07-13-double-call-hack.html
    # for explanation why this function is required
    # tl;dr: for tests
    return datetime.datetime.utcnow()


def random_true(prob):
    """
    Return True with the probability of :param:`prob`

    :param prob: float value in range [0, 1]. 0 means "never return True", 1
                 means "always return True"
    """
    return random.random() < prob
