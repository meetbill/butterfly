# coding=UTF-8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 19:31:25

# File Name: encode.py
# Description:
    encode
"""

import ctypes
from xlib.ral.mcpack import const
from xlib.ral.mcpack import pack


def dumps(v):
    """mcpack序列化
    Arguments:
        v {Any} -- 被序列化对象
    Returns:
        bytes -- 序列化后字节
    """
    es = McpackEncoder()
    return es.marshal(v)


class McpackEncoder(object):
    """mcpack 编码类
    """

    def __init__(self):
        self.data = bytearray()
        self.off = 0

    def __next(self, step=1):
        self.off += step

    def __set_type(self, t):
        self.data[self.off] = t
        self.__next()

    def __set_key_len(self, k):
        klen = len(k)
        if klen > const.MCPACKV2_KEY_MAX_LEN:
            raise ValueError("Key is longger than {}".format(
                const.MCPACKV2_KEY_MAX_LEN))
        self.data[self.off] = klen + 1 if klen > 0 else 0
        self.__next()
        return klen

    def __set_key(self, k, klen):
        if klen <= 0:
            return
        self.data[self.off:self.off + klen] = k.encode()
        self.__next(klen)
        self.data[self.off] = 0
        self.__next()

    def marshal(self, v):
        """mcpack marshal
        """
        self.__value_encoder(v)("", v)
        return self.data

    def __value_encoder(self, v):
        """根据value选择解析方法
        """
        if not v:
            return
        return self.__type_encoder(type(v))

    def __type_encoder(self, v):
        if v is ctypes.c_bool:
            return self.__bool_encoder
        elif v is bool:
            return self.__bool_encoder
        elif v is int:
            return self.__int64_encoder
        elif v is ctypes.c_byte:
            return self.__int8_encoder
        elif v is ctypes.c_ubyte:
            return self.__uint8_encoder
        elif v is ctypes.c_short:
            return self.__int16_encoder
        elif v is ctypes.c_ushort:
            return self.__uint16_encoder
        elif v is ctypes.c_int:
            return self.__int32_encoder
        elif v is ctypes.c_uint:
            return self.__uint32_encoder
        elif v is ctypes.c_long:
            return self.__int64_encoder
        elif v is ctypes.c_ulong:
            return self.__uint64_encoder
        elif v is ctypes.c_float:
            return self.__float32_encoder
        elif v is float:
            return self.__double_encoder
        elif v is ctypes.c_double:
            return self.__double_encoder
        elif v is str or v is unicode:
            return self.__string_encoder
        elif isinstance(None, v):
            return self.__null_encoder
        elif v in [bytes, bytearray]:
            return self.__binary_encoder
        elif v in [list, tuple]:
            return self.__array_encoder
        elif v is dict:
            return self.__dict_encoder
        else:
            return self.__unsupposedtype_encoder

    def __unsupposedtype_encoder(self, k, v):
        print(k, v)
        return None

    def __bool_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 1))
        self.__set_type(const.MCPACKV2_BOOL)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off] = 1 if v else 0
        self.__next()

    def __int8_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 1))
        self.__set_type(const.MCPACKV2_INT8)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 1] = pack.pack_int8(v)
        self.__next()

    def __int16_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 2))
        self.__set_type(const.MCPACKV2_INT16)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 2] = pack.pack_int16(v)
        self.__next(2)

    def __int32_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 4))
        self.__set_type(const.MCPACKV2_INT32)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 4] = pack.pack_int32(v)
        self.__next(4)

    def __int64_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 8))
        self.__set_type(const.MCPACKV2_INT64)
        self.__set_key(k, self.__set_key_len(k))
        v = ctypes.c_int64(v) if isinstance(v, int) else v
        self.data[self.off:self.off + 8] = pack.pack_int64(v)
        self.__next(8)

    def __uint8_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 1))
        self.__set_type(const.MCPACKV2_UINT8)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 1] = pack.pack_uint8(v)
        self.__next()

    def __uint16_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 2))
        self.__set_type(const.MCPACKV2_UINT16)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 2] = pack.pack_uint16(v)
        self.__next(2)

    def __uint32_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 4))
        self.__set_type(const.MCPACKV2_UINT32)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off +
                  4] = pack.pack_uint32(v)
        self.__next(4)

    def __uint64_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 8))
        self.__set_type(const.MCPACKV2_UINT64)
        self.__set_key(k, self.__set_key_len(k))
        v = ctypes.c_uint64(v) if isinstance(v, int) else v
        self.data[self.off:self.off + 8] = pack.pack_uint64(v)
        self.__next(8)

    def __float_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 4))
        self.__set_type(const.MCPACKV2_FLOAT)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off:self.off + 4] = pack.pack_float(v)
        self.__next(4)

    def __double_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 8))
        self.__set_type(const.MCPACKV2_DOUBLE)
        self.__set_key(k, self.__set_key_len(k))
        v = ctypes.c_double(v) if isinstance(v, float) else v
        self.data[self.off:self.off + 8] = pack.pack_double(v)
        self.__next(8)

    def __string_encoder(self, k, v):
        if isinstance(v, unicode):
            vbyte = v.encode('utf-8')
        elif isinstance(v, str):
            vbyte = unicode(v.replace(r'\\', r'\\\\'),
                            "unicode_escape").encode('utf-8')
        vreal_len = len(vbyte)
        self.data.extend(bytearray(1 + 1 + 4 + len(k) + 1 + vreal_len + 1))
        vlen = vreal_len + 1
        if vlen < const.MAX_SHORT_VITEM_LEN:
            self.__set_type(const.MCPACKV2_SHORT_STRING)
            klen = self.__set_key_len(k)
            self.data[self.off:self.off +
                      1] = pack.pack_uint8(ctypes.c_uint8(vlen))
            self.__next()
            self.__set_key(k, klen)
        else:
            self.__set_type(const.MCPACKV2_STRING)
            klen = self.__set_key_len(k)
            self.data[self.off:self.off +
                      4] = pack.pack_uint32(ctypes.c_uint32(vlen))
            self.__next(4)
            self.__set_key(k, klen)
        self.data[self.off:self.off + vreal_len] = vbyte
        self.__next(vreal_len)
        self.data[self.off] = 0
        self.__next()

    def __binary_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + 4 + len(k) + 1 + len(v)))
        vlen = len(v)
        if vlen < const.MAX_SHORT_VITEM_LEN:
            self.__set_type(const.MCPACKV2_SHORT_BINARY)
            klen = self.__set_key_len(k)
            self.data[self.off:self.off +
                      1] = pack.pack_uint8(ctypes.c_uint8(vlen))
            self.__next()
            self.__set_key(k, klen)
        else:
            self.__set_type(const.MCPACKV2_BINARY)
            klen = self.__set_key_len(k)
            self.data[self.off:self.off +
                      4] = pack.pack_uint32(ctypes.c_uint32(vlen))
            self.__next(4)
            self.__set_key(k, klen)

        self.data[self.off:self.off + len(v)] = v
        self.__next(len(v))

    def __null_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + len(k) + 1 + 1))
        self.__set_type(const.MCPACKV2_NULL)
        self.__set_key(k, self.__set_key_len(k))
        self.data[self.off] = 0
        self.__next()

    def __array_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + 4 + len(k) + 1 + 4))
        list_type = set(type(x) for x in v)
        if len(list_type) > 1:
            raise ValueError(
                "the type of element in list or tuple must be same")
        self.__set_type(const.MCPACKV2_ARRAY)
        klen = self.__set_key_len(k)
        vlen = self.off
        self.__next(4)
        self.__set_key(k, klen)
        vpos = self.off
        self.data[self.off:self.off +
                  4] = pack.pack_int32(ctypes.c_int32(len(v)))
        self.__next(4)
        for item in v:
            self.__type_encoder(list(list_type)[0])("", item)
        b = pack.pack_int32(ctypes.c_int32(self.off - vpos))
        self.data[vlen:vlen + len(b)] = b

    def __dict_encoder(self, k, v):
        self.data.extend(bytearray(1 + 1 + 4 + len(k) + 1 + 4))
        self.__set_type(const.MCPACKV2_OBJECT)
        klen = self.__set_key_len(k)
        vlen = self.off
        self.__next(4)
        self.__set_key(k, klen)
        vpos = self.off
        self.data[self.off:self.off +
                  4] = pack.pack_int32(ctypes.c_int32(len(v)))
        self.__next(4)
        for key, value in v.items():
            self.__type_encoder(type(value))(key, value)
        b = pack.pack_int32(ctypes.c_int32(self.off - vpos))
        self.data[vlen:vlen + len(b)] = b
