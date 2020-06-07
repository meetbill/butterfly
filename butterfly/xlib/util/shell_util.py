#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-05-17 11:49:36

# File Name: shell_util.py
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
        if not result.success():
            print result.output()

    Example2 直接执行:
        python shell.py run "echo xx"   # 执行成功命令
        python shell.py run "echoxx"    # 执行失败命令

# 版本更新
    v1.0.1(2020-05-17 11:49:36)
    v1.0.2(2020-05-21 08:12:33)
        去掉 reqid 参数，通过 logging 添加 Filters 自动添加 reqid 方式
    v1.0.3(2020-05-25 11:02:38)
        增加 butterfly logger
"""

import inspect
import subprocess
import time
import logging


log = logging.getLogger("butterfly")


class Result(object):
    """
    easyrun 返回结果封装
    """

    def __init__(self, command="", retcode="", output="", cost=""):
        """
        command : (str) 执行命令
        retcode : (int) 执行结果返回码
        output  : (str) 输出结果
        cost    : (str) 执行命令耗时
        """
        self.command = command or ''
        self.retcode = retcode
        self._output = output
        self._output_len = len(output)
        self._success = False
        self.cost = cost
        if retcode == 0:
            self._success = True
            self.err_msg = "OK"
        else:
            self.err_msg = output

        self._logger()

    def __str__(self):
        """
        object str format
        """
        return "[command]:{command} [success]:{success} [output]:{output}".format(
            command=self.command,
            success=self._success,
            output=self._output
        )

    def _logger(self):
        """
        record log
        """
        f = inspect.currentframe().f_back.f_back
        file_name, lineno, func_name = self._get_backframe_info(f)

        if self._output_len > 50:
            output_log = self._output[:50].replace("\n", ">>>") + "... :("
        else:
            output_log = self._output.replace("\n", ">>>") + ":)"

        log_msg = ("[file={file_name}:{func_name}:{lineno} "
                   "type=shell "
                   "req_path={req_path} "
                   "req_data=None "
                   "cost={cost} "
                   "is_success={is_success} "
                   "err_no={err_no} "
                   "err_msg={err_msg} "
                   "res_len={res_len} "
                   "res_data={res_data} "
                   "res_attr=None]".format(
                       file_name=file_name, func_name=func_name, lineno=lineno,
                       req_path=self.command,
                       cost=self.cost,
                       is_success=self._success,
                       err_no=self.retcode,
                       err_msg=self.err_msg,
                       res_len=self._output_len,
                       res_data=output_log,
                   ))

        if self._success:
            log.info(log_msg)
        else:
            log.error(log_msg)

    def _get_backframe_info(self, f):
        """
        get backframe info
        """
        return f.f_back.f_code.co_filename, f.f_back.f_lineno, f.f_back.f_code.co_name

    def success(self):
        """
        检查执行是否成功
        """
        return self._success

    def output(self):
        """
        返回输出结果
        """
        return self._output


def run(command, timeout=10):
    """
    Args:
        command : (str) 执行的命令
        timeout : (int) 默认 10s
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
            cost_str = "%.6f" % seconds_passed
            return Result(command=command, retcode=124, output="exe timeout", cost=cost_str)

        time.sleep(0.1)

    output, _ = process.communicate()
    output = output.strip('\n')
    cost_str = "%.6f" % seconds_passed
    return Result(command=command, retcode=process.returncode, output=output, cost=cost_str)


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
