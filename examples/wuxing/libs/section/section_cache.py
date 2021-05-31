#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-02-28 12:49:53

# File Name: section_cache.py
# Description:
    Section 记录缓存
"""
import json

from handlers.wuxing.models import model
from handlers.wuxing.libs import cache


class SectionCache(object):
    """
    wuxing cache
    """
    _cache_key_template = "WX_section@{namespace}@{section_name}@{section_version}"
    # 用于检查缓存的数据版本，当数据缓存很长时间，同时又需要在缓存的 key 中增加新的字段时，可以通过更改此项强制刷新
    _cache_version = "1.0.1"

    @classmethod
    def get(cls, subreq, namespace, section_name, section_version):
        """
        获取 section data

        Args:
            subreq          : (object)
            namespace       : (str) 名字空间
            section_name    : (str) section name
            section_version : (str) section version
        Returns:
            section_data    : (Dict)
                section_template
                section_md5
                is_enabled

            or None
        """
        cache_key = cls._cache_key_template.format(
            namespace=namespace,
            section_name=section_name,
            section_version=section_version
        )
        section_dict = cache.Cache.get(subreq, cache_key)
        if section_dict is not None:
            cache_version = section_dict.pop("cache_version", None)
            if cache_version == cls._cache_version:
                return section_dict

        section_model = model.WuxingSection
        section_object = section_model.get_or_none(section_model.namespace == namespace,
                                                   section_model.section_name == section_name,
                                                   section_model.section_version == section_version
                                                   )
        if section_object is None:
            return None

        # 添加数据到缓存
        section_data = {}
        section_data["section_template_dict"] = json.loads(section_object.section_template)
        section_data["is_enabled"] = section_object.is_enabled
        section_data["section_md5"] = section_object.section_md5
        section_data["cache_version"] = cls._cache_version
        # 缓存一周
        cache.Cache.set(subreq, cache_key, section_data, 604800)
        return section_data

    @classmethod
    def delete(cls, subreq, namespace, section_name, section_version):
        """
        删除 section cache

        Args:
            subreq          : (object)
            namespace       : (str) 名字空间
            section_name    : (str) section name
            section_version : (str) section version
        Returns:
            bool
        """
        cache_key = cls._cache_key_template.format(
            namespace=namespace,
            section_name=section_name,
            section_version=section_version
        )
        return cache.Cache.delete(subreq, cache_key)
