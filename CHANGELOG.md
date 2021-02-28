Changelog
===
以下记录了项目中所有值得关注的变更内容，其格式基于 [Keep a Changelog]。

本项目版本遵守 [Semantic Versioning] 和 [PEP-440]。

## [1.1.8] - 2021-02-28
### Added

- 服务：添加【百川】app，开启百川后 butterfly 服务将自动消费 MQ 中的消息
- 服务：优化【五行】app，增加五行数据缓存功能

### Changed

- 日志：talk、params、res 的分割符由`,`改为`;`
- 调试：test_handler.py 执行过程中的 logging 日志移动至 logs/dev 目录

## [1.1.7] - 2021-02-11
### Added

- 添加【五行】app，用于实现配置类/监控类数据存储，可配合状态机实现更强大功能
- 添加 demo_async_job, 演示如何发起异步任务

### Changed

- 配置: 支持 MySQL/Redis 多实例支持
- 日志: access 日志字段变更, 更方便进行日志监控
- apscheduler: Merge part of apscheduler-3.7.0 code

## [1.1.6] - 2021-01-09
### Fixed

- 修复解锁已过期任务可能导致的死锁问题 https://github.com/meetbill/butterfly/issues/4
- 修复存在暂停中任务时，调度失败问题 https://github.com/meetbill/butterfly/issues/24

### Added

scheduler manager

- 添加查询 scheduler 状态接口
- 添加强制唤醒 scheduler 接口
- 增加 scheduler http job 方法

### Changed

- 修改 scheduler 部分日志
- http_util 增加 cost 属性

## [1.1.5] - 2021-01-05
### Changed

- update APScheduler 2.1.2 ==> APScheduler 3.6.3
```
(1) add apscheduler mysql jobstores use peewee
(2) 增加 scheduler job_lock，scheduler 检查任务时进行抢锁发起任务
(3) 增加 scheduler manager 作为通用配置
(4) 增加 scheduler 执行历史，存储在 MySQL 中
(5) 增加 scheduler 定期探测是否有任务配置
(6) scheduler 增加到 req.scheduler 属性中
```
- update test_handler.py
```
如果开启 scheduler，则使用 test_handler.py 调试时以 MemoryJobStore 方式启动
```
- 日志
```
启动时插件加载相关日志从 logs/init.log 修改为 logs/init.log
```

## [1.1.4] - 2020-12-16
### Added

- Add APScheduler
- Add Redis ORM

## [1.1.3] - 2020-11-22
### Added

- Add the nshead client example with mcpack
- Add peewee tests
- 添加大部分函数注释

### Changed

- 修正 butterfly/xlib/util/http_util.py get 方法例子
- 将代码中 `__xxx__` 修改为 `_xxx_` （因为变量名`__xxx__`对 Python 来说有特殊含义，对于普通的变量应当避免这种命名风格）
- statemachine metaclass 方法从 `__init__` 修改为 `__new__`
- 修改 access 日志，将耗时部分从 `{cost}` 修改为 `cost:{cost}`，方便进行监控服务采集日志中的耗时
- 部分类名修正为"骆驼命名"
- 修改 json 序列化 Datetime 类型方法

### Removed

- [butterfly/xlib/db/pymysql/times.py] 文件
- [butterfly/xlib/db/peewee.py] 部分函数

### Fixed

- [butterfly/xlib/db/peewee.py] fix regexp method already defined bug

## [1.1.2] - 2020-10-11
### Added

- 新增百度特有协议 nshead + mcpack 协议支持
- 新增解析 reqid 方法，可以解析 reqid 获取生成 reqid 的时间戳
- add pep8 tool

### Changed

- Modify the dependency decorator of retry to wrapt (decorator.py 也是个第三方包）
- 使用 test_handler.py 调试时，排序输出 handler
- handler 方法当没有 funcattr 装饰时，修改为默认不读取 body 中内容

## [1.1.1] - 2020-08-23
### Added

- 新增【星枢】用于管理服务 API，比如在线调整 log level ，以及获取服务运行信息等
- 新增加权随机算法 util
- 新增磁盘缓存 diskcache

### Changed

```
handlers/report ==> handlers/x_lv
```
### Fixed

- 修复日志按日期切割时句柄不释放问题（原因是不同的 logger 写入了同一个日志文件）

## [1.1.0] - 2020-08-10
### Changed
- 更新 wsgiserver, 为支持 Py3 做准备

```
Cherrypy/3.2.0 wsgiserver ==> Cherrypy/8.9.1 wsgiserver 绝版 :(
```

基于 CherryPy/8.9.1 wsgiserver , 增加 perfork

> * 修改 HTTPServer
> * 修改 CherryPyWSGIServer
> * 使用本地 six

## [1.0.24] - 2020-08-10
### Added
- 新增 protocol_file 用于封装文件下载 handler, 用于实现报表导出，日志下载等功能

```
【普通 API】当 handler 使用 @funcattr.api 装饰器装饰时，使用 protocol_json 进行封装
【文件上传】当 handler 使用 @funcattr.api_upload 装饰器装饰时，使用 protocol_json 进行封装
【文件下载】当 handler 使用 @funcattr.api_download 装饰器装饰时，使用 protocol_file 进行封装
【自定义】当 handler 不使用装饰器时，会使用 protocol_json 进行封装，但不会将结果进行封装为 json
```

## [1.0.23] - 2020-06-07
### Changed
- http_util 默认会将 response json 转为 dict, 同时可以通过 check_key 和 check_value 两个参数来检查返回结果是否符合预期
- shell_util 检查是否成功，由 success 属性修改为 success() 方法

### Added
单独测试框架中的某些函数时，可以通过 `source ./run.sh env` 进行设置 PYTHONPATH 环境变量

## [1.0.22] - 2020-06-03
### Added
- 增加 db 之 redis lib

## [1.0.21] - 2020-05-25
### Added
- 增加 butterfly Logger, butterfly logger 日志中会记录 reqid, root logger 中 reqid 字段则以 16 个 "@" 替代

### Fixed
- 修复自定义 logger 从 root Logger 继承后，reqid 不存在问题

## [1.0.20] - 2020-05-24
### Changed
- 修改 xlib/util/shell.py ==> xlib/util/shell_util.py
- 修改 xlib/util/shell_util.py 打印日志内容
- 增加 xlib/util/http_util.py 库，用于访问第三方接口

## [1.0.19] - 2020-05-21
### Changed
- 使用 logging 库记录日志时，日志中将自动添加 reqid 信息
- xlib.util.host_util 更改方法名
- xlib.util.shell 去掉了对 reqid 的传参

## [1.0.18] - 2020-05-19
### Fixed
- 修复 1.0.17 因 version 字段导致 acclog 不打印情况
```
将 butterfly_version 在启动时初始化，同时可以通过《变量本地化》提高性能
```
- 修复单元测试中因添加 header 异常导致的单元测试遗漏问题

## [1.0.17] - 2020-05-17
### Added
- shell util 模块用于执行系统命令
```
基于 subprocess.Popen 封装，增加如下功能
    (1) 超时，默认 10s
    (2) 日志，每次调用系统命令都进行记录，日志中包含 reqid （如果传入的话）及调用处代码信息
    (3) 结果封装

日志记录在 logs/common.log 及 logs/common.log.wf （异常日志）
```

## [1.0.16] - 2020-05-07
### Changed
- acc.log 中新增 method 字段

## [1.0.15] - 2020-05-01
### Changed
- 更新 pysnooper 为社区版 0.4.0
- 在社区版 pysnooper 基础上，添加彩色输出功能
- test_handler.py 默认使用 pysnooper 彩色输出
- 增加 handler 单测例子

## [1.0.14] - 2020-04-29
### Fixed
- 修复获取不存在的前端静态文件时，日志中文件名缺失问题
- 修复获取 Header 中的 用户名不存在时，日志中用户名列缺失问题

## [1.0.13] - 2020-04-15
### Added
- 增加状态机 statemachine

## [1.0.12] - 2020-04-14
### Changed
- 新增 MySQL 连接池自动重连，保持连接配置

## [1.0.11] - 2020-03-23
### Changed
- content 在 josn 序列化时，添加对 Datetime 类型的支持
```
变更原因：
使用 peewee DateTimeField 时，为 Datetime 类型
```

## [1.0.10] - 2020-03-07
### Changed
- 增加默认获取请求 header 中的 `X-Username` 用作日志中中记录的用户名
```
变更原因：
当身份验证组件和接口服务组件分离时，接口服务组件需要获取到用户名

比如当用户认证使用 nginx auth_request module 进行身份验证时，验证身份通过后，可以将验证后的用户名使用 header 传到后端接口
```

## [1.0.9] - 2020-02-01
### Changed
- 增加通过装饰器自定义 handler 属性
### Removed
- 删除 x 目录下自动设置 handler 属性逻辑

## [1.0.8] - 2020-01-09
### Changed
- 修改访问日志格式，方便统计
### Added
- 增加报表（输出用户访问分布量 / 状态码分布图 / 认证请求路径分布图 / 每天访问量等）

## [1.0.7] - 2019-12-02
### Changed
- 添加 redirect 重定向

## [1.0.6] - 2019-11-15
### Changed
- butterfly 添加 test_handler.py 用于方便测试 handlers 方法输出
- xlib 添加 middleware
- xlib 添加 util [wrapt 1.11.2](https://github.com/GrahamDumpleton/wrapt)
- request 添加 cookie 解析
- request 添加 user 属性

## [1.0.5] - 2019-10-06
### Fixed
- 修正请求静态文件时，日志中不打印静态文件信息以及状态码问题
### Changed
- 日志中添加打印 filename 以及 lineno 列，方便排查问题

## [1.0.4] - 2019-08-09
### Added
- 支持 auth(pyjwt)
- 添加 MySQL pool

## [1.0.3] - 2019-08-03
### Changed
- 支持多级路由，自动加载路由从自动从 moudle 中加载，修改为自动从指定 package 下自动加载
- 路由字典中的 key 由 func_name ，修改为 `/package_name/func_name`

```
请求 PATH_INFO    ==> 路由字典中的 key ==> 实际的函数路径
/ping or /ping/   ==> /ping            ==> handlers/__init__.py::ping
/apidemo/ping     ==> /apidemo/ping    ==> handlers/apidemo/__init__.py::ping
```

## [1.0.2] - 2019-07-24
### Added
- 增加通用 logging 配置
- 请求的响应中包含 butterfly 的版本信息

[Keep a Changelog]: https://keepachangelog.com/zh-CN/1.0.0/
[Semantic Versioning]: https://semver.org/lang/zh-CN/
[PEP-440]: https://www.python.org/dev/peps/pep-0440/
[1.0.2]: https://github.com/meetbill/butterfly/wiki/butterfly_man1.0.2
