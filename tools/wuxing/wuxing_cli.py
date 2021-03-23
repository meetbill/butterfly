#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-03-19 16:00:26

# File Name: wuxing_cli.py
# Description:
    Usage:
        wuxing_cli.py create 'instance_name'
        wuxing_cli.py delete 'instance_name'
        wuxing_cli.py get 'instance_name'
        wuxing_cli.py list
        wuxing_cli.py update 'instance_name' 'item_name' 'item_value' 'item_value_old=None'
        wuxing_cli.py upgrade 'instance_name' 'section_version'
    version:
        1.0.1: 2021-03-19
            初始版本，可创建 instance, 获取 instance 列表，获取 instance 详情，修改 instance item
        1.0.2: 2021-03-23
            (1) 增加: upgrade 方法用于升级 instance 版本
            (2) 修改: list 方法增加输出 instance 版本号
"""
import urllib
import urllib2
import json

# ----------------------------wuxing_cli config----------------------------------
WX_NAMESPACE = "namespace"
WX_SECTION_NAME = "section_name"
WX_SECTION_VERSION = "1.0.1"
WX_ADDR = "http://IP:PORT"
# -------------------------------------------------------------------------------
WX_INSTANCE_LIST = "{addr}/wuxing/instance_list".format(addr=WX_ADDR)
WX_INSTANCE_DELETE = "{addr}/wuxing/instance_delete".format(addr=WX_ADDR)
WX_INSTANCE_CREATE = "{addr}/wuxing/instance_create".format(addr=WX_ADDR)
WX_INSTANCE_UPDATE = "{addr}/wuxing/instance_update_item".format(addr=WX_ADDR)
WX_INSTANCE_UPGRADE = "{addr}/wuxing/instance_update_section".format(addr=WX_ADDR)
WX_INSTANCE_GET = "{addr}/wuxing/instance_get".format(addr=WX_ADDR)


def list():
    """
    instance list
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["section_name"] = WX_SECTION_NAME
    params["page_index"] = 1
    while True:
        request = urllib2.Request(WX_INSTANCE_LIST + "?" + urllib.urlencode(params))
        response = urllib2.urlopen(request)
        rep_data_json = response.read()
        rep_data = json.loads(rep_data_json)
        if len(rep_data["data"]["list"]) == 0:
            break

        for instance in rep_data["data"]["list"]:
            print "{instance_name}\t{section_version}".format(
                instance_name=instance["instance_name"],
                section_version=instance["section_version"])
        params["page_index"] = params["page_index"] + 1


def get(instance_name):
    """
    instance list
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["instance_name"] = instance_name
    request = urllib2.Request(WX_INSTANCE_GET + "?" + urllib.urlencode(params))
    response = urllib2.urlopen(request)
    rep_data_json = response.read()
    rep_data = json.loads(rep_data_json)
    print json.dumps(rep_data, sort_keys=True, indent=4)


def create(instance_name):
    """
    create instance
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["instance_name"] = instance_name
    params["section_name"] = WX_SECTION_NAME
    params["section_version"] = WX_SECTION_VERSION
    params_json = json.dumps(params)
    request = urllib2.Request(WX_INSTANCE_CREATE, params_json)
    response = urllib2.urlopen(request)
    rep_data_json = response.read()
    print rep_data_json


def delete(instance_name):
    """
    delete instance
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["instance_name"] = instance_name
    params_json = json.dumps(params)
    request = urllib2.Request(WX_INSTANCE_DELETE, params_json)
    response = urllib2.urlopen(request)
    rep_data_json = response.read()
    print rep_data_json


def update(instance_name, item_name, item_value, item_value_old=None):
    """
    update instance item
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["instance_name"] = instance_name
    params["item_name"] = item_name
    params["item_value"] = item_value
    if item_value_old is not None:
        params["item_value_old"] = item_value_old
    params_json = json.dumps(params)
    request = urllib2.Request(WX_INSTANCE_UPDATE, params_json)
    response = urllib2.urlopen(request)
    rep_data_json = response.read()
    print rep_data_json


def upgrade(instance_name, section_version):
    """
    update instance section version
    """
    params = {}
    params["namespace"] = WX_NAMESPACE
    params["instance_name"] = instance_name
    params["section_version"] = section_version
    params_json = json.dumps(params)
    request = urllib2.Request(WX_INSTANCE_UPGRADE, params_json)
    response = urllib2.urlopen(request)
    rep_data_json = response.read()
    print rep_data_json


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
