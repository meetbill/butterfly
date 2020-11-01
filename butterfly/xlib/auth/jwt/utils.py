# coding=utf8
"""
# Description:
    pyjwt 工具
"""
import base64
import binascii
import struct

from .compat import binary_type, bytes_from_int, text_type

try:
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature, encode_dss_signature
    )
except ImportError:
    pass


def force_unicode(value):
    """
    Python3 字符序列的两种表示为 byte 和 str
       前者的实例包含原始的 8 位值，即原始的字节；后者的实例包括 Unicode 字符。
    Python2 字符序列的两种表示为 str 和 unicode
        与 Python3 不同的是，str 实例包含原始的 8 位值；而 unicode 的实例，则包含 Unicode 字符。

    所以强制转为 unicode 的话，Python3 是 str 字符序列， Python2 是 unicode 序列
    """
    if isinstance(value, binary_type):
        return value.decode('utf-8')
    elif isinstance(value, text_type):
        return value
    else:
        raise TypeError('Expected a string value')


def force_bytes(value):
    """
    转为字节
    """
    if isinstance(value, text_type):
        return value.encode('utf-8')
    elif isinstance(value, binary_type):
        return value
    else:
        raise TypeError('Expected a string value')


def base64url_decode(input):
    """
    Base64 解码, 需要通过补 "=", 成为 4 的倍数
    """
    if isinstance(input, text_type):
        input = input.encode('ascii')

    rem = len(input) % 4

    if rem > 0:
        input += b'=' * (4 - rem)

    return base64.urlsafe_b64decode(input)


def base64url_encode(input):
    """
    在 Base64 的基础上，将末尾的 "=" 去掉
    """
    return base64.urlsafe_b64encode(input).replace(b'=', b'')


def to_base64url_uint(val):
    """
    int 转为 base64url
    """
    if val < 0:
        raise ValueError('Must be a positive integer')

    int_bytes = bytes_from_int(val)

    if len(int_bytes) == 0:
        int_bytes = b'\x00'

    return base64url_encode(int_bytes)


def from_base64url_uint(val):
    """
    base64url 转为 int
    """
    if isinstance(val, text_type):
        val = val.encode('ascii')

    data = base64url_decode(val)

    buf = struct.unpack('%sB' % len(data), data)
    return int(''.join(["%02x" % byte for byte in buf]), 16)


def merge_dict(original, updates):
    """
    两个字典（dict）合并
    """
    if not updates:
        return original

    try:
        merged_options = original.copy()
        merged_options.update(updates)
    except (AttributeError, ValueError) as e:
        raise TypeError('original and updates must be a dictionary: %s' % e)

    return merged_options


def number_to_bytes(num, num_bytes):
    """
    数字转为二进制格式
    """
    padded_hex = '%0*x' % (2 * num_bytes, num)
    big_endian = binascii.a2b_hex(padded_hex.encode('ascii'))
    return big_endian


def bytes_to_number(string):
    """
    二进制格式转为数字
    """
    return int(binascii.b2a_hex(string), 16)


def der_to_raw_signature(der_sig, curve):
    """
    生成签名
    Args:
        der_sig: header.payload
        curve: key
    Returns:
        签名
    """
    num_bits = curve.key_size
    num_bytes = (num_bits + 7) // 8

    r, s = decode_dss_signature(der_sig)

    return number_to_bytes(r, num_bytes) + number_to_bytes(s, num_bytes)


def raw_to_der_signature(raw_sig, curve):
    """
    Args:
        raw_sig: signature
        curve: key
    Returns:
        header.payload
    """
    num_bits = curve.key_size
    num_bytes = (num_bits + 7) // 8

    if len(raw_sig) != 2 * num_bytes:
        raise ValueError('Invalid signature')

    r = bytes_to_number(raw_sig[:num_bytes])
    s = bytes_to_number(raw_sig[num_bytes:])

    return encode_dss_signature(r, s)
