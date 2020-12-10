"""
Lightweight Python utilities for working with Redis.


Removed:
    tusks
Changed:
    Model.__database__ ==> Model._database_
    Model.__namespace__ ==> Model._namespace_
"""

_author_ = 'Charles Leifer'
_license_ = 'MIT'
_version_ = '0.8.1'

#               ___
#            .-9 9 `\
#          =(:(::)=  ;
#            ||||     \
#            ||||      `-.
#           ,\|\|         `,
#          /                \
#         ;                  `'---.,
#         |                         `\
#         ;                     /     |
#         \                    |      /
#  jgs     )           \  __,.--\    /
#       .-' \,..._\     \`   .-'  .-'
#      `-=``      `:    |   /-/-/`
#                   `.__/

from xlib.db.redisorm.autocomplete import Autocomplete
from xlib.db.redisorm.cache import Cache
from xlib.db.redisorm.containers import Array
from xlib.db.redisorm.containers import BitField
from xlib.db.redisorm.containers import BloomFilter
from xlib.db.redisorm.containers import ConsumerGroup
from xlib.db.redisorm.containers import Container
from xlib.db.redisorm.containers import Hash
from xlib.db.redisorm.containers import HyperLogLog
from xlib.db.redisorm.containers import List
from xlib.db.redisorm.containers import Set
from xlib.db.redisorm.containers import Stream
from xlib.db.redisorm.containers import ZSet
from xlib.db.redisorm.counter import Counter
from xlib.db.redisorm.database import Database
from xlib.db.redisorm.fts import Index
from xlib.db.redisorm.graph import Graph
from xlib.db.redisorm.lock import Lock
from xlib.db.redisorm.models import *
from xlib.db.redisorm.rate_limit import RateLimit
from xlib.db.redisorm.rate_limit import RateLimitException
from xlib.db.redisorm.streams import Message
from xlib.db.redisorm.streams import TimeSeries

# Friendly alias.
Walrus = Database
