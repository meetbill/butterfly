#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2019-11-15 17:45:43

# File Name: test_handler.py
# Description:
  用于编写 handlers 时，测试 handlers 的输出

# 注意
  如果进行调试时，有些资源已经在使用，则可能会出错，如 crontab 中使用的 example.db
"""

import os
import sys

# ********************************************************
# * Third lib                                            *
# ********************************************************
if os.path.exists('third'):
    cur_path = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(0, os.path.join(cur_path, 'third'))

from conf import logger_conf
from xlib import urls
from xlib import httpgateway
from xlib import uuid64

route = urls.Route(logger_conf.infolog, logger_conf.errlog)
# 自动将 handlers 目录加 package 自动注册
route.autoload_handler("handlers")
# 手动添加注册(访问 /ping ,则会自动转到 apidemo.ping)
# route.addapi("/ping", apidemo.ping, True, True)
apicube = route.get_route()

if __name__ == "__main__":
    from xlib.debug import pysnooper

    # 封装 req
    ip = "0.0.0.0"
    reqid = uuid64.UUID64().gen()
    wsgienv = {"PATH_INFO": "/echo"}
    req = httpgateway.Request(reqid, wsgienv, ip)

    import inspect
    if len(sys.argv) < 2:
        print("Usage:")
        for url in apicube:
            func = apicube[url]._func
            # ArgSpec(args=['req', 'str_info'], varargs=None, keywords=None, defaults=None)
            args, __, __, defaults = inspect.getargspec(func)
            if defaults:
                line = (sys.argv[0],
                        url,
                        str(args[1:-len(defaults)])[1:-1].replace(",", ""),
                        str(["%s=%s" % (a, b) for a, b in zip(args[-len(defaults):], defaults)])[1:-1].replace(",", "")
                        )
            else:
                line = (sys.argv[0],
                        url,
                        str(func.func_code.co_varnames[1:func.func_code.co_argcount])[1:-1].replace(",", "")
                        )
            print(" ".join(line))

        sys.exit(-1)
    else:
        url = sys.argv[1]
        func = apicube[url]._func
        args = sys.argv[2:]
        args.insert(0, req)
        try:
            @pysnooper.snoop(thread_info=True, depth=2)
            def main():
                """
                test main
                此函数用于 pysnooper 输出 debug 信息
                """
                return func(*args)

            result = main()
            print("=============================================================")
            print(result)
            print("=============================================================")
        except Exception:
            print("-------------------------------------------------------------")
            print("Usage:")
            line = (sys.argv[0],
                    sys.argv[1],
                    str(func.func_code.co_varnames[:func.func_code.co_argcount])[1:-1].replace(",", "")
                    )
            print(" ".join(line))
            print("-------------------------------------------------------------")
            if func.func_doc:
                print("\n".join(["\t\t" + line.strip() for line in func.func_doc.strip().split("\n")]))

            import traceback
            traceback.print_exc()
