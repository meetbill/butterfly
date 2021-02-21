#!/usr/bin/python
# coding=utf8
"""
# File Name: worker_registration.py
# Description:

"""

from .compat import as_text


WORKERS_BY_QUEUE_KEY = 'mq:workers:%s'
REDIS_WORKER_KEYS = 'mq:workers'


def register(worker):
    """Store worker key in Redis so we can easily discover active workers."""
    connection = worker.connection
    connection.sadd(worker.redis_workers_keys, worker.key)
    for name in worker.queue_names():
        redis_key = WORKERS_BY_QUEUE_KEY % name
        connection.sadd(redis_key, worker.key)


def unregister(worker):
    """Remove worker key from Redis."""
    connection = worker.connection

    connection.srem(worker.redis_workers_keys, worker.key)
    for name in worker.queue_names():
        redis_key = WORKERS_BY_QUEUE_KEY % name
        connection.srem(redis_key, worker.key)


def get_keys(queue=None, connection=None):
    """Returnes a list of worker keys for a queue"""
    if queue is None and connection is None:
        raise ValueError('"queue" or "connection" argument is required')

    if queue:
        redis = queue.connection
        redis_key = WORKERS_BY_QUEUE_KEY % queue.name
    else:
        redis = connection
        redis_key = REDIS_WORKER_KEYS

    return {as_text(key) for key in redis.smembers(redis_key)}


def clean_worker_registry(queue):
    """Delete invalid worker keys in registry

    定时清理未发送心跳的 worker
    """
    keys = list(get_keys(queue))

    with queue.connection.pipeline(transaction=False) as pipeline:

        for key in keys:
            pipeline.exists(key)
        results = pipeline.execute()

        invalid_keys = []

        for i, key_exists in enumerate(results):
            if not key_exists:
                invalid_keys.append(keys[i])

        if invalid_keys:
            pipeline.srem(WORKERS_BY_QUEUE_KEY % queue.name, *invalid_keys)
            pipeline.srem(REDIS_WORKER_KEYS, *invalid_keys)
            pipeline.execute()
