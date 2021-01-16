#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2020-03-22 22:52:08

# File Name: model.py for wuxing
# Description:

"""
from datetime import datetime

from xlib.db.peewee import AutoField
from xlib.db.peewee import CharField
from xlib.db.peewee import IntegerField
from xlib.db.peewee import DateTimeField
from xlib.db.peewee import CompositeKey
from xlib.db.peewee import DoubleField
from xlib.db.peewee import BooleanField
import xlib.db


# Define a model class
class WuxingSection(xlib.db.BaseModel):
    """
    配置模板列表
    更新频率低
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    # 命名空间(如 group_config/service_config/group_attr/service_attr/host_attr), 此处相当于是 1 级分类
    namespace = CharField(max_length=16)
    # 如果 namespace 是 service 的话，这里可能是组件名 twemproxy/memcache, 此处相当于是 2 级分类，对应实际配置的 instance 字段
    section_name = CharField(max_length=64)
    # 此模板的版本号
    section_version = CharField(max_length=16)
    # 模板内容，是个 json
    # 模板中字段维 item_name, 其内容需要包含(item_name, item_type, item_description, item_default)
    section_template = CharField(max_length=4096, default="{}")
    # section_md5
    section_md5 = CharField(max_length=64, index=True)
    # 模板开关，默认是未启用状态
    is_enabled = BooleanField(default=False, index=True)
    # 创建用户
    user = CharField(max_length=32, default="-", index=True)
    # 更新时间
    u_time = DateTimeField(column_name="u_time", default=datetime.now)
    # 创建时间
    c_time = DateTimeField(column_name="c_time", default=datetime.now)

    class Meta(object):
        table_name = 'wuxing_section'
        primary_key = CompositeKey('namespace', 'section_name', 'section_version')


class WuxingInstance(xlib.db.BaseModel):
    """
    配置模板与配置关联关系
    更新频率低
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    # 命名空间(如 group_config/service_config/group_attr/service_attr/host_attr), 此处相当于是 1 级分类
    namespace = CharField(max_length=16)
    # 如果 namespace 是 service 的话，这里可能是组件名 twemproxy/memcache, 此处相当于是 2 级分类，对应实际配置的 instance 字段
    instance_name = CharField(max_length=64)
    # 存储配置模板，是个 json
    instance_template = CharField(max_length=4096)
    section_name = CharField(max_length=64, index=True)
    section_version = CharField(max_length=64, index=True)
    section_md5 = CharField(max_length=64, index=True)
    # 配置是否有效
    is_valid = BooleanField(default=True)
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)
    u_time = DateTimeField(column_name="u_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_instance'
        primary_key = CompositeKey('namespace', 'instance_name')

# Define a model class


class WuxingInstanceItem(xlib.db.BaseModel):
    """
    配置 item
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    # 命名空间(如 group_config/service_config/group_attr/service_attr/host_attr)
    id = AutoField(primary_key=True)
    namespace = CharField(max_length=16, index=True)
    section_name = CharField(max_length=64, index=True)
    instance_name = CharField(max_length=64, index=True)
    item_name = CharField(max_length=64, index=True)
    item_type = CharField(max_length=64, index=True)
    item_value_bool = BooleanField(null=True, index=True)
    item_value_float = DoubleField(null=True, index=True)
    item_value_int = IntegerField(null=True, index=True)
    item_value_string = CharField(max_length=128, null=True, index=True)
    user = CharField(max_length=32, default="-")
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)
    u_time = DateTimeField(column_name="u_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_instance_item'

# Define a model class


class WuxingHistoryBool(xlib.db.BaseModel):
    """
    五行表结构, float 历史数据
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    id = AutoField(primary_key=True)
    item_id = IntegerField(index=True)
    item_value = BooleanField()
    cmd = CharField(max_length=8)
    user = CharField(max_length=32, default="-")
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_history_bool'

# Define a model class


class WuxingHistoryFloat(xlib.db.BaseModel):
    """
    五行表结构, float 历史数据
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    id = AutoField(primary_key=True)
    item_id = IntegerField(index=True)
    item_value = DoubleField(default=0)
    cmd = CharField(max_length=8)
    user = CharField(max_length=32, default="-")
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_history_float'

# Define a model class


class WuxingHistoryInt(xlib.db.BaseModel):
    """
    五行表结构, Int 历史数据
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    # 命名空间(如 group_config/service_config/group_attr/service_attr/host_attr)
    id = AutoField(primary_key=True)
    item_id = IntegerField(index=True)
    item_value = IntegerField(default=0)
    cmd = CharField(max_length=8)
    user = CharField(max_length=32, default="-")
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_history_int'

# Define a model class


class WuxingHistoryString(xlib.db.BaseModel):
    """
    五行表结构, String 历史数据
    """
    # If none of the fields are initialized with primary_key=True,
    # an auto-incrementing primary key will automatically be created and named 'id'.
    # 命名空间(如 group_config/service_config/group_attr/service_attr/host_attr)
    id = AutoField(primary_key=True)
    item_id = IntegerField(index=True)
    item_value = CharField(max_length=128)
    cmd = CharField(max_length=8)
    user = CharField(max_length=32, default="-")
    c_time = DateTimeField(column_name="c_time", default=datetime.now, index=True)

    class Meta(object):
        table_name = 'wuxing_history_string'


if __name__ == "__main__":
    xlib.db.my_database.connect()
    model_list = [
        WuxingSection,
        WuxingInstance,
        WuxingInstanceItem,
        WuxingHistoryBool,
        WuxingHistoryFloat,
        WuxingHistoryInt,
        WuxingHistoryString]

    # xlib.db.my_database.drop_tables(model_list)
    xlib.db.my_database.create_tables(model_list)
