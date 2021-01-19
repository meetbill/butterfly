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

# File Name: section.py
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
import json
import hashlib
from datetime import datetime

from xlib.httpgateway import Request
from xlib.middleware import funcattr
from xlib.db import shortcuts

from handlers.wuxing.models import model
from handlers.wuxing.libs import retstat


__info = "wuxing"
__version = "1.0.1"


@funcattr.api
def section_list(req, page_index=1, page_size=10):
    """
    Args:
        namespace   : (str) 命名空间
        page_index  : (int) 页数
        page_size   : (int) 每页显示条数
    """
    isinstance(req, Request)
    section_model = model.WuxingSection
    data = {}
    data_list = []

    select_list = [
        section_model.namespace,
        section_model.section_name,
        section_model.section_version,
        section_model.section_md5,
        section_model.is_enabled,
        section_model.u_time
    ]

    query_cmd = section_model.select(*select_list)

    record_count = query_cmd.count()
    record_list = query_cmd.paginate(int(page_index), int(page_size))
    for record in record_list:
        record_dict = shortcuts.model_to_dict(record, only=select_list)
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def section_create(req, namespace, section_name, section_version):
    """
    创建 section 模板配置
    """
    isinstance(req, Request)
    op_user = req.username
    section_template = "{}"
    md5 = hashlib.md5()
    md5.update(section_template)
    section_md5 = md5.hexdigest()[:8]
    # get_or_create 的参数是 **kwargs，其中 defaults 为非查询条件的参数
    try:
        instance_data, is_create = model.WuxingSection.get_or_create(
            namespace=namespace,
            section_name=section_name,
            section_version=section_version,
            defaults={
                "section_template": section_template,
                "section_md5": section_md5,
                "user": op_user}
        )
    except BaseException as e:
        req.error_str = str(e)
        return retstat.ERR_SECTION_CREATE_FAILED, {}, [(__info, __version)]

    if is_create:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_SECTION_IS_EXIST, {}, [(__info, __version)]


@funcattr.api
def section_item_add(req, namespace, section_name, section_version, item_name,
                     item_type, item_default, item_description):
    """
    创建 section 模板配置

    只能对未启用状态的 section 进行变更
    """
    isinstance(req, Request)
    op_user = req.username
    section_model = model.WuxingSection

    if item_type not in ["string", "int", "float", "bool"]:
        return retstat.ERR_SECTION_ITEM_TYPE_FAILED, {}, [(__info, __version)]

    section_object = section_model.get_or_none(section_model.namespace == namespace,
                                               section_model.section_name == section_name,
                                               section_model.section_version == section_version
                                               )
    # 检查 section 是否存在
    if section_object is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    # 检查 section 是否是未启用状态
    if section_object.is_enabled:
        return retstat.ERR_SECTION_IS_ENABLED, {}, [(__info, __version)]

    section_template_dict = json.loads(section_object.section_template)
    if item_name in section_template_dict.keys():
        return retstat.ERR_SECTION_ITEM_IS_EXIST, {}, [(__info, __version)]

    section_template_dict[item_name] = {}
    section_template_dict[item_name]["a1"] = item_type
    section_template_dict[item_name]["a2"] = item_default
    section_template_dict[item_name]["a3"] = item_description

    section_template = json.dumps(section_template_dict)
    md5 = hashlib.md5()
    md5.update(section_template)
    section_md5 = md5.hexdigest()[:8]

    update_data = {}
    update_data[section_model.section_template] = section_template
    update_data[section_model.section_md5] = section_md5
    update_data[section_model.u_time] = datetime.now()
    update_data[section_model.user] = op_user

    effect_count = section_model.update(update_data).where(section_model.namespace == namespace,
                                                           section_model.section_name == section_name,
                                                           section_model.section_version == section_version,
                                                           section_model.u_time == section_object.u_time).execute()

    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_SECTION_ITEM_ADD_FAILED, {}, [(__info, __version)]


@funcattr.api
def section_item_delete(req, namespace, section_name, section_version, item_name):
    """
    删除 section item

    只能对未启用状态的 section 进行操作
    """
    isinstance(req, Request)
    op_user = req.username
    section_model = model.WuxingSection

    section_object = section_model.get_or_none(section_model.namespace == namespace,
                                               section_model.section_name == section_name,
                                               section_model.section_version == section_version
                                               )
    # 检查 section 是否存在
    if section_object is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    # 检查 section 是否是未启用状态
    if section_object.is_enabled:
        return retstat.ERR_SECTION_IS_ENABLED, {}, [(__info, __version)]

    section_template_dict = json.loads(section_object.section_template)
    if item_name not in section_template_dict.keys():
        return retstat.ERR_SECTION_ITEM_IS_NOT_EXIST, {}, [(__info, __version)]

    section_template_dict.pop(item_name)

    section_template = json.dumps(section_template_dict)
    md5 = hashlib.md5()
    md5.update(section_template)
    section_md5 = md5.hexdigest()[:8]

    update_data = {}
    update_data[section_model.section_template] = section_template
    update_data[section_model.section_md5] = section_md5
    update_data[section_model.u_time] = datetime.now()
    update_data[section_model.user] = op_user

    effect_count = section_model.update(update_data).where(section_model.namespace == namespace,
                                                           section_model.section_name == section_name,
                                                           section_model.section_version == section_version,
                                                           section_model.u_time == section_object.u_time).execute()

    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_SECTION_ITEM_DELETE_FAILED, {}, [(__info, __version)]


@funcattr.api
def section_get(req, namespace, section_name, section_version):
    """
    获取 section 模板配置
    """
    isinstance(req, Request)
    section_model = model.WuxingSection
    section_object = section_model.get_or_none(section_model.namespace == namespace,
                                               section_model.section_name == section_name,
                                               section_model.section_version == section_version
                                               )
    if section_object is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    data = {}
    data["section_template"] = {}
    section_template_dict = json.loads(section_object.section_template)
    for item_name in section_template_dict.keys():
        data["section_template"][item_name] = {}
        data["section_template"][item_name]["item_type"] = section_template_dict[item_name]["a1"]
        data["section_template"][item_name]["item_default"] = section_template_dict[item_name]["a2"]
        data["section_template"][item_name]["item_description"] = section_template_dict[item_name]["a3"]

    data["is_enabled"] = section_object.is_enabled

    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def section_enable(req, namespace, section_name, section_version):
    """
    获取 section 模板配置
    """
    isinstance(req, Request)
    section_model = model.WuxingSection
    section_object = section_model.get_or_none(section_model.namespace == namespace,
                                               section_model.section_name == section_name,
                                               section_model.section_version == section_version
                                               )
    if section_object is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]
    update_data = {}
    update_data[section_model.is_enabled] = True

    effect_count = section_model.update(update_data).where(section_model.namespace == namespace,
                                                           section_model.section_name == section_name,
                                                           section_model.section_version == section_version).execute()

    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_SECTION_ENABLE_FAILED, {}, [(__info, __version)]


@funcattr.api
def section_delete(req, namespace, section_name, section_version):
    """
    删除 section_delete
    """
    isinstance(req, Request)
    section_model = model.WuxingSection
    section_object = section_model.get_or_none(section_model.namespace == namespace,
                                               section_model.section_name == section_name,
                                               section_model.section_version == section_version
                                               )
    if section_object is None:
        return retstat.ERR_SECTION_IS_NOT_EXIST, {}, [(__info, __version)]

    # 删除此实例
    effect_count = section_object.delete_instance()
    if effect_count:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR_SECTION_DELETE_FAILED, {}, [(__info, __version)]
