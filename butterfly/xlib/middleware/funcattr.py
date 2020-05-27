#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-02-01 15:23:59

# File Name: funcattr.py
# Description:
    对 handler 函数添加属性

    is_parse_post: 是否将请求 body 数据使用 json.loads() 解析 post 数据
                   如果请求是上传文件的话，则不需要进行解析，应该设置为 False
                   如果请求是请求的参数的话，则需要设置为 True
    is_encode_response: 是否将响应包转为 json
                   目前如果返回数据为 dict 的话，则自动转为 json

"""
def api(func):
    """
    common api

    (1) 解析请求 body 中数据
    (2) 编码 Response body 数据

    Args:
        func: handler func
    Returns:
        func
    """
    func.apiattr = {"is_parse_post": True, "is_encode_response": True}
    return func


def api_download(func):
    """

    (1) 解析请求 body 中数据
    (2) 不编码 Response body 数据

    Args:
        func: handler func
    Returns:
        func
    """
    # default
    func.apiattr = {"is_parse_post": True, "is_encode_response": False}
    return func


def api_upload(func):
    """

    (1) 不解析请求 body 中数据
    (2) 编码 Response body 数据

    Args:
        func: handler func
    Returns:
        func
    """
    func.apiattr = {"is_parse_post": False, "is_encode_response": True}
    return func
