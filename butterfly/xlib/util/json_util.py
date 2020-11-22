#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-03-23 20:19:31

# File Name: json_util.py
# Description:
    str,int,list,tuple,dict,bool,None 这些数据类型都支撑 json 序列化操作。
    但是 datetime 类型不支持 json 序列化，我们可以自定义 datetime 的序列化。

"""
import json
import datetime


def json_default(obj):
    """
    json default
    """
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')

    return obj


if __name__ == "__main__":
    d = {'name': 'meetbill', 'age': 18, 'data': datetime.datetime.now()}
    print json.dumps(d, default=json_default)
