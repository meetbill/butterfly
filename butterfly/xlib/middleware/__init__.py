# coding=utf8
"""
Butterfly 常用装饰器
"""

import logging

from xlib.util import wrapt
from xlib import auth


@wrapt.decorator
def login_required(wrapped, instance, args, kwargs):
    """
    使用 web 接口访问时，是通过 kwargs 进行传值
    使用 test_handler.py 进行接口调试时，则是使用 args 进行传值，所以接口调试时会自动绕过身份验证

    此接口不会返回额外登录地址

    eg: 前端访问访问，前端发送 aJax 请求时，拦截到响应状态码为 401 时，进行跳转到前端的登录页
    """
    if "req" in kwargs:
        req = kwargs["req"]
        log_msg = "[reqid]:{reqid} [wsgienv]:{wsgienv}".format(
            reqid=req.reqid, wsgienv=str(req.wsgienv))
        logging.info(log_msg)
        token_check = auth.is_token_valid(req)
        if not token_check.success:
            return token_check.err_content
        else:
            req.username = token_check.token_info["username"]
    result = wrapped(*args, **kwargs)
    return result


@wrapt.decorator
def login_required_nginx(wrapped, instance, args, kwargs):
    """
    Nginx auth_request 需要跳转到外部地址时使用

    eg:单点登录，前端发送 AJAX 请求时，拦截到响应状态码为 401 时，前端进行跳转操作登录接口
       此时不能直接返回 302 让浏览器自行跳转，会跨域
    """
    if "req" in kwargs:
        req = kwargs["req"]
        token_check = auth.is_token_valid(req)

        # 获取用户真实请求 URI ,需要在 Nginx 上配置 "proxy_set_header X-Original-URI $request_uri;"
        if "HTTP_X_ORIGINAL_URI" in req.wsgienv:
            req.log_params["uri"] = req.wsgienv.get("HTTP_X_ORIGINAL_URI")

        # 认证失败时返回 401，及需要跳转的登录地址放到 header 中
        # 可通过此配置 "auth_request_set    $butterfly_location $upstream_http_location;" 将要跳转的地址传给 Nginx 的 $butterfly_location 变量
        if not token_check.success:
            http_code, context = token_check.err_content
            protocol = "http://"
            host = req.wsgienv.get("HTTP_HOST")
            login_url = protocol + host + "/auth/ssologin"
            return http_code, context, [("Location", login_url)]
        else:
            req.username = token_check.token_info["username"]

    result = wrapped(*args, **kwargs)
    return result
