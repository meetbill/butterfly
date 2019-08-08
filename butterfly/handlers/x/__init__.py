# coding=utf8
import os
import struct

from xlib import util
from xlib.httpgateway import Request
from xlib import retstat

from conf import logger_conf

__info__ = "meetbill"
__version__ = "1.0.1"


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
            > content: (str)非必须(当返回值为 2 个的时候，第 2 个返回值为 Content)
            > headers: 非必须(当返回值为 3 个的时候，第 3 个返回值为 headers)

        如下例子为简单接口函数
    """
    isinstance(req, Request)
    req.log_params["x"] = 1
    clen = struct.unpack("i", os.urandom(4))[0] % 64 + 64
    randstr = util.Base64_16.bin_to_b64(os.urandom(clen))
    return retstat.OK, {"randstr": randstr}, [(__info__, __version__)]


def hello(req, str_info):
    isinstance(req, Request)
    return retstat.OK, {"str_info": str_info}, [(__info__, __version__)]