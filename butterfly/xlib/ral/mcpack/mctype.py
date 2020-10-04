# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:33:03

# File Name: mctype.py
# Description:
    封装 python 不知道的特殊类型，比如 uint_32 等
"""


class McUint8(object):
    """uint_8 类型的整形值"""

    def __init__(self, value):
        self.value = value


class McUint16(object):
    """uint_16 类型的整形值"""

    def __init__(self, value):
        self.value = value


class McUint32(object):
    """uint_32 类型的整形值"""

    def __init__(self, value):
        self.value = value


class McUint64(object):
    """uint_64 类型的整形值"""

    def __init__(self, value):
        self.value = value
