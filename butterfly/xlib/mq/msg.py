# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import zlib
import socket
from functools import partial
from uuid import uuid4

from xlib.mq.compat import as_text, decode_redis_hash, string_types, text_type
from xlib.mq.exceptions import NoSuchMsgError, UnpickleError
from xlib.mq.utils import (enum, parse_timeout, str_to_date, utcformat, utcnow)
from xlib.mq import defaults
from xlib.util import host_util

try:
    import cPickle as pickle
except ImportError:  # noqa  # pragma: no cover
    import pickle

# Serialize pickle dumps using the highest pickle protocol (binary, default
# uses ascii)
dumps = partial(pickle.dumps, protocol=pickle.HIGHEST_PROTOCOL)
loads = pickle.loads

MsgStatus = enum(
    'MsgStatus',
    QUEUED='queued',
    FINISHED='finished',
    FAILED='failed',
    STARTED='started',
)

# Sentinel value to mark that some of our lazily evaluated properties have not
# yet been evaluated.
UNEVALUATED = object()


def unpickle(pickled_string):
    """Unpickles a string, but raises a unified UnpickleError in case anything
    fails.

    This is a helper method to not have to deal with the fact that `loads()`
    potentially raises many types of exceptions (e.g. AttributeError,
    IndexError, TypeError, KeyError, etc.)
    """
    try:
        obj = loads(pickled_string)
    except Exception as e:
        raise UnpickleError('Could not unpickle', pickled_string, e)
    return obj


def cancel_msg(msg_id, connection=None):
    """Cancels the msg with the given msg ID, preventing execution.  Discards
    any msg info (i.e. it can't be requeued later).
    """
    Msg.fetch(msg_id, connection=connection).cancel()


def requeue_msg(msg_id, connection):
    msg = Msg.fetch(msg_id, connection=connection)
    return msg.requeue()


class Msg(object):
    """A Msg is just a convenient datastructure to pass around msg (meta) data.
    """
    redis_msg_namespace_prefix = defaults.REDIS_MSG_NAMESPACE_PREFIX

    # Msg construction
    @classmethod
    def create(cls, data, connection=None,
               result_ttl=None, ttl=None, status=None, description=None,
               timeout=None, id=None, origin=None, meta=None,
               failure_ttl=None):
        """Creates a new Msg instance for the given function, arguments, and
        keyword arguments.
        """

        msg = cls(connection=connection)
        if id is not None:
            msg.set_id(id)

        if origin is not None:
            msg.origin = origin

        msg.data = data

        # Extra meta data
        msg.description = description
        msg.result_ttl = parse_timeout(result_ttl)
        msg.failure_ttl = parse_timeout(failure_ttl)
        msg.ttl = parse_timeout(ttl)
        msg.timeout = parse_timeout(timeout)
        msg._status = status
        msg.meta = meta or {}
        return msg

    def get_status(self, refresh=True):
        if refresh:
            self._status = as_text(self.connection.hget(self.key, 'status'))

        return self._status

    def set_status(self, status, save=True):
        self._status = status
        if save:
            self.connection.hset(self.key, 'status', self._status)

    def set_handle_worker(self, worker_name):
        """
        set handle_worker
        """
        self.handle_worker = worker_name
        self.connection.hset(self.key, 'handle_worker', self.handle_worker)

    def set_cost(self, cost):
        """
        set cost
        """
        self.cost = cost
        self.connection.hset(self.key, 'cost', self.cost)

    @property
    def is_finished(self):
        return self.get_status() == MsgStatus.FINISHED

    @property
    def is_queued(self):
        return self.get_status() == MsgStatus.QUEUED

    @property
    def is_failed(self):
        return self.get_status() == MsgStatus.FAILED

    @property
    def is_started(self):
        return self.get_status() == MsgStatus.STARTED

    @classmethod
    def exists(cls, msg_id, connection=None):
        """Returns whether a msg hash exists for the given msg ID."""
        conn = connection
        return conn.exists(cls.key_for(msg_id))

    @classmethod
    def fetch(cls, id, connection=None):
        """Fetches a persisted msg from its corresponding Redis key and
        instantiates it.
        """
        msg = cls(id, connection=connection)
        msg.refresh()
        return msg

    def __init__(self, id=None, connection=None):
        self.connection = connection
        self._id = id
        self.created_at = utcnow()
        self.data = UNEVALUATED
        self._func_name = UNEVALUATED
        self.description = None
        self.origin = None
        self.enqueued_at = None
        self.started_at = None
        self.ended_at = None
        self._result = None
        self.exc_info = None
        # 指定 msg 的最大运行时间
        self.timeout = None
        # 指定成功的 msg 及其结果保留的时间（以秒为单位）。过期的作业将被自动删除。默认为 500 秒。
        self.result_ttl = None
        # 指定失败的 msg 保留多长时间（以秒为单位）（默认为1年）
        self.failure_ttl = None
        # 指定作业被丢弃之前的最长排队时间（以秒为单位）。此参数默认为 None（无限 TTL）
        self.ttl = None
        self._status = None
        self.meta = {}
        # --------------------------------custom
        hostname = socket.gethostname()
        self.ip = host_util.get_ip_by_host(hostname)
        self.handle_worker = ""
        self.cost = "0"

    def __repr__(self):  # noqa  # pragma: no cover
        return '{0}({1!r}, enqueued_at={2!r})'.format(self.__class__.__name__,
                                                      self._id,
                                                      self.enqueued_at)

    def __str__(self):
        return '<{0} {1}: {2}>'.format(self.__class__.__name__,
                                       self.id,
                                       self.description)

    # Msg equality
    def __eq__(self, other):  # noqa
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self):  # pragma: no cover
        return hash(self.id)

    # Data access
    def get_id(self):  # noqa
        """The msg ID for this msg instance. Generates an ID lazily the
        first time the ID is requested.
        """
        if self._id is None:
            self._id = text_type(uuid4())
        return self._id

    def set_id(self, value):
        """Sets a msg ID for the given msg."""
        if not isinstance(value, string_types):
            raise TypeError('id must be a string, not {0}'.format(type(value)))
        self._id = value

    id = property(get_id, set_id)

    @classmethod
    def key_for(cls, msg_id):
        """The Redis key that is used to store msg hash under."""
        return (cls.redis_msg_namespace_prefix + msg_id).encode('utf-8')

    @property
    def key(self):
        """The Redis key that is used to store msg hash under."""
        return self.key_for(self.id)

    @property
    def result(self):
        """Returns the return value of the msg.

        Initially, right after enqueueing a msg, the return value will be
        None.  But when the msg has been executed, and had a return value or
        exception, this will return that value or exception.

        Note that, when the msg has no return value (i.e. returns None), the
        ReadOnlyMsg object is useless, as the result won't be written back to
        Redis.

        Also note that you cannot draw the conclusion that a msg has _not_
        been executed when its return value is None, since return values
        written back to Redis will expire after a given amount of time (500
        seconds by default).
        """
        if self._result is None:
            rv = self.connection.hget(self.key, 'result')
            if rv is not None:
                # cache the result
                self._result = loads(rv)
        return self._result

    """Backwards-compatibility accessor property `return_value`."""
    return_value = result

    def restore(self, raw_data):
        """Overwrite properties with the provided values stored in Redis"""
        obj = decode_redis_hash(raw_data)
        self.data = obj['data']
        self.created_at = str_to_date(obj.get('created_at'))
        self.origin = as_text(obj.get('origin'))
        self.description = as_text(obj.get('description'))
        self.enqueued_at = str_to_date(obj.get('enqueued_at'))
        self.started_at = str_to_date(obj.get('started_at'))
        self.ended_at = str_to_date(obj.get('ended_at'))
        result = obj.get('result')
        if result:
            try:
                self._result = unpickle(obj.get('result'))
            except UnpickleError:
                self._result = 'Unpickleable return value'
        self.timeout = parse_timeout(obj.get('timeout')) if obj.get('timeout') else None
        self.result_ttl = int(obj.get('result_ttl')) if obj.get('result_ttl') else None  # noqa
        self.failure_ttl = int(obj.get('failure_ttl')) if obj.get('failure_ttl') else None  # noqa
        self._status = as_text(obj.get('status')) if obj.get('status') else None
        self.ttl = int(obj.get('ttl')) if obj.get('ttl') else None
        self.meta = unpickle(obj.get('meta')) if obj.get('meta') else {}
        self.handle_worker = as_text(obj.get('handle_worker'))
        self.cost = as_text(obj.get('cost'))

        raw_exc_info = obj.get('exc_info')
        if raw_exc_info:
            try:
                self.exc_info = as_text(zlib.decompress(raw_exc_info))
            except zlib.error:
                # Fallback to uncompressed string
                self.exc_info = as_text(raw_exc_info)

    # Persistence
    def refresh(self):  # noqa
        """Overwrite the current instance's properties with the values in the
        corresponding Redis key.

        Will raise a NoSuchMsgError if no corresponding Redis key exists.
        """
        data = self.connection.hgetall(self.key)
        if not data:
            raise NoSuchMsgError('No such msg: {0}'.format(self.key))
        self.restore(data)

    def to_dict(self, include_meta=True):
        """
        Returns a serialization of the current msg instance

        You can exclude serializing the `meta` dictionary by setting
        `include_meta=False`.

        Used to store to redis.
        """
        obj = {}
        obj['created_at'] = utcformat(self.created_at or utcnow())
        obj['data'] = self.data

        if self.origin is not None:
            obj['origin'] = self.origin
        if self.description is not None:
            obj['description'] = self.description
        if self.enqueued_at is not None:
            obj['enqueued_at'] = utcformat(self.enqueued_at)
        if self.started_at is not None:
            obj['started_at'] = utcformat(self.started_at)
        if self.ended_at is not None:
            obj['ended_at'] = utcformat(self.ended_at)
        if self._result is not None:
            try:
                obj['result'] = dumps(self._result)
            except BaseException:
                obj['result'] = 'Unpickleable return value'
        if self.exc_info is not None:
            obj['exc_info'] = zlib.compress(str(self.exc_info).encode('utf-8'))
        if self.timeout is not None:
            obj['timeout'] = self.timeout
        if self.result_ttl is not None:
            obj['result_ttl'] = self.result_ttl
        if self.failure_ttl is not None:
            obj['failure_ttl'] = self.failure_ttl
        if self._status is not None:
            obj['status'] = self._status
        if self.meta and include_meta:
            obj['meta'] = dumps(self.meta)
        if self.ttl:
            obj['ttl'] = self.ttl
        obj['ip'] = self.ip
        obj['handle_worker'] = self.handle_worker
        obj['cost'] = self.cost

        return obj

    def save(self, include_meta=True):
        """
        Dumps the current msg instance to its corresponding Redis key.

        Exclude saving the `meta` dictionary by setting
        `include_meta=False`. This is useful to prevent clobbering
        user metadata without an expensive `refresh()` call first.

        Redis key persistence may be altered by `cleanup()` method.
        """
        key = self.key
        self.connection.hmset(key, self.to_dict(include_meta=include_meta))

    def save_meta(self):
        """Stores msg meta from the msg instance to the corresponding Redis key."""
        meta = dumps(self.meta)
        self.connection.hset(self.key, 'meta', meta)

    def cancel(self):
        """Cancels the given msg, which will prevent the msg from ever being
        ran (or inspected).

        This method merely exists as a high-level API call to cancel msgs
        without worrying about the internals required to implement msg
        cancellation.
        """
        from .queue import Queue
        if self.origin:
            q = Queue(name=self.origin, connection=self.connection)
            q.remove(self)

    def requeue(self):
        """Requeues msg."""
        self.failed_msg_registry.requeue(self)

    def delete(self, remove_from_queue=True):
        """Cancels the msg and deletes the msg hash from Redis."""
        if remove_from_queue:
            self.cancel()

        if self.is_finished:
            from .registry import FinishedMsgRegistry
            registry = FinishedMsgRegistry(self.origin,
                                           connection=self.connection,
                                           msg_class=self.__class__)
            registry.remove(self)

        elif self.is_started:
            from .registry import StartedMsgRegistry
            registry = StartedMsgRegistry(self.origin,
                                          connection=self.connection,
                                          msg_class=self.__class__)
            registry.remove(self)

        elif self.is_failed:
            self.failed_msg_registry.remove(self)

        self.connection.delete(self.key)

    def get_ttl(self, default_ttl=None):
        """Returns ttl for a msg that determines how long a msg will be
        persisted. In the future, this method will also be responsible
        for determining ttl for repeated msgs.
        """
        return default_ttl if self.ttl is None else self.ttl

    def get_result_ttl(self, default_ttl=None):
        """Returns ttl for a msg that determines how long a msgs result will
        be persisted. In the future, this method will also be responsible
        for determining ttl for repeated msgs.
        """
        return default_ttl if self.result_ttl is None else self.result_ttl

    def cleanup(self, ttl=None, remove_from_queue=True):
        """Prepare msg for eventual deletion (if needed). This method is usually
        called after successful execution. How long we persist the msg and its
        result depends on the value of ttl:
        - If it's a positive number, set the msg to expire in X seconds.
        - If ttl is negative, don't set an expiry to it (persist
          forever)
        """
        if not ttl:
            return
        elif ttl > 0:
            self.connection.expire(self.key, ttl)

    @property
    def failed_msg_registry(self):
        from .registry import FailedMsgRegistry
        return FailedMsgRegistry(self.origin, connection=self.connection,
                                 msg_class=self.__class__)
