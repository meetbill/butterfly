#!/usr/bin/python
# coding=utf8
##########################################################################
#
# Copyright (c) 2020 Baidu.com, Inc. All Rights Reserved
#
##########################################################################
"""
# Author: wangbin34
# Created Time : 2020-02-23 21:40:27

# File Name: __init__.py
# Description:
    五行 API

+namespace1-------------------------------------------------------+
|                   +section1-----------------+                   |
|                   |+section_template-------+|                   |
|                   ||+-----+ +-----+ +-----+||                   |
|                   |||item1| |item2| |item3||| version:1.0.1     |
|                   ||+-----+ +-----+ +-----+||                   |
|                   |+-----------------------+|                   |
|                   +------+---------+--------+                   |
|                          |         |                            |
|                          |         +---------+                  |
|                          |                   |                  |
|                          |                   |                  |
|   +instance1-------------V--+  +instance2----V-----------+      |
|   |+instance_template------+|  |+instance_template------+|      |
|   ||+id:1-+ +id:2-+ +id:3-+||  ||+id:4-+ +id:5-+ +id:6-+||      |
|   |||item1| |item2| |item3|||  |||item1| |item2| |item3|||      |
|   ||+----++ +---+-+ +---+-+||  ||+--+--+ +---+-+ +---+-+||      |
|   |+-----|------|-------|--+|  |+---|--------|-------|--+|      |
|   +------|------|-------|---+  +----|--------|-------|---+      |
|          |      |       |           |        |       |          |
|   +item--|------|-------|-----------|--------|-------+---+      |
|   | +id:1V--+   |       |           |        |       |   |      |
|   | +-------+   |       |           |        |       |   |      |
|   |        +id:2V--+    |           |        |       |   |      |
|   |        +-------+    |           |        |       |   |      |
|   |               +id:3-V-+         |        |       |   |      |
|   |               +-------+         |        |       |   |      |
|   |                           +id:4-V-+      |       |   |      |
|   |                           +-------+      |       |   |      |
|   |                                    +id:5-V-+     |   |      |
|   |                                    +-------+     |   |      |
|   |                                            +id:6-V-+ |      |
|   |                                            +-------+ |      |
|   +------------------------------------------------------+      |
+-----------------------------------------------------------------+

+history----------------------------------------------------------+
|+------------------------+           +-------------------------+ |
||wuxing_history_bool     |           |wuxing_history_float     | |
|+------------------------+           +-------------------------+ |
|+------------------------+           +-------------------------+ |
||wuxing_history_int      |           |wuxing_history_string    | |
|+------------------------+           +-------------------------+ |
+-----------------------------------------------------------------+
"""
from handlers.wuxing.libs import section
from handlers.wuxing.libs import instance
from handlers.wuxing.libs import item


# section
section_list = section.section_list
section_create = section.section_create
section_item_add = section.section_item_add
section_item_delete = section.section_item_delete
section_get = section.section_get
section_enable = section.section_enable
section_delete = section.section_delete

# instance
instance_list = instance.instance_list
instance_create = instance.instance_create
instance_delete = instance.instance_delete
instance_get = instance.instance_get
# update item
instance_update_item = instance.instance_update_item
# update section
instance_update_section = instance.instance_update_section
# check instance_template 和 item 是否一致

# item
# item 的新增与删除统一由 instance 控制，故不直接暴露接口
# 不过 item 可以进行更新值等操作
item_update = item.item_update
item_get = item.item_get
item_list = item.item_list
