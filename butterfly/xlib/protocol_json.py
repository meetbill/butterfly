# coding:utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2019-03-04 14:44:34

# File Name: protocol_json.py
# Description:
    json Response 封装, 封装 handler 的返回结果

    + Protocol json--------------------------------+
    |+ handler -----------------------------------+|
    ||file  :/handlers/{app}/__init__.py:{handler}||
    ||return:(stat_str, data_dict, headers_list)  ||
    |+--------------------------------------------+|
    | return:httpstatus, headers, content          |
    +----------------------------------------------+

    HTTP 请求方法

    HTTP 响应状态码及 Content-Type:
        当需要序列化为 JSON 时, HTTP 状态码均为 200, 响应内容类型均为 ("Content-Type", "application/json"):
            检查参数错误时，返回 {"stat": "ERR_BAD_PARAMS"}
            程序执行异常时，返回 {"stat": "ERR_SERVER_EXCEPTION"}
        当不进行序列化时, HTTP 状态码视情况而定，响应内容类型均为 ("Content-Type", "text/html"):
            检查参数错误时，HTTP 状态码为 400
            程序执行异常时，HTTP 状态码为 500
"""

import traceback
import json
import httplib
import logging
import collections

from xlib import httpgateway
from xlib.util import json_util


class Protocol(object):
    """HTTP Response
    Attributes:
        _func               : (Object) func
        _errlog             : (Object) err log logger
        _code_err           : (String) retstat.ERR_SERVER_EXCEPTION
                            : 需要序列化为 JSON 时使用
        _code_badparam      : (String) retstat.ERR_BAD_PARAMS
                            : 需要序列化为 JSON 时使用
        _is_parse_post      : (Bool) Whether to convert the data in body in post request to dict
        _is_encode_response : (Bool) Whether to return handler results as JSON to HTTP content
    """

    def __init__(self, func, code_err, code_badparam,
                 is_parse_post, is_encode_response, errlog):
        """
        Args:
            func               : (Object) func
            code_err           : (String) retstat.ERR_SERVER_EXCEPTION (500)
            code_badparam      : (String) retstat.ERR_BAD_PARAMS (400)
            is_parse_post      : (Bool) Whether to convert the data in body in post request to dict
            is_encode_response : (Bool) Whether to return handler results as JSON to HTTP content
            errlog             : (Object) err log logger
        """
        self._func = func
        self._errlog = errlog
        self._code_err = code_err
        self._code_badparam = code_badparam
        self._is_parse_post = is_parse_post
        self._is_encode_response = is_encode_response

    def _mk_ret(self, req, stat, data, headers):
        """
        将 handler 结果进行封装, 封装为 JSON 后进行返回

        Args:
            req     : (Object) Request instance
            stat    : (String) Value with the name stat in the return value. default: ERR_SERVER_EXCEPTION
            data    : (Dict) Http body data
            headers : (List) http headers
        Returns:
            status, headders, content
        """
        if data is None:
            data = {}
        if headers is None:
            headers = []
        try:
            jsoncontent = self._mk_json_content(data, stat)
        except BaseException:
            req.log(self._errlog, "Json dump failed\n%s" % traceback.format_exc())
            req.error_str = "Dump json exception"
            return "200 OK", [], ""
        headers.append(("Content-Length", str(len(jsoncontent))))
        return "200 OK", headers, (jsoncontent,)

    def _mk_json_content(self, data, stat=None):
        """make json content
        将 stat(状态信息) 和 data(数据信息) 合成 JSON

        Args:
            data: (Dict) return content
            stat: (string) Value with the name stat in the return value. default: ERR_SERVER_EXCEPTION
        Returns:
            ret : (json)
        """
        if stat is not None:
            data["stat"] = stat
        ret = json.dumps(data, default=json_util.json_default)
        if isinstance(ret, unicode):
            ret = ret.encode("utf8")
        return ret

    def _mk_err_ret(self, req, is_bad_param, err_msg, log_msg):
        """make err return
        Args:
            req         : (Object) Request instance
            is_bad_param: (Bool)
            err_msg     : (String) err msg
                        : (1) 记录在 acc.log 访问日志中
                        : (2) 在响应头中 x-reason 记录此信息
            log_msg     : (String) err log msg
        Returns:
            status, headders, content
        """
        req.error_str = err_msg
        req.error_detail = log_msg
        if log_msg:
            req.log(self._errlog, log_msg)

        if self._is_encode_response:
            err_code = self._code_badparam if is_bad_param else self._code_err
            req.log_ret_code = err_code
            return self._mk_ret(req, err_code, None, [])
        else:
            err_code = 400 if is_bad_param else 500
            req.log_ret_code = err_code
            status_line = "%s %s" % (err_code, httplib.responses.get(err_code, ""))
            return status_line, [], ""

    def __call__(self, req):
        # 请求参数获取和检查
        try:
            params = httpgateway.httpget2dict(req.wsgienv.get("QUERY_STRING"))
            if self._is_parse_post and req.wsgienv.get("REQUEST_METHOD") == "POST":
                post_data = httpgateway.read_wsgi_post(req.wsgienv)
                if post_data:
                    post_params = json.loads(post_data)
                    for k, v in post_params.iteritems():
                        params[str(k)] = v
            req.log_params.update(params)

            params["req"] = req

            if not httpgateway.check_param(self._func, params):
                return self._mk_err_ret(req, True, "Param check failed", "%s Param check failed" % req.ip)
        except BaseException:
            return self._mk_err_ret(req, True, "Param check exception",
                                    "%s Param check failed\n%s" % (req.ip, traceback.format_exc()))

        # 返回值校验
        try:
            log_msg = "[butterfly Request] [reqid]:{reqid} [wsgienv]:{wsgienv}".format(
                reqid=req.reqid, wsgienv=str(req.wsgienv))
            logging.debug(log_msg)
            ret = self._func(**params)
            log_msg = "[butterfly Response] [reqid]:{reqid} [ret]:{ret}".format(reqid=req.reqid, ret=str(ret))
            logging.debug(log_msg)
            headers = []
            if self._is_encode_response:
                code = self._code_err
                data = {}
                if isinstance(ret, (str, int)):
                    code = ret
                elif len(ret) == 2:
                    code, data = ret
                elif len(ret) == 3:
                    code, data, headers = ret
                else:
                    return self._mk_err_ret(req, False, "Invalid ret format", "Invalid ret format %s" % type(ret))

                req.log_ret_code = code
                # 如果执行到这里，说明函数处理逻辑正常，此处会返回 200 状态码
                return self._mk_ret(req, code, data, headers)
            else:
                status = 500
                data = ""
                if isinstance(ret, int):
                    status = ret
                elif len(ret) == 2:
                    status, data = ret
                elif len(ret) == 3:
                    status, data, headers = ret
                else:
                    return self._mk_err_ret(req, False, "Invalid ret format", "Invalid ret format %s" % type(ret))

                if not isinstance(data, collections.Iterable):
                    return self._mk_err_ret(req, False, "Invalid ret format",
                                            "Invalid ret format, data %s" % type(data))
                elif not isinstance(status, int):
                    return self._mk_err_ret(req, False, "Invalid ret format",
                                            "Invalid ret format, status %s" % type(status))

                if isinstance(data, dict):
                    data = self._mk_json_content(data)
                    headers.append(("Content-Length", str(len(data))))
                    headers.append(("Content-Type", "application/json"))
                else:
                    headers.append(("Content-Type", "text/html"))

                req.log_ret_code = status
                status_line = "%s %s" % (status, httplib.responses.get(status, ""))
                return status_line, headers, data
        except BaseException:
            return self._mk_err_ret(req, False, "API Processing Exception",
                                    "Server exception\n%s" % traceback.format_exc())
