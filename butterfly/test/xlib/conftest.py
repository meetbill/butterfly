#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2019-07-18 21:01:55

# File Name: conftest.py
# Description:

"""
import os
import pytest
from xlib import httpgateway
from xlib import protocol_json
from xlib import protocol_file
from xlib import retstat
from conf import config
from xlib import logger

PATH_ACC_LOG = "logs/acc.log_test"
PATH_ERR_LOG = "logs/err.log_test"
acclog = logger.LoggerBase(PATH_ACC_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)
errlog = logger.LoggerBase(PATH_ERR_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)


def demo_test1(req, str_info):
    return retstat.OK, {"str_info": str_info}


def demo_file1(req):
    return retstat.OK, {"filename": "test/static_file/test_html.html", "is_download": False}


@pytest.fixture()
def init_data():
    """
    函数级别的初始化及结束执行。每个测试用例执行一次
    :return:
    """
    apicube = {}
    apicube["/demo_test1"] = protocol_json.Protocol(demo_test1,
                                                    retstat.ERR_SERVER_EXCEPTION,
                                                    retstat.ERR_BAD_PARAMS,
                                                    True,
                                                    True,
                                                    errlog)
    apicube["/demo_file1"] = protocol_file.Protocol(demo_file1,
                                                    retstat.ERR_SERVER_EXCEPTION,
                                                    retstat.ERR_BAD_PARAMS,
                                                    True,
                                                    False,
                                                    errlog)
    wsgigw = httpgateway.WSGIGateway(
        httpgateway.get_func_name,
        errlog,
        acclog,
        apicube,
        config.STATIC_PATH,
        config.STATIC_PREFIX
    )
    yield wsgigw

    # 清理日志
    if True:
        if os.path.exists(PATH_ACC_LOG):
            os.remove(PATH_ACC_LOG)
        if os.path.exists(PATH_ERR_LOG):
            os.remove(PATH_ERR_LOG)
