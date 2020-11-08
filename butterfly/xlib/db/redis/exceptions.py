# coding=utf8
"""
# File Name: exceptions.py
# Description:
    Core exceptions raised by the Redis client
"""


class RedisError(Exception):
    """
    Redis 异常基类
    """
    pass


class ConnectionError(RedisError):
    """
    连接异常
    """
    pass


class TimeoutError(RedisError):
    """
    超时异常
    """
    pass


class AuthenticationError(ConnectionError):
    """
    认证异常
    """
    pass


class BusyLoadingError(ConnectionError):
    """
    繁忙异常
    """
    pass


class InvalidResponse(RedisError):
    """
    无效异常
    """
    pass


class ResponseError(RedisError):
    """
    响应异常
    """
    pass


class DataError(RedisError):
    """
    数据异常
    """
    pass


class PubSubError(RedisError):
    """
    发布订阅异常
    """
    pass


class WatchError(RedisError):
    """
    Watch 异常
    """
    pass


class NoScriptError(ResponseError):
    """
    脚本异常
    """
    pass


class ExecAbortError(ResponseError):
    """
    执行异常
    """
    pass


class ReadOnlyError(ResponseError):
    """
    只读异常
    """
    pass


class NoPermissionError(ResponseError):
    """
    无权限异常
    """
    pass


class LockError(RedisError, ValueError):
    """
    Errors acquiring or releasing a lock
    # NOTE: For backwards compatability, this class derives from ValueError.
    # This was originally chosen to behave like threading.Lock.
    """
    pass


class LockNotOwnedError(LockError):
    """
    Error trying to extend or release a lock that is (no longer) owned
    """
    pass


class ChildDeadlockedError(Exception):
    """
    Error indicating that a child process is deadlocked after a fork()
    """
    pass


class AuthenticationWrongNumberOfArgsError(ResponseError):
    """
    An error to indicate that the wrong number of args
    were sent to the AUTH command
    """
    pass
