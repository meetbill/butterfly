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

# File Name: item_history.py
# Description:
    五行 API

"""
from xlib.httpgateway import Request
from xlib.middleware import funcattr
from xlib.db import shortcuts
from xlib.db import peewee

from handlers.wuxing.libs import retstat
from handlers.wuxing.libs import common_map


__info = "wuxing"
__version = "1.0.1"


@funcattr.api
def item_history_list(req, item_type, item_id, page_index=1, page_size=10):
    """
    获取对应 item 的历史数据

    Args:
        item_type       : (str) item type
        item_id         : (str) item id
        page_index      : (int) 页数
        page_size       : (int) 每页显示条数
    """
    isinstance(req, Request)
    if item_type not in common_map.modelhistory_map.keys():
        return retstat.ERR_ITEM_TYPE_NOT_FOUND, {}, [__info, __version]

    item_history_model = common_map.modelhistory_map[item_type]
    data = {}
    data_list = []

    query_cmd = item_history_model.select()
    expressions = []
    expressions.append(peewee.NodeList((item_history_model.item_id, peewee.SQL('='), item_id)))
    if len(expressions):
        query_cmd = query_cmd.where(*expressions)

    record_count = query_cmd.count()
    record_list = query_cmd.paginate(int(page_index), int(page_size))
    for record in record_list:
        record_dict = shortcuts.model_to_dict(record)
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]
