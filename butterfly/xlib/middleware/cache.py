#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-08-14 11:33:24

# File Name: cache.py
# Description:

---------------------------------------------------- example
from xlib.middleware.cache import cache_page

# 缓存 1 秒
@cache_page(expire=1)
def generate_landing_page():
    return 3
----------------------------------------------------
"""

from xlib import diskcache as _dc

_cache = _dc.Cache()
cache_page = _cache.memoize
