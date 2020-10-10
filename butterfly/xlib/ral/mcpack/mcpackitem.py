# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:31:25

# File Name: mcpackitem.py
# Description:
    此模块：
    1）构建 mcpack 序列化、反序列化的类: McpackItem及其子类；
    2）构建实例化 McpackItem 的工厂类 McpackItemFactory。
"""
import struct

from xlib.ral.mcpack import mctype

MCPACKV2_BOOL = 0x31  # 49
"""布尔值字节标识"""
MCPACKV2_INT_8 = 0x11  # 17
"""一个字节INT字节标识"""
MCPACKV2_UINT_8 = 0x21  # 33
"""一个字节unsigned int字节标识"""
MCPACKV2_INT_16 = 0x12  # 18
"""二个字节INT字节标识"""
MCPACKV2_UINT_16 = 0x22  # 34
"""二个字节unsigned int字节标识"""
MCPACKV2_INT_32 = 0x14  # 20
"""四个字节INT字节标识"""
MCPACKV2_UINT_32 = 0x24  # 36
"""四个字节unsigned int字节标识"""
MCPACKV2_INT_64 = 0x18  # 24
"""八个字节INT字节标识"""
MCPACKV2_UINT_64 = 0x28  # 40
"""八个字节unsigned int字节标识"""
MCPACKV2_FLOAT = 0x44  # 68
"""单精度浮点数字节标识"""
MCPACKV2_DOUBLE = 0x48  # 72
"""双精度浮点数字节标识"""
MCPACKV2_STRING = 0x50  # 80
"""字符串字节标识"""
MCPACKV2_ARRAY = 0x20  # 32
"""字符串字节标识"""
MCPACKV2_OBJECT = 0x10  # 16
"""对象字节标识"""
MCPACKV2_NULL = 0x61  # 97
"""空值标识"""
MCPACKV2_SHORT_ITEM = -128  # 128
MCPACKV2_FIXED_ITEM = 0xf  # 15

# 基本类型的边界
UINT8_MAX = 2 ** 8
UINT16_MAX = 2 ** 16
UINT32_MAX = 2 ** 32
UINT64_MAX = 2 ** 64
INT8_MIN = -(2 ** 7)
INT8_MAX = 2 ** 7 - 1
INT16_MIN = -(2 ** 15)
INT16_MAX = 2 ** 15 - 1
INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1
INT64_MIN = -(2 ** 63)
INT64_MAX = 2 ** 63 - 1
FLOAT_MIN = -3.4E38
FLOAT_MAX = 3.4E38
DOUBLE_MIN = -1.7E308
DOUBLE_MAX = 1.7E308


class McpackItem(object):
    """mcpack的基类
    @attention: 考虑到python面向对象的能力，继承更多考虑的是代码复用
    """

    def serialize(self, packvalue_list, name, element):
        """序列化过程
        @param packvalue_list: 打包的字节数组（返回值）
        @param name: 字段名字
        @param element: 对象值
        @raise NotSpecifiedTypeError: 必须指定具体类型（自定义）
        @return: size 打包数组的长度
        """
        raise NotSpecifiedTypeError(self)

    def deserialize(self, byte_tuple, pos):
        """反序列化过程
        @param byte_tuple: 字节数组
        @param pos: 数组的当前位置
        @raise NotSpecifiedTypeError: 必须指定具体类型（自定义）
        @return: (pos,re_decode)
        pos：解包字节数组的当前位置，
        re_decode：解包值：1)基本类型值，或者2）字符串str，或者3）数组list，或者4）对象dict
        """
        raise NotSpecifiedTypeError(self)

    def write_name(self, packvalue_list, name):
        """将字段名称进行编码
        @param packvalue_list: 打包的字节数组（返回值）
        @param name: 字段名
        @return: size 打包数组长度
        """
        size = 0
        if name:
            barr = self.str_to_bytes(name)

            packvalue_list.append(len(barr) + 1)
            size += 1

            for ba in barr:
                size += 1
                packvalue_list.append(ba)
        packvalue_list.append(0)
        size += 1
        return size

    def read_name(self, byte_tuple, pos):
        """读取字段名称
        @param byte_tuple: 解包的字节数组
        @param pos: 数组的当前位置
        @return: (rawname , pos)
        rawname:名称
        pos：解包字节数组的当前位置
        """
        name_len = byte_tuple[pos]
        pos += 1
        rawname = None
        if name_len > 0:
            byList = []
            for i in range(name_len - 1):
                by = byte_tuple[pos + i]
                if by < 0:
                    by = 256 + by
                byList.append(chr(by))
            rawname = ''.join(byList)
            pos += name_len

        return (rawname, pos)

    def write_complex_name_len(self, packvalue_list, name):
        """计算复杂类型字段名称长度并进行编码
        @param packvalue_list: 打包的字节数组（返回值）
        @param name: 字段名
        @return: (name_byte_list,size)
        name_byte_list:字段名称的编码
        size: 打包数组长度
        """
        size = 0
        name_byte_list = []
        if name:
            name_byte_list = self.str_to_bytes(name)
            packvalue_list.append(len(name_byte_list) + 1)
            size += 1
        else:
            packvalue_list.append(0)
            size += 1
        return (name_byte_list, size)

    def write_complex_name(self, packvalue_list, name_byte_list):
        """将复杂字段名称进行编码
        @param packvalue_list: 打包的字节数组（返回值）
        @param name_byte_list: 字段名数组
        @return: size 打包数组长度
        """
        size = 0
        if name_byte_list and len(name_byte_list) > 0:
            for ba in name_byte_list:
                size += 1
                packvalue_list.append(ba)
            packvalue_list.append(0)
            size += 1
        return size

    def read_complex_name(self, byte_tuple, pos, name_len):
        """读取字段名称
        @param byte_tuple: 解包的字节数组
        @param pos: 数组的当前位置
        @return: (rawname , pos)
        rawname:名称
        pos：解包字节数组的当前位置
        """
        rawname = None
        if name_len > 0:
            bylist = []
            for i in range(name_len - 1):
                by = byte_tuple[pos + i]
                if by < 0:
                    by = 256 + by
                bylist.append(chr(by))
            rawname = ''.join(bylist)
            pos += name_len

        return (rawname, pos)

    def str_to_bytes(self, source_str):
        """将字符串转化为字节数组
        @param source_str: 字符串
        @return: alist 字节数组
        """
        alist = []
        barr = bytearray(source_str)
        for ba in barr:
            if ba > 127:
                ba = ba - 256
            elif ba < -128:
                ba = 256 + ba
            alist.append(ba)
        return alist

    def primitive_serialize(self, packvalue_list, name, element, flag, fmt, byte_len):
        """基本类型的打包过程
        @param packvalue_list: 打包的字节数组（返回值）
        @param name: 字段名字
        @param element: 对象值
        @param flag: 类型标记
        @param fmt: 值类型
        @param byte_len: 对象值的字节数
        @return: size 打包数组长度
        """
        size = 0
        packvalue_list.append(flag)
        size += 1

        size += self.write_name(packvalue_list, name)
        if flag == MCPACKV2_NULL:
            element = 0
        byte_list = self.primitive_to_bytes(element, fmt)
        for ele in byte_list:
            packvalue_list.append(ele)
        size += byte_len
        return size

    def deserialize_primitive(self, byte_tuple, pos, fmt, byte_len):
        """基本类型的解包过程
        @param byte_tuple: 解包字节数组
        @param pos: 数组的当前位置
        @param fmt: 值类型
        @param byte_len: 对象值的字节数
        @return: (pos,re_decode)
        pos：解包字节数组的当前位置，
        re_decode：解包值,基本类型值
        """
        flag = byte_tuple[pos]
        re_decode = None
        pos += 1

        rawname, pos = self.read_name(byte_tuple, pos)

        byte_list = []
        for i in range(byte_len):
            byte_list.append(byte_tuple[pos + i])
        value = None
        if flag != MCPACKV2_NULL:
            value = self.bytes_to_primitive(byte_list, fmt)
        if rawname:
            re_decode = {rawname: value}
        else:
            re_decode = value
        pos += byte_len
        return (pos, re_decode)

    def primitive_to_bytes(self, value, fmt):
        """使用struct将python基本类型值转化为字节数组
        @param value: 需要转化的值
        @param fmt: 值类型，c->char,b->signed char,B->unsigned char,?->_Bool,h->short,H->unsigned short,
        i->int,I->unsigned int,l->long,L->unsigned long,f->float,d->double
        @return: byte_list->字节数组
        @see: struct
        @raise OutOfBoundError: 长度越界异常（自定义）
        """
        try:
            # unsigned -> signed
            if fmt == 'B':
                if value < 0 or value > UINT8_MAX:
                    raise OutOfBoundError('type is UINT8,value is ' + str(value))
                if value > INT8_MAX:
                    value = value - UINT8_MAX
                elif value < INT8_MIN:
                    value = UINT8_MAX + value
                fmt = 'b'
            elif fmt == 'H':
                if value < 0 or value > UINT16_MAX:
                    raise OutOfBoundError('type is UINT16,value is ' + str(value))
                if value > INT16_MAX:
                    value = value - UINT16_MAX
                elif value < INT16_MIN:
                    value = UINT16_MAX + value
                fmt = 'h'
            elif fmt == 'I':
                if value < 0 or value > UINT32_MAX:
                    raise OutOfBoundError('type is UINT32,value is ' + str(value))
                if value > INT32_MAX:
                    value = value - UINT32_MAX
                elif value < INT32_MIN:
                    value = UINT32_MAX + value
                fmt = 'i'
            elif fmt == 'L':
                if value < 0 or value > UINT64_MAX:
                    raise OutOfBoundError('type is UINT64,value is ' + str(value))
                if value > INT64_MAX:
                    value = value - UINT64_MAX
                elif value < INT64_MIN:
                    value = UINT64_MAX + value
                fmt = 'q'

            length = 0
            if fmt in ['b', '?']:
                if value < INT8_MIN or value > INT8_MAX:
                    raise OutOfBoundError('type is INT8,value is ' + str(value))
                length = 1
            elif fmt == 'h':
                if value < INT16_MIN or value > INT16_MAX:
                    raise OutOfBoundError('type is INT16,value is ' + str(value))
                length = 2
            elif fmt == 'i':
                if value < INT32_MIN or value > INT32_MAX:
                    raise OutOfBoundError('type is INT32,value is ' + str(value))
                length = 4
            elif fmt == 'f':
                if value < FLOAT_MIN or value > FLOAT_MAX:
                    raise OutOfBoundError('type is float,value is ' + str(value))
                length = 4
            elif fmt == 'q':
                if value < INT64_MIN or value > INT64_MAX:
                    raise OutOfBoundError('type is INT64,value is ' + str(value))
                length = 8
            elif fmt == 'd':
                if value < DOUBLE_MIN or value > DOUBLE_MAX:
                    raise OutOfBoundError('type is double,value is ' + str(value))
                length = 8
            byte_str = struct.pack(fmt, value)
            un_fmt = '' + str(length) + 'b'
            if length == 8:
                try:
                    atuple = struct.unpack('bbbbbbbb', byte_str)
                    return list(atuple)
                except BaseException:
                    temp = struct.unpack('bbbb', byte_str)
                    atuple = list(temp)
                    atuple.append(0)
                    atuple.append(0)
                    atuple.append(0)
                    atuple.append(0)
                    return atuple
            else:
                atuple = struct.unpack(un_fmt, byte_str)
                return list(atuple)
        except BaseException:
            raise

    def bytes_to_primitive(self, byte_list, fmt):
        """使用struct将字节数组转化成python基本类型
        @param byte_list: 需要转化的字节数组
        @param fmt: 值类型，c->char,b->signed char,B->unsigned char,?->_Bool,h->short,H->unsigned short,
        i->int,I->unsigned int,l->long,L->unsigned long,f->float,d->double
        @return: value->基本类型的值
        @see: struct
        """
        try:
            length = len(byte_list)

            b_fmt = '' + str(length) + 'b'
            byte_str = struct.pack(b_fmt, *byte_list)
            value = 0
            if length == 8:
                try:
                    (value,) = struct.unpack(fmt, byte_str)
                except BaseException:
                    (value,) = struct.unpack('q', byte_str)
            else:
                (value,) = struct.unpack(fmt, byte_str)
            if fmt == 'B':
                value &= 0xff
            elif fmt == 'H':
                value &= 0xffff
            elif fmt == 'I':
                value &= 0xffffffff
            elif fmt == 'L':
                value &= 0xffffffffffffffff
            return value
        except BaseException:
            raise


class McpackBolean(McpackItem):
    """布尔值"""
    flag = MCPACKV2_BOOL
    fmt = '?'
    byte_len = 1

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackBolean.flag,
                                        McpackBolean.fmt, McpackBolean.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackBolean.fmt, McpackBolean.byte_len)


class McpackNull(McpackItem):
    """空值"""
    flag = MCPACKV2_NULL
    fmt = 'b'
    byte_len = 1

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackNull.flag,
                                        McpackNull.fmt, McpackNull.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackNull.fmt, McpackNull.byte_len)


class McpackInt8(McpackItem):
    """8位整型"""
    flag = MCPACKV2_INT_8
    fmt = 'b'
    byte_len = 1

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackInt8.flag,
                                        McpackInt8.fmt, McpackInt8.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackInt8.fmt, McpackInt8.byte_len)


class McpackUInt8(McpackItem):
    """8位无符号位整型"""
    flag = MCPACKV2_UINT_8
    fmt = 'B'
    byte_len = 1

    def serialize(self, packvalue_list, name, element):
        element = element.value
        return self.primitive_serialize(packvalue_list, name, element, McpackUInt8.flag,
                                        McpackUInt8.fmt, McpackUInt8.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackUInt8.fmt, McpackUInt8.byte_len)


class McpackInt16(McpackItem):
    """16 位整型"""
    flag = MCPACKV2_INT_16
    fmt = 'h'
    byte_len = 2

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackInt16.flag,
                                        McpackInt16.fmt, McpackInt16.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackInt16.fmt, McpackInt16.byte_len)


class McpackUInt16(McpackItem):
    """16 位无符号整型"""
    flag = MCPACKV2_UINT_16
    fmt = 'H'
    byte_len = 2

    def serialize(self, packvalue_list, name, element):
        element = element.value
        return McpackItem.primitive_serialize(self, packvalue_list, name, element,
                                              McpackUInt16.flag, McpackUInt16.fmt, McpackUInt16.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackUInt16.fmt, McpackUInt16.byte_len)


class McpackInt32(McpackItem):
    """32 位整型"""
    flag = MCPACKV2_INT_32
    fmt = 'i'
    byte_len = 4

    def serialize(self, packvalue_list, name, element):
        return McpackItem.primitive_serialize(self, packvalue_list, name, element,
                                              McpackInt32.flag, McpackInt32.fmt, McpackInt32.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackInt32.fmt, McpackInt32.byte_len)


class McpackUInt32(McpackItem):
    """32 位无符号整型"""
    flag = MCPACKV2_UINT_32
    fmt = 'I'
    byte_len = 4

    def serialize(self, packvalue_list, name, element):
        element = element.value
        return McpackItem.primitive_serialize(self, packvalue_list, name, element,
                                              McpackUInt32.flag, McpackUInt32.fmt, McpackUInt32.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackUInt32.fmt, McpackUInt32.byte_len)


class McpackInt64(McpackItem):
    """64 位整型"""
    flag = MCPACKV2_INT_64
    fmt = 'q'
    byte_len = 8

    def serialize(self, packvalue_list, name, element):
        return McpackItem.primitive_serialize(self, packvalue_list, name, element,
                                              McpackInt64.flag, McpackInt64.fmt, McpackInt64.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackInt64.fmt, McpackInt64.byte_len)


class McpackUInt64(McpackItem):
    """64 位无符号整型"""
    flag = MCPACKV2_UINT_64
    fmt = 'L'
    byte_len = 8

    def serialize(self, packvalue_list, name, element):
        element = element.value
        return self.primitive_serialize(packvalue_list, name, element, McpackUInt64.flag,
                                        McpackUInt64.fmt, McpackUInt64.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackUInt64.fmt, McpackUInt64.byte_len)


class McpackFloat(McpackItem):
    """单精度浮点数"""
    flag = MCPACKV2_FLOAT
    fmt = 'f'
    byte_len = 4

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackFloat.flag,
                                        McpackFloat.fmt, McpackFloat.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackFloat.fmt, McpackFloat.byte_len)


class McpackDouble(McpackItem):
    """双精度浮点数"""
    flag = MCPACKV2_DOUBLE
    fmt = 'd'
    byte_len = 8

    def serialize(self, packvalue_list, name, element):
        return self.primitive_serialize(packvalue_list, name, element, McpackDouble.flag,
                                        McpackDouble.fmt, McpackDouble.byte_len)

    def deserialize(self, byte_tuple, pos):
        return self.deserialize_primitive(byte_tuple, pos, McpackDouble.fmt, McpackDouble.byte_len)


class McpackString(McpackItem):
    """字符串"""

    def serialize(self, packvalue_list, name, element):
        length = len(element)
        size = 0

        if length > 254:
            packvalue_list.append(MCPACKV2_STRING)
        else:
            flag = MCPACKV2_STRING | MCPACKV2_SHORT_ITEM
            if flag > 127:
                flag = flag - 256
            elif flag < -128:
                flag = 256 + flag
            packvalue_list.append(flag)
        size += 1

        name_byte_list, temp_size = self.write_complex_name_len(packvalue_list, name)
        size += temp_size

        if length > 254:
            size += 4
            byte_list = self.primitive_to_bytes(length + 1, 'i')
            for ele in byte_list:
                packvalue_list.append(ele)
        else:
            size += 1
            ele_size = (length + 1) & 0xff
            if ele_size > 127:
                ele_size = ele_size - 256
            elif ele_size < -128:
                ele_size = 256 + ele_size
            packvalue_list.append(ele_size)

        size += self.write_complex_name(packvalue_list, name_byte_list)

        barr = self.str_to_bytes(element)
        for ba in barr:
            size += 1
            packvalue_list.append(ba)

        size += 1
        packvalue_list.append(0)
        return size

    def deserialize(self, byte_tuple, pos):
        re_decode = None
        ty = byte_tuple[pos]
        pos += 1

        name_len = byte_tuple[pos]
        pos += 1

        if ty & MCPACKV2_SHORT_ITEM == 0:
            length_list = []
            for i in range(4):
                length_list.append(byte_tuple[pos + i])
            length = self.bytes_to_primitive(length_list, 'i')
            pos += 4
        else:
            length = byte_tuple[pos]
            length = length & 0xff
            if length < 0:
                by = 256 + length
            pos += 1

        rawname, pos = self.read_complex_name(byte_tuple, pos, name_len)

        length = length - 1
        byList = []
        for i in range(length):
            by = byte_tuple[pos + i]
            if by < 0:
                by = 256 + by
            byList.append(chr(by))
        pos += length

        if rawname:
            re_decode = {rawname: ''.join(byList)}
        else:
            re_decode = ''.join(byList)

        pos += 1
        return (pos, re_decode)


class McpackArray(McpackItem):
    """数组"""

    def serialize(self, packvalue_list, name, element):

        pos = len(packvalue_list)
        size = 0
        size += 1
        packvalue_list.append(MCPACKV2_ARRAY)

        name_byte_list, temp_size = self.write_complex_name_len(packvalue_list, name)
        size += temp_size

        pos += size
        size += 4
        byte_list = self.primitive_to_bytes(0, 'i')
        for ele in byte_list:
            packvalue_list.append(ele)

        size += self.write_complex_name(packvalue_list, name_byte_list)

        step = 0

        size += 4
        step += 4
        byte_list = self.primitive_to_bytes(len(element), 'i')
        for ele in byte_list:
            packvalue_list.append(ele)

        for ele in element:
            item = McpackItemFactory.get_item_by_ele(ele)
            lenght = item.serialize(packvalue_list, None, ele)
            size += lenght
            step += lenght

        byte_list = self.primitive_to_bytes(step, 'i')
        i = 0
        for ele in byte_list:
            packvalue_list[pos + i] = ele
            i += 1

        return size

    def deserialize(self, byte_tuple, pos):
        re_decode = None
        pos += 1
        name_len = byte_tuple[pos]
        pos += 1

        length_list = []
        for i in range(4):
            length_list.append(byte_tuple[pos + i])
        pos += 4

        rawname, pos = self.read_complex_name(byte_tuple, pos, name_len)

        length_list = []
        for i in range(4):
            length_list.append(byte_tuple[pos + i])
        eleLength = self.bytes_to_primitive(length_list, 'i')
        pos += 4

        tempList = []
        for i in range(eleLength):
            flag = byte_tuple[pos]
            item = McpackItemFactory.get_item_by_flag(flag)
            if not item:
                break
            (pos, temp_decode) = item.deserialize(byte_tuple, pos)
            tempList.append(temp_decode)

        if rawname:
            re_decode = {rawname: tempList}
        else:
            re_decode = tempList

        return (pos, re_decode)


class McpackObject(McpackItem):
    """对象"""

    def serialize(self, packvalue_list, name, element):
        pos = len(packvalue_list)
        size = 0
        packvalue_list.append(MCPACKV2_OBJECT)
        size += 1

        name_byte_list, temp_size = self.write_complex_name_len(packvalue_list, name)
        size += temp_size

        pos += size
        byteList = self.primitive_to_bytes(0, 'i')
        for ele in byteList:
            packvalue_list.append(ele)
        size += 4

        size += self.write_complex_name(packvalue_list, name_byte_list)

        step = 0

        try:
            # 是对象
            ele_dict = element.__dict__
        except BaseException:
            # 是字典
            ele_dict = element
        byteList = self.primitive_to_bytes(len(ele_dict), 'i')
        for ele in byteList:
            packvalue_list.append(ele)
        size += 4
        step += 4

        for key in ele_dict:
            item = McpackItemFactory.get_item_by_ele(ele_dict[key])
            lenght = item.serialize(packvalue_list, key, ele_dict[key])
            size += lenght
            step += lenght

        byteList = self.primitive_to_bytes(step, 'i')
        i = 0
        for ele in byteList:
            packvalue_list[pos + i] = ele
            i += 1

        return size

    def deserialize(self, byte_tuple, pos):
        pos += 1
        name_len = byte_tuple[pos]
        pos += 1

        lengthList = []
        for i in range(4):
            lengthList.append(byte_tuple[pos + i])
        pos += 4

        rawname, pos = self.read_complex_name(byte_tuple, pos, name_len)

        lengthList = []
        for i in range(4):
            lengthList.append(byte_tuple[pos + i])
        eleLength = self.bytes_to_primitive(lengthList, 'i')
        pos += 4

        temp_dic = {}
        for i in range(eleLength):
            flag = byte_tuple[pos]
            item = McpackItemFactory.get_item_by_flag(flag)
            if not item:
                break
            (pos, temp_decode) = item.deserialize(byte_tuple, pos)
            if isinstance(temp_decode, dict):
                for key in temp_decode:
                    temp_dic[key] = temp_decode[key]

        if rawname:
            re_decode = {rawname: temp_dic}
        else:
            re_decode = temp_dic

        return (pos, re_decode)


class McpackItemFactory(object):
    """实例化McpackItem的工厂类"""
    boolean_item = McpackBolean()
    int8_item = McpackInt8()
    uint8_item = McpackUInt8()
    int16_item = McpackInt16()
    uint16_item = McpackUInt16()
    int32_item = McpackInt32()
    uint32_item = McpackUInt32()
    float_item = McpackFloat()
    double_item = McpackDouble()
    int64_item = McpackInt64()
    uint64_item = McpackUInt64()
    string_item = McpackString()
    array_item = McpackArray()
    object_item = McpackObject()
    null_item = McpackNull()
    error_item = McpackItem()

    @staticmethod
    def get_item_by_ele(element):
        """根据对象值，得到进行序列化的McpackItem对象
        @param element:   对象值
        @return: McpackItem对象
        """
        if element is None:
            return McpackItemFactory.null_item
        if isinstance(element, bool):
            return McpackItemFactory.boolean_item
        elif isinstance(element, mctype.McUint8):
            return McpackItemFactory.uint8_item
        elif isinstance(element, mctype.McUint16):
            return McpackItemFactory.uint16_item
        elif isinstance(element, mctype.McUint32):
            return McpackItemFactory.uint32_item
        elif isinstance(element, mctype.McUint64):
            return McpackItemFactory.uint64_item
        elif isinstance(element, int):
            return McpackItemFactory.int32_item
        elif isinstance(element, long):
            return McpackItemFactory.int64_item
        elif isinstance(element, float):
            return McpackItemFactory.double_item
        elif isinstance(element, str) or isinstance(element, unicode):
            return McpackItemFactory.string_item
        elif isinstance(element, tuple) or isinstance(element, list):
            return McpackItemFactory.array_item
        elif isinstance(element, object) or isinstance(element, dict):
            return McpackItemFactory.object_item
        else:
            return McpackItemFactory.error_item

    @staticmethod
    def get_item_by_flag(flag):
        """根据字节标志，得到进行反序列化的McpackItem对象
        @param flag: 字节（数据类型的标志）
        @return: McpackItem对象
        """
        if flag & MCPACKV2_FIXED_ITEM != 0:
            if flag == MCPACKV2_BOOL:
                return McpackItemFactory.boolean_item
            elif flag == MCPACKV2_INT_8:
                return McpackItemFactory.int8_item
            elif flag == MCPACKV2_UINT_8:
                return McpackItemFactory.uint8_item
            elif flag == MCPACKV2_INT_16:
                return McpackItemFactory.int16_item
            elif flag == MCPACKV2_UINT_16:
                return McpackItemFactory.uint16_item
            elif flag == MCPACKV2_INT_32:
                return McpackItemFactory.int32_item
            elif flag == MCPACKV2_INT_32:
                return McpackItemFactory.int32_item
            elif flag == MCPACKV2_UINT_32:
                return McpackItemFactory.uint32_item
            elif flag == MCPACKV2_INT_64:
                return McpackItemFactory.int64_item
            elif flag == MCPACKV2_UINT_64:
                return McpackItemFactory.uint64_item
            elif flag == MCPACKV2_FLOAT:
                return McpackItemFactory.float_item
            elif flag == MCPACKV2_DOUBLE:
                return McpackItemFactory.double_item
            elif flag == MCPACKV2_NULL:
                return McpackItemFactory.null_item
            else:
                return McpackItemFactory.error_item
        elif flag & MCPACKV2_SHORT_ITEM != 0:
            if MCPACKV2_STRING | MCPACKV2_SHORT_ITEM:
                return McpackItemFactory.string_item
            else:
                return McpackItemFactory.error_item
        else:
            if flag == MCPACKV2_ARRAY:
                return McpackItemFactory.array_item
            elif flag == MCPACKV2_STRING:
                return McpackItemFactory.string_item
            elif flag == MCPACKV2_OBJECT:
                return McpackItemFactory.object_item
            else:
                return McpackItemFactory.error_item


class OutOfBoundError(Exception):
    """定义越界异常"""

    def __init__(self, value):
        self.value = 'Out of bounds! ' + str(value)

    def __str__(self):
        return repr(self.value)


class NotSpecifiedTypeError(Exception):
    """没有指定解析类型"""

    def __init__(self, value):
        self.value = 'Not Specified Type! ' + str(value)

    def __str__(self):
        return repr(self.value)
