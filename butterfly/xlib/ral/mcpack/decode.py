# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:31:25

# File Name: decode.py
# Description:
    反序列化
"""

from functools import wraps
from xlib.ral.mcpack import const
from xlib.ral.mcpack import pack


def loads(data):
    """反序列化mcpack
    Arguments:
        data {bytes} -- 二进制数据
    Returns:
        dict -- 反序列化后的原始数据
    """
    ds = McpackDecoder(data)
    return ds.unmarshal()


class McpackDecoder(object):
    """mcpack 解析类
    """

    def __init__(self, data):
        self.data = bytearray(data)
        self.off = 0

    def unmarshal(self):
        """mcpack 反序列化
        """
        return self.__value_decoder()

    def __next(self, step=1):
        """数据指向
        Keyword Arguments:
            step {int} -- 数据指向步长 (default: {1})
        """
        self.off += step

    def number_decoder(step=1):
        """number类型解析装饰器
        """

        def decorator(func):
            """passthrough func
            """

            @wraps(func)
            def __decode(self):
                self.__next()
                klen = pack.to_uint8(self.data[self.off:self.off + 1])
                self.__next(1 + klen)
                value = func(self)
                self.__next(step)
                return value

            return __decode

        return decorator

    def __value_decoder(self):
        if not len(self.data):
            return None
        p_value = self.data[self.off]
        if p_value == const.MCPACKV2_OBJECT:
            return self.__object_decoder()
        elif p_value == const.MCPACKV2_ARRAY:
            return self.__array_decoder()
        elif p_value in [const.MCPACKV2_STRING, const.MCPACKV2_SHORT_STRING]:
            return self.__string_decoder(p_value)
        elif p_value in [const.MCPACKV2_BINARY, const.MCPACKV2_SHORT_BINARY]:
            return self.__binary_decoder(p_value)
        elif p_value == const.MCPACKV2_BOOL:
            return self.__bool_decoder()
        elif p_value == const.MCPACKV2_INT8:
            return self.__int8_decoder()
        elif p_value == const.MCPACKV2_INT16:
            return self.__int16_decoder()
        elif p_value == const.MCPACKV2_INT32:
            return self.__int32_decoder()
        elif p_value == const.MCPACKV2_INT64:
            return self.__int64_decoder()
        elif p_value == const.MCPACKV2_UINT8:
            return self.__uint8_decoder()
        elif p_value == const.MCPACKV2_UINT16:
            return self.__uint16_decoder()
        elif p_value == const.MCPACKV2_UINT32:
            return self.__uint32_decoder()
        elif p_value == const.MCPACKV2_UINT64:
            return self.__uint64_decoder()
        elif p_value == const.MCPACKV2_FLOAT:
            return self.__float_decoder()
        elif p_value == const.MCPACKV2_DOUBLE:
            return self.__double_decoder()
        elif p_value == const.MCPACKV2_NULL:
            return self.__null_decoder()
        return None

    def __key_decoder(self):
        kstart = 0
        itype = self.data[self.off]
        if (itype in [const.MCPACKV2_INT8, const.MCPACKV2_INT16, const.MCPACKV2_INT32, const.MCPACKV2_INT64,
                      const.MCPACKV2_UINT8, const.MCPACKV2_UINT16, const.MCPACKV2_UINT32, const.MCPACKV2_UINT64,
                      const.MCPACKV2_BOOL, const.MCPACKV2_FLOAT, const.MCPACKV2_DOUBLE, const.MCPACKV2_NULL]):
            kstart = 2  # type + klen
        elif itype in [const.MCPACKV2_SHORT_STRING, const.MCPACKV2_SHORT_BINARY]:
            kstart = 3  # type + klen + vlen(1)
        elif itype in [const.MCPACKV2_BINARY, const.MCPACKV2_STRING, const.MCPACKV2_ARRAY, const.MCPACKV2_OBJECT]:
            kstart = 6  # type + klen + vlen(4)

        klen = pack.to_uint8(self.data[self.off + 1:self.off + 2])
        if klen < 0:
            raise KeyError("Empty key")

        return self.data[self.off + kstart:self.off + kstart + klen - 1].decode()

    @number_decoder()
    def __bool_decoder(self):
        value = False if self.data[self.off] == 0 else True
        return value

    @number_decoder()
    def __uint8_decoder(self):
        value = pack.to_uint8(self.data[self.off:self.off + 1])
        return value

    @number_decoder(2)
    def __uint16_decoder(self):
        value = pack.to_uint16(self.data[self.off:self.off + 2])
        return value

    @number_decoder(4)
    def __uint32_decoder(self):
        value = pack.to_uint32(self.data[self.off:self.off + 4])
        return value

    @number_decoder(8)
    def __uint64_decoder(self):
        value = pack.to_uint64(self.data[self.off:self.off + 8])
        return value

    @number_decoder()
    def __int8_decoder(self):
        value = pack.to_int8(self.data[self.off:self.off + 1])
        return value

    @number_decoder(2)
    def __int16_decoder(self):
        value = pack.to_int16(self.data[self.off:self.off + 2])
        return value

    @number_decoder(4)
    def __int32_decoder(self):
        value = pack.to_int32(self.data[self.off:self.off + 4])
        return value

    @number_decoder(8)
    def __int64_decoder(self):
        value = pack.to_int64(self.data[self.off:self.off + 8])
        return value

    @number_decoder(4)
    def __float_decoder(self):
        value = pack.to_float(self.data[self.off:self.off + 4])
        return value

    @number_decoder(8)
    def __double_decoder(self):
        value = pack.to_double(self.data[self.off:self.off + 8])
        return value

    @number_decoder()
    def __null_decoder(self):
        return None

    def __string_decoder(self, itype):
        self.__next()
        klen = pack.to_uint8(self.data[self.off:self.off + 1])
        self.__next()
        if itype == const.MCPACKV2_STRING:
            vlen = pack.to_uint32(self.data[self.off:self.off + 4])
            self.__next(4 + klen)
        else:
            vlen = pack.to_uint8(self.data[self.off:self.off + 1])
            self.__next(1 + klen)
        try:
            value = self.data[self.off:self.off + vlen - 1].decode('utf-8')
        except Exception:
            value = self.data[self.off:self.off + vlen - 1]
        self.__next(vlen)

        return value

    def __binary_decoder(self, itype):
        self.__next()
        klen = pack.to_uint8(self.data[self.off:self.off + 1])
        self.__next()
        if itype == const.MCPACKV2_BINARY:
            vlen = pack.to_uint32(self.data[self.off:self.off + 4])
            self.__next(4 + klen)
        else:
            vlen = pack.to_uint8(self.data[self.off:self.off + 1])
            self.__next(1 + klen)
        value = self.data[self.off:self.off + vlen]
        self.__next(vlen)
        return value

    def __array_decoder(self):
        arr = []
        self.__next()
        klen = pack.to_uint8(self.data[self.off:self.off + 1])
        self.__next(1 + 4 + klen)
        alen = pack.to_uint32(self.data[self.off:self.off + 4])
        self.__next(4)
        for i in range(alen):
            arr.append(self.__value_decoder())
        return arr

    def __object_decoder(self):
        obj = {}
        self.__next()
        klen = pack.to_uint8(self.data[self.off:self.off + 1])
        self.__next(1 + 4 + klen)
        olen = pack.to_uint32(self.data[self.off:self.off + 4])
        self.__next(4)
        for i in range(olen):
            key = self.__key_decoder()
            value = self.__value_decoder()
            obj.update({key: value})
        return obj
