#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2019-07-18 21:15:03

# File Name: test_httpgateway_app.py
# Description:

"""

from test.xlib import util


def test_demo_file1(init_data):
    """
    test func demo_test1
    """
    environ = {
        "PATH_INFO": "/demo_file1",
        "REMOTE_ADDR": "192.10.10.10",
        "QUERY_STRING": ""
    }
    status, headers, content = init_data.process(environ)
    header_dict = util.get_header_dict(headers)
    assert status == "200 OK"
    assert header_dict["Content-Type"] == "text/html; charset=UTF-8"
