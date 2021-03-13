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
from xlib.db.redisorm.rate_limit import RateLimit
from xlib.db.redisorm.rate_limit import RateLimitException
from xlib.db.redisorm.streams import Message
from xlib.db.redisorm.streams import TimeSeries

# models
from xlib.db.redisorm.models import Field
from xlib.db.redisorm.models import IntegerField
from xlib.db.redisorm.models import AutoIncrementField
from xlib.db.redisorm.models import FloatField
from xlib.db.redisorm.models import ByteField
from xlib.db.redisorm.models import TextField
from xlib.db.redisorm.models import BooleanField
from xlib.db.redisorm.models import UUIDField
from xlib.db.redisorm.models import DateTimeField
from xlib.db.redisorm.models import DateField
from xlib.db.redisorm.models import JSONField
from xlib.db.redisorm.models import PickledField
from xlib.db.redisorm.models import HashField
from xlib.db.redisorm.models import ListField
from xlib.db.redisorm.models import SetField
from xlib.db.redisorm.models import ZSetField
from xlib.db.redisorm.models import Query
from xlib.db.redisorm.models import BaseIndex
from xlib.db.redisorm.models import AbsoluteIndex
from xlib.db.redisorm.models import ContinuousIndex
from xlib.db.redisorm.models import FullTextIndex
from xlib.db.redisorm.models import BaseModel
from xlib.db.redisorm.models import Model

# Friendly alias.
Walrus = Database
