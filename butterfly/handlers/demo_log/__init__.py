# coding=utf8
"""
# Description:
    * 在线调整日志级别
"""
import os
import struct
import logging

from xlib import util
from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr

butterfly_logger = logging.getLogger("butterfly")
root_logger = logging.getLogger()

__info = "demo"
__version = "1.0.1"


ERR_LEVEL_INVALID = "ERR_LEVEL_INVALID"
ERR_LEVEL_NOT_NUM = "ERR_LEVEL_NOT_NUM"
ERR_NAME_INVALID = "ERR_NAME_INVALID"


@funcattr.api
def ping(req):
    """demo
    Args:
        req:
    Returns:
        当此函数作为简单接口函数返回时:
            json_status, [content], [headers]
            > json_status: (int,str)必须有，实际返回给用户时，json_status 也会放到 json 串中
            > content: (dict)非必须(当返回值为 2 个的时候，第 2 个返回值为 Content)
            > headers: 非必须(当返回值为 3 个的时候，第 3 个返回值为 headers)
        当此函数作为 HTTP 方法返回时:
            httpstatus, [content], [headers]
            > httpstatus: (int)必须有
            > content: (str/dict)非必须(当返回值为 2 个的时候，第 2 个返回值为 Content)
                       当 content 为 dict 时，会自动转为 json ，并且设置 header("Content-Type","application/json")
                       当 content 为其他时，会自动设置为 ("Content-Type","text/html")
            > headers: 非必须(当返回值为 3 个的时候，第 3 个返回值为 headers)

        如下例子为简单接口函数
    """
    isinstance(req, Request)
    req.log_params["x"] = 1
    clen = struct.unpack("i", os.urandom(4))[0] % 64 + 64
    randstr = util.Base64_16.bin_to_b64(os.urandom(clen))
    return retstat.OK, {"randstr": randstr}, [(__info, __version)]


@funcattr.api
def loglevel_get(req):
    """
    获取 logging logger 日志级别

    DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50)

    Args:
        req     : Request
    Returns:
        json_status, Content, headers
    """
    isinstance(req, Request)
    data = {}
    root_level = root_logger.level
    butterfly_level = butterfly_logger.level
    data["root"] = root_level
    data["butterfly"] = butterfly_level
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def loglevel_set(req, name, level):
    """
    调整 logging logger 日志级别

    DEBUG(10) < INFO(20) < WARNING(30) < ERROR(40) < CRITICAL(50)

    Args:
        req     : Request
        name    : logger name
        level   : 日志级别，应该为数字，并在 [10, 20, 30, 40, 50] 中
    Returns:
        json_status, Content, headers
        "ERR_LEVEL_NOT_NUM": level 不是数字
        "ERR_LEVEL_INVALID": level 不在 [10, 20, 30, 40, 50] 中
        "ERR_NAME_INVALID" : name 不为 root 或 butterfly
    """
    isinstance(req, Request)
    try:
        level_num = int(level)
    except BaseException:
        return ERR_LEVEL_NOT_NUM, {}, [(__info, __version)]

    if level_num not in [10, 20, 30, 40, 50]:
        return ERR_LEVEL_INVALID, {}, [(__info, __version)]

    if name == "root":
        root_logger.setLevel(level_num)
        return retstat.OK, {}, [(__info, __version)]
    elif name == "butterfly":
        butterfly_logger.setLevel(level_num)
        return retstat.OK, {}, [(__info, __version)]
    else:
        return ERR_NAME_INVALID, {}, [(__info, __version)]
