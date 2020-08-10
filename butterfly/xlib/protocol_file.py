# coding:utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-08-09 14:14:24

# File Name: protocol_file.py
# Description:
    File Response 封装, 封装 handler 的返回结果

    + Protocol file--------------------------------+
    |+ handler -----------------------------------+|
    ||file  :/handlers/{app}/__init__.py:{handler}||
    ||return:(stat_str, data_dict, headers_list)  ||
    |+--------------------------------------------+|
    | return:httpstatus, headers, content          |
    +----------------------------------------------+

    HTTP 请求方法:
        仅支持 GET 方法(仅用于获取文件)

    HTTP 响应状态码及 Content-Type:
        HTTP 响应状态码:
            文件不存在时，HTTP 状态码为 404
            文件没读权限时，HTTP 状态码为 403
            检查参数错误时，HTTP 状态码为 400
            程序执行异常时，HTTP 状态码为 500
        HTTP 响应 Content-Type:
            文件 is_download 为 True 时，会根据文件后缀名进行识别文件类型
            文件 is_download 为 False 时，响应内容类型均为 ("Content-Type", "text/html")
"""

import os
import traceback
import httplib
import mimetypes


from xlib import httpgateway
from xlib import retstat


class Protocol(object):
    """HTTP Response
    Attributes:
        _func               : (Object) func
        _errlog             : (Object) err log logger
        _code_err           : (String) retstat.ERR_SERVER_EXCEPTION (500)
        _code_badparam      : (String) retstat.ERR_BAD_PARAMS (400)
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
                               : 此处用于处理静态文件，所以不是序列化为 JSON
            errlog             : (Object) err log logger
        """
        self._func = func
        self._errlog = errlog
        self._code_err = code_err
        self._code_badparam = code_badparam
        self._is_parse_post = is_parse_post
        self._is_encode_response = False

    def _mk_ret(self, req, stat, data, headers):
        """
        将 handler 结果进行封装, 封装为 JSON 后进行返回

        Args:
            req     : (Object) Request instance
            stat    : (String) Value with the name stat in the return value. default: ERR_SERVER_EXCEPTION
            data    : (Dict) Http body data
                      filename    : (String) 文件相对路径
                      is_download : (Bool) 是否下载
            headers : (List) http headers
        Returns:
            status, headders, content
        """
        if data is None:
            data = {}
        if headers is None:
            headers = []

        filename = data["filename"]
        is_download = data["is_download"]
        if not os.path.exists(filename) or not os.path.isfile(filename):
            return self._mk_err_ret(req, retstat.HTTP_NOT_FOUND, "File does not exist",
                                    "filename={filename} err_msg=Not found".format(filename=filename))
        if not os.access(filename, os.R_OK):
            return self._mk_err_ret(req, retstat.HTTP_FORBIDDEN, "Not have permission to access this file",
                                    "filename={filename} err_msg=Not have permission".format(filename=filename))

        if is_download:
            mimetype, encoding = mimetypes.guess_type(filename)
            if (mimetype[:5] == 'text/' or mimetype == 'application/javascript') and 'charset' not in mimetype:
                mimetype += '; charset=UTF-8'
            headers.append(("Content-Type", mimetype))
        else:
            headers.append(("Content-Type", "text/html; charset=UTF-8"))

        try:
            with open(filename) as f:
                filecontent = f.read()

        except BaseException:
            req.log(self._errlog, "Open file failed\n%s" % traceback.format_exc())
            req.error_str = "Open file Failed"
            status_line = "%s %s" % (500, httplib.responses.get(500, ""))
            return status_line, [], ""

        stats = os.stat(filename)
        headers.append(("Content-Length", str(stats.st_size)))
        return "200 OK", headers, filecontent

    def _mk_err_ret(self, req, err_code, err_msg, log_msg):
        """make err return
        Args:
            req         : (Object) Request instance
            err_code    : (int) HTTP 错误码
            err_msg     : (String) err msg
                        : (1) 记录在 acc.log
                        : (2) 在响应头中 x-reason 记录此信息
            log_msg     : (String) err log msg
        Returns:
            status, headders, content
        """
        req.error_str = err_msg
        if log_msg:
            req.log(self._errlog, log_msg)

        req.log_ret_code = err_code
        status_line = "%s %s" % (err_code, httplib.responses.get(err_code, ""))
        return status_line, [], ""

    def __call__(self, req):
        # 请求参数获取和检查
        try:
            params = httpgateway.httpget2dict(req.wsgienv.get("QUERY_STRING"))
            req.log_params.update(params)

            params["req"] = req

            if not httpgateway.check_param(self._func, params):
                return self._mk_err_ret(req, retstat.HTTP_BAD_PARAM, "Param check failed",
                                        "%s Param check failed" % req.ip)
        except BaseException:
            return self._mk_err_ret(req, retstat.HTTP_BAD_PARAM, "Param check exception",
                                    "%s Param check failed\n%s" % (req.ip, traceback.format_exc()))

        # 返回值校验
        try:
            ret = self._func(**params)
            headers = []

            code = self._code_err
            data = {}
            if isinstance(ret, (str, int)):
                code = ret
            elif len(ret) == 2:
                code, data = ret
            elif len(ret) == 3:
                code, data, headers = ret
            else:
                return self._mk_err_ret(req, retstat.HTTP_SERVER_ERROR, "Invalid ret format",
                                        "Invalid ret format %s" % type(ret))

            req.log_ret_code = code
            # 如果执行到这里，说明函数处理逻辑正常，此处会返回 200 状态码
            return self._mk_ret(req, code, data, headers)

        except BaseException:
            return self._mk_err_ret(req, retstat.HTTP_SERVER_ERROR, "API Processing Exception",
                                    "Server exception\n%s" % traceback.format_exc())
