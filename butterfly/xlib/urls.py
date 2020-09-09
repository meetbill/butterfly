#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2019-08-02 21:14:43

# File Name: urls.py
# Description:
    Managing Routing and Automatically register the handler to route
"""

import importlib
import pkgutil
import inspect

from xlib import retstat
from xlib import protocol_json
from xlib import protocol_file


def import_submodules(package):
    """
    Import all submodules of a module
    只加载指定 package 及此 package 的子 package

    From http://stackoverflow.com/questions/3365740/how-to-import-all-submodules

    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]

    Examples:
        local dir:
            handlers/__init__.py
            handlers/api/__init__.py
        input: package = "handlers"
        return:{
                'handlers.api': <module 'handlers.api' from '/home/users/meetbill/butterfly/handlers/api/__init__.pyc'>,
                'handlers':     <module 'handlers' from '/home/users/meetbill/butterfly/handlers/__init__.pyc'>
               }
    """
    results = {}
    if isinstance(package, str):
        results[package] = importlib.import_module(package)
        package = importlib.import_module(package)

    # package.__path__ 是个文件夹路径列表，在本框架此处即为 ["handlers"]
    for _loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        if is_pkg:
            full_name = package.__name__ + '.' + name
            results[full_name] = importlib.import_module(full_name)
    return results


class Route(object):
    """Managing Route

    Attributes:
        infolog:(logger.LoggerBase) record info log
        errlog:(logger.LoggerBase) record error log
        apicube:(Dict) route info
    """

    def __init__(self, infolog, errlog):
        self._infolog = infolog
        self._errlog = errlog
        self.apicube = {}

    def addapi(self, name, func, is_serialize_response, is_parse_post, is_encode_response):
        """注册函数
        Args:
            name                    : (String)函数的注册名，默认为包中函数的全小写方法名
            func                    : (Object) 函数
            is_serialize_response   : (Bool) 是否进行将 handler 返回结果进行封装为 json 还是 file Protocol
                                    : True 时，handler return 为: (stat_str, data_dict, headers_list)
                                    : False 时，handler, return 为: (httpcode_int, data_str, headers_list)
            is_parse_post           : (Bool) 是否将请求 Body 中的内容解析为参数，传递给后端 handler
            is_encode_response      : (Bool) 是否进行序列化为 JSON
        Returns:
            response_type
                json/file/none
        """
        if not is_serialize_response:
            self.apicube[name] = protocol_json.Protocol(func, retstat.ERR_SERVER_EXCEPTION, retstat.ERR_BAD_PARAMS,
                                                        is_parse_post, is_encode_response, self._errlog)
            return "none"

        if is_encode_response:
            self.apicube[name] = protocol_json.Protocol(func, retstat.ERR_SERVER_EXCEPTION, retstat.ERR_BAD_PARAMS,
                                                        is_parse_post, is_encode_response, self._errlog)
            return "json"
        else:
            self.apicube[name] = protocol_file.Protocol(func, retstat.ERR_SERVER_EXCEPTION, retstat.ERR_BAD_PARAMS,
                                                        is_parse_post, is_encode_response, self._errlog)
            return "file"

    def add_apis(self, py_module, package_name=""):
        """将某个 module 文件中函数注册到路由中
        Args:
            py_module:Python module or package
            package_name: If py_module is a package ,You have to pass this parameter.
        """
        for func_name, func in py_module.__dict__.iteritems():
            if func_name.startswith("_"):
                continue
            if not inspect.isfunction(func):
                continue
            args_count = func.func_code.co_argcount
            if args_count < 1:
                continue
            args = func.func_code.co_varnames
            if args[0] != "req":
                continue
            name = "{package_name}.{func_name}".format(
                package_name=package_name, func_name=func_name)
            # handlers.api.ping ==> /api/ping
            path_name = "/" + "/".join(name.split(".")[1:])

            # adder_args 为 [is_parse_post,is_encode_response] 默认值为 [False, False]
            adder_args = [False, False]
            is_serialize_response = False
            if hasattr(func, 'apiattr'):
                is_serialize_response = True
                apiattr = getattr(func, 'apiattr')
                is_parse_post = apiattr['is_parse_post']
                is_encode_response = apiattr['is_encode_response']
                adder_args = [is_parse_post, is_encode_response]
            response_type = self.addapi(path_name.lower(), func, is_serialize_response, *adder_args)

            args_count = func.func_code.co_argcount - 1 if inspect.ismethod(func) else func.func_code.co_argcount
            func_args = func.func_code.co_varnames[:args_count]
            self._infolog.log(
                "[Init handler] {path:20} [args]:{func_args:30} [response_type]:{response_type} [is_parse_post]:{is_parse_post}"
                " [is_encode_response]:{is_encode_response}".format(
                    path=path_name,
                    func_args=func_args,
                    response_type=response_type,
                    is_parse_post=adder_args[0],
                    is_encode_response=adder_args[1]))

    def autoload_handler(self, package_dir):
        """自动加载指定目录下的所有 package
        Args:
            package_dir: package dir
        """
        # 将 "handlers" 目录下的 package 自动加载，也就是 __init__.py
        self._infolog.log("-----------------------------------------start autoload_handler")
        results = import_submodules(package_dir)
        for package_name in results:
            package = results[package_name]
            self.add_apis(
                package,
                package_name=package_name)

    def get_route(self):
        """
        获取路由 dict
        """
        return self.apicube
