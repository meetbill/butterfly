# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:31:25

# File Name: pack.py
# Description:
    number 打包
"""

import struct


def to_int8(b):
    """byte to int8
    """
    return struct.unpack("<b", str(b))[0]


def pack_int8(v):
    """int8 to byte
    """
    return struct.pack("<b", v.value)


def to_int16(b):
    """byte to int16
    """
    return struct.unpack("<h", str(b))[0]


def pack_int16(v):
    """int16 to byte
    """
    return struct.pack("<h", v.value)


def to_int32(b):
    """byte to int32
    """
    return struct.unpack("<i", str(b))[0]


def pack_int32(v):
    """int32 to byte
    """
    return struct.pack("<i", v.value)


def to_int64(b):
    """byte to int64
    """
    return struct.unpack("<q", str(b))[0]


def pack_int64(v):
    """int64 to byte
    """
    return struct.pack("<q", v.value)


def to_uint8(b):
    """byte to uint8
    """
    return struct.unpack("<B", str(b))[0]


def pack_uint8(v):
    """uint8 to byte
    """
    return struct.pack("<B", v.value)


def to_uint16(b):
    """byte to uint16
    """
    return struct.unpack("<H", str(b))[0]


def pack_uint16(v):
    """uint16 to byte
    """
    return struct.pack("<H", v.value)


def to_uint32(b):
    """byte to uint32
    """
    return struct.unpack("<I", str(b))[0]


def pack_uint32(v):
    """uint32 to byte
    """
    return struct.pack("<I", v.value)


def to_uint64(b):
    """byte to uint64
    """
    return struct.unpack("<Q", str(b))[0]


def pack_uint64(v):
    """uint64 to byte
    """
    return struct.pack("<Q", v.value)


def to_float(b):
    """byte to float
    """
    return struct.unpack("<f", str(b))[0]


def pack_float(v):
    """float to byte
    """
    return struct.pack("<f", v.value)


def to_double(b):
    """byte to double
    """
    return struct.unpack("<d", str(b))[0]


def pack_double(v):
    """double to byte
    """
    return struct.pack("<d", v.value)
