Changelog
===
以下记录了项目中所有值得关注的变更内容，其格式基于 [Keep a Changelog]。

本项目版本遵守 [Semantic Versioning] 和 [PEP-440]。

## [1.0.17] - 2020-05-17
### Added
- shell util 模块用于执行系统命令
```
基于 subprocess.Popen 封装, 增加如下功能
    (1) 超时，默认 10s
    (2) 日志，每次调用系统命令都进行记录, 日志中包含 reqid (如果传入的话)及调用处代码信息
    (3) 结果封装

日志记录在 logs/common.log 及 logs/common.log.wf (异常日志)
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
- content 在 josn 序列化时,添加对 Datetime 类型的支持
```
变更原因:
使用 peewee DateTimeField 时，为 Datetime 类型
```

## [1.0.10] - 2020-03-07
### Changed
- 增加默认获取请求 header 中的 `X-Username` 用作日志中中记录的用户名
```
变更原因:
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
