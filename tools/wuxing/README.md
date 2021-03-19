# wuxing_cli.py
<!-- vim-markdown-toc GFM -->

* [1 作用](#1-作用)
* [2 使用](#2-使用)
    * [2.1 前置条件](#21-前置条件)
    * [2.2 配置](#22-配置)
    * [2.3 使用方法](#23-使用方法)
* [3 备注](#3-备注)

<!-- vim-markdown-toc -->

# 1 作用
通过 wuxing_cli.py 进行执行创建，删除，修改，查询 instance

# 2 使用
## 2.1 前置条件
> * 已经创建 section 以及 section 处于 enable 状态

## 2.2 配置
修改 wuxing_cli.py 中的
```
#----------------------------wuxing_cli config----------------------------------
WX_NAMESPACE="namespace"
WX_SECTION_NAME="section_name"
WX_SECTION_VERSION="1.0.1"
WX_ADDR="http://IP:PORT"
#-------------------------------------------------------------------------------
```
## 2.3 使用方法
```
Usage:
python wuxing_cli.py create 'instance_name'
python wuxing_cli.py delete 'instance_name'
python wuxing_cli.py get 'instance_name'
python wuxing_cli.py list
python wuxing_cli.py update 'instance_name' 'item_name' 'item_value' 'item_value_old=None'
```
# 3 备注

item_name 使用 `|` 作为 item 类型前缀的分割符，在 Linux 命令行中是管道符，故在使用的时候，需要对 itme_name 加双引号或者单引号

> 例子
```
"s|region" 或者 's|region'
```
