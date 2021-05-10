# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:31:25

# File Name: const.py
# Description:
    mcpack v2 协议支持类型
"""


MCPACKV2_INVALID = 0x00
"""对象字节标识"""
MCPACKV2_OBJECT = 0x10  # 16
"""字符串字节标识"""
MCPACKV2_ARRAY = 0x20   # 32
"""字符串字节标识"""
MCPACKV2_STRING = 0x50  # 80
MCPACKV2_BINARY = 0x60
"""一个字节INT字节标识"""
MCPACKV2_INT8 = 0x11    # 17
"""二个字节INT字节标识"""
MCPACKV2_INT16 = 0x12   # 18
"""四个字节INT字节标识"""
MCPACKV2_INT32 = 0x14   # 20
"""八个字节INT字节标识"""
MCPACKV2_INT64 = 0x18   # 24
"""一个字节unsigned int字节标识"""
MCPACKV2_UINT8 = 0x21   # 33
"""二个字节unsigned int字节标识"""
MCPACKV2_UINT16 = 0x22  # 34
"""四个字节unsigned int字节标识"""
MCPACKV2_UINT32 = 0x24  # 36
"""八个字节unsigned int字节标识"""
MCPACKV2_UINT64 = 0x28  # 40
"""布尔值字节标识"""
MCPACKV2_BOOL = 0x31    # 49
"""单精度浮点数字节标识"""
MCPACKV2_FLOAT = 0x44   # 68
"""双精度浮点数字节标识"""
MCPACKV2_DOUBLE = 0x48  # 72
MCPACKV2_DATE = 0x58
"""空值标识"""
MCPACKV2_NULL = 0x61    # 97
MCPACKV2_SHORT_ITEM = 0x80
MCPACKV2_FIXED_ITEM = 0xf0
MCPACKV2_DELETED_ITEM = 0x70

MCPACKV2_SHORT_STRING = MCPACKV2_STRING | MCPACKV2_SHORT_ITEM
MCPACKV2_SHORT_BINARY = MCPACKV2_BINARY | MCPACKV2_SHORT_ITEM

MCPACKV2_KEY_MAX_LEN = 255  # 0xff
MAX_SHORT_VITEM_LEN = 255  # 0xff
