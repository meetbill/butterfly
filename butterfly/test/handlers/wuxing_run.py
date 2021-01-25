#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-05-01 10:37:21

# File Name: test_apidemo-hello.py
# Description:
    用于测试五行接口，会将记录写入到数据库中

    备注: 此操作会进行 drop 表

    section:
        创建 section_name 为 group_appid 的三个 section_version 的记录
        1.0.1 :item (qn_failover, name_alias, resource_name, master_region, group_name), is_enabled (True)
        1.0.2 :item (qn_failover, name_alias, resource_name), is_enabled(True)
        1.0.3 :item (qn_failover, name_alias, resource_name, master_region, group_name, vip_list), is_enabled(True)
        1.0.4 :item (), is_enabled(False)

    执行方式：
        python wuxing.py main

"""

import xlib.db
from handlers.wuxing.models import model

from wuxing import wuxing_section
from wuxing import wuxing_instance
from wuxing import wuxing_item

def _clear_and_create_database():
    """
    清理和创建数据库
    """
    xlib.db.my_databases["default"].connect()
    model_list = [
        model.WuxingSection,
        model.WuxingInstance,
        model.WuxingInstanceItem,
        model.WuxingHistoryBool,
        model.WuxingHistoryFloat,
        model.WuxingHistoryInt,
        model.WuxingHistoryString]

    xlib.db.my_databases["default"].drop_tables(model_list)
    xlib.db.my_databases["default"].create_tables(model_list)

def main():
    """
    总程序
    """
    print ".............................reset database"
    _clear_and_create_database()
    print ".............................test section"
    wuxing_section.main()

    # instance
    print ".............................test instance"
    wuxing_section.test_section_create()
    wuxing_section.test_section_item_add()
    wuxing_section.test_section_enable()
    wuxing_instance.main()

    # item
    print ".............................test item"
    wuxing_item.main()


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
