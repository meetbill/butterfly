#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-06-07 12:51:27

# File Name: test_http_util.py
# Description:
    集成测试（pytest_httpserver 需要 python3 支持，暂时没有使用)

    httpserver 需要设置两方面内容，输入（Request）和输出（Response）
    先通过 expect_request 指定输入，再通过 respond_with_data 指定输出
    最后，通过 url_for 来获取随机生成 Server 的完整 URL
    这里，仅对 / 的 Request 响应，返回 status=200 的 Response。

    demo
    -----------------------------------------------------
    import requests
    from pytest_httpserver import HTTPServer
    from pytest_httpserver.httpserver import RequestHandler


    def test_root():
        with HTTPServer() as httpserver:
            handler = httpserver.expect_request('/')
            assert isinstance(handler, RequestHandler)
            handler.respond_with_data('', status=200)

            response = requests.get(httpserver.url_for('/'))
            assert response.status_code == 200
    -----------------------------------------------------
"""

import mock
class SubClass(object):
    def add(self, a, b):
        """两个数相加"""
        pass

class TestSub():
    """测试两个数相加用例"""
    def test_sub(self):
        sub = SubClass()                        # 初始化被测函数类实例
        sub.add = mock.Mock(return_value=10)    # mock add方法 返回10
        result = sub.add(5, 5)                  # 调用被测函数
        assert result == 10
