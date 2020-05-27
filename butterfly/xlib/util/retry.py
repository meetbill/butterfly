#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-04-13 09:46:41

# File Name: retry.py
# Description: A simple python module to add a retry function decorator

可以根据以下条件触发重试：
    成功条件（例如状态码不等于200）
    异常（例如引发 request.RequestException）

被装饰函数可能基于以下原因而执行失败：
    超过最大重试次数
    达到最大超时

被装饰函数可以按特定间隔进行下次重试

base: https://github.com/seemethere/retry.it
"""
import functools
import itertools
import logging
import time

from decorator import decorator


class _DummyException(Exception):
    pass


class MaximumRetriesExceeded(Exception):
    """
    重试次数用完，返回的异常
    """
    pass


class MaximumTimeoutExceeded(Exception):
    """
    执行耗时超时返回的异常
    """
    pass


def retry(exceptions=(Exception,), interval=0, max_retries=10, success=None, timeout=-1):
    """Decorator to retry a function 'max_retries' amount of times

    :param tuple exceptions: Exceptions to be caught for retries
    :param int interval: Interval between retries in seconds
    :param int max_retries: Maximum number of retries to have, if
        set to -1 the decorator will loop forever
    :param function success: Function to indicate success criteria
    :param int timeout: Timeout interval in seconds, if -1 will retry forever
    :raises MaximumRetriesExceeded: Maximum number of retries hit without reaching the success criteria
    :raises TypeError: Both exceptions and success were left None causing the
        decorator to have no valid exit criteria.

    Example:
        Use it to decorate a function!

        .. sourcecode:: python

            from retry import retry

            @retry(exceptions=(ArithmeticError,), success=lambda x: x > 0)
            def foo(bar):
                if bar < 0:
                    raise ArithmeticError('testing this')
                return bar

            foo(5)
            # Should return 5
            foo(-1)
            # Should raise ArithmeticError
            foo(0)
            # Should raise MaximumRetriesExceeded
    """
    if not exceptions and success is None:
        raise TypeError('`exceptions` and `success` parameter can not both be None')

    # For python 3 compatability
    exceptions = exceptions or (_DummyException,)
    _retries_error_msg = '[retry] Exceeded maximum number of retries {} at an interval of {}s for function {}'
    _timeout_error_msg = '[retry] Maximum timeout of {}s reached for function {}'

    @decorator
    def wrapper(func, *args, **kwargs):
        run_func = functools.partial(func, *args, **kwargs)
        logger = logging.getLogger(func.__module__)

        if max_retries < 0:
            iterator = itertools.count()
        else:
            iterator = range(max_retries)

        t_beginning = time.time()

        for num, _ in enumerate(iterator, 1):
            try:
                result = run_func()
                if success is None or success(result):
                    return result

            except exceptions:
                logger.exception('[retry] Exception experienced when trying function {}'.format(func.__name__))

                # 所装饰函数体中有返回异常，且执行次数达到上限，进行返回异常
                if num == max_retries:
                    raise

            logger.warning('[retry] Retrying {} in {}s...'.format(func.__name__, interval))
            seconds_passed = time.time() - t_beginning

            if timeout > 0 and seconds_passed > timeout:
                # 若配置了 timeout，且所装饰函数执行时间超过了 timeout，则返回 MaximumTimeoutExceeded 异常
                raise MaximumTimeoutExceeded(_timeout_error_msg.format(timeout, func.__name__))
            else:
                time.sleep(interval)

        # 循环次数用完, 所装饰函数本身没有返回异常，但返回结果不符合预期，返回 MaximumRetriesExceeded 异常
        raise MaximumRetriesExceeded(_retries_error_msg.format(max_retries, interval, func.__name__))
    return wrapper
