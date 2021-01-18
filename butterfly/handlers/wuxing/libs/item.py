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

# File Name: item.py
# Description:
    五行 API

"""
from datetime import datetime
from xlib.httpgateway import Request
from xlib.middleware import funcattr
from xlib.db import shortcuts
from xlib.db import peewee

from handlers.wuxing.models import model
from handlers.wuxing.libs import retstat


__info = "wuxing"
__version = "1.0.1"


modeltype_map = {
    "bool": bool,
    "int": int,
    "float": float,
    "string": str,
}

value_field_map = {
    "bool": "item_value_bool",
    "int": "item_value_int",
    "float": "item_value_float",
    "string": "item_value_string",
}

modelhistory_map = {
    "bool": model.WuxingHistoryBool,
    "int": model.WuxingHistoryInt,
    "float": model.WuxingHistoryFloat,
    "string": model.WuxingHistoryString,
}


def get_value_by_modeltype(modeltype, value_old):
    """
    Args:
        modeltype: (String) bool/int/float/string
        value_old: (String/Int/Float/Bool)
    return:
        value
    """
    # 如果期望类型与传的类型一致，则直接返回内容
    if modeltype == "string" and isinstance(value_old, str):
        return value_old

    if modeltype == "bool" and isinstance(value_old, bool):
        return value_old

    if modeltype == "float" and isinstance(value_old, float):
        return value_old

    if modeltype == "int" and isinstance(value_old, int):
        return value_old

    # 如果期望类型与传的类型不一致，则进行强制转换类型
    if modeltype == "string":
        return str(value_old)
    if modeltype == "int":
        return int(value_old)
    if modeltype == "float":
        return float(value_old)
    if modeltype == "bool":
        if value_old.lower() == "false":
            return False
        else:
            return True


@funcattr.api
def item_list(req, namespace=None, section_name=None, instance_name=None, item_name=None, page_index=1, page_size=10):
    """
    获取对应 item 的数据

    (namespace, instance_name, item_name) 三者条件，正常情况下只有 1 条数据
    (namespace, section_name, item_name) 可以输出 instance 列表

    Args:
        namespace       : (str) 命名空间
        section_name    : (str) section name
        instance_name   : (str) instance name
        item_name       : (str) item name
        page_index      : (int) 页数
        page_size       : (int) 每页显示条数
    Returns:
        stat, data, header_list
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem
    data = {}
    data_list = []

    query_cmd = item_model.select()
    expressions = []
    if namespace is not None:
        expressions.append(peewee.NodeList((item_model.namespace, peewee.SQL('='), namespace)))

    if section_name is not None:
        expressions.append(peewee.NodeList((item_model.section_name, peewee.SQL('='), section_name)))

    if instance_name is not None:
        expressions.append(peewee.NodeList((item_model.instance_name, peewee.SQL('='), instance_name)))

    if item_name is not None:
        expressions.append(peewee.NodeList((item_model.item_name, peewee.SQL('='), item_name)))

    if len(expressions):
        query_cmd = query_cmd.where(*expressions)

    record_count = query_cmd.count()
    record_list = query_cmd.paginate(int(page_index), int(page_size))
    for record in record_list:
        record_dict_source = shortcuts.model_to_dict(record)
        record_dict = {}
        record_dict["item_id"] = record_dict_source["id"]
        record_dict["namespace"] = record_dict_source["namespace"]
        record_dict["section_name"] = record_dict_source["section_name"]
        record_dict["instance_name"] = record_dict_source["instance_name"]
        record_dict["item_name"] = record_dict_source["item_name"]
        # 将 item_value_bool/item_value_int/item_value_string/item_value_float 转换为 item_value
        item_type = record_dict_source["item_type"]
        item_field = value_field_map[item_type]
        record_dict["item_value"] = record_dict_source[item_field]
        record_dict["user"] = record_dict_source["user"]
        record_dict["c_time"] = record_dict_source["c_time"]
        record_dict["u_time"] = record_dict_source["u_time"]
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def item_get(req, item_id, item_type):
    """
    Args:
        item_id  : item_id
        item_type: item value 类型
    Returns:
        stat, data, header_list
            data: {"data":{"item_value": item_value, "u_time": u_time}}
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem

    instance_data = item_model.get_or_none(item_model.id == item_id)
    if instance_data is None:
        return retstat.ERR_ITEM_IS_NOT_FOUND, {}, [(__info, __version)]

    instance_data_dict = shortcuts.model_to_dict(instance_data)
    value_field = value_field_map[item_type]
    item_value = instance_data_dict[value_field]
    u_time = instance_data_dict["u_time"]
    return retstat.OK, {"data": {"item_value": item_value, "u_time": u_time}}, [(__info, __version)]


@funcattr.api
def item_update(req, item_id, item_type, item_value):
    """
    更新 item value
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem
    op_user = req.username

    new_value = get_value_by_modeltype(item_type, item_value)
    value_field = value_field_map[item_type]

    update_data = {}
    update_data[value_field] = new_value
    update_data["user"] = op_user
    update_data["u_time"] = datetime.now()

    effect_count = item_model.update(update_data).where(
        item_model.id == item_id).execute()

    if effect_count == 1:
        modelhistory_map[item_type].create(item_id=item_id, item_value=new_value, cmd="update", user=op_user)
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR, {}, [(__info, __version)]


@funcattr.api
def item_create(req, namespace, section_name, instance_name, item_name, item_type, item_value):
    """
    创建 item
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem

    op_user = req.username
    new_value = get_value_by_modeltype(item_type, item_value)
    value_field = value_field_map[item_type]

    data = {}
    data["namespace"] = namespace
    data["section_name"] = section_name
    data["instance_name"] = instance_name
    data["item_name"] = item_name
    data["item_type"] = item_type
    data[value_field] = new_value
    data["user"] = op_user

    item_id = item_model.insert(data).execute()

    if item_id:
        modelhistory_map[item_type].create(
            item_id=item_id,
            item_value=new_value,
            cmd="create",
            user=op_user)

        return retstat.OK, {"data": item_id}, [(__info, __version)]
    else:
        return retstat.ERR_ITEM_INSERT_FAILD, {}, [(__info, __version)]


@funcattr.api
def item_delete(req, item_id):
    """
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem
    effect_count = item_model.delete_by_id(int(item_id))
    if effect_count:
        return retstat.OK, {"data": {}}, [(__info, __version)]
    else:
        return retstat.ERR_ITEM_DELETE_FAILED, {"data": {}}, [(__info, __version)]


@funcattr.api
def item_delete_of_instance(req, namespace, instance_name):
    """
    """
    isinstance(req, Request)
    item_model = model.WuxingInstanceItem
    record_list = item_model.select(
        item_model.id).where(
        item_model.namespace == namespace,
        item_model.instance_name == instance_name)
    for record in record_list:
        item_stat, item_data, header_list = item_delete(req, record.id)
        if item_stat != retstat.OK:
            return item_stat, item_data, header_list

    return retstat.OK, {"data": {}}, [(__info, __version)]
