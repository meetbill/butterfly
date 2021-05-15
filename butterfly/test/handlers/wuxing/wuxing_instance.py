#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-05-01 10:37:21

# File Name: wuxing_instance
# Description:
    用于测试五行 instance 接口
"""


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

    # 创建 instance 时，指定 item_value 值
    section_version = "1.0.1"
    instance_name = "2525"
    items_data = {"s|master_region", "bj"}
    stat, data, header_list = wuxing.instance_create(
        req, namespace, instance_name, section_name, section_version, items_data)
    assert stat == retstat.OK

    # ERR_INSTANCE_NAME_IS_INVALID
    instance_name = "1234567890" * 7
    stat, data, header_list = wuxing.instance_create(
        req, namespace, instance_name, section_name, section_version, items_data)
    assert stat == retstat.ERR_INSTANCE_NAME_IS_INVALID


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
    extra_items = "b|qn_failover,s|resource_name"
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
        for extra_item in extra_items.split(","):
            assert extra_item in instance_data.keys()


def test_instance_get():
    """
    获取 instance 信息
    """

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"

    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, value_format="detail")
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
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, demo_item_name, value_format="detail")
    assert stat == retstat.OK
    demo_data = {
        'data': {
            u'b|qn_failover': {
                'item_value': True,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            },
        }
    }
    # 去掉返回值中的 u_time
    assert data["data"]["b|qn_failover"].pop("u_time")
    assert data["data"]["b|qn_failover"].pop("item_id")
    assert data == demo_data


def test_instance_update_item():
    """
    更新 instance item
    """

    # ---------------------------------------------直接变更 item_value----------------------------------------------------start
    # OK
    namespace = "group_qingnang"
    instance_name = "2523"
    item_name = "b|qn_failover"
    item_value = False

    stat, data, header_list = wuxing.instance_update_item(req, namespace, instance_name, item_name, item_value)
    assert stat == retstat.OK

    # 检查配置是否修改成功
    demo_item_name = "b|qn_failover"
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, demo_item_name, value_format="detail")
    assert stat == retstat.OK
    demo_data = {
        'data': {
            "b|qn_failover": {
                'item_value': False,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            }
        }
    }
    # 去掉返回值中的 u_time
    assert data["data"]["b|qn_failover"].pop("u_time")
    assert data["data"]["b|qn_failover"].pop("item_id")
    assert data == demo_data

    # ERR_ITEM_IS_NOT_EXIST
    item_name = "qn_failover_xx"
    stat, data, header_list = wuxing.instance_update_item(req, namespace, instance_name, item_name, item_value)
    assert stat == retstat.ERR_ITEM_IS_NOT_EXIST
    # ---------------------------------------------直接变更 item_value----------------------------------------------------end

    # ------------------------------------------检查设置了前置变更条件的变更----------------------------------------------start
    # Fail
    namespace = "group_qingnang"
    instance_name = "2523"
    item_name = "b|qn_failover"
    item_value = False
    item_value_old = True

    stat, data, header_list = wuxing.instance_update_item(
        req, namespace, instance_name, item_name, item_value, item_value_old=item_value_old)
    assert stat == retstat.ERR_ITEM_UPDATE_FAILED

    # OK
    namespace = "group_qingnang"
    instance_name = "2523"
    item_name = "b|qn_failover"
    item_value = True
    item_value_old = False

    stat, data, header_list = wuxing.instance_update_item(
        req, namespace, instance_name, item_name, item_value, item_value_old=item_value_old)
    assert stat == retstat.OK

    # 检查配置是否修改成功
    demo_item_name = "b|qn_failover"
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, demo_item_name, value_format="detail")
    assert stat == retstat.OK
    demo_data = {
        'data': {
            "b|qn_failover": {
                'item_value': True,
                u'item_name': u'b|qn_failover',
                u'item_type': u'bool',
                u'item_description': u'qn failover switch'
            }
        }
    }
    # 去掉返回值中的 u_time
    assert data["data"]["b|qn_failover"].pop("u_time")
    assert data["data"]["b|qn_failover"].pop("item_id")
    assert data == demo_data
    # ------------------------------------------检查设置了前置变更条件的变更----------------------------------------------end


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
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, value_format="detail")
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
    stat, data, header_list = wuxing.instance_get(req, namespace, instance_name, value_format="detail")
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
            },
            u's|vip_list': {
                'item_value': u'-',
                u'item_name': u's|vip_list',
                u'item_type': u'string',
                u'item_description': u'vip list'
            },
            u't|service_log': {
                "item_name": "t|service_log",
                "item_default": "-",
                'item_type': 'text',
                "item_description": "log"
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
    # 默认值创建的 instance
    instance_name = "2523"
    stat, data, header_list = wuxing.instance_delete(req, namespace, instance_name)
    assert stat == retstat.OK

    # 指定值创建的 instance
    instance_name = "2525"
    stat, data, header_list = wuxing.instance_delete(req, namespace, instance_name)
    assert stat == retstat.OK


def main():
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
