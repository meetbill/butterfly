#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-05-01 10:37:21

# File Name: wuxing_instance
# Description:
    用于测试五行 instance 接口
"""

import time
import datetime

from handlers import wuxing
from handlers.wuxing.libs import retstat
from xlib import httpgateway

__info = "wuxing"
__version = "1.0.1"

# 生成 req
reqid = "test_hello"
ip = "127.0.0.1"
wsgienv = {}
req = httpgateway.Request(reqid, wsgienv, ip)

def test_instance_create():
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    instance_name = "3001"

    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.OK

    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    instance_name = "3002"

    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.OK

    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    instance_name = "3003"

    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.OK

def test_instance_update():
    time.sleep(3)
    namespace = "group_qingnang"
    instance_name = "3002"
    item_name = "s|resource_name"
    item_value = "common"

    stat, data, header_list = wuxing.instance_update_item(req, namespace, instance_name, item_name, item_value)
    assert stat == retstat.OK

def test_item_list():
    """
    test item list
    """
    namespace = "group_qingnang"
    section_name = "group_appid"
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name")
    assert len(data["data"]["list"]) == 3

    # 测试 item_value 搜索
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name",
            item_value_operator="=", item_value="common"
            )
    assert len(data["data"]["list"]) == 1

    # 测试 start_time 检索条件
    now_time_datetime = datetime.datetime.now()
    start_time_datetime = now_time_datetime + datetime.timedelta(seconds=-1)
    start_time = start_time_datetime.strftime("%Y%m%d%H%M%S")
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name",
            start_time=start_time)
    assert len(data["data"]["list"]) == 1
    assert data["data"]["list"][0]["instance_name"] == "3002"

    # 测试排序检索
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name", sort="instance_name")
    assert data["data"]["list"][0]["instance_name"] == "3001"
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name", sort="-instance_name")
    assert data["data"]["list"][0]["instance_name"] == "3003"

    # 排序字段可以是 {item_name}
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name", sort="s|resource_name")
    assert data["data"]["list"][0]["item_value"] == "common"
    stat, data, header_list = wuxing.item_list(req, namespace, section_name, item_name="s|resource_name", sort="-s|resource_name")
    assert data["data"]["list"][0]["item_value"] == "common_ssd"

def main():

    print("instance create---------------------------------")
    test_instance_create()

    print("instance update item----------------------------")
    test_instance_update()

    print("item list---------------------------------------")
    test_item_list()

if __name__ == "__main__":
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
