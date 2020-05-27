#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-04-10 18:34:31

# File Name: host_util.py
# Description:

"""
import re
import socket
import logging


def get_host_by_ip(ip):
    """找到机器名
    :param ip: IP, str
    :return host: str/None
    """
    if not ip:
        return None
    try:
        host = socket.gethostbyaddr(ip)[0]
        return host
    except Exception as e:
        logging.error('Get host of ip[{}] failed, error: {}'.format(ip, e))
        return None


def get_ip_by_host(host):
    """找到机器的IP
    :param host: 机器名, str
    :return ip: str/None
    """
    if not host:
        return None
    try:
        ip = socket.gethostbyname(host)
        return ip
    except Exception as e:
        logging.error('Get ip of host[{}] failed, error: {}'.format(host, e))
        return None


def is_ip(host):
    """检查是否为 IP
    :param host: 机器名/ip, str
    :return: True/False
    """
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(host):
        return True
    else:
        return False


if __name__ == '__main__':
    import sys
    import inspect

    def _usage(func_name=""):
        """
        output the module usage
        """
        print("Usage:")
        print("-------------------------------------------------")
        for k, v in sorted(globals().items(), key=lambda item: item[0]):
            if func_name and func_name != k:
                continue

            if not inspect.isfunction(v) or k[0] == "_":
                continue

            args, __, __, defaults = inspect.getargspec(v)
            #
            # have defaults:
            #       def hello(str_info, test="world"):
            #               |
            #               V
            #       return: (args=['str_info', 'test'], varargs=None, keywords=None, defaults=('world',)
            # no defaults:
            #       def echo2(str_info1, str_info2):
            #               |
            #               V
            #       return: (args=['str_info1', 'str_info2'], varargs=None, keywords=None, defaults=None)
            #
            # str(['str_info1', 'str_info2'])[1:-1].replace(",", "") ===> 'str_info1' 'str_info2'
            #
            if defaults:
                args_all = str(args[:-len(defaults)])[1:-1].replace(",", ""), \
                    str(["%s=%s" % (a, b) for a, b in zip(args[-len(defaults):], defaults)])[1:-1].replace(",", "")
            else:
                args_all = str(v.func_code.co_varnames[:v.func_code.co_argcount])[1:-1].replace(",", "")

            if not isinstance(args_all, tuple):
                args_all = tuple(args_all.split(" "))

            exe_info = "{file_name} {func_name} {args_all}".format(
                file_name=sys.argv[0],
                func_name=k,
                args_all=" ".join(args_all))
            print(exe_info)

            # output func_doc
            if func_name and v.func_doc:
                print("\n".join(["\t" + line.strip() for line in v.func_doc.strip().split("\n")]))

        print("-------------------------------------------------")

    if len(sys.argv) < 2:
        _usage()
        sys.exit(-1)
    else:
        func = eval(sys.argv[1])
        args = sys.argv[2:]
        try:
            r = func(*args)
        except Exception:
            _usage(func_name=sys.argv[1])

            r = -1
            import traceback
            traceback.print_exc()

        if isinstance(r, int):
            sys.exit(r)

        print r
