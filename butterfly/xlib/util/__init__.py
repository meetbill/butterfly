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
    @staticmethod
    def b16_to_b64(b16str):
        if len(b16str) % 2 == 0:
            return base64.b64encode(base64.b16decode(b16str, True), "()").strip("=")
        else:
            return "@" + b16str[0] + base64.b64encode(base64.b16decode(b16str[1:], True), "()").strip("=")

    @staticmethod
    def b64_to_b16(b64str_v):
        if b64str_v[0] == "@":
            return b64str_v[1] + base64.b16encode(Base64_16.b64_to_bin(b64str_v[2:])).lower()
        else:
            return base64.b16encode(Base64_16.b64_to_bin(b64str_v)).lower()

    @staticmethod
    def b64_to_bin(b64str):
        slen = len(b64str)
        tail = slen % 4
        if tail:
            b64str += ("=" * (4 - tail))
        return base64.b64decode(b64str, "()")

    @staticmethod
    def bin_to_b64(b):
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
