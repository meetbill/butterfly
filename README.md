# butterfly

<div align=center><img src="https://github.com/meetbill/butterfly/blob/master/images/butterfly.png" width="350"/></div>

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
    * [1.1 介绍](#11-介绍)
    * [1.2 环境](#12-环境)
    * [1.3 特性](#13-特性)
* [2 五分钟 Butterfly 体验指南](#2-五分钟-butterfly-体验指南)
    * [2.1 五分钟体验之部署 Butterfly（预计 1 分钟）](#21-五分钟体验之部署-butterfly预计-1-分钟)
    * [2.2 五分钟体验之编写 handler （预计 3 分钟）](#22-五分钟体验之编写-handler-预计-3-分钟)
    * [2.3 五分钟体验之调试 handler （预计 1 分钟）](#23-五分钟体验之调试-handler-预计-1-分钟)
* [3 设计蓝图](#3-设计蓝图)
    * [3.1 单实例内部请求流](#31-单实例内部请求流)
    * [3.2 多实例间消息队列通信](#32-多实例间消息队列通信)
* [4 了解更多](#4-了解更多)
    * [4.1 传送门](#41-传送门)
    * [4.2 自带 app 介绍](#42-自带-app-介绍)
    * [4.3 报告错误](#43-报告错误)
* [5 贡献](#5-贡献)
* [6 版本信息](#6-版本信息)
* [7 参加步骤](#7-参加步骤)

<!-- vim-markdown-toc -->

# 1 简介
## 1.1 介绍

Butterfly（轻量化 WSGI web 应用程序框架）如同蝴蝶一样，小而美，简单可依赖。目的是让入门变得简单快捷，能够扩展到复杂的应用程序。

> * 接入：普通 Python 函数可快速升级为 butterfly handler
> * 异步：开启【百川】，butterfly handler 可自动成为消息队列消费者，异步处理任务
> * 编排：使用【星桥】，设置 butterfly handler 依赖，有序编排 handler

## 1.2 环境

```
env:Python 2.7
```
## 1.3 特性

> * 快速开发
>   * (1) 无需配置路由：根据 handlers package 下目录结构自动加载路由（目前不支持动态路由）
>   * (2) 参数保持一致：Handler 的参数列表与 HTTP 请求参数保持一致，HTTP 接口所需参数一目了然
>   * (3) 自动参数检查：自动对 HTTP 请求参数进行参数检查
>   * (4) 简易调试模式：简易方便的 DEBUG
>   * (5) 引擎之状态机：具有可复用性的状态处理
>   * (6) 引擎之工作流：长流程分步执行，可在运行关键点处进行 checkpoint，可生成 dot 流程图
>   * (7) 对象关系映射：自带 ORM
>   * (8) 定时任务调度：支持定时执行某些方法
> * 方便运维
>   * (1) 请求完整追溯：请求的响应 Header 中包含请求的 reqid（会记录在日志中）, 便于进行 trace
>   * (2) 自定义响应头：Header 函数中很方便自定义 HTTP header, 如增加固定的接口版本号
>   * (3) 代码耗时打点：通过代码打点可以准确获代码执行耗时
> * 容易扩展
>   * (1) 消息队列通信：启动时开启百川配置即成为一个消费者，以拉模式消费由其他实例发布的消息

# 2 五分钟 Butterfly 体验指南

> 流程简述
```
(1) 下载 butterfly 包
(2) 编写 handler
   开发人员主要就是编写 {butterfly_project}/handlers/{app}/{handler}
   * {app} 是 Python package, 即 Linux 系统上的 目录
   * {handler} 是 Python function
(3) 测试 handler
   python test_handler.py /{app}/{handler} param1 param2 ...
(4) 启动 butterfly 提供 web 服务
   curl -v "http://{IP}:{PORT}/{app}/{handler}?{param1}=value1&..."
```

## 2.1 五分钟体验之部署 Butterfly（预计 1 分钟）
> 部署
```
$ wget https://github.com/meetbill/butterfly/archive/master.zip -O butterfly.zip
$ unzip butterfly.zip
$ cd butterfly-master/butterfly
```
> 配置端口 --- 默认 8585 端口，若无需修改可进入下一项启动
```
conf/config.py
```
> 启动
```
$ bash run.sh start
```
> 访问
```
$ curl "http://127.0.0.1:8585/demo_api/ping"
{"stat": "OK", "randstr": "..."}

$ curl "http://127.0.0.1:8585/demo_api/hello?str_info=meetbill"
{"stat": "OK", "str_info": "meetbill"}
```
##  2.2 五分钟体验之编写 handler （预计 3 分钟）

> 创建 app （handlers 目录下的子目录均为 app）, 直接拷贝个现有的 app 即可
```
$ cp -rf handlers/demo_api handlers/test_app
```
> 新增 handler (app 目录下的`__init__.py` 中编写 handler 函数）
```
$ vim handlers/test_app/__init__.py

新增如下内容：

# ------------------------------ handler
@funcattr.api
def test_handler(req, info):
    return retstat.OK, {"data": info}
```
> 重启服务
```
$ bash run.sh restart
```

> 访问
```
$ curl "http://127.0.0.1:8585/test_app/test_handler?info=helloworld"
{"stat": "OK", "data": "helloworld"}
```

##  2.3 五分钟体验之调试 handler （预计 1 分钟）

假如编写的 handler 不符合预期的时候，可以通过 test_handler.py 进行调试

> 调试刚才编写的 test_handler
```
$ python test_handler.py /test_app/test_handler helloworld
... 此处会输出彩色的  DEBUG 信息
Source path:... test_handler.py
>>>>>|19:03:53.293076 4694912448-MainThread call        66             def main():
------19:03:53.294108 4694912448-MainThread line        67                 return func(*args)
    Source path:... /Users/meetbill/butterfly-master/butterfly/handlers/test_app/__init__.py
    Starting var:.. req = <xlib.httpgateway.Request object at 0x10b4148d0>
    Starting var:.. info = 'helloworld'
    >>>>>|19:03:53.294402 4694912448-MainThread call        49 def test_handler(req, info):
    ------19:03:53.294864 4694912448-MainThread line        50     return retstat.OK, {"data": info}
    |<<<<<19:03:53.294989 4694912448-MainThread return      50     return retstat.OK, {"data": info}
    Return value:.. ('OK', {'data': 'helloworld'})
Source path:... test_handler.py
|<<<<<19:03:53.295114 4694912448-MainThread return      67                 return func(*args)
Return value:.. ('OK', {'data': 'helloworld'})
Elapsed time: 00:00:00.002140
=============================================================
('OK', {'data': 'helloworld'})
=============================================================
```
运行中产生的 logging 日志会记录在 `logs/dev/` 目录

# 3 设计蓝图

## 3.1 单实例内部请求流
```
       +-------------------------------------------------------------+
       |                        WEB brower                           |
       +-----------------------------------^-------------------------+
     /                      |              |
    |  +--------------------V--------------|-------------------------+
    |  | +----------------HTTPServer(Threadpool&Queue)-------------+ |
    |  | |   +-------------------+ put +-----------------------+   | |
    |  | |   |ThreadPool(Queue) <------+ HTTPConnection        |   | |
    |  | |   |+---------------+  |     | +-------------------+ |   | |
    |  | |   ||WorkerThread   |  |     | |req=HTTPRequest()  | |   | |
    |  | |   ||+-+ +-+ +-+ +-+|  |     | |req.parse_request()| |   | |（把 socket 字节流，按 HTTP 协议解析）
    |  | |   ||+-+ +-+ +-+ +-+|  |     | |req.respond()#^!^  | |   | |（封装了 WSGIGateway.response)
    |  | |   |+-|---|---|---|-+  |     | +-------------------+ |   | |
    |  | |   +--|---|---|---|----+     +-----------------------+   | |
    |  | +------|---|---|---|-----------------------^--------------+ |
    |  |        |   |   |   |                       |                | WSGI server
    |  | +------V---V---V---V-WSGIGateway(response)-|--------------+ |
    |  | |                       +------------------+-------------+| |
    |  | |+----------------+     | +----------+   +-------------+ || |
    |  | ||   gen environ  |     | |header_set|   |response body| || |
    |  | |+-----+----------+     | +----------+   +-------------+ || |
    |  | |      |                +--^------^----------^-----------+| |
    |  | +------|-------------------|------|----------|------------+ |
    |  +--------|-------------------|------|----------|--------------+
    |  .........|...................|......|..........|......................
    |           |                   |      |          |
    |  +--------V--------+          |      |          |
    |  |       req       |          |      |          |        (1) 封装 environ 为 Request
    |  +-----------------+          |      |          |            生成 reqid
Butterfly       |                   |      |          |
    |           |                   |      |          |      \
    |  +--------V--------+          |      |          |       |(2) 路由
    |  |  apiname_getter |          |      |          |       |    在路由字典中匹配 environ['PATH_INFO']
    |  +-----------------+          |      |          |       |    {
    |           |                   |      |          |       |      '/apidemo/ping':
    |           |                   |      |          |       |        <xlib.protocol_json.Protocol object>,
    |  +--------V--------+ False +--+--+   |          |       |      '/{app}/{handler}':
    |  |is_protocol_exist|------>| 400 |   |          |       |        <xlib.protocol_json.Protocol object>
    |  +-----------------+       +-----+   |          |       |    }
    |           |                          |          |      /
    |           | (protocol_process)       |          |      \
    |           V                          |          |       |(3) 返回 Response
    |  +-----------------+                 |          |       |    参数：第一个参数为 Request 实例化对象 req
    |  | protocol        | Exception    +-----+       |       |          其他参数为 GET 请求参数名
    |  | +-------------+ |------------->| 500 |       |       |    例子：environ['QUERY_STRING']: 'age=16'
    |  | |/app1/handler| |              +-----+       |       |    +-------------handler demo---------------
    |  | |/app2/handler| |Normal+----------------------------+|    |@funcattr.api      # 标识 handler 类型
    |  | +--+-------+--+ |----->|httpstatus, headers, content||    |def demo(req, age):# req + HTTP 请求参数
    |  +----|-------|----+      +----------------------------+|    |   #（状态信息，数据信息，响应头列表）
    |       |       |                                         |    |   return "OK", {"data": age}, []
    |       |       |                                        /     +----------------------------------------
    |       |  +----V----------------------------------+
    |       |  |+---------+  +---------+  +-----------+|
    |       |  ||DiskCache|  |   FSM   |  |APScheduler||       基础公共库
    |       |  |+---------+  +---------+  +-----------+|
    |       |  +---------------------------------------+
    |  +----V------------------------------------------+
    |  |       (Redis ORM) / (MySQL ORM) / RAL         |       数据访问层
     \ +-----------------------------------------------+
```
## 3.2 多实例间消息队列通信

默认实例只能被动接受请求，然后返回响应，通过开启【百川】，实例将主动消费 MQ 中消息

> * 开启方式
>   * Butterfly 服务配置文件中，CACHES 配置开启 `"baichuan"` 的 Redis 连接配置
> * Butterfly 行为
>   * (1) 每分钟发送心跳到 MQ(Redis)
>   * (2) 每 15 分钟进行一次清理 MQ 中过期任务，运行此任务时会加锁
>   * (3) 启动单独线程检查相关的任务，以 `拉` 模式从队列中拉取消息并进行处理，处理结果也会存储在此 Redis 中
> * MQ
>   * (1) Redis 服务，支持 Twemproxy 组成的 Redis 集群
>   * (2) 每个 `/{app}/{handler}` 是个单独的队列
>     * topic: `/{app}/{handler}`
>     * message: 消息为 json（butterfly 消费消息时，会将 json 转为字典以参数传给 handler）
>   * (3) 消息的四种状态 (queued: 还在队列中，started: 执行中，failed: 执行失败，finished: 完成）

```
                    +Message Queue ------------------------------------------+
+---------------+   |                                                        |    +----------------+
|  other  app   |   |                                                        |    |   other app    |
|     ...       |-->| +Canghai Dashboard ---+------+-------+--------+------+ |<---|      ...       |
+---------------+   | |Queue                |Queued|Started|Finished|Failed| |    +----------------+
                    | +---------------------+------+-------+--------+------+ |
                    | |/demo_api/hello      |  0   |   0   |  91    |  0   | |
                    | |/demo_api/ping       |71731 |  50   | 71736  |  27  | |
                    | |/{app}/{handler}     |  X   |   X   |   X    |  X   | |
+ruqi-----------+   | +---------------------+------+-------+--------+------+ |    +baichuan/canghai--+
|port:4100      |   |                                                        |    |port:4300         |
|handlers/ruqi  |-->| +Redis Arch -----------------------------------------+ |<---|handlers/baichuan |
+---------------+   | |               +---------+                          | |    |handlers/canghai  |
                    | |               |Twemproxy| \                        | |    +------------------+
                    | |               +--+---+--+  +----------+            | |
                    | |                  |   |     |Metaserver|            | |
+wuxing---------+   | |               +--V---V--+  +----------+            | |    +xingqiao----------+
|port:4200      |   | |               |  Redis  | /                        | |    |port:             |
|handlers/wuxing|-->| |               +---------+                          | |<---|handler/xingqiao  |
+---------------+   | +----------------------------------------------------+ |    +------------------+
                    +--------------------------------------------------------+
                                                ^
                                                |
                                                |
                                    +sinan--------------------+
                                    |port:4800                |
                                    |handlers/sinan           |
                                    +-------------------------+
```

通用服务能力 (app)：

> * 【如期】而至 --- 定时调度服务
> * 【五行】化一 --- 数据管理服务
> * 【百川】归海 --- 消息队列服务
> * 【星桥】锁月 --- 流程编排服务

butterfly 框架基础能力：

> * 工作流
> * 状态机
> * 定时器

# 4 了解更多

## 4.1 传送门

> * 手册
>   * [Butterfly 用户手册](https://github.com/meetbill/butterfly/wiki/usage)
>   * [Butterfly 进阶手册](https://github.com/meetbill/butterfly/wiki)
> * [Butterfly 示例](https://github.com/meetbill/butterfly-examples)
> * [Butterfly 前端](https://github.com/meetbill/butterfly-fe)
> * [Butterfly nginx 配置](https://github.com/meetbill/butterfly-nginx)

## 4.2 自带 app 介绍

看文档不过瘾，还可以通过了解当前 handler 的实现，进而实现自己的需求：

> * 【例子】/handlers/demo_api: 简单 api handler demo
> * 【例子】/handlers/demo_download: 文件下载 handler demo
> * 【例子】/handlers/demo_httpapi: 自定义 HTTP 返回码 handler demo
> * 【例子】/handlers/demo_log: 日志级别调整 handler demo
> * 【例子】/handlers/demo_template: 后端模板 handler demo, 本例子用于输出访问日志统计状态图
> * 【例子】/handlers/demo_async_job: 异步任务 handler demo
> * 【例子】/handlers/demo_stackdump: 打印 Butterfly stack trace 信息到日志
> * 【火眼】/handlers/huoyan: 用于后端接口认证，仅仅抛砖引玉，删除了具体实现
> * 【如期】/handlers/ruqi: 高可用定时任务，可发起 HTTP POST 请求或者执行 Shell/Python 脚本
> * 【五行】/handlers/wuxing: 用于存储配置类 / 监控类 / 巡检类数据，可配合状态机进行使用
> * 【星桥】/handlers/xingqiao: 用于管理 handler 依赖，流程编排

> 备注：
```
可将 examples 下 app 拷贝到 {butterfly_project}/handlers/ 下
```
## 4.3 报告错误

如果您想报告错误，请在 GitHub 上[创建一个新问题](https://github.com/meetbill/butterfly/issues/new)。

# 5 贡献

Use issues for everything

> * For a small change, just send a PR.
> * For bigger changes open an issue for discussion before sending a PR.
> * PR should have:
>   * Test case
>   * Documentation
>   * Example (If it makes sense)
> * You can also contribute by:
>   * Reporting issues
>   * Suggesting new features or enhancements
>   * Improve/fix documentation

# 6 版本信息

本项目的各版本信息和变更历史可以在[这里][changelog] 查看。

# 7 参加步骤

* 在 GitHub 上 `fork` 到自己的仓库，然后 `clone` 到本地，并设置用户信息。
```bash
$ git clone https://github.com/meetbill/butterfly.git
$ cd butterfly
$ git config user.name "yourname"
$ git config user.email "your email"
```
* 修改代码后提交，并推送到自己的仓库。
```bash
$ #do some change on the content
$ git commit -am "Fix issue #1: change helo to hello"
$ git push
```
* 在 GitHub 网站上提交 pull request。
* 定期使用项目仓库内容更新自己仓库内容。
```bash
# 配置原仓库地址
$ git remote add upstream https://github.com/meetbill/butterfly.git
# 查看当前仓库的远程仓库地址和原仓库地址
$ git remote -v
# 获取原仓库的更新，使用 fetch 更新，fetch 后会被存储在一个本地分支 upstream/master 上
$ git fetch upstream
# 切换到本地 master 分支
$ git checkout master
# 合并
$ git rebase upstream/master
# 查看更新
$ git log
# 推送到自己仓库
$ git push -f origin master
# 把本地全部存在的 tag 推送到服务器
$ git push origin --tags
```

[changelog]: CHANGELOG.md
