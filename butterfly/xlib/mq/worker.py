# coding=utf8
"""
# File Name: worker.py
# Description:

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
import signal
import socket
import sys
import traceback
import warnings
import time
import json
from xlib import httpgateway
import urllib

try:
    from signal import SIGKILL
except ImportError:
    from signal import SIGTERM as SIGKILL

from xlib.mq import worker_registration
from xlib.mq.compat import as_text, string_types

from xlib.mq import defaults
from xlib.mq.msg import Msg, MsgStatus
from xlib.mq.queue import Queue
from xlib.mq.registry import FailedMsgRegistry, StartedMsgRegistry, clean_registries
from xlib.mq.utils import (backend_class, ensure_list, enum,
                           utcformat, utcnow, utcparse)
from xlib.mq.worker_registration import clean_worker_registry, get_keys


import xlib
from conf import config

addr_host, addr_port = config.SERVER_LISTEN_ADDR
logger = logging.getLogger(__name__)


def compact(l):
    """
    compact
    """
    return [x for x in l if x is not None]


_signames = dict((getattr(signal, signame), signame)
                 for signame in dir(signal)
                 if signame.startswith('SIG') and '_' not in signame)


WorkerStatus = enum(
    'WorkerStatus',
    STARTED='started',
    SUSPENDED='suspended',
    BUSY='busy',
    IDLE='idle'
)


class Worker(object):
    """
    Worker class
    """
    redis_worker_namespace_prefix = 'mq:worker:'
    redis_workers_keys = worker_registration.REDIS_WORKER_KEYS
    queue_class = Queue
    msg_class = Msg
    # `log_result_lifespan` controls whether "Result is kept for XXX seconds"
    # messages are logged after every msg, by default they are.
    log_result_lifespan = True

    @classmethod
    def all(cls, connection=None, msg_class=None, queue_class=None, queue=None):
        """Returns an iterable of all Workers.
        """
        if queue:
            connection = queue.connection
        elif connection is None:
            connection = connection

        worker_keys = get_keys(queue=queue, connection=connection)
        workers = []
        for key in worker_keys:
            workers.append(cls.find_by_key(as_text(key), connection=connection,
                msg_class=msg_class, queue_class=queue_class))

        return compact(workers)

    @classmethod
    def all_keys(cls, connection=None, queue=None):
        """
        Returns all_keys
        """
        return [as_text(key) for key in get_keys(queue=queue, connection=connection)]

    @classmethod
    def count(cls, connection=None, queue=None):
        """Returns the number of workers by queue or connection"""
        return len(get_keys(queue=queue, connection=connection))

    @classmethod
    def find_by_key(cls, worker_key, connection=None, msg_class=None,
                    queue_class=None):
        """Returns a Worker instance, based on the naming conventions for
        naming the internal Redis keys.  Can be used to reverse-lookup Workers
        by their Redis keys.
        """
        prefix = cls.redis_worker_namespace_prefix
        if not worker_key.startswith(prefix):
            raise ValueError('Not a valid RQ worker key: %s' % worker_key)

        connection = connection
        if not connection.exists(worker_key):
            connection.srem(cls.redis_workers_keys, worker_key)
            return None

        name = worker_key[len(prefix):]
        worker = cls([], name, connection=connection, msg_class=msg_class,
                     queue_class=queue_class, prepare_for_work=False)

        worker.refresh()

        return worker

    def __init__(self, queues, name=None, default_result_ttl=None,
                 connection=None, exc_handler=None, exception_handlers=None,
                 default_worker_ttl=None, msg_class=None,
                 queue_class=None,
                 prepare_for_work=True,
                 acclog=None, errlog=None,
                 pool=None, apicube=None
                 ):  # noqa
        if connection is None:
            connection = connection
        self.connection = connection

        if prepare_for_work:
            self.hostname = socket.gethostname()
            self.pid = os.getpid()
        else:
            self.hostname = None
            self.pid = None

        self.msg_class = backend_class(self, 'msg_class', override=msg_class)
        self.queue_class = backend_class(self, 'queue_class', override=queue_class)
        self.version = xlib.butterfly_version
        self.python_version = sys.version
        self.name = name or "{hostname}:{addr_port}:{pid}".format(
            hostname=self.hostname, addr_port=addr_port, pid=self.pid)
        queues_list = []
        for q in ensure_list(queues):
            if isinstance(q, string_types):
                queues_list.append(self.queue_class(name=q, connection=connection, msg_class=self.msg_class))
            else:
                queues_list.append(q)
        self.queues = queues_list
        self.validate_queues()
        self._exc_handlers = []

        if default_result_ttl is None:
            self.default_result_ttl = defaults.DEFAULT_RESULT_TTL
        else:
            self.default_result_ttl = default_result_ttl

        if default_worker_ttl is None:
            self.default_worker_ttl = defaults.DEFAULT_WORKER_TTL
        else:
            self.default_worker_ttl = default_worker_ttl

        self._state = 'starting'
        self._horse_pid = 0
        self._stop_requested = False
        self.log = logger
        self.last_cleaned_at = None
        self.successful_msg_count = 0
        self.failed_msg_count = 0
        self.total_working_time = 0
        self.birth_date = None

        if isinstance(exception_handlers, list):
            for handler in exception_handlers:
                self.push_exc_handler(handler)
        elif exception_handlers is not None:
            self.push_exc_handler(exception_handlers)

        self._acclog = acclog
        self._errlog = errlog
        self.pool = pool
        self.apicube = apicube

    def validate_queues(self):
        """Sanity check for the given queues."""
        for queue in self.queues:
            if not isinstance(queue, self.queue_class):
                raise TypeError('{0} is not of type {1} or string types'.format(queue, self.queue_class))

    def queue_names(self):
        """Returns the queue names of this worker's queues."""
        return [queue.name for queue in self.queues]

    def queue_keys(self):
        """Returns the Redis keys representing this worker's queues."""
        return [queue.key for queue in self.queues]

    @property
    def key(self):
        """Returns the worker's Redis hash key."""
        return self.redis_worker_namespace_prefix + self.name

    def register_birth(self):
        """Registers its own birth."""

        self.log.debug('Registering birth of worker %s', self.name)
        if self.connection.exists(self.key) and \
                not self.connection.hexists(self.key, 'death'):
            msg = 'There exists an active worker named {0!r} already'
            raise ValueError(msg.format(self.name))

        key = self.key
        queues = ','.join(self.queue_names())

        self.connection.delete(key)

        now = utcnow()
        now_in_string = utcformat(now)
        self.birth_date = now

        self.connection.hmset(key, {
            'birth': now_in_string,
            'last_heartbeat': now_in_string,
            'queues': queues,
            'pid': self.pid,
            'hostname': self.hostname,
            'version': self.version,
            'python_version': self.python_version,
        })
        worker_registration.register(self)

        self.connection.expire(key, self.default_worker_ttl)

    def register_death(self):
        """Registers its own death."""
        try:
            worker_registration.unregister(self)
            self.connection.hset(self.key, 'death', utcformat(utcnow()))
            self.connection.expire(self.key, 60)
        except BaseException:
            pass

    def set_shutdown_requested_date(self):
        """Sets the date on which the worker received a (warm) shutdown request"""
        self.connection.hset(self.key, 'shutdown_requested_date', utcformat(utcnow()))

    @property
    def shutdown_requested_date(self):
        """Fetches shutdown_requested_date from Redis."""
        shutdown_requested_timestamp = self.connection.hget(self.key, 'shutdown_requested_date')
        if shutdown_requested_timestamp is not None:
            return utcparse(as_text(shutdown_requested_timestamp))

    def set_state(self, state):
        """
        Set state
        """
        self._state = state
        self.connection.hset(self.key, 'state', state)

    def _set_state(self, state):
        """Raise a DeprecationWarning if ``worker.state = X`` is used"""
        warnings.warn(
            "worker.state is deprecated, use worker.set_state() instead.",
            DeprecationWarning
        )
        self.set_state(state)

    def get_state(self):
        """
        Get state
        """
        return self._state

    def _get_state(self):
        """Raise a DeprecationWarning if ``worker.state == X`` is used"""
        warnings.warn(
            "worker.state is deprecated, use worker.get_state() instead.",
            DeprecationWarning
        )
        return self.get_state()

    state = property(_get_state, _set_state)

    def _install_signal_handlers(self):
        """Installs signal handlers for handling SIGINT and SIGTERM
        gracefully.
        """

        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGTERM, self.request_stop)

    def request_stop(self, signum, frame):
        """Stops the current worker loop but waits for child processes to
        end gracefully (warm shutdown).
        """
        self.log.info('Warm shut down requested')
        self._stop_requested = True
        self.register_death()
        sys.exit()

    def run_maintenance_tasks(self):
        """
        Runs periodic maintenance tasks, these include:
        1. Cleaning registries

        Operate every 15 minutes
        """
        self.clean_registries()

    def init(self):
        """
        init worker
        """
        try:
            # 1: 将 worker 注册到系统中
            self.register_birth()

            # 2: 将 worker 标记为 started
            self.set_state(WorkerStatus.STARTED)
            qnames = self.queue_names()

            self._install_signal_handlers()
        except BaseException:
            self.log.error(traceback.format_exc())

    def heartbeat(self):
        """
        Specifies a new worker timeout, typically by extending the
        expiration time of the worker, effectively making this a "heartbeat"
        to not expire the worker until the timeout passes.

        One heartbeat per minute
        """
        timeout = 120
        self.connection.expire(self.key, timeout)
        self.connection.hset(self.key, 'last_heartbeat', utcformat(utcnow()))

    def refresh(self):
        """
        Update data from redis
        """
        data = self.connection.hmget(
            self.key, 'queues', 'state', 'last_heartbeat',
            'birth', 'failed_msg_count', 'successful_msg_count',
            'total_working_time', 'hostname', 'pid', 'version', 'python_version',
        )
        (queues, state, last_heartbeat, birth, failed_msg_count,
         successful_msg_count, total_working_time, hostname, pid, version, python_version) = data
        queues = as_text(queues)
        self.hostname = as_text(hostname)
        self.pid = int(pid) if pid else None
        self.version = as_text(version)
        self.python_version = as_text(python_version)
        self._state = as_text(state or '?')
        if last_heartbeat:
            self.last_heartbeat = utcparse(as_text(last_heartbeat))
        else:
            self.last_heartbeat = None
        if birth:
            self.birth_date = utcparse(as_text(birth))
        else:
            self.birth_date = None
        if failed_msg_count:
            self.failed_msg_count = int(as_text(failed_msg_count))
        if successful_msg_count:
            self.successful_msg_count = int(as_text(successful_msg_count))
        if total_working_time:
            self.total_working_time = float(as_text(total_working_time))

        if queues:
            self.queues = []
            for queue in queues.split(','):
                self.queues.append(self.queue_class(queue, connection=self.connection, msg_class=self.msg_class))

    def increment_failed_msg_count(self):
        """
        Incr failed msg count
        """
        self.connection.hincrby(self.key, 'failed_msg_count', 1)

    def increment_successful_msg_count(self):
        """
        Incr successful msg count
        """
        self.connection.hincrby(self.key, 'successful_msg_count', 1)

    def increment_total_working_time(self, msg_execution_time):
        """
        incr total working time
        """
        self.connection.hincrbyfloat(self.key, 'total_working_time', msg_execution_time.total_seconds())

    def handle_msg_failure(self, msg, started_msg_registry=None,
                           exc_string=''):
        """Handles the failure or an executing msg by:
            1. Setting the msg status to failed
            2. Removing the msg from StartedMsgRegistry
            3. Add the msg to FailedMsgRegistry
        """
        if started_msg_registry is None:
            started_msg_registry = StartedMsgRegistry(
                msg.origin,
                self.connection,
                msg_class=self.msg_class
            )

        # 1. Setting the msg status to failed
        msg.set_status(MsgStatus.FAILED)

        # 2. Removing the msg from StartedMsgRegistry
        started_msg_registry.remove(msg)

        # 3. Add the msg to FailedMsgRegistry
        failed_msg_registry = FailedMsgRegistry(msg.origin, msg.connection, msg_class=self.msg_class)
        failed_msg_registry.add(msg, ttl=msg.failure_ttl, exc_string=exc_string)

        self.increment_failed_msg_count()
        if msg.started_at and msg.ended_at:
            self.increment_total_working_time(msg.ended_at - msg.started_at)

    def handle_msg_success(self, msg, queue, started_msg_registry):
        """
        Handle msg success
        """
        self.log.debug('Handling successful execution of msg %s', msg.id)
        self.increment_successful_msg_count()
        self.increment_total_working_time(msg.ended_at - msg.started_at)
        result_ttl = msg.get_result_ttl(self.default_result_ttl)
        if result_ttl != 0:
            msg.set_status(MsgStatus.FINISHED)
            # Don't clobber the user's meta dictionary!
            msg.save(include_meta=False)

            finished_msg_registry = queue.finished_msg_registry
            finished_msg_registry.add(msg, result_ttl)

        msg.cleanup(result_ttl, remove_from_queue=False)
        started_msg_registry.remove(msg)

    @staticmethod
    def _get_safe_exception_string(exc_strings):
        """Ensure list of exception strings is decoded on Python 2 and joined as one string safely."""
        if sys.version_info[0] < 3:
            try:
                exc_strings = [exc.decode("utf-8") for exc in exc_strings]
            except ValueError:
                exc_strings = [exc.decode("latin-1") for exc in exc_strings]
        return ''.join(exc_strings)

    def push_exc_handler(self, handler_func):
        """Pushes an exception handler onto the exc handler stack."""
        self._exc_handlers.append(handler_func)

    def pop_exc_handler(self):
        """Pops the latest exception handler off of the exc handler stack."""
        return self._exc_handlers.pop()

    def __eq__(self, other):
        """Equality does not take the database/connection into account"""
        if not isinstance(other, self.__class__):
            raise TypeError('Cannot compare workers to other types (of workers)')
        return self.name == other.name

    def __hash__(self):
        """The hash does not take the database/connection into account"""
        return hash(self.name)

    def clean_registries(self):
        """Runs maintenance msgs on each Queue's registries."""
        for queue in self.queues:
            # If there are multiple workers running, we only want 1 worker
            # to run clean_registries().
            if queue.acquire_cleaning_lock():
                self.log.info('Cleaning registries for queue: %s', queue.name)
                clean_registries(queue)
                clean_worker_registry(queue)
        self.last_cleaned_at = utcnow()

    def _mk_ret(self, req, httpstatus, headers, content):
        """normal return
        Args:
            req       : http req
            httpstatus: (String) httpstatus eg.:"200 OK","400 Get API Exception"
            headers   : (List) http headers
            context   : (String) http body
        Returns:
            httpstatus, headers, content
        """
        cost = time.time() - req.init_tm
        cost_str = "%.6f" % cost
        try:
            talk_str = ";".join("%s=%.3f" % (k, v) for k, v in req.log_talk.iteritems())
            # 这里的参数有可能是带 = 的 URL, 如果需要根据日志进行取参数时，需要仅对第一个 = 进行分割处理
            log_params_str = ";".join("%s=%s" % (k, v) for k, v in req.log_params.iteritems())
            self._acclog.log(("{ip}\t{reqid}\t{method}\t{funcname}\tcost:{cost}\t"
                              "stat:{ret_code}\tuser:{username}\ttalk:{talk}\t"
                              "params:{log_params}\terror_msg:{error}\tres:{res}".format
                              (ip=req.ip,
                               reqid=req.reqid,
                               method=req.wsgienv.get("REQUEST_METHOD"),
                               funcname=req.funcname,
                               cost=cost_str,
                               ret_code=req.log_ret_code,
                               username=req.username,
                               talk=talk_str,
                               log_params=log_params_str,
                               error=req.error_str,
                               res=";".join(req.log_res))))
        except BaseException:
            try:
                self._errlog.log(
                    "%s %s %s Make Acclog Error %s" %
                    (req.reqid, req.ip, req.funcname, traceback.format_exc()))
            except BaseException:
                traceback.print_exc()

        return httpstatus, headers, content

    def perform_msg(self, msg, queue):
        """Performs the actual work of a msg.  Will/should only be called
        inside the work horse's process.
        """

        started_msg_registry = queue.started_msg_registry
        try:
            msg.started_at = utcnow()
            msg.set_status(MsgStatus.STARTED)

            ip = msg.ip
            reqid = msg.get_id()
            data = json.loads(msg.data)
            QUERY_STRING = urllib.urlencode(data)
            wsgienv = {
                "PATH_INFO": queue.name,
                "QUERY_STRING": QUERY_STRING,
                "REQUEST_METHOD": "GET"
            }
            req = httpgateway.Request(reqid, wsgienv, ip)
            protocol = self.apicube[queue.name]
            httpstatus, headers, content = protocol(req)
            # acclog
            self._mk_ret(req, httpstatus, headers, content)
            msg.ended_at = utcnow()

            # content is a set
            msg._result = content[0]

            if req.log_ret_code == "OK":
                self.log.info('%s: %s (%s)', msg.origin, 'Msg OK', msg.id)
                self.handle_msg_success(msg=msg, queue=queue, started_msg_registry=started_msg_registry)
            else:
                self.log.error('%s: %s (%s)', msg.origin, 'Msg ERROR', msg.id)
                exc_string = self._get_safe_exception_string(req.error_detail)
                self.handle_msg_failure(msg=msg, exc_string=exc_string, started_msg_registry=started_msg_registry)
        except BaseException:
            self.log.error('worker exe msg exception {exception_info}'.format(exception_info=traceback.format_exc()))
            return False
        return True

    def executor_callback(self, task):
        """
        Record task execution exception
        """
        logging.info("called worker callback function")
        task_exception = task.exception()
        if task_exception:
            logging.exception("Worker return exception: {}".format(task_exception))

    def work(self):
        """Starts the work loop.

        Pops and performs all msgs on the current list of queues.  When all
        queues are empty, block and wait for new msgs to arrive on any of the
        queues

        The return value indicates whether any msgs were processed.
        """
        while True:
            try:
                if self._stop_requested:
                    self.log.info('Worker %s: stopping on request', self.key)
                    break

                result = self.queue_class.dequeue_any(
                    self.queues, connection=self.connection, msg_class=self.msg_class)

                if result is None:
                    time.sleep(5)
                    continue

                if result == defaults.RATE_LIMITED:
                    time.sleep(0.02)
                    continue

                msg, queue = result
                msg.set_status(MsgStatus.STARTED)
                self.connection.hset(msg.key, 'started_at', utcformat(utcnow()))

                task = self.pool.submit(self.perform_msg, msg=msg, queue=queue)
                task.add_done_callback(self.executor_callback)
            except BaseException:
                self.log.error(
                    'worker get msg exception {exception_info}'.format(
                        exception_info=traceback.format_exc()))
        return result
