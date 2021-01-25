#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-01-24 12:41:27

# File Name: common_map.py
# Description:

"""
from handlers.wuxing.models import model

# 根据 item_prefix 获取当前 item_type
item_type_map = {
    "i|": "int",
    "s|": "string",
    "f|": "float",
    "b|": "bool"
}

# 根据 item_type 获取存储 item 值 field
value_field_model_map = {
    "bool": model.WuxingInstanceItem.item_value_bool,
    "int": model.WuxingInstanceItem.item_value_int,
    "float": model.WuxingInstanceItem.item_value_float,
    "string": model.WuxingInstanceItem.item_value_string,
}

# 根据 item_type 获取转换方法
modeltype_map = {
    "bool": bool,
    "int": int,
    "float": float,
    "string": str,
}

# 根据 item_type 获取存储 item 值 field
value_field_map = {
    "bool": "item_value_bool",
    "int": "item_value_int",
    "float": "item_value_float",
    "string": "item_value_string",
}

# 根据 item_type 获取 item 历史表 model
modelhistory_map = {
    "bool": model.WuxingHistoryBool,
    "int": model.WuxingHistoryInt,
    "float": model.WuxingHistoryFloat,
    "string": model.WuxingHistoryString,
}
