# coding=utf8
from datetime import datetime
from threading import Thread
from time import sleep

import pytest

from xlib.util import retry

exception_message = 'testing exceptions'


def foo(bar):
    if bar < 0:
        raise ArithmeticError(exception_message)
    return bar


def test_success_criteria():
    """Success criteria successfully raises MaximumRetriesExceeded"""
    foo_with_success = retry.retry(success=lambda x: x > 0)(foo)
    with pytest.raises(retry.MaximumRetriesExceeded):
        foo_with_success(0)


def test_exception_criteria():
    """Exceptions specified are raised on MaximumRetriesExceeded"""
    foo_with_exception = retry.retry(exceptions=(ArithmeticError,))(foo)
    with pytest.raises(ArithmeticError) as exc_info:
        foo_with_exception(-1)
    assert exception_message in str(exc_info.value)


def test_execution():
    """Expected execution of a successful runstill works"""
    foo_with_both = retry.retry(
        exceptions=(ArithmeticError,), success=lambda x: x > 0)(foo)
    assert foo_with_both(1) == 1


def test_interval():
    """Interval expected is the interval to complete an action"""
    def _success_interval(in_dict):
        in_dict['num'] += 1
        return in_dict['num']

    baz_with_interval = retry.retry(
        success=lambda x: x > 5, interval=1)(_success_interval)
    start = datetime.now()
    baz_with_interval({'num': 0})
    elapsed = datetime.now() - start
    assert elapsed.seconds >= 5


# 设置了 exceptions 默认值，此 test 目前无效
#def test_invalid_parameters():
#    """The exceptions and success parameter can not both be None"""
#    with pytest.raises(TypeError):
#        retry.retry(exceptions=None, success=None)(foo)


def test_unsuccessful_timeout():
    """Unsuccessful functions with a timeout work"""
    foo_with_timeout = retry.retry(
        success=lambda x: x > 0, timeout=5, interval=1)(foo)
    with pytest.raises(retry.MaximumTimeoutExceeded):
        foo_with_timeout(-1)


def test_successful_timeout():
    """Success with a timeout still works"""
    def _success_timeout(in_dict):
        in_dict['num'] += 1
        return in_dict['num']

    try:
        _test_func = retry.retry(
            success=lambda x: x == 5, timeout=10, interval=1)(
                _success_timeout)
        _test_func({'num': 0})
    except retry.MaximumTimeoutExceeded:
        pytest.fail('Expected the timeout not to be exceeded')


def test_disarm_signal_on_success():
    """Success with a timeout disarms signal"""
    _test_func = retry.retry(success=lambda x: True, timeout=1, interval=0.5)(foo)
    _test_func(1)
    sleep(1.2)


def test_successful_thread():
    """Success with function as thread"""
    retryed = []

    @retry.retry(timeout=1, success=lambda x: len(x) == 3)
    def f(retryed):
        retryed.append(0)
        return retryed

    t = Thread(target=f, args=[retryed])
    t.start()
    t.join()
    assert 3 == len(retryed)


def test_unsuccessful_thread():
    """Unsuccessful with function as thread, timed out"""
    retryed = []

    def foo(retryed):
        @retry.retry(timeout=1, success=lambda x: False)
        def bar(retryed):
            sleep(0.2)
            retryed.append(0)

        with pytest.raises(retry.MaximumTimeoutExceeded):
            bar(retryed)

    t = Thread(target=foo, args=[retryed])
    t.start()
    t.join()
    assert 3 <= len(retryed) <= 5


