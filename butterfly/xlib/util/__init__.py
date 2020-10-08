# coding:utf8
"""
Butterfly 工具 module
"""

import os
import urlparse
import base64
import inspect


def is_digit_vars(variables):
    """
    Check if the variable is a number
    """
    for var in variables:
        if isinstance(var, str) and var.isdigit():
            continue
        elif isinstance(var, int):
            continue
        else:
            return False
    return True


def write_pid(path):
    """
    Write PID
    """
    open(path, "w").write(str(os.getpid()))


class Base64_16(object):
    """
    Base64 相关工具

    Base64 是一种将不可见字符转换为可见字符的编码方式
    b64 是基于 64 个可打印字符来表示二进制数据的表示方法
    b16 是基于 16 个可打印字符来表示二进制数据的表示方法
    """
    @staticmethod
    def b16_to_b64(b16str):
        """
        b16 ==> b64
        """
        if len(b16str) % 2 == 0:
            return base64.b64encode(base64.b16decode(b16str, True), "()").strip("=")
        else:
            return "@" + b16str[0] + base64.b64encode(base64.b16decode(b16str[1:], True), "()").strip("=")

    @staticmethod
    def b64_to_b16(b64str_v):
        """
        b64 ==> b16
        """
        if b64str_v[0] == "@":
            return b64str_v[1] + base64.b16encode(Base64_16.b64_to_bin(b64str_v[2:])).lower()
        else:
            return base64.b16encode(Base64_16.b64_to_bin(b64str_v)).lower()

    @staticmethod
    def b64_to_bin(b64str):
        """
        b64 ==> bytes

        进行转换时，先补齐 = 号
        """
        slen = len(b64str)
        tail = slen % 4
        if tail:
            b64str += ("=" * (4 - tail))
        return base64.b64decode(b64str, "()")

    @staticmethod
    def bin_to_b64(b):
        """
        bytes ==> b64
        由于 = 字符也可能出现在 Base64 编码中，但 = 用在 URL、Cookie 里面会造成歧义，所以去掉 =

        # 标准 Base64:
        'abcd' -> 'YWJjZA=='
        # 自动去掉 =:
        'abcd' -> 'YWJjZA'
        """
        return base64.b64encode(b, "()").strip("=")


def spliturl(url):
    """
    拆分 url

    Args:
        url：HTTP url
    Returns:
        (host,port,path)
    """
    assert url.startswith("http://")
    r = urlparse.urlsplit(url)
    host_port = r.netloc.split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 80
    path = r.path
    if r.query:
        path += ("?" + r.query)
    if r.fragment:
        path += ("#" + r.fragment)
    return host, port, path


def msg(msg_str):
    """
    Args:
        msg_str: (str)
    Returns:
        cur_info
    """

    func = inspect.currentframe().f_back
    filename = func.f_code.co_filename
    lineno = func.f_lineno
    cur_info = "[line={filename}:{lineno} msg={msg_str}]".format(filename=filename, lineno=lineno, msg_str=msg_str)
    return cur_info


if __name__ == "__main__":
    print msg("ceshi info")
