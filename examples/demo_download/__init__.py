# coding=utf8
"""
# Description:
api demo
"""
from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr

__info = "demo"
__version = "1.0.1"


@funcattr.api_download
def download(req):
    """
    带参数请求例子

    Args:
        req             : (Object) Request
    Returns:
        stat_str, content_dict, headers_list
        > stat_str      : (String)
        > content_dict  : (Dict)
            filename    : (String) 文件路径
            is_download : (Bool) 是否需要下载
        > headers_list  : (List)
            key 和 value 都需要是 str 类型
    """
    isinstance(req, Request)
    return retstat.OK, {"filename": "test/static_file/test_html.html", "is_download": True}, [(__info, __version)]
