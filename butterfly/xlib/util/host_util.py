#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2020-04-10 18:34:31

# File Name: host_util.py
# Description:

"""
import re
import socket
import logging


def find_host_of_ip(ip):
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


def find_ip_of_host(host):
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
    if len(sys.argv) < 2:
        print "Usage:"
        for k, v in sorted(globals().items(), key=lambda item: item[0]):
            if inspect.isfunction(v) and k[0] != "_":
                args, __, __, defaults = inspect.getargspec(v)
                if defaults:
                    print sys.argv[0], k, str(args[:-len(defaults)])[1:-1].replace(",", ""), \
                        str(["%s=%s" % (a, b) for a, b in zip(args[-len(defaults):], defaults)])[1:-1].replace(",", "")
                else:
                    print sys.argv[0], k, str(v.func_code.co_varnames[:v.func_code.co_argcount])[1:-1].replace(",", "")
        sys.exit(-1)
    else:
        func = eval(sys.argv[1])
        args = sys.argv[2:]
        try:
            r = func(*args)
            print r
        except Exception as e:
            print "Usage:"
            print "\t", "python %s" % sys.argv[1], str(func.func_code.co_varnames[:func.func_code.co_argcount])[
                1:-1].replace(",", "")
            if func.func_doc:
                print "\n".join(["\t\t" + line.strip() for line in func.func_doc.strip().split("\n")])
            print e
            r = -1
            import traceback
            traceback.print_exc()
        if isinstance(r, int):
            sys.exit(r)
