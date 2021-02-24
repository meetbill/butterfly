#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-02-24 21:05:21

# File Name: registry.py
# Description:

"""
from datetime import datetime

from xlib.mq.compat import as_text
from xlib.mq.defaults import DEFAULT_FAILURE_TTL
from xlib.mq.exceptions import InvalidMsgOperation, NoSuchMsgError
from xlib.mq.msg import Msg, MsgStatus
from xlib.mq.queue import Queue
from xlib.mq.utils import backend_class, current_timestamp


class BaseRegistry(object):
    """
    Base implementation of a msg registry, implemented in Redis sorted set.
    Each msg is stored as a key in the registry, scored by expiration time
    (unix timestamp).
    """
    msg_class = Msg
    key_template = 'mq:registry:{{{0}}}'

    def __init__(self, name='default', connection=None, msg_class=None,
                 queue=None):
        if queue:
            self.name = queue.name
            self.connection = queue.connection
        else:
            self.name = name
            self.connection = connection

        self.key = self.key_template.format(self.name)
        self.msg_class = backend_class(self, 'msg_class', override=msg_class)

    def __len__(self):
        """Returns the number of msgs in this registry"""
        return self.count

    def __eq__(self, other):
        return (self.name == other.name and self.connection == other.connection)

    def __contains__(self, item):
        """
        Returns a boolean indicating registry contains the given
        msg instance or msg id.
        """
        msg_id = item
        if isinstance(item, self.msg_class):
            msg_id = item.id
        return self.connection.zscore(self.key, msg_id) is not None

    @property
    def count(self):
        """Returns the number of msgs in this registry"""
        self.cleanup()
        return self.connection.zcard(self.key)

    def add(self, msg, ttl=0):
        """Adds a msg to a registry with expiry time of now + ttl, unless it's -1 which is set to +inf"""
        score = ttl if ttl < 0 else current_timestamp() + ttl
        if score == -1:
            score = '+inf'
        return self.connection.zadd(self.key, {msg.id: score})

    def remove(self, msg, delete_msg=False):
        """Removes msg from registry and deletes it if `delete_msg == True`"""
        msg_id = msg.id if isinstance(msg, self.msg_class) else msg
        result = self.connection.zrem(self.key, msg_id)
        if delete_msg:
            if isinstance(msg, self.msg_class):
                msg_instance = msg
            else:
                msg_instance = Msg.fetch(msg_id, connection=self.connection)
            msg_instance.delete()
        return result

    def get_expired_msg_ids(self, timestamp=None):
        """Returns msg ids whose score are less than current timestamp.

        Returns ids for msgs with an expiry time earlier than timestamp,
        specified as seconds since the Unix epoch. timestamp defaults to call
        time if unspecified.
        """
        score = timestamp if timestamp is not None else current_timestamp()
        return [as_text(msg_id) for msg_id in
                self.connection.zrangebyscore(self.key, 0, score)]

    def get_msg_ids(self, start=0, end=-1):
        """Returns list of all msg ids."""
        self.cleanup()
        return [as_text(msg_id) for msg_id in
                self.connection.zrange(self.key, start, end)]

    def get_queue(self):
        """Returns Queue object associated with this registry."""
        return Queue(self.name, connection=self.connection)

    def get_expiration_time(self, msg):
        """Returns msg's expiration time."""
        score = self.connection.zscore(self.key, msg.id)
        return datetime.utcfromtimestamp(score)


class StartedMsgRegistry(BaseRegistry):
    """
    Registry of currently executing msgs. Each queue maintains a
    StartedMsgRegistry. Msgs in this registry are ones that are currently
    being executed.

    Msgs are added to registry right before they are executed and removed
    right after completion (success or failure).
    """
    key_template = 'mq:wip:{{{0}}}'

    def cleanup(self, timestamp=None):
        """Remove expired msgs from registry and add them to FailedMsgRegistry.

        Removes msgs with an expiry time earlier than timestamp, specified as
        seconds since the Unix epoch. timestamp defaults to call time if
        unspecified. Removed msgs are added to the global failed msg queue.
        """
        score = timestamp if timestamp is not None else current_timestamp()
        msg_ids = self.get_expired_msg_ids(score)

        if msg_ids:
            failed_msg_registry = FailedMsgRegistry(self.name, self.connection)

            for msg_id in msg_ids:
                try:
                    msg = self.msg_class.fetch(msg_id, connection=self.connection)
                    msg.set_status(MsgStatus.FAILED)
                    msg.exc_info = "Moved to FailedMsgRegistry at {now}".format(now=datetime.now())
                    msg.save(include_meta=False)
                    msg.cleanup(ttl=-1)
                    failed_msg_registry.add(msg, msg.failure_ttl)
                except NoSuchMsgError:
                    pass

        self.connection.zremrangebyscore(self.key, 0, score)

        return msg_ids


class FinishedMsgRegistry(BaseRegistry):
    """
    Registry of msgs that have been completed. Msgs are added to this
    registry after they have successfully completed for monitoring purposes.
    """
    key_template = 'mq:finished:{{{0}}}'

    def cleanup(self, timestamp=None):
        """Remove expired msgs from registry.

        Removes msgs with an expiry time earlier than timestamp, specified as
        seconds since the Unix epoch. timestamp defaults to call time if
        unspecified.
        """
        score = timestamp if timestamp is not None else current_timestamp()
        self.connection.zremrangebyscore(self.key, 0, score)


class FailedMsgRegistry(BaseRegistry):
    """
    Registry of containing failed msgs.
    """
    key_template = 'mq:failed:{{{0}}}'

    def cleanup(self, timestamp=None):
        """Remove expired msgs from registry.

        Removes msgs with an expiry time earlier than timestamp, specified as
        seconds since the Unix epoch. timestamp defaults to call time if
        unspecified.
        """
        score = timestamp if timestamp is not None else current_timestamp()
        self.connection.zremrangebyscore(self.key, 0, score)

    def add(self, msg, ttl=None, exc_string=''):
        """
        Adds a msg to a registry with expiry time of now + ttl.
        `ttl` defaults to DEFAULT_FAILURE_TTL if not specified.
        """
        if ttl is None:
            ttl = DEFAULT_FAILURE_TTL
        score = ttl if ttl < 0 else current_timestamp() + ttl

        msg.exc_info = exc_string
        msg.save(include_meta=False)
        msg.cleanup(ttl=ttl)
        self.connection.zadd(self.key, {msg.id: score})

    def requeue(self, msg_or_id):
        """Requeues the msg with the given msg ID."""
        if isinstance(msg_or_id, self.msg_class):
            msg = msg_or_id
        else:
            msg = self.msg_class.fetch(msg_or_id, connection=self.connection)

        result = self.connection.zrem(self.key, msg.id)
        if not result:
            raise InvalidMsgOperation

        queue = Queue(msg.origin, connection=self.connection,
                      msg_class=self.msg_class)

        return queue.enqueue_msg(msg)


def clean_registries(queue):
    """Cleans StartedMsgRegistry and FinishedMsgRegistry of a queue."""
    registry = FinishedMsgRegistry(name=queue.name,
                                   connection=queue.connection,
                                   msg_class=queue.msg_class)
    registry.cleanup()
    registry = StartedMsgRegistry(name=queue.name,
                                  connection=queue.connection,
                                  msg_class=queue.msg_class)
    registry.cleanup()

    registry = FailedMsgRegistry(name=queue.name,
                                 connection=queue.connection,
                                 msg_class=queue.msg_class)
    registry.cleanup()
