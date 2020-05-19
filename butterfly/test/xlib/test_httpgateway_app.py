#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2019-07-18 21:15:03

# File Name: test_httpgateway_app.py
# Description:

"""
from conf import config

def test_demo_test1(init_data):
    """
    test func demo_test1
    """
    # ERR_BAD_PARAMS
    environ={
            "PATH_INFO":"/demo_test1",
            "REMOTE_ADDR": "192.10.10.10"
            }

    status, headers, content = init_data.process(environ)
    assert status == "200 OK"
    assert content == ('{"stat": "ERR_BAD_PARAMS"}',)

    environ={
            "PATH_INFO":"/demo_test1",
            "REMOTE_ADDR": "192.10.10.10",
            "QUERY_STRING": "str_info1=meetbill"
            }
    status, headers, content = init_data.process(environ)
    assert status == "200 OK"
    ## headers : [('Content-Length', '26'), ('x-reqid', 'B820746074ACC4AF'), ('x-cost', '0.000111'), ('x-reason', 'Param check failed')]

    #-------------------------------------------------------------------
    # 通过循环 headers 方式获取方式会漏掉 header 不存在的情况
    #
    # 举个例子
    # 在 xlib/httpgateway.py:_mk_ret 中添加 header 失败或者写 acclog 日志失败, 当 headers 不存在对应的属性值时，则误判
    # 可以将 headers 通过 dict(headers) 转为字典, 然后
    #-------------------------------------------------------------------

    headers_dict = dict(headers)
    x_reason = headers_dict.get("x-reason") or ""
    assert x_reason == "Param check failed"

    assert content == ('{"stat": "ERR_BAD_PARAMS"}',)

    # OK
    environ={
            "PATH_INFO":"/demo_test1",
            "REMOTE_ADDR": "192.10.10.10",
            "QUERY_STRING": "str_info=meetbill"
            }
    status, headers, content = init_data.process(environ)
    assert status == "200 OK"
    ## headers:[('Content-Length', '38'), ('x-reqid', '32E6F4F44155B85F'), ('x-cost', '0.000206')]

    assert content == ('{"stat": "OK", "str_info": "meetbill"}',)

def test_400(init_data):
    """
    not found api
    """
    # ERR_BAD_PARAMS
    environ={
            "PATH_INFO":"/demo_401",
            "REMOTE_ADDR": "192.10.10.10"
            }
    status, headers, content = init_data.process(environ)
    assert status == "400 Bad Request"
    ## headers:[('x-reqid', '83CAEEF6E4C397B7'), ('x-cost', '0.000029'), ('x-reason', 'API Not Found')]
    headers_dict = dict(headers)
    x_reason = headers_dict.get("x-reason") or ""
    assert x_reason == "API Not Found"

    assert content == ""


def test_static(init_data):
    """
    If there is a static file flag, the static file path is returned
    """
    # File Not Found
    static_prefix = config.STATIC_PREFIX
    environ1={
            "PATH_INFO":"/{prefix}/static_file".format(prefix = static_prefix),
            "REMOTE_ADDR": "192.10.10.10"
            }
    status, headers, content = init_data.process(environ1)
    assert status == "404 Not Found"
    ## headers:[('x-reqid', '83CAEEF6E4C397B7'), ('x-cost', '0.000029'), ('x-reason', 'File Not Found')]
    headers_dict = dict(headers)
    x_reason = headers_dict.get("x-reason") or ""
    assert x_reason == "File Not Found"

    assert content == ""

    # File exist
