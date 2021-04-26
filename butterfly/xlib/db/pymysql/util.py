# coding=utf8
"""
# File Name: util.py
# Description:

"""
import struct


def byte2int(b):
    """
    byte -> int
    """
    if isinstance(b, int):
        return b
    else:
        return struct.unpack("!B", b)[0]


def int2byte(i):
    """
    int -> byte
    """
    return struct.pack("!B", i)

