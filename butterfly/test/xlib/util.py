#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-08-09 23:11:31

# File Name: util.py
# Description:

"""


def get_header_dict(headers):
    header_dict = {}
    for header in headers:
        assert isinstance(header[0], str)
        assert isinstance(header[1], str)
        header_dict[header[0]] = header[1]

    return header_dict
