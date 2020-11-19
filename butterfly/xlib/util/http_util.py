#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-05-23 22:08:46

# File Name: http_util.py
# Description:

    Simple module to request HTTP

    get(url, **kwargs)
    post(url, **kwargs)
    download(url, **kwargs)

    RequestTool(
        'http://127.0.0.1:8585',
        data = {},
        type = 'GET',                   # (str) GET POST default: POST
        is_decode_response = False,     # (bool) If True, json ==> dict
        check_key = None,               # (str) Check key
        check_value = None,             # (str, int, list) Check value, May be a list
        referer = '',
        user_agent = '',
        cookie = None,                  # CookieJar, Cookie.S*Cookie, dict, string
        auth = {'usr':'', 'pwd':''},    # Only Basic Authorization
        debug = False
        )
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import base64
import sys
import inspect
import logging
import time
import json


log = logging.getLogger("butterfly")


PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3


if PY2:
    from urllib import ContentTooShortError
    from urllib2 import HTTPError, URLError
    from urllib import urlencode
    from urllib2 import Request as urlRequest
    from urllib2 import build_opener
    from urllib2 import HTTPHandler, HTTPSHandler, HTTPCookieProcessor
    import Cookie
    from cookielib import CookieJar

if PY3:
    from urllib.error import ContentTooShortError, HTTPError, URLError
    from urllib.parse import urlencode
    from urllib.request import Request as urlRequest
    from urllib.request import build_opener
    from urllib.request import HTTPHandler, HTTPSHandler, HTTPCookieProcessor
    from http import cookies as Cookie
    from http.cookiejar import CookieJar


_DEFAULT_TIMEOUT = 90


def get(url, **kwargs):
    """
    http get request
    """
    kwargs.update(type='GET')
    kwargs.update(is_decode_response=True)
    return RequestTool(url, **kwargs)


def post_form(url, **kwargs):
    """
    http post request
    """
    kwargs.update(type='POST')
    kwargs.update(post_type='form')
    kwargs.update(is_decode_response=True)
    return RequestTool(url, **kwargs)


def post_json(url, **kwargs):
    """
    http post request
    """
    kwargs.update(type='POST')
    kwargs.update(post_type='json')
    kwargs.update(is_decode_response=True)
    return RequestTool(url, **kwargs)


def download(url, local, **kwargs):
    """
    download file
    """
    if not local:
        raise ValueError('local filepath is empty')
    try:
        if not os.path.exists(os.path.dirname(local)):
            os.makedirs(os.path.dirname(local))
        res = RequestTool(url, **kwargs)
        read_size = 0
        real_size = int(res.header['content-length'])
        with open(local, 'wb') as f:
            while True:
                block = res.response.read(1024 * 8)
                if not block:
                    break
                f.write(block)
                read_size += len(block)
        if read_size < real_size:
            raise ContentTooShortError(
                'retrieval incomplete: got only {} out of {} bytes'.formate(read_size, real_size),
                None
            )
    except Exception as e:
        raise e


class RequestTool(object):
    """
    Request Class
    """

    def __init__(self, url, **kwargs):
        """
        Request init
        """
        self.request = None
        self.response = None
        self.code = -1
        self.header = {}
        self.cookieJar = None
        self.reason = ''
        self.content = ''
        self.content_dict = {}

        # 是否将服务端返回结果从 json 转为 dict
        self.is_decode_response = kwargs.get('is_decode_response', False)

        data = kwargs.get('data', None)
        # 当请求是 GET 请求，同时传了 data 字典的话，post_type 默认是 form，会进行 urlencode，并拼接到请求 URL 上
        post_type = kwargs.get('post_type', 'form')
        if data is not None:
            if isinstance(data, dict):
                if post_type == 'json':
                    data_str = json.dumps(data)
                else:
                    # data = {"name":"meetbill", "age":"21"}  ==> urlencode(data) = 'age=21&name=meetbill'
                    data_str = urlencode(data)

            if not isinstance(data_str, basestring):
                raise ValueError('data must be string or dict')
        else:
            data_str = None

        request_type = kwargs.get('type', 'POST')
        if data_str and isinstance(request_type, basestring) and request_type.upper() != 'POST':
            # 如果是 GET 请求，则将 data 中的内容转为 url 的一部分
            url = '{}?{}'.format(url, data_str)
            data_str = None  # GET data must be None

        self.request = urlRequest(url, data_str)
        # Content-type, 默认是 'application/x-www-form-urlencoded'
        if request_type.upper() == 'POST' and post_type == "json":
            self.request.add_header('Content-type', 'application/json')

        # referer
        referer = kwargs.get('referer', None)
        if referer:
            self.request.add_header('referer', referer)

        # user-agent
        user_agent = kwargs.get('user_agent', None)
        if user_agent:
            self.request.add_header('User-Agent', user_agent)

        # auth
        auth = kwargs.get('auth', None)
        if auth and isinstance(auth, dict) and 'usr' in auth:
            auth_string = base64.b64encode('{}:{}'.format(auth.get('usr', ''), auth.get('pwd', '')))
            self.request.add_header('Authorization', 'Basic {}'.format(auth_string))

        # cookie
        cookie = kwargs.get('cookie', None)
        cj = None
        if cookie:
            if isinstance(cookie, CookieJar):
                cj = cookie
            elif isinstance(cookie, dict):
                result = []
                for k, v in cookie.items():
                    result.append('{}={}'.format(k, v))
                cookie = '; '.join(result)
            elif isinstance(cookie, Cookie.BaseCookie):
                cookie = cookie.output(header='')
            if isinstance(cookie, basestring):
                self.request.add_header('Cookie', cookie)

        if cj is None:
            cj = CookieJar()

        #! TODO: proxy

        # build opener
        debuglevel = 1 if kwargs.get('debug', False) else 0
        opener = build_opener(
            HTTPHandler(debuglevel=debuglevel),
            HTTPSHandler(debuglevel=debuglevel),
            HTTPCookieProcessor(cj)
        )

        # timeout
        timeout = kwargs.get('timeout')
        if not isinstance(timeout, int):
            timeout = _DEFAULT_TIMEOUT

        t_beginning = time.time()
        try:
            # opener.open accept a URL or a Request object
            # 程序中判断是字符串时按照 URL 来处理, 否则按照是已经封装好的 Request 处理
            self.response = opener.open(self.request, timeout=timeout)
            self.code = self.response.getcode()
            self.header = self.response.info().dict
            self.cookieJar = cj
            self.content = self.response.read()
            # 进行将 response 转为 dict
            if self.is_decode_response:
                self.content_dict = json.loads(self.content)

                # 检查 response 内容是否符合预期
                check_key = kwargs.get('check_key', None)
                check_value = kwargs.get('check_value', None)
                if check_key is not None and check_value is not None:
                    # 检查 check_value 类型
                    if isinstance(check_value, list):
                        if self.content_dict[check_key] not in check_value:
                            self.code = -1
                            self.reason = "[response not match: {response_value} not in {check_value}]".format(
                                response_value=self.content_dict[check_key],
                                check_value=check_value
                            )
                    elif self.content_dict[check_key] != check_value:
                        self.code = -1
                        self.reason = "[response not match: {response_value} != {check_value}]".format(
                            response_value=self.content_dict[check_key],
                            check_value=check_value
                        )
        except HTTPError as e:
            self.code = e.code
            self.reason = '{}'.format(e)
        except URLError as e:
            self.code = -1
            self.reason = e.reason
        except Exception as e:
            self.code = -1
            self.reason = '{}'.format(e)

        seconds_passed = time.time() - t_beginning
        cost_str = "%.6f" % seconds_passed

        # 打印日志
        f = inspect.currentframe().f_back
        file_name, lineno, func_name = self._get_backframe_info(f)

        log_msg = ("[file={file_name}:{func_name}:{lineno} "
                   "type=http_{method} "
                   "req_path={req_path} "
                   "req_data={req_data} "
                   "cost={cost} "
                   "is_success={is_success} "
                   "err_no={err_no} "
                   "err_msg={err_msg} "
                   "res_len={res_len} "
                   "res_data={res_data} "
                   "res_attr={res_attr}]".format(
                       file_name=file_name, func_name=func_name, lineno=lineno,
                       method=request_type,
                       req_path=url,
                       req_data=data,
                       cost=cost_str,
                       is_success=self.success(),
                       err_no=self.code,
                       err_msg=self.reason,
                       res_len=len(self.content),
                       res_data=self.content,
                       res_attr=json.dumps(self.header)
                   ))

        if self.success():
            log.info(log_msg)
        else:
            log.error(log_msg)

    def _get_backframe_info(self, f):
        """
        get backframe info
        """
        return f.f_back.f_code.co_filename, f.f_back.f_lineno, f.f_back.f_code.co_name

    def success(self):
        """
        check http code
        """
        return 200 <= self.code < 300

    def output(self):
        """
        return content
        """
        if self.is_decode_response:
            return self.content_dict
        else:
            return self.content


if __name__ == "__main__":
    # Butterfly 例子
    # GET 请求，无参数
    print("[GET], no pargs---------------------------------")
    res = get("http://127.0.0.1:8585/x/ping", debug=True)
    if res.success():
        print(res.output())
        assert isinstance(res.output(), dict)

    print("[GET], no pargs---------------------------------, check status")
    res = get("http://127.0.0.1:8585/x/ping", check_key="stat", check_value=0)
    assert res.success() == False
    res = get("http://127.0.0.1:8585/x/ping", check_key="stat", check_value="OK")
    assert res.success() == True
    print res.output()

    print("[GET], have pargs---------------------------------")
    get("http://127.0.0.1:8585/x/hello?str_info=meetbill", debug=True)

    print("[POST], post json---------------------------------")
    post_json("http://127.0.0.1:8585/x/hello", data={"str_info": "meetbill"}, debug=True)

    print("[POST], post form---------------------------------[exe error]")
    post_form("http://127.0.0.1:8585/x/hello", data={"str_info": "meetbill"}, debug=True)
