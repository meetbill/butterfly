# coding=utf8
"""
# Description:
api demo
"""
import os
import struct

from xlib import util
from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr

__info = "api_demo"
__version = "1.0.1"


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
def hello(req, str_info):
    """
    带参数请求例子

    Args:
        req     : Request
        str_info: (str)
    Returns:
        json_status, Content, headers
    """
    isinstance(req, Request)
    return retstat.OK, {"str_info": str_info}, [(__info, __version)]
