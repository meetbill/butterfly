#!/usr/bin/python
# coding=utf8
##########################################################################
#
# Copyright (c) 2020 Baidu.com, Inc. All Rights Reserved
#
##########################################################################
"""
# Author: wangbin34
# Created Time : 2020-02-23 21:40:27

# File Name: instance.py
# Description:
    五行 API

    section_template/instance_template 压缩大小：
        (1) 通过 attr 缩写(a1...) 代替 (item_type 等), 减少 key 长度
        (2) section_template 中没有 item_id
        (3) item 属性中去掉 item_name
    字节对比：
        (1) item_id+item_name+item_type+item_default+item_description = 53 个字节
        (2) id+a1+a1+a3=8 字节
        +-------+---------+------------+----------------+
        |   id  |   a1    |    a2      |       a3       |
        +-------+---------+------------+----------------+
        |item_id|item_type|item_default|item_description|
        +-------+---------+------------+----------------+
"""
from datetime import datetime
import copy
import json

from xlib.httpgateway import Request
from xlib.middleware import funcattr
from xlib.db import shortcuts
from xlib.db import peewee

from handlers.wuxing.models import model
from handlers.wuxing.libs import retstat
from handlers.wuxing.libs import item


__info = "wuxing"
__version = "1.0.1"


@funcattr.api
def instance_list(req, namespace, section_name, instance_name=None,
                  section_version=None, section_md5=None, extra_items=None,
                  page_index=1, page_size=10):
    """
    获取 instance 列表

    Args:
        namespace       : (str) 必传，命名空间, 匹配时进行完全匹配
        section_name    : (str) 必传，section name, 匹配时进行完全匹配
        instance_name   : (str) 选传，instance name, 匹配时进行模糊匹配
        section_version : (str) 选传, section 版本，匹配时进行完全匹配
        section_md5     : (str) 选传，section md5, 匹配时进行完全匹配
        extra_items     : (str) 选传, 此参数用于获取额外 item 进行列表展示，多个item 使用冒号 ":" 进行分割
        page_index      : (int) 页数
        page_size       : (int) 每页显示条数
    """
    isinstance(req, Request)
    instance_model = model.WuxingInstance
    data = {}
    data_list = []

    select_list = [
        instance_model.namespace,
        instance_model.instance_name,
        instance_model.section_name,
        instance_model.section_version,
        instance_model.section_md5,
        instance_model.u_time
    ]

    if extra_items is not None:
        extra_item_list = extra_items.split(":")
        select_list.append(instance_model.instance_template)
    else:
        extra_item_list = []

    query_cmd = instance_model.select(*select_list)
    expressions = []
    if namespace is not None:
        expressions.append(peewee.NodeList((instance_model.namespace, peewee.SQL('='), namespace)))

    if section_name is not None:
        expressions.append(peewee.NodeList((instance_model.section_name, peewee.SQL('='), section_name)))

    if instance_name is not None:
        instance_name = "%{instance_name}%".format(instance_name=instance_name)
        expressions.append(peewee.NodeList((instance_model.instance_name, peewee.SQL('LIKE'), instance_name)))

    if section_version is not None:
        expressions.append(peewee.NodeList((instance_model.section_version, peewee.SQL('='), section_version)))

    if section_md5 is not None:
        expressions.append(peewee.NodeList((instance_model.section_md5, peewee.SQL('='), section_md5)))

    if len(expressions):
        query_cmd = query_cmd.where(*expressions)

    record_count = query_cmd.count()
    record_list = query_cmd.paginate(int(page_index), int(page_size))
    for record in record_list:
        record_dict = shortcuts.model_to_dict(record, only=select_list)
        if not extra_item_list:
            data_list.append(record_dict)
            continue

        instance_template_dict = json.loads(record_dict["instance_template"])
        # 列表求交集
        extra_item_reality_list = list(set(extra_item_list) & set(instance_template_dict.keys()))
        for item_name in extra_item_reality_list:
            # 获取 item_value
            item_id = instance_template_dict[item_name]["id"]
            item_type = instance_template_dict[item_name]["a1"]
            stat, item_data, headher_list = item.item_get(req, item_id, item_type)

            # 将 item 信息合并到 record_dict
            record_dict[item_name] = item_data["data"]["item_value"]

        # 返回列表时去掉模板信息
        record_dict.pop("instance_template")
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def instance_create(req, namespace, instance_name, section_name, section_version):
    """
    创建时会创建模板关联，以及创建初始配置
    """
    isinstance(req, Request)
    instance_model = model.WuxingInstance
    section_model = model.WuxingSection

    # 检查是否有此 instance
    instance_object = instance_model.get_or_none(instance_model.namespace == namespace,
                                                 instance_model.instance_name == instance_name
                                                 )
    if instance_object is not None:
        return retstat.ERR_INSTANCE_IS_EXIST, {}, [(__info, __version)]

    # 获取模板
    section_data = section_model.get_or_none(section_model.namespace == namespace,
                                             section_model.section_name == section_name,
                                             section_model.section_version == section_version
                                             )
    if section_data is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    if not section_data.is_enabled:
        return retstat.ERR_SECTION_IS_NOT_ENABLED, {}, [(__info, __version)]

    section_template_dict = json.loads(section_data.section_template)
    for item_name in section_template_dict.keys():
        item_dict = section_template_dict[item_name]
        item_type = item_dict["a1"]
        item_default = item_dict["a2"]

        # 进行创建 item
        stat, item_data, headher_list = item.item_create(req, namespace, section_name,
                                                         instance_name, item_name,
                                                         item_type, item_default)

        if stat != retstat.OK:
            return stat, {}, [(__info, __version)]
        section_template_dict[item_name]["id"] = item_data["data"]

    template_str = json.dumps(section_template_dict)
    # 插入模板
    # get_or_create 的参数是 **kwargs，其中 defaults 为非查询条件的参数
    model.WuxingInstance.create(
        namespace=namespace,
        instance_name=instance_name,
        instance_template=template_str,
        section_name=section_name,
        section_version=section_version,
        section_md5=section_data.section_md5,
    )
    return retstat.OK, {}, [(__info, __version)]


@funcattr.api
def instance_update_section(req, namespace, instance_name, section_version):
    """
    更新模板关联，以及创建初始配置，更新 section 版本
    * 新的模板可能新增 item
    * 新的模板可能删除 item
    """
    isinstance(req, Request)
    section_model = model.WuxingSection
    instance_model = model.WuxingInstance

    # 检查是否有此 instance
    instance_object = instance_model.get_or_none(instance_model.namespace == namespace,
                                                 instance_model.instance_name == instance_name
                                                 )
    # 获取 instance 旧模板
    if instance_object is None:
        return retstat.ERR_INSTANCE_IS_NOT_EXIST, {}, [(__info, __version)]
    template_old = json.loads(instance_object.instance_template)
    template_new = copy.deepcopy(template_old)

    section_name = instance_object.section_name
    # 获取 section 新模板
    section_data = section_model.get_or_none(section_model.namespace == namespace,
                                             section_model.section_name == section_name,
                                             section_model.section_version == section_version
                                             )
    if section_data is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    if not section_data.is_enabled:
        return retstat.ERR_SECTION_IS_NOT_ENABLED, {}, [(__info, __version)]

    template_section = json.loads(section_data.section_template)

    # 需要新增的 item
    add_list = list(set(template_section.keys()) - set(template_old.keys()))
    remove_list = list(set(template_old.keys()) - set(template_section.keys()))

    # 进行新增 item
    for item_name in add_list:
        item_dict = template_section[item_name]
        item_type = item_dict["a1"]
        item_default = item_dict["a2"]

        item_stat, item_data, headher_list = item.item_create(req, namespace, section_name,
                                                              instance_name, item_name,
                                                              item_type, item_default)
        if item_stat != retstat.OK:
            return item_stat, {}, [(__info, __version)]

        template_new[item_name] = item_dict
        template_new[item_name]["id"] = item_data["data"]

    # 进行删除 item
    for item_name in remove_list:
        item_dict = template_old[item_name]
        item_stat, item_data, headher_list = item.item_delete(req, item_dict["id"])
        if item_stat != retstat.OK:
            return item_stat, {}, [(__info, __version)]

        template_new.pop(item_name)

    template_str = json.dumps(template_new)
    # 更新模板
    query = instance_model.update(
        section_version=section_version,
        instance_template=template_str,
        section_md5=section_data.section_md5,
        u_time=datetime.now()
    ).where(instance_model.namespace == namespace, instance_model.instance_name == instance_name)
    effect_count = query.execute()
    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_INSTANCE_UPDATE_FAILED, {}, [(__info, __version)]


@funcattr.api
def instance_get(req, namespace, instance_name, item_name=None):
    """
    Args:
        namespace: namespace
        instance_name: instance_name
        item_name: item key

    Returns:
        dict
        {
            key1:{
                key1_attr1: xxx,
                key1_attr2: xxx
            },
            key2:{
                key2_attr1: xxx,
                key2_attr2: xxx
            }
        }
        当请求特定的 key 时，直接返回此 key 的 value
        dict
        {
            key1: xxx/None
        }
    """
    isinstance(req, Request)
    instance_model = model.WuxingInstance
    # 此处可以检查是否有缓存

    # 检查是否有此 instance
    instance_object = instance_model.get_or_none(model.WuxingInstance.namespace == namespace,
                                                 model.WuxingInstance.instance_name == instance_name)
    if instance_object is None:
        return retstat.ERR_INSTANCE_IS_NOT_EXIST, {}, [(__info, __version)]

    if not instance_object.is_valid:
        return retstat.ERR_INSTANCE_IS_NOT_VALID, {}, [(__info, __version)]

    # 模板也可以缓存住
    instance_data = json.loads(instance_object.instance_template)

    data = {}
    if item_name is None:
        for key_ in instance_data.keys():
            item_id = instance_data[key_]["id"]
            item_type = instance_data[key_]["a1"]
            item_description = instance_data[key_]["a3"]

            # 将模板 + item_value 进行合并
            data[key_] = {}
            data[key_]["item_id"] = item_id
            data[key_]["item_name"] = key_
            data[key_]["item_type"] = item_type
            data[key_]["item_description"] = item_description

            # 获取 item_value
            stat, item_data, headher_list = item.item_get(req, item_id, item_type)
            data[key_]["item_value"] = item_data["data"]["item_value"]
            data[key_]["u_time"] = item_data["data"]["u_time"]

        return retstat.OK, {"data": data}, [(__info, __version)]

    if item_name not in instance_data.keys():
        return retstat.ERR_ITEM_IS_NOT_EXIST, {"data": data}, [(__info, __version)]

    item_id = instance_data[item_name]["id"]
    item_type = instance_data[item_name]["a1"]
    item_description = instance_data[item_name]["a3"]
    stat, item_data, headher_list = item.item_get(req, item_id, item_type)
    if stat != retstat.OK:
        return stat, {}, [(__info, __version)]

    data = {}
    data["item_name"] = item_name
    data["item_id"] = item_id
    data["item_type"] = item_type
    data["item_value"] = item_data["data"]["item_value"]
    data["item_description"] = item_description
    data["u_time"] = item_data["data"]["u_time"]

    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def instance_update_item(req, namespace, instance_name, item_name, item_value):
    """
    更新 item
    """
    isinstance(req, Request)
    instance_model = model.WuxingInstance

    # 检查是否有此 instance
    instance_object = instance_model.get_or_none(instance_model.namespace == namespace,
                                                 instance_model.instance_name == instance_name
                                                 )
    if instance_object is None:
        return retstat.ERR_INSTANCE_IS_NOT_EXIST, {}, [(__info, __version)]

    # 获取模板
    template_str = instance_object.instance_template
    template_dict = json.loads(template_str)

    # 检查 key 是否存在
    if item_name not in template_dict.keys():
        return retstat.ERR_ITEM_IS_NOT_EXIST, {}, [(__info, __version)]

    item_id = template_dict[item_name]["id"]
    item_type = template_dict[item_name]["a1"]
    return item.item_update(req, item_id, item_type, item_value)


@funcattr.api
def instance_delete(req, namespace, instance_name):
    """
    Args:
        namespace: {String} 命名空间
        instance: {String}
    Returns:
        stat, data_dict, headher_list
    """
    isinstance(req, Request)
    instance_model = model.WuxingInstance

    # 检查是否有此 instance
    instance_object = instance_model.get_or_none(instance_model.namespace == namespace,
                                                 instance_model.instance_name == instance_name
                                                 )
    if instance_object is None:
        return retstat.ERR_INSTANCE_IS_NOT_EXIST, {}, [(__info, __version)]

    # 删除此实例的所有 item
    item_stat, item_data, headher_list = item.item_delete_of_instance(req, namespace, instance_name)
    if item_stat != retstat.OK:
        return item_stat, item_data, headher_list

    # 删除此实例
    effect_count = instance_object.delete_instance()
    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_INSTANCE_DELETE_FAILED, {}, [(__info, __version)]
