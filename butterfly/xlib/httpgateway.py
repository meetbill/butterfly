# coding:utf8
"""
# Author: meetbill
# Created Time : 2019-03-04 14:44:34

# File Name: httpgateway.py
# Description:
    This module provides parsing WSGI Env and returning HTTP results
"""

import os
import traceback
import urlparse
import time
import httplib
import inspect

import xlib.uuid64

__version__ = "1.0.15"


def parse_cookie(cookie):
    """
    Return a dictionary parsed from a `Cookie:` header string.

    Args:
        cookie: (str)environ["HTTP_COOKIE"]
    Return:
        cookie dict
    """
    r = {}
    if not cookie:
        return r
    for item in cookie.split(";"):
        item = item.strip(" ")
        kv = item.split("=")
        if len(kv) == 2:
            r[kv[0].strip(" ")] = kv[1].strip(" ")
    return r


class Request(object):
    """Request Class

    Used to package a request

    Attributes:
        reqid: (String)
        wsgienv: (Dict)
        ip: (String)
        log_params: (Dict)
        log_stat: (Dict)
        log_ret: (Dict)
        funcname: (String)
        error_str: (String)
        init_tm: (Float)time.time()
        _tm: (Float)

    """

    def __init__(self, reqid, wsgienv, ip):
        """
        Args:
            reqid : (String)
            wsgienv : (Dict) wsgi env
            ip : (String)
        """
        self.reqid = reqid
        self.wsgienv = wsgienv
        self.ip = ip

        self.log_params = {}
        self.log_stat = {}
        self.log_ret_code = ""
        self.log_res = set()
        self.funcname = ""
        self.error_str = ""
        self.init_tm = time.time()
        self._tm = self.init_tm
        self.username = "-"

    def log(self, logger, logline):
        """butterfly req log
        主要用于记录异常日志以及其他类型日志，日志中会记录 reqid
        Args:
            logger: logger Instance
            logline: log msg
        Examples:
            req.log(self._errlog, "Json dump failed\n%s" % traceback.format_exc())
        """
        _logline = "%s %s" % (self.reqid, logline)
        logger.log(_logline)

    def start_timming(self):
        """set _tm"""
        self._tm = time.time()

    def timming(self, name):
        """获取从 _tm 到当前的耗时"""
        tm = time.time()
        cost = tm - self._tm
        self._tm = tm
        if name in self.log_stat:
            try:
                self.log_stat[name] += cost
            except BaseException:
                pass
        else:
            self.log_stat[name] = cost

    def cookies(self):
        """parse cookie"""
        cookie = self.wsgienv.get('HTTP_COOKIE', '')
        return parse_cookie(cookie)


class WSGIGateway(object):
    """WSGIGateway class
    Attributes:
        _protocols: (Dict) api 字典
        _apiname_getter: (Func)根据 URL 获取到的函数名
        _acclog: (Instance) Log class
        _errlog: (Instance) Log class
        _uuid64: (Instance)
        _static_path: (String) static path
        _static_prefix: (String) static prefix
    """

    def __init__(self,
                 funcname_getter,
                 errlog,
                 acclog,
                 protocols,
                 static_path="",
                 static_prefix=None):
        self._protocols = protocols
        self._apiname_getter = funcname_getter
        self._acclog = acclog
        self._errlog = errlog
        self._uuid64 = xlib.uuid64.UUID64()
        self._static_path = static_path
        self._static_prefix = static_prefix

    def process(self, wsgienv):
        """Process wsgienv
        Args:
            wsgienv:(Dict) wsgi env
        Returns:
            HTTP_STATUS(str), HEADERS([(k,v),..]), ContentGenerator
        """
        ip = "0.0.0.0"
        reqid = self._uuid64.gen()
        req = Request(reqid, wsgienv, ip)
        try:
            # 当使用 nginx ，可在 nginx 上配置 "proxy_set_header X-Real-IP  $remote_addr;" 获取真实源 IP
            ip = wsgienv.get("HTTP_X_REAL_IP") or wsgienv.get("REMOTE_ADDR")
            assert ip
            req.ip = ip

            # 当使用 nginx auth_request module 进行接口认证时，可以在 nginx 中配置将认证后的用户名透传
            # 获取不到时，值为 "-", 用于日志统计
            req.username = wsgienv.get("HTTP_X_USERNAME") or "-"

            # 如果匹配到静态文件前缀，就会返回静态文件
            file_path = self._try_to_handler_static(wsgienv)
            if file_path:
                return self._mk_static_ret(req, file_path)

            funcname = self._apiname_getter(wsgienv)
            req.funcname = funcname
            protocol = self._protocols.get(funcname)
            if not protocol:
                return self._mk_err_ret(req, 400, "API Not Found", "")

        except BaseException:
            return self._mk_err_ret(
                req, 400, "Get API Exception", "Get API Exception %s" % traceback.format_exc())

        try:
            httpstatus, headers, content = protocol(req)
            # httpstatus, headers, content = "200 OK", [], ""
        except BaseException:
            return self._mk_err_ret(
                req, 500, "API Processing Error", "API Processing Error %s" % traceback.format_exc())

        return self._mk_ret(req, httpstatus, headers, content)

    def _mk_err_ret(self, req, err_code, err_msg, log_msg):
        """error return
        Args:
            req: req
            err_code: (Int) err_code
            err_msg : (String) err msg info
            log_msg : (String) log msg info
        Returns:
            _mk_ret
        """
        req.log_ret_code = err_code
        req.error_str = err_msg
        if log_msg:
            req.log(self._errlog, log_msg)
        status_line = "%s %s" % (err_code, httplib.responses.get(err_code, ""))
        return self._mk_ret(req, status_line, [], "")

    def _mk_ret(self, req, httpstatus, headers, content):
        """normal return
        Args:
            req       : http req
            httpstatus: (String) httpstatus eg.:"200 OK","400 Get API Exception"
            headers   : (List) http headers
            context   : (String) http body
        Returns:
            httpstatus, headers, content
        """
        cost = time.time() - req.init_tm
        cost_str = "%.6f" % cost
        try:
            headers.append(("butterfly", __version__))
            headers.append(("x-reqid", req.reqid))
            # cost time
            headers.append(("x-cost", cost_str))
            if req.error_str:
                headers.append(("x-reason", req.error_str))
            stat_str = ",".join("%s:%.3f" % (k, v) for k, v in req.log_stat.iteritems())
            log_params_str = ",".join("%s:%s" % (k, v) for k, v in req.log_params.iteritems())
            self._acclog.log("{ip}\t{reqid}\t{funcname}\t{cost}\t{ret_code}\t{username}\tstat:{stat}\tparams:{log_params}\terror_msg:{error}\tres:{res}".format
                             (ip=req.ip,
                              reqid=req.reqid,
                              funcname=req.funcname,
                              cost=cost_str,
                              ret_code=req.log_ret_code,
                              username=req.username,
                              stat=stat_str,
                              log_params=log_params_str,
                              error=req.error_str,
                              res=",".join(req.log_res)))
        except BaseException:
            try:
                self._errlog.log(
                    "%s %s %s Make Acclog Error %s" %
                    (req.reqid, req.ip, req.funcname, traceback.format_exc()))
            except BaseException:
                traceback.print_exc()

        return httpstatus, headers, content

    def _mk_static_ret(self, req, file_path):
        """Static file return

        Args:
            req:http req
            file_path:static file path
        Returns:
            self._mk_ret or self._mk_err_ret
        """
        req.funcname = file_path

        if not os.path.exists(file_path):
            return self._mk_err_ret(
                req, 404, "File Not Found", "File Not Found,path:{file_path}".format(file_path=file_path))

        httpstatus = "200 OK"
        headers = []
        req.log_ret_code = 200
        try:
            with open(file_path, "r") as f:
                data = f.read()
                headers.append(("Content-Length", str(len(data))))
                data = [data]
                return self._mk_ret(req, httpstatus, headers, data)
        except BaseException:
            return self._mk_err_ret(
                req, 500, "Read File Error", "Read File Error %s" % traceback.format_exc())

    def _try_to_handler_static(self, wsgienv):
        """
        If there is a static file flag, the static file path is returned

        Args：
            wsgienv:(Dict)
        Returns:
            static file path
        Examples:
            wsgienv["PATH_INFO"] : /static/vendor/angular/angular/angular.min.js
            self._static_prefix  : (default: static)
            self._static_path    : (default: static)
                |
                V
            file_path            : static/vendor/angular/angular/angular.min.js

        """
        if not self._static_prefix:
            return None

        path = wsgienv.get("PATH_INFO", "")
        if path.startswith("/" + self._static_prefix):
            if self._static_path[-1] == "/":
                file_path = self._static_path + "/".join(path.split("/")[2:])
            else:
                file_path = self._static_path + "/" + "/".join(path.split("/")[2:])

            return file_path

        return None


def httpget2dict(qs):
    """
    解析 http get 请求参数

    Args:
        qs: req.wsgienv["QUERY_STRING"]
    Returns:
        ret: (dict) HTTP get 请求参数字典
    Examples:
        params = httpget2dict(req.wsgienv.get("QUERY_STRING"))
    """
    if not qs:
        return {}
    else:
        queries = urlparse.parse_qs(qs)
        ret = {}
        for k, v in queries.items():
            if len(v) == 1:
                ret[k] = v[0]
            else:
                ret[k] = v
        return ret


def check_param(func, params):
    """
    检查 hander 方法与请求参数是否一致

    Args:
        func: hander 方法
        params: 请求参数
    Returns:
        True/False
    Examples:
        check_param(self._func, params)
    """
    args_count = func.func_code.co_argcount - \
        1 if inspect.ismethod(func) else func.func_code.co_argcount
    args = func.func_code.co_varnames[:args_count]

    for arg in params:
        if arg not in args:
            return False

    if func.func_defaults:
        args_needed = args[:-len(func.func_defaults)]
    else:
        args_needed = args

    for arg in args_needed:
        if arg not in params:
            return False
    return True


def get_uri_tail_sec(uri):
    """
    获取 uri 最后一段 section

    Examples:
        get_uri_tail_sec("/app/list") ==> list
    """
    if uri.endswith("/"):
        i = uri.rfind("/", 0, -1)
        sec = uri[i + 1: -1].encode("ascii")
    else:
        i = uri.rfind("/")
        sec = uri[i + 1:].encode("ascii")
    return sec


def get_uri_head_sec(uri):
    """
    获取 uri head 一段 section

    Examples:
        get_uri_tail_sec("/app/list") ==> app
    """
    if not uri:
        return ""
    i = 1 if uri[0] == "/" else 0

    j = uri.find("/", i)
    if j < 0:
        j = len(uri)
    return uri[i: j].encode("ascii")


def read_wsgi_post(wsgienv):
    """
    获取 post 数据

    Examples:
        post_data = read_wsgi_post(req.wsgienv)
    """
    post_len = wsgienv.get("CONTENT_LENGTH")
    post_len = int(post_len) if post_len else 0
    if post_len:
        return wsgienv["wsgi.input"].read(post_len)
    else:
        return ""


def parse_multipart_raw(s):
    """
    获取 multipart/form-data 的raw data
    """
    ret = {}
    lines = s.split("\n")
    for i in range(0, 4 * (len(lines) / 4), 4):
        infoline = lines[i + 1]

        infoline_lower = infoline.lower()
        if "content-disposition:" not in infoline_lower or \
           "form-data" not in infoline_lower or \
           "name=\"" not in infoline_lower:
            continue

        start = infoline.find("name=\"")
        end = infoline.find("\"", start + 6)
        if start < 0 or end < 0:
            continue
        name = infoline[start + 6: end]

        value = lines[i + 3].strip("\r\n ")
        if value:
            ret[name] = value
    return ret


def get_func_name(wsgienv):
    """get func name by wsgienv PATH_INFO
    Args:
        wsgienv:(Dict)
    Returns:
        func_name:(String) func name
    """
    path = wsgienv.get("PATH_INFO", "")
    if path.endswith("/") and path != "/":
        func_name = path[:-1].encode("ascii")
    else:
        func_name = path.encode("ascii")
    return func_name


def redirect(req, url, code=None):
    """ Aborts execution and causes a 303 or 302 redirect, depending on
        the HTTP protocol version. """
    if not code:
        code = 303 if req.wsgienv.get('SERVER_PROTOCOL') == "HTTP/1.1" else 302
    return code, {}, [("Location", url)]
