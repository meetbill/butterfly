# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import uuid

from xlib.mq.compat import as_text, string_types, total_ordering
from xlib.mq.exceptions import NoSuchMsgError, UnpickleError
from xlib.mq.msg import Msg, MsgStatus
from xlib.mq.utils import backend_class, import_attribute, parse_timeout, utcnow
from xlib.mq.utils import current_timestamp
from xlib.mq import defaults


def compact(lst):
    return [item for item in lst if item is not None]


@total_ordering
class Queue(object):
    msg_class = Msg
    DEFAULT_TIMEOUT = 180  # Default timeout seconds.
    redis_queue_namespace_prefix = defaults.REDIS_QUEUE_NAMESPACE_PREFIX
    redis_queues_keys = defaults.REDIS_QUEUES_KEYS

    @classmethod
    def all(cls, connection=None, msg_class=None):
        """Returns an iterable of all Queues.
        """
        connection = connection

        def to_queue(queue_key):
            return cls.from_queue_key(as_text(queue_key),
                                      connection=connection,
                                      msg_class=msg_class)
        return [to_queue(rq_key)
                for rq_key in connection.smembers(cls.redis_queues_keys)
                if rq_key]

    @classmethod
    def from_queue_key(cls, queue_key, connection=None, msg_class=None):
        """Returns a Queue instance, based on the naming conventions for naming
        the internal Redis keys.  Can be used to reverse-lookup Queues by their
        Redis keys.
        """
        prefix = cls.redis_queue_namespace_prefix
        if not queue_key.startswith(prefix):
            raise ValueError('Not a valid RQ queue key: {0}'.format(queue_key))

        # 需要去掉 hashtab {}
        name = queue_key[len(prefix):][1:-1]
        return cls(name, connection=connection, msg_class=msg_class)

    def __init__(self, name='default', default_timeout=None, connection=None,
                 msg_class=None, **kwargs):
        self.connection = connection
        prefix = self.redis_queue_namespace_prefix
        self.name = name
        # 将 key 进行添加 hashtag, 两个左花括号输出左花括号本身，两个右花括号输出右花括号本身。
        self._key = '{prefix}{{{name}}}'.format(prefix=prefix, name=name)
        self._default_timeout = parse_timeout(default_timeout) or self.DEFAULT_TIMEOUT

        # override class attribute msg_class if one was passed
        if msg_class is not None:
            if isinstance(msg_class, string_types):
                msg_class = import_attribute(msg_class)
            self.msg_class = msg_class

    def __len__(self):
        return self.count

    def __nonzero__(self):
        return True

    def __bool__(self):
        return True

    def __iter__(self):
        yield self

    @property
    def key(self):
        """Returns the Redis key for this Queue."""
        return self._key

    @property
    def registry_cleaning_key(self):
        """Redis key used to indicate this queue has been cleaned."""
        return 'mq:clean_registries:%s' % self.name

    def acquire_cleaning_lock(self):
        """Returns a boolean indicating whether a lock to clean this queue
        is acquired. A lock expires in 899 seconds (15 minutes - 1 second)
        """
        return self.connection.set(self.registry_cleaning_key, 1, nx=1, ex=899)

    def empty(self):
        """Removes all messages on the queue."""
        script = """
            local prefix = "{0}"
            local q = KEYS[1]
            local count = 0
            while true do
                local msg_id = redis.call("lpop", q)
                if msg_id == false then
                    break
                end

                -- Delete the relevant keys
                redis.call("del", prefix..msg_id)
                count = count + 1
            end
            return count
        """.format(self.msg_class.redis_msg_namespace_prefix).encode("utf-8")
        script = self.connection.register_script(script)
        return script(keys=[self.key])

    def delete(self, delete_msgs=True):
        """Deletes the queue. If delete_msgs is true it removes all the associated messages on the queue first."""
        if delete_msgs:
            self.empty()

        self.connection.srem(self.redis_queues_keys, self._key)
        self.connection.delete(self._key)

    def is_empty(self):
        """Returns whether the current queue is empty."""
        return self.count == 0

    def fetch_msg(self, msg_id):
        try:
            msg = self.msg_class.fetch(msg_id, connection=self.connection)
        except NoSuchMsgError:
            self.remove(msg_id)
        else:
            if msg.origin == self.name:
                return msg

    def get_msg_ids(self, offset=0, length=-1):
        """Returns a slice of msg IDs in the queue."""
        start = offset
        if length >= 0:
            end = offset + (length - 1)
        else:
            end = length
        return [as_text(msg_id) for msg_id in
                self.connection.lrange(self.key, start, end)]

    def get_msgs(self, offset=0, length=-1):
        """Returns a slice of msgs in the queue."""
        msg_ids = self.get_msg_ids(offset, length)
        return compact([self.fetch_msg(msg_id) for msg_id in msg_ids])

    @property
    def msg_ids(self):
        """Returns a list of all msg IDS in the queue."""
        return self.get_msg_ids()

    @property
    def msgs(self):
        """Returns a list of all (valid) msgs in the queue."""
        return self.get_msgs()

    @property
    def count(self):
        """Returns a count of all messages in the queue."""
        return self.connection.llen(self.key)

    @property
    def failed_msg_registry(self):
        """Returns this queue's FailedMsgRegistry."""
        from xlib.mq.registry import FailedMsgRegistry
        return FailedMsgRegistry(queue=self, msg_class=self.msg_class)

    @property
    def started_msg_registry(self):
        """Returns this queue's FailedMsgRegistry."""
        from xlib.mq.registry import StartedMsgRegistry
        return StartedMsgRegistry(queue=self, msg_class=self.msg_class)

    @property
    def finished_msg_registry(self):
        """Returns this queue's FailedMsgRegistry."""
        from xlib.mq.registry import FinishedMsgRegistry
        return FinishedMsgRegistry(queue=self)

    def remove(self, msg_or_id):
        """Removes Msg from queue, accepts either a Msg instance or ID."""
        msg_id = msg_or_id.id if isinstance(msg_or_id, self.msg_class) else msg_or_id
        return self.connection.lrem(self.key, 1, msg_id)

    def compact(self):
        """Removes all "dead" msgs from the queue by cycling through it, while
        guaranteeing FIFO semantics.
        """
        COMPACT_QUEUE = '{0}_compact:{1}'.format(
            self.redis_queue_namespace_prefix, uuid.uuid4())  # noqa

        self.connection.rename(self.key, COMPACT_QUEUE)
        while True:
            msg_id = as_text(self.connection.lpop(COMPACT_QUEUE))
            if msg_id is None:
                break
            if self.msg_class.exists(msg_id, self.connection):
                self.connection.rpush(self.key, msg_id)

    def push_msg_id(self, msg_id, at_front=False):
        """Pushes a msg ID on the corresponding Redis queue.
        'at_front' allows you to push the msg onto the front instead of the back of the queue"""
        if at_front:
            self.connection.lpush(self.key, msg_id)
        else:
            self.connection.rpush(self.key, msg_id)

    def create_msg(self, data, timeout=None,
                   result_ttl=None, ttl=None, failure_ttl=None,
                   description=None, msg_id=None,
                   meta=None, status=MsgStatus.QUEUED):
        """Creates a msg based on parameters given."""
        timeout = parse_timeout(timeout)

        if timeout is None:
            timeout = self._default_timeout
        elif timeout == 0:
            raise ValueError('0 timeout is not allowed. Use -1 for infinite timeout')

        result_ttl = parse_timeout(result_ttl)
        failure_ttl = parse_timeout(failure_ttl)

        ttl = parse_timeout(ttl)
        if ttl is not None and ttl <= 0:
            raise ValueError('Msg ttl must be greater than 0')

        msg = self.msg_class.create(
            data, connection=self.connection,
            result_ttl=result_ttl, ttl=ttl, failure_ttl=failure_ttl,
            status=status, description=description,
            timeout=timeout, id=msg_id,
            origin=self.name, meta=meta
        )

        return msg

    def enqueue_call(self, data, timeout=None,
                     result_ttl=None, ttl=None, failure_ttl=None,
                     description=None, msg_id=None,
                     at_front=False, meta=None):
        """Creates a msg to represent the delayed function call and enqueues
        it.

        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for RQ itself.
        """

        msg = self.create_msg(
            data, result_ttl=result_ttl, ttl=ttl,
            failure_ttl=failure_ttl, description=description,
            msg_id=msg_id, meta=meta, status=MsgStatus.QUEUED, timeout=timeout,
        )
        msg = self.enqueue_msg(msg, at_front=at_front)
        return msg

    @classmethod
    def parse_args(cls, data, *args, **kwargs):
        """
        Parses arguments passed to `queue.enqueue()`
        """
        if not isinstance(data, string_types):
            raise ValueError('message data must be string')

        # Detect explicit invocations, i.e. of the form:
        #     q.enqueue(foo, args=(1, 2), kwargs={'a': 1}, msg_timeout=30)
        timeout = kwargs.pop('msg_timeout', None)
        description = kwargs.pop('description', None)
        result_ttl = kwargs.pop('result_ttl', None)
        ttl = kwargs.pop('ttl', None)
        failure_ttl = kwargs.pop('failure_ttl', None)
        msg_id = kwargs.pop('msg_id', None)
        at_front = kwargs.pop('at_front', False)
        meta = kwargs.pop('meta', None)
        return (data, timeout, description, result_ttl, ttl, failure_ttl,
                msg_id, at_front, meta)

    def enqueue(self, data, *args, **kwargs):
        """Creates a msg to represent the delayed function call and enqueues it."""

        (data, timeout, description, result_ttl, ttl, failure_ttl,
         msg_id, at_front, meta) = Queue.parse_args(data, *args, **kwargs)

        return self.enqueue_call(
            data=data, timeout=timeout,
            result_ttl=result_ttl, ttl=ttl, failure_ttl=failure_ttl,
            description=description, msg_id=msg_id,
            at_front=at_front, meta=meta
        )

    def enqueue_msg(self, msg, at_front=False):
        """Enqueues a msg for delayed execution.
        """
        # 1 Add Queue key set
        # 将当前 queue_name 添加到 mq:queues set 中，如 "SADD" "mq:queues" "mq:queue:meet"
        self.connection.sadd(self.redis_queues_keys, self.key)

        # save 为 False 时，仅变更状态，不写入 Redis, 由 msg.save 统一写入 Redis
        msg.set_status(MsgStatus.QUEUED, save=False)

        msg.origin = self.name
        msg.enqueued_at = utcnow()

        if msg.timeout is None:
            msg.timeout = self._default_timeout

        # 2 将 msg 信息写入 msg key
        msg.save()
        # 设定任务在队列中的存活时长，默认永久存活，即 ttl 为 None
        msg.cleanup(ttl=msg.ttl)

        # 3 将 msg id push 到列表中
        self.push_msg_id(msg.id, at_front=at_front)
        return msg

    def pop_msg_id(self):
        """Pops a given msg ID from this Redis queue."""
        return as_text(self.connection.lpop(self.key))

    @classmethod
    def lpop(cls, queues, connection=None):
        """
        +-----------------------------------------------
        |       list                     set
        |mq:queue:{queue_name} ==> mq:wip:{queue_name}
        +-----------------------------------------------
        """
        lua = '''
            local v = redis.call("lpop", KEYS[1])
            if v then
                redis.call('zadd',KEYS[2],ARGV[1],v)
            end
            return v
        '''
        connection = connection
        key_template = 'mq:wip:{{{0}}}'
        for queue in queues:
            queue_key = queue.key
            queue_name = queue.name
            queue_wip_key = key_template.format(queue_name)
            score = current_timestamp()

            keys_args_list = [queue_key, queue_wip_key, score]
            blob = connection.eval(lua, 2, *keys_args_list)
            if blob is not None:
                return queue_key, blob
        return None

    @classmethod
    def dequeue_any(cls, queues, connection=None, msg_class=None):
        """Class method returning the msg_class instance at the front of the given
        set of Queues, where the order of the queues is important.

        When all of the Queues are empty, depending on the `timeout` argument,
        either blocks execution of this function for the duration of the
        timeout or until new messages arrive on any of the queues, or returns
        None.

        See the documentation of cls.lpop for the interpretation of timeout.

        从队列中获取任务, 并将任务同时加到正在处理 zset 中
        """
        msg_class = backend_class(cls, 'msg_class', override=msg_class)

        while True:
            result = cls.lpop(queues, connection=connection)
            if result is None:
                return None
            queue_key, msg_id = map(as_text, result)
            queue = cls.from_queue_key(queue_key,
                                       connection=connection,
                                       msg_class=msg_class)
            try:
                msg = msg_class.fetch(msg_id, connection=connection)
            except NoSuchMsgError:
                # Silently pass on msgs that don't exist (anymore),
                # and continue in the look
                continue
            except UnpickleError as e:
                # Attach queue information on the exception for improved error
                # reporting
                e.msg_id = msg_id
                e.queue = queue
                raise e
            return msg, queue
        return None, None

    # Total ordering defition (the rest of the required Python methods are
    # auto-generated by the @total_ordering decorator)
    def __eq__(self, other):  # noqa
        if not isinstance(other, Queue):
            raise TypeError('Cannot compare queues to other objects')
        return self.name == other.name

    def __lt__(self, other):
        if not isinstance(other, Queue):
            raise TypeError('Cannot compare queues to other objects')
        return self.name < other.name

    def __hash__(self):  # pragma: no cover
        return hash(self.name)

    def __repr__(self):  # noqa  # pragma: no cover
        return '{0}({1!r})'.format(self.__class__.__name__, self.name)

    def __str__(self):
        return '<{0} {1}>'.format(self.__class__.__name__, self.name)
