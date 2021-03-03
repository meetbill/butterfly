#!/usr/bin/python
# coding=utf8
"""
# File Name: defaults.py
# Description:

"""

# Redis 中 Msg key 前缀
REDIS_MSG_NAMESPACE_PREFIX = 'mq:msg:'
# Redis 中队列的汇总 key
REDIS_QUEUES_KEYS = 'mq:queues'
# Redis 中队列 name 的 key 前缀
REDIS_QUEUE_NAMESPACE_PREFIX = 'mq:queue:'
DEFAULT_WORKER_TTL = 420
DEFAULT_RESULT_TTL = 31536000   # 1 year in seconds
DEFAULT_FAILURE_TTL = 31536000  # 1 year in seconds

# 限速标识
RATE_LIMITED="RATE_LIMITED"
