#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2020-05-01 10:37:21

# File Name: test_apidemo-hello.py
# Description:
    用于测试 apidemo/hello handler

"""


from handlers.apidemo import hello
from xlib import httpgateway

def test_hello():
    # 生成 req
    reqid="test_hello"
    ip = "127.0.0.1"
    wsgienv = {}
    req = httpgateway.Request(reqid, wsgienv, ip)

    # OK
    assert hello(req, "test_info") == (200, {'stat': 'OK', 'str_info': 'test_info'}, [('http_demo', '1.0.1')])
