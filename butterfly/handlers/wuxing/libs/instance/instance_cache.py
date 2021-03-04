#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-02-28 12:49:53

# File Name: instance_cache.py
# Description:
    instance 记录缓存

"""
import json

from handlers.wuxing.models import model
from handlers.wuxing.libs import cache


class InstanceCache(object):
    """
    wuxing cache
    """
    _cache_key_template = "WX_instance@{namespace}@{instance_name}"
    # 用于检查缓存的数据版本，当数据缓存很长时间，同时又需要在缓存的 key 中增加新的字段时，可以通过更改此项强制刷新
    _cache_version = "1.0.1"

    @classmethod
    def get(cls, subreq, namespace, instance_name):
        """
        获取 instance data

        Args:
            subreq          : (object)
            namespace       : (str) 名字空间
            instance_name   : (str) instance name
        Returns:
            instance_data    : (Dict)
                instance_template
                is_valid
            or None
        """
        cache_key = cls._cache_key_template.format(
            namespace=namespace,
            instance_name=instance_name
        )
        instance_dict = cache.Cache.get(subreq, cache_key)
        if instance_dict is not None:
            cache_version = instance_dict.pop("cache_version", None)
            if cache_version == cls._cache_version:
                return instance_dict

        instance_model = model.WuxingInstance
        instance_object = instance_model.get_or_none(model.WuxingInstance.namespace == namespace,
                                                     model.WuxingInstance.instance_name == instance_name)
        if instance_object is None:
            return None

        # 添加数据到缓存
        instance_dict = {}
        instance_dict["instance_template_dict"] = json.loads(instance_object.instance_template)
        instance_dict["is_valid"] = instance_object.is_valid
        instance_dict["cache_version"] = cls._cache_version
        # 缓存一周
        cache.Cache.set(subreq, cache_key, instance_dict, 604800)
        return instance_dict

    @classmethod
    def delete(cls, subreq, namespace, instance_name):
        """
        删除 instance cache

        Args:
            subreq          : (object)
            namespace       : (str) 名字空间
            instance_name   : (str) instance_name
        Returns:
            bool
        """
        cache_key = cls._cache_key_template.format(
            namespace=namespace,
            instance_name=instance_name,
        )
        return cache.Cache.delete(subreq, cache_key)
