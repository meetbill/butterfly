# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 18:12:58

# File Name: __init__.py
# Description: mcpack-2 协议的 python 实现；
    1）序列化过程，将对象转化为 mcpack 协议的字节编码，并返回字节流；
    2）反序列化过程：将 mcpack 协议的字节流转化对象（值）。
"""

import struct
from xlib.ral.mcpack import mcpackitem


def dumps(ele, mcpack_item=None):
    """将对象序列化为 mcpack 协议的字节流
    @param ele: 对象值
    @param mcpack_item: mcpack_item == None ? 根据ele值自动选择mcpack解析类型
    @return: mcpack 协议字节流
    """
    try:
        if mcpack_item is None:
            mcpack_item = mcpackitem.McpackItemFactory.get_item_by_ele(ele)
        packvalue_list = []
        size = mcpack_item.serialize(packvalue_list, None, ele)
        pacformat_list = []
        for i in range(size):
            pacformat_list.append('b')

        return struct.pack(''.join(pacformat_list), *packvalue_list)
    except BaseException:
        raise


def loads(byte_source):
    """将 mcpack 协议的字节编码反序列化为对象（值）
    @param byte_source: 字节流
    @return: 值:1)基本类型值，或者2）字符串str，或者3）数组list，或者4）对象dict
    """
    try:
        length = len(byte_source)
        if length <= 0:
            return None
        formatstr = '' + str(length) + 'b'
        byte_tuple = struct.unpack(formatstr, byte_source)
        flag = byte_tuple[0]
        item = mcpackitem.McpackItemFactory.get_item_by_flag(flag)
        if item:
            (pose, element) = item.deserialize(byte_tuple, 0)
            return element
        else:
            return None
    except BaseException:
        raise
