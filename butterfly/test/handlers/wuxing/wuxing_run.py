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


from handlers import wuxing
from handlers.wuxing.models import model
from handlers.wuxing.libs import retstat
import xlib.db
from xlib import httpgateway

__info = "wuxing"
__version = "1.0.1"

# 生成 req
reqid = "test_hello"
ip = "127.0.0.1"
wsgienv = {}
req = httpgateway.Request(reqid, wsgienv, ip)


def test_section_create():
    """
    创建 section
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"  # item 5 个
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    # ERR_SECTION_IS_EXIST
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.ERR_SECTION_IS_EXIST

    # 创建同 section_name , section_version 不同的实例
    section_version = "1.0.2"  # item 3 个
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    # 创建同 section_name , section_version 不同的实例
    section_version = "1.0.3"  # item 6 个
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    section_version = "1.0.4"  # item 0 个
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    # ERR_SECTION_CREATE_FAILED
    # namespace 超出长度
    namespace = "12345678901234567"
    stat, data, header_list = wuxing.section_create(req, namespace, section_name, section_version)
    assert stat == retstat.ERR_SECTION_CREATE_FAILED


def test_section_item_add():
    """
    section 添加 item
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    item_list = [
        {
            "item_name": "b|qn_failover",
            "item_default": "true",
            "item_description": "qn failover switch"
        },
        {
            "item_name": "s|name_alias",
            "item_default": "-",
            "item_description": "group name alias"
        },
        {
            "item_name": "s|resource_name",
            "item_default": "common_ssd",
            "item_description": "resource for deploy"
        },
        {
            "item_name": "s|master_region",
            "item_default": "-",
            "item_description": "master region"
        },
        {
            "item_name": "s|group_name",
            "item_default": "-",
            "item_description": "group name"
        }
    ]
    for item in item_list:
        stat, data, header_list = wuxing.section_item_add(req, namespace, section_name, section_version,
                                                          item["item_name"], item["item_default"], item["item_description"])

        assert stat == retstat.OK

    # ERR_SECTION_ITEM_IS_EXIST
    stat, data, header_list = wuxing.section_item_add(req, namespace, section_name, section_version,
                                                      "b|qn_failover", "true", "qn failover switch")
    assert stat == retstat.ERR_SECTION_ITEM_IS_EXIST

    # 创建其他 section_version 的 item
    section_version = "1.0.2"
    item_list = [
        {
            "item_name": "b|qn_failover",
            "item_default": "true",
            "item_description": "qn failover switch"
        },
        {
            "item_name": "s|name_alias",
            "item_default": "-",
            "item_description": "group name alias"
        },
        {
            "item_name": "s|resource_name",
            "item_default": "common_ssd",
            "item_description": "resource for deploy"
        }
    ]
    for item in item_list:
        stat, data, header_list = wuxing.section_item_add(req, namespace, section_name, section_version,
                                                          item["item_name"], item["item_default"], item["item_description"])

        assert stat == retstat.OK
    section_version = "1.0.3"
    item_list = [
        {
            "item_name": "b|qn_failover",
            "item_default": "true",
            "item_description": "qn failover switch"
        },
        {
            "item_name": "s|name_alias",
            "item_default": "-",
            "item_description": "group name alias"
        },
        {
            "item_name": "s|resource_name",
            "item_default": "common_ssd",
            "item_description": "resource for deploy"
        },
        {
            "item_name": "s|master_region",
            "item_default": "-",
            "item_description": "master region"
        },
        {
            "item_name": "s|group_name",
            "item_default": "-",
            "item_description": "group name"
        },
        {
            "item_name": "s|vip_list",
            "item_default": "-",
            "item_description": "vip list"
        }
    ]
    for item in item_list:
        stat, data, header_list = wuxing.section_item_add(req, namespace, section_name, section_version,
                                                          item["item_name"], item["item_default"], item["item_description"])

        assert stat == retstat.OK


def test_section_enable():
    """
    enable section
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    stat, data, header_list = wuxing.section_enable(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.2"
    stat, data, header_list = wuxing.section_enable(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.3"
    stat, data, header_list = wuxing.section_enable(req, namespace, section_name, section_version)
    assert stat == retstat.OK


def test_section_list():
    """
    section list
    """

    # OK
    stat, data, header_list = wuxing.section_list(req)
    assert stat == "OK"
    # section count
    assert data["data"]["total"] != 0


def test_section_get():
    """
    获取 section
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    stat, data, header_list = wuxing.section_get(req, namespace, section_name, section_version)
    assert stat == "OK"

    demo_data = {
        'data': {
            'is_enabled': True,
            'section_template': {
                u'b|qn_failover': {
                    u'item_type': u'bool',
                    u'item_default': u'true',
                    u'item_description': u'qn failover switch'
                },
                u's|name_alias': {
                    u'item_type': u'string',
                    u'item_default': u'-',
                    u'item_description': u'group name alias'
                },
                u's|resource_name': {
                    u'item_type': u'string',
                    u'item_default': u'common_ssd',
                    u'item_description': u'resource for deploy'
                },
                u's|master_region': {
                    u'item_type': u'string',
                    u'item_default': u'-',
                    u'item_description': u'master region'
                },
                u's|group_name': {
                    u'item_type': u'string',
                    u'item_default': u'-',
                    u'item_description': u'group name'
                }
            }
        }
    }
    assert data == demo_data


def test_instance_create():
    """
    创建 instance
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    instance_name = "2523"

    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.OK

    # ERR_SECTION_IS_EXIST
    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.ERR_INSTANCE_IS_EXIST

    # ERR_SECTION_IS_NOT_ENABLED
    section_version = "1.0.4"
    instance_name = "2524"
    stat, data, header_list = wuxing.instance_create(req, namespace, instance_name, section_name, section_version)
    assert stat == retstat.ERR_SECTION_IS_NOT_ENABLED


def test_instance_list():
    """
    获取 instance 列表
    """

    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    # instance_name="2523"

    stat, data, header_list = wuxing.instance_list(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    # get extra item
    extra_items = "b|qn_failover:s|resource_name"
    stat, data, header_list = wuxing.instance_list(req, namespace, section_name, extra_items=extra_items)
    """
    data:
    {
        'data': {
            'total': 1,
            'list': [
                {
                    'u_time': datetime.datetime(2021, 1, 22, 9, 5, 11),
                    'namespace': u'group_qingnang',
                    'instance_name': u'2523',
                    'qn_failover': True,
                    'section_version': u'1.0.1',
                    'section_name': u'group_appid',
                    'resource_name': u'common_ssd',
                    'section_md5': u'a688a0b0'
                }
            ]
        }
    }
    """
    for instance_data in data["data"]["list"]:
        for extra_item in extra_items.split(":"):
            assert extra_item in instance_data.keys()


def test_instance_get():
    """
    获取 instance 信息
    """

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"

    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name)
    assert stat == retstat.OK

    demo_data = {
        'data': {
            u'b|qn_failover': {
                'item_value': True,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            },
            u's|name_alias': {
                'item_value': u'-',
                u'item_name': u's|name_alias',
                u'item_type': u'string',
                u'item_description': u'group name alias'
            },
            u's|resource_name': {
                'item_value': u'common_ssd',
                u'item_name': u's|resource_name',
                u'item_type': u'string',
                u'item_description': u'resource for deploy'
            },
            u's|master_region': {
                'item_value': u'-',
                u'item_name': u's|master_region',
                u'item_type': u'string',
                u'item_description': u'master region'
            },
            u's|group_name': {
                'item_value': u'-',
                u'item_name': u's|group_name',
                u'item_type': u'string',
                u'item_description': u'group name'
            }
        }
    }
    # 去掉返回值中的 u_time
    for item_name in data["data"].keys():
        assert data["data"][item_name].pop("u_time")
        assert data["data"][item_name].pop("item_id")

    assert data == demo_data

    # 测试某个 item 获取
    demo_item_name = "b|qn_failover"
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, demo_item_name)
    assert stat == retstat.OK
    demo_data = {
        'data': {
            'item_value': True,
            u'item_name': u'b|qn_failover',
            u'item_type': u'bool',
            u'item_description': u'qn failover switch'
        }
    }
    # 去掉返回值中的 u_time
    assert data["data"].pop("u_time")
    assert data["data"].pop("item_id")
    assert data == demo_data


def test_instance_update_item():
    """
    更新 instance item
    """

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"
    item_name = "b|qn_failover"
    item_value = False

    stat, data, header_list = wuxing.instance_update_item(req, namespace, instance_name, item_name, item_value)
    assert stat == retstat.OK

    # 检查配置是否修改成功
    demo_item_name = "b|qn_failover"
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, demo_item_name)
    assert stat == retstat.OK
    demo_data = {
        'data': {
            'item_value': False,
            u'item_name': u'b|qn_failover',
            u'item_type': u'bool',
            u'item_description': u'qn failover switch'
        }
    }
    # 去掉返回值中的 u_time
    assert data["data"].pop("u_time")
    assert data["data"].pop("item_id")
    assert data == demo_data

    # ERR_ITEM_IS_NOT_EXIST
    item_name = "qn_failover_xx"
    stat, data, header_list = wuxing.instance_update_item(req, namespace, instance_name, item_name, item_value)
    assert stat == retstat.ERR_ITEM_IS_NOT_EXIST


def test_instance_update_section():
    """
    更新 instance section
    """

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"
    section_version = "1.0.2"
    stat, data, header_list = wuxing.instance_update_section(req, namespace, instance_name, section_version)
    assert stat == retstat.OK

    # check
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name)
    assert stat == retstat.OK

    demo_data = {
        'data': {
            u'b|qn_failover': {
                # 此值进行过更新
                'item_value': False,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            },
            u's|name_alias': {
                'item_value': u'-',
                u'item_name': u's|name_alias',
                u'item_type': u'string',
                u'item_description': u'group name alias'
            },
            u's|resource_name': {
                'item_value': u'common_ssd',
                u'item_name': u's|resource_name',
                u'item_type': u'string',
                u'item_description': u'resource for deploy'
            },
        }
    }
    # 去掉返回值中的 u_time
    for item_name in data["data"].keys():
        assert data["data"][item_name].pop("u_time")
        assert data["data"][item_name].pop("item_id")
    assert data == demo_data

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"
    section_version = "1.0.3"
    stat, data, header_list = wuxing.instance_update_section(req, namespace, instance_name, section_version)
    assert stat == retstat.OK

    # check
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name)
    assert stat == retstat.OK

    demo_data = {
        'data': {
            u'b|qn_failover': {
                'item_value': False,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            },
            u's|name_alias': {
                'item_value': u'-',
                u'item_name': u's|name_alias',
                u'item_type': u'string',
                u'item_description': u'group name alias'
            },
            u's|resource_name': {
                'item_value': u'common_ssd',
                u'item_name': u's|resource_name',
                u'item_type': u'string',
                u'item_description': u'resource for deploy'
            },
            u's|master_region': {
                'item_value': u'-',
                u'item_name': u's|master_region',
                u'item_type': u'string',
                u'item_description': u'master region'
            },
            u's|group_name': {
                'item_value': u'-',
                u'item_name': u's|group_name',
                u'item_type': u'string',
                u'item_description': u'group name'
            },
            u's|vip_list': {
                'item_value': u'-',
                u'item_name': u's|vip_list',
                u'item_type': u'string',
                u'item_description': u'vip list'
            }
        }
    }
    # 去掉返回值中的 u_time
    for item_name in data["data"].keys():
        assert data["data"][item_name].pop("u_time")
        assert data["data"][item_name].pop("item_id")
    assert data["data"].keys() == demo_data["data"].keys()

    # 检测 item
    assert data["data"]["b|qn_failover"] == demo_data["data"]["b|qn_failover"]
    assert data["data"]["s|name_alias"] == demo_data["data"]["s|name_alias"]
    assert data["data"]["s|resource_name"] == demo_data["data"]["s|resource_name"]

    # ERR_SECTION_IS_NOT_ENABLED
    namespace = "group_qingnang"
    instance_name = "2523"
    section_version = "1.0.4"
    stat, data, header_list = wuxing.instance_update_section(req, namespace, instance_name, section_version)
    assert stat == retstat.ERR_SECTION_IS_NOT_ENABLED

    # ERR_SECTION_IS_NOT_EXIST
    namespace = "group_qingnang"
    instance_name = "2523"
    section_version = "1.0.5"
    stat, data, header_list = wuxing.instance_update_section(req, namespace, instance_name, section_version)
    assert stat == retstat.ERR_SECTION_IS_NOT_EXIST


def test_instance_delete():
    """
    instance delete
    """
    namespace = "group_qingnang"
    instance_name = "2523"
    stat, data, header_list = wuxing.instance_delete(req, namespace, instance_name)
    assert stat == retstat.OK


def test_section_delete():
    """
    section delete
    """
    # OK
    namespace = "group_qingnang"
    section_name = "group_appid"
    section_version = "1.0.1"
    stat, data, header_list = wuxing.section_delete(req, namespace, section_name, section_version)
    assert stat == retstat.OK

    # ERR_SECTION_IS_NOT_EXIST
    section_version = "1.0.5"
    stat, data, header_list = wuxing.section_delete(req, namespace, section_name, section_version)
    assert stat == retstat.ERR_SECTION_IS_NOT_EXIST


def main():
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
    # create section
    print("section create----------------------------------")
    test_section_create()

    # create item_add
    print("section item add--------------------------------")
    test_section_item_add()

    # section enable
    print("section enable----------------------------------")
    test_section_enable()

    # section_list
    print("section list------------------------------------")
    test_section_list()

    # section_get
    print("section get-------------------------------------")
    test_section_get()

    # instance create
    print("instance create---------------------------------")
    test_instance_create()

    # instance list
    print("instance list-----------------------------------")
    test_instance_list()

    # instance get
    print("instance get------------------------------------")
    test_instance_get()

    # instance update item
    print("instance update item----------------------------")
    test_instance_update_item()

    # instance update section
    print("instance update section-------------------------")
    test_instance_update_section()

    # instance delete
    print("instance delete---------------------------------")
    test_instance_delete()

    # section delete
    print("section delete----------------------------------")
    test_section_delete()


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
