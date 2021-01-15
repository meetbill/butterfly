# butterfly

<div align=center><img src="https://github.com/meetbill/butterfly/blob/master/images/butterfly.png" width="350"/></div>

蝴蝶（轻量化 Web 框架）如同蝴蝶一样，此框架小而美，简单可依赖

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
* [2 五分钟 Butterfly 体验指南](#2-五分钟-butterfly-体验指南)
    * [2.1 五分钟体验之部署 Butterfly（预计 1 分钟）](#21-五分钟体验之部署-butterfly预计-1-分钟)
    * [2.2 五分钟体验之编写 handler （预计 3 分钟）](#22-五分钟体验之编写-handler-预计-3-分钟)
    * [2.3 五分钟体验之调试 handler （预计 1 分钟）](#23-五分钟体验之调试-handler-预计-1-分钟)
* [3 设计蓝图](#3-设计蓝图)
* [4 了解更多](#4-了解更多)
    * [4.1 手册](#41-手册)
    * [4.2 自带 app 介绍](#42-自带-app-介绍)
    * [4.3 报告错误](#43-报告错误)
* [5 版本信息](#5-版本信息)
* [6 参加步骤](#6-参加步骤)

<!-- vim-markdown-toc -->

# 1 简介
## 1.1 环境

```
env:Python 2.7
```
## 1.2 特性

> * 方便开发
>   * (1) 无需配置路由：根据 handlers package 下 package 目录结构自动加载路由（目前不支持动态路由）
>   * (2) 参数保持一致：Handler 的参数列表与 HTTP 请求参数保持一致，HTTP 接口所需参数一目了然
>   * (3) 自动参数检查：自动对 HTTP 请求参数进行参数检查
>   * (4) 简易调试模式：简易方便的 DEBUG
> * 方便运维
>   * (1) 请求完整追溯：请求的响应 Header 中包含请求的 reqid（会记录在日志中）, 便于进行 trace
>   * (2) 自定义响应头：Header 函数中很方便自定义 HTTP header, 如增加固定的接口版本号
>   * (3) 代码耗时打点：通过代码打点可以准确获取每个方法的执行时间，耗时比较长的可能是某个 SQL，可能是某个接口

# 2 五分钟 Butterfly 体验指南

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

# 3 设计蓝图

```
       +-------------------------------------------------------------+
       |                        WEB brower                           |
       +-------------------------------------------------------------+
                            |              ^
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
    |  | +------|---|---|---|--------------------------------------+ |
    |  |        |   |   |   |                       ^                | WSGI server
    |  |        V   V   V   V                       |                |
    |  | +---------------WSGIGateway(response)------|--------------+ |
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

# 4 了解更多

## 4.1 手册

> * [Butterfly 用户手册](https://github.com/meetbill/butterfly/wiki/usage)
> * [Butterfly 进阶手册](https://github.com/meetbill/butterfly/wiki)
> * [Butterfly 示例](https://github.com/meetbill/butterfly-examples)
> * [Butterfly 前端](https://github.com/meetbill/butterfly-fe)
> * [Butterfly nginx 配置](https://github.com/meetbill/butterfly-nginx)

## 4.2 自带 app 介绍

看文档不过瘾，还可以通过了解当前 handler 的实现, 进而实现自己的需求:

> * demo_api--------------------: api demo
> * demo_download---------------: 下载文件 demo
> * demo_httpapi----------------: 自定义 HTTP 返回码 demo
> * demo_log--------------------: 日志级别调整 demo
> * demo_template---------------: 使用后端模板 demo, 本例子会输出访问日志统计状态图
> * huoyan----------------------: 【火眼金睛】（用于后端接口认证，仅仅抛砖引玉，删除了具体实现）
> * ruqi------------------------: 【如期而至】（高可用定时任务, 可用于定时发起 HTTP 请求或者执行 Shell/Python 脚本）
> * wuxing----------------------: 【五行属性】（用于存储配置类/监控类/巡检类数据，可配合状态机进行使用）

> 备注:
```
handlers 目录下 APP, 均可移除，具体操作就是将对应 app 目录进行删除
```
## 4.3 报告错误

如果您想报告错误，请在 GitHub 上[创建一个新问题](https://github.com/meetbill/butterfly/issues/new)。

# 5 版本信息

本项目的各版本信息和变更历史可以在[这里][changelog] 查看。

# 6 参加步骤

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
