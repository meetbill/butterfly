# butterfly

<div align=center><img src="https://github.com/meetbill/butterfly/blob/master/images/butterfly.png" width="350"/></div>

蝴蝶（轻量化 Web 框架）如同蝴蝶一样，此框架小而美

```
    __          __  __            ______
   / /_  __  __/ /_/ /____  _____/ __/ /_  __
  / __ \/ / / / __/ __/ _ \/ ___/ /_/ / / / /
 / /_/ / /_/ / /_/ /_/  __/ /  / __/ / /_/ /
/_.___/\__,_/\__/\__/\___/_/  /_/ /_/\__, /
                                    /____/
```
<!-- vim-markdown-toc GFM -->

* [1 简介](#1-简介)
    * [1.1 环境](#11-环境)
    * [1.2 特性](#12-特性)
    * [1.3 快速上手](#13-快速上手)
* [2 设计概述](#2-设计概述)
    * [2.1 架构](#21-架构)
    * [2.2 WSGI server 服务器模型](#22-wsgi-server-服务器模型)
    * [2.3 WSGI App MVC 模型](#23-wsgi-app-mvc-模型)
        * [2.3.1 Model 是核心](#231-model-是核心)
        * [2.3.2 本框架中的 MVC](#232-本框架中的-mvc)
    * [2.4 路由自动生成](#24-路由自动生成)
* [3 使用手册](#3-使用手册)
    * [3.1 手册传送门](#31-手册传送门)
    * [3.2 举个栗子](#32-举个栗子)
* [4 版本信息](#4-版本信息)
* [5 参加步骤](#5-参加步骤)

<!-- vim-markdown-toc -->

## 1 简介

### 1.1 环境

```
env:Python 2.7
```
### 1.2 特性

```
# GET 不带参数
GET http://IP:PORT/{app}/{handler}

# GET 带参数
GET http://IP:PORT/{app}/{handler}?args1=value1

# POST 参数时, 数据类型需要是 application/json

如:
curl -v "http://127.0.0.1:8585/x/ping"                                  ===> handlers/x/__init__.py:ping()
curl -v "http://127.0.0.1:8585/x/hello?str_info=meetbill"               ===> handlers/x/__init__.py:hello(str_info=meetbill)
curl -v  -d '{"str_info":"meetbill"}' http://127.0.0.1:8585/x/hello     ===> handlers/x/__init__.py:hello(str_info=meetbill)
```

> * 根据 handlers package 下 package 目录结构自动加载路由(目前不支持动态路由)
>   * 只加载 handlers package 及其子 package 下符合条件的函数作为 handler
> * 自定义 HTTP header
> * Handler 的参数列表与 HTTP 请求参数保持一致，便于接口开发
> * 自动对 HTTP 请求参数进行参数检查
> * 请求的响应 Header 中包含请求的 reqid(会记录在日志中),便于进行 trace

### 1.3 快速上手
> 部署
```
$git clone https://github.com/meetbill/butterfly.git
$cd butterfly/butterfly
```
> 配置端口---默认 8585
```
conf/config.py
```
> 启动
```
$bash run.sh start
```
> 访问
```
$curl "http://127.0.0.1:8585/x/ping"
{"stat": "OK", "randstr": "..."}

$curl "http://127.0.0.1:8585/x/hello?str_info=meetbill"
{"stat": "OK", "str_info": "meetbill"}
```
> 调试 handler
```
$python test_handler.py /x/ping
('OK', {'randstr': '...'}, [('demo', '1.0.1')])
```

## 2 设计概述

### 2.1 架构

```
         +---------------------------------------------------------+
         |                       WEB brower                        |
         +---------------------------------------------------------+
             |                           ^       ^          ^
             |                           |       |          |
             |HTTP request               |       |          |
             |                           |       |          |
      -- +---V-----------------------------------------------------+
    /    |                       HTTPServer                        |  WSGI server
    |    |     +-------------------+ put +-------------------+     |
    |    |     |ThreadPool(Queue) <+-----+ HTTPConnection    |     |
    |    |     |+---------------+  |     | +---------------+ |     |
    |    |     ||WorkerThread   |  |     | |HTTPRequest    | |     |
    |    |     |+---------------+  |     | +---------------+ |     |
    |    |     +-------------------+     +-------------------+     |
    |    +---------------------------------------------------------+
    |          /------------\            ^       ^          ^
    |         |   environ    |           |       |          |
    |          \------------/            |       |          |
    |   .............|...................|.......|..........|.........WSGI
    |                |                   |       |          |
    |         +------V-------+           |       |          |
    |         |      req     |           |       |          |
    |         +--------------+           |       |          |
Butterfly            |                   |       |          |
    |         +------V-------+           |       |          |
    |         |apiname_getter|           |       |          |
    |         +--------------+           |       |          |
    |                |                   |       |          |
    |       +--------V--------+ False +--+--+    |          |
    |       |is_protocol_exist|------>| 400 |    |          |
    |       +-----------------+       +-----+    |          |
    |                |                           |          |
    |                | (protocol_process)        |          |
    |                V                           |          |
    |       +-----------------+                  |          |
    |       | protocol        |  Exception    +-----+       |
    |       | +-------------+ |---------------| 500 |       |
    |       | |/app1/handler| |               +-----+       |
    |       | |/app2/handler| |               +----------------------------+
    |       | +-------------+ |---------------|httpstatus, headers, content|
    \       +-----------------+               +----------------------------+
     ---
```

### 2.2 WSGI server 服务器模型

ThreadPool 线程池

### 2.3 WSGI App MVC 模型

#### 2.3.1 Model 是核心

Model，也就是模型，是对现实的反映和简化。**对问题的本质的描述就是 Model。解决问题就是给问题建立 Model。**

当我们关注业务问题时，只有描述 “用户所关心的问题” 的代码才是 Model。当你的关注转移到其他问题时，Model 也会相应发生变化。

**失去了解决特定问题这一语境，单谈 Model 没有意义。**

可以说，View 和 Controller 是 Model 的一部分。

> 为人们要单独把他们跟 Model 分开呢？
```
View 和 Controller 是外在的东西，只有 Model 是本质的东西。
外在的东西天天变化，但很少影响本质。把他们分开比较容易维护。
```

#### 2.3.2 本框架中的 MVC

简单来说，Controller 和 View 分别是 Model 的 输入 和 输出。

> * Model，也就是模型，是对现实的反映和简化
> * View，也就是视图/视野，是你真正看到的，而非想象中的 Model。
> * Controller，也就是控制器，是你用来改变 Model 方式。

View 建议在 [butterfly-fe](https://github.com/meetbill/butterfly-fe) 实现，即前后端分离

使用 butterfly 框架时主要是编写 handler
```
                                               handler
                              +-----------------------------------------+
    +-----------+ user action | +------------+  update  +-------------+ |
    |   view    |-------------+>| controller |--------->|    model    | |
    |           |<------------+-|            |<---------|             | |
    +--+--------+  update     | +------------+   notify +-------------+ |
                              +-----------------------------------------+
```
### 2.4 路由自动生成

无需人为进行路由配置操作

> 约定优于配置，配置优于实现
```
在 handlers 文件夹下的 package 中的 __init__.py 编写 handler controller 函数来完成 "功能的抽象"
controller 函数是第一个参数为 "req" 的非私有函数
```
重新启动服务时，框架会自动加载 handlers 各 package  `__init__.py` 中符合条件的函数并生成路由

> 条件(第一个参数为 "req" 的非私有函数)
```
(1) 私有函数不会被加载，即函数名是 "_" 开头
(2) 类不会被加载，即 handler 中 controller 使用函数来完成 "功能的抽象"
(3) 函数的第一个形参名需要是 "req"
    调用此函数时的实参 req 是对 HTTP request environ 的封装
```

## 3 使用手册

### 3.1 手册传送门

* [Butterfly 手册](https://github.com/meetbill/butterfly/wiki)
* [Butterfly 示例](https://github.com/meetbill/butterfly-examples)
* [Butterfly 前端](https://github.com/meetbill/butterfly-fe)
* [Butterfly nginx 配置](https://github.com/meetbill/butterfly-nginx)

### 3.2 举个栗子

> 前后端分离 + 单点登录应用
>  * 整体方案的后端接口认证使用 nginx auth_request 进行验证
>  * [接口认证方案](https://github.com/meetbill/butterfly/wiki/butterfly_cas)模块化，复用性强

```
               +--------------------------------------------------------------------------+
               |                          butterfly-nginx                                 |
               +--------------------------------------------------------------------------+
                       |                     |                                      |
                       V                     V                                      V
               +-------------+    +---------------------+                      +----------+
               |~* /static/  |    |= /auth/verification |                      |/         |
               |= /index.html|    |= /butterfly_401     |                      |          |
               |= /          |    |= /auth/ssologin     |                      |          |
               +-------------+    +---------------------+                      +----------+
                       |                     |                                       |
                       V                     V                                       V
+----------+       +------------+     +--------------+       +----------+     +-----------+
|web browse|       |butterfly-fe|     |butterfly-auth|       |cas-server|     |app-backend|
+----------+       +------------+     +--------------+       +----------+     +-----------+
     |                    |                  |                     |                   |
     +-------route------->|/                 |                     |                   |
     |<-------page--------+/index.html       |                     |                   |
     |                    |                  |                     |                   |
     ==================================================================== not have token
     |                    |                  |                     |                   |
     +--V----------------request api-------------------------------------------------->|
     |  +-sub request-header not have token->|(/auth/verification) |                   |
     |<-code=401,targetURL=../auth/ssologin--+                     |                   |
     |                    |                  |                     |                   |
     +--window.location.herf=directurl------>|(/auth/ssologin)     |                   |
     |<----code=302,Location=cas-server------+                     |                   |
     |                    |                  |                     |                   |
     +-----302 http://cas-server/login  login page --------------->|(/login)           |
     |<-------------code=302,set Cookie TGT=xxx -------------------+                   |
     |                    |                  |                     |                   |
     +-----302 /auth/ssologin?ticket=xxx --->|                     |                   |
     |                    |                  +-------check st----->|(/session/validate)|
     |                    |                  |<-------st vaild-----+                   |
     |<--code=302 set Cookie butterfly_token-+                     |                   |
     |                    |                  |                     |                   |
     +--302 / ----------->|                  |                     |                   |
     |<-------page--------+/index.html       |                     |                   |
     |                    |                  |                     |                   |
     ======================================================================== have token
     |                    |                  |                     |                   |
     +---V----------------request api------------------------------------------------->|
     |   +-sub request-header have token---->|/auth/verification   |                   |
     |<-------------------response-----------------------------------------------------+
```

## 4 版本信息

本项目的各版本信息和变更历史可以在[这里][changelog]查看。

## 5 参加步骤

* 在 GitHub 上 `fork` 到自己的仓库，然后 `clone` 到本地，并设置用户信息。
```
$ git clone https://github.com/meetbill/butterfly.git
$ cd butterfly
$ git config user.name "yourname"
$ git config user.email "your email"
```
* 修改代码后提交，并推送到自己的仓库。
```
$ #do some change on the content
$ git commit -am "Fix issue #1: change helo to hello"
$ git push
```
* 在 GitHub 网站上提交 pull request。
* 定期使用项目仓库内容更新自己仓库内容。
```
$ git remote add upstream https://github.com/meetbill/butterfly.git
$ git fetch upstream
$ git checkout master
$ git rebase upstream/master
$ git push -f origin master
```

[changelog]: CHANGELOG.md
