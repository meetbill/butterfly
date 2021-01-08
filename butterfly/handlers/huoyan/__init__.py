#!/usr/bin/python
# coding=utf8
"""
火眼(金睛)
用于单点登录以及接口认证
"""
from xlib.httpgateway import Request
from xlib import retstat
from xlib import middleware
from xlib import auth
import Cookie


__info = "butterfly_auth"
__version = "1.0.1"


def ssologin(req, ticket=""):
    """
    ssologin
    """
    isinstance(req, Request)
    ##################################
    # 此处添加单点登录认证代码
    ##################################
    username = "meetbill"
    req.username = username
    token = auth.gen_token(username)

    # header 处理
    protocol = "http://"
    host = req.wsgienv.get("HTTP_HOST")
    homepage = protocol + host
    C = Cookie.SimpleCookie()
    C["butterfly_token"] = token
    C['butterfly_token']['domain'] = '.baidu.com'
    C['butterfly_token']['path'] = '/'
    header_list = []
    for c in C.values():
        header_list.append(('Set-Cookie', c.OutputString()))

    header_list.append((__info, __version))
    header_list.append(("Location", homepage))

    context = {"success": True, "message": "{username} login success".format(username=username), "data": {
        "butterfly_token": token}}
    return retstat.HTTP_REDIRECT, context, header_list


@middleware.login_required_nginx
def verification(req):
    """
    auth verification
    """
    isinstance(req, Request)
    context = ""
    return retstat.HTTP_OK, context
