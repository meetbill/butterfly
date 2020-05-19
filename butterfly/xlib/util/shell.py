#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2020-05-17 11:49:36

# File Name: shell.py
# Description:
    基于 subprocess.Popen 封装, 增加如下功能
        (1) 超时，默认 10s
        (2) 日志，每次调用系统命令都进行记录, 日志中包含 reqid (如果传入的话)及调用处代码信息
            调用系统命令返回的结果大于 50 个字符时，将会被截断，否则使用此模块获取日志时, 记录日志会比较多
            调用系统命令返回的结果中的回车符将会被替换为 '>>>'
        (3) 结果封装

    Example1 程序调用:
        from xlib.util import shell
        result = shell.run("echo hello world")
        if not result.success:
            print result.output

    Example2 直接执行:
        python shell.py run "echo xx"   # 执行成功命令
        python shell.py run "echoxx"    # 执行失败命令
"""

import inspect
import subprocess
import time
import logging


class Result(object):
    """
    easyrun 返回结果封装
    """

    def __init__(self, command="", retcode="", output="", reqid=""):
        """
        command : (str) 执行命令
        retcode : (int) 执行结果返回码
        output  : (str) 输出结果
        reqid   : (str) 请求 id
        """
        self.command = command or ''
        self.retcode = retcode
        self.output = output
        self.output_len = len(output)
        self.success = False
        self.reqid = reqid
        if retcode == 0:
            self.success = True
        self._logger()

    def __str__(self):
        """
        object str format
        """
        return "[command]:{command} [success]:{success} [output]:{output}".format(
            command=self.command,
            success=self.success,
            output=self.output
        )

    def _logger(self):
        """
        record log
        """
        f = inspect.currentframe().f_back.f_back
        file_name, lineno, func_name = self._get_backframe_info(f)

        if self.output_len > 50:
            output_log = self.output[:50].replace("\n", ">>>") + "... :("
        else:
            output_log = self.output.replace("\n", ">>>") + ":)"

        log_msg = ("[reqid]:{reqid} [command]:{command} [success]:{success} "
                   "[code]:{retcode} [output_len]:{output_len} [output]:{output} "
                   "[req_info]:{file_name}:{func_name}:{lineno}".format(
                       reqid=self.reqid,
                       command=self.command,
                       success=self.success,
                       retcode=self.retcode,
                       output_len=self.output_len,
                       output=output_log,
                       file_name=file_name,
                       func_name=func_name,
                       lineno=lineno
                   ))

        if self.success:
            logging.info(log_msg)
        else:
            logging.error(log_msg)

    def _get_backframe_info(self, f):
        """
        get backframe info
        """
        return f.f_back.f_code.co_filename, f.f_back.f_lineno, f.f_back.f_code.co_name


def run(command, timeout=10, reqid=""):
    """
    Args:
        command : (str) 执行的命令
        timeout : (int) 默认 10s
        reqid   : (str) reqid
    Returns:
        Result
    """
    timeout = int(timeout)
    process = subprocess.Popen(
        command,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        shell=True)

    t_beginning = time.time()
    seconds_passed = 0
    while True:
        if process.poll() is not None:
            break

        seconds_passed = time.time() - t_beginning
        if timeout and seconds_passed > timeout:
            process.terminate()
            return Result(command=command, retcode=124, output="exe timeout", reqid=reqid)

        time.sleep(0.1)

    output, _ = process.communicate()
    output = output.strip('\n')
    return Result(command=command, retcode=process.returncode, output=output, reqid=reqid)


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