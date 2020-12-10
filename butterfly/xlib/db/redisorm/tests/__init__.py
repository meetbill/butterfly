import sys
import unittest

from xlib.db.redisorm.tests.autocomplete import *
from xlib.db.redisorm.tests.cache import *
from xlib.db.redisorm.tests.containers import *
from xlib.db.redisorm.tests.counter import *
from xlib.db.redisorm.tests.database import *
from xlib.db.redisorm.tests.fts import *
from xlib.db.redisorm.tests.graph import *
from xlib.db.redisorm.tests.lock import *
from xlib.db.redisorm.tests.models import *
from xlib.db.redisorm.tests.rate_limit import *
from xlib.db.redisorm.tests.streams import *



if __name__ == '__main__':
    unittest.main(argv=sys.argv)
