#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-02-28 12:49:53

# File Name: item_cache.py
# Description:
    item 记录缓存
"""
import json

from handlers.wuxing.models import model
from handlers.wuxing.libs import cache
from xlib.db import shortcuts
from handlers.wuxing.libs import common_map


class ItemCache(object):
    """
    wuxing cache
    """
    _cache_key_template = "WX_item@{item_id}"
    # 用于检查缓存的数据版本，当数据缓存很长时间，同时又需要在缓存的 key 中增加新的字段时，可以通过更改此项强制刷新
    _cache_version = "1.0.1"

    @classmethod
    def get(cls, subreq, item_id, item_type):
        """
        获取 section data

        Args:
            subreq          : (object)
            item_id         : (str) item_id
            item_type       : (str) item type
        Returns:
            item_data    : (Dict)
                item_value
                u_time
            or None
        """
        cache_key = cls._cache_key_template.format(
            item_id=item_id
        )
        item_dict = cache.Cache.get(subreq, cache_key)
        if item_dict is not None:
            cache_version = item_dict.pop("cache_version", None)
            if cache_version == cls._cache_version:
                return item_dict

        item_model = model.WuxingInstanceItem
        item_object = item_model.get_or_none(item_model.id == item_id)
        if item_object is None:
            return None

        item_data_dict = shortcuts.model_to_dict(item_object)
        value_field = common_map.value_field_map[item_type]
        item_value = item_data_dict[value_field]
        u_time = item_data_dict["u_time"]

        # 添加数据到缓存
        item_dict = {}
        item_dict["item_value"] = item_value
        item_dict["u_time"] = u_time
        item_dict["cache_version"] = cls._cache_version
        # 缓存一周
        cache.Cache.set(subreq, cache_key, item_dict, 604800)
        return item_dict

    @classmethod
    def delete(cls, subreq, item_id):
        """
        删除 item cache

        Args:
            subreq          : (object)
            item_id         : (str) item_id
        Returns:
            bool
        """
        cache_key = cls._cache_key_template.format(
            item_id=item_id
        )
        return cache.Cache.delete(subreq, cache_key)
