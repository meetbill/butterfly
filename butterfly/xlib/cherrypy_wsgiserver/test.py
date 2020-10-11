#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-05-27 15:20:44

# File Name: test.py
# Description:

"""
from xlib import cherrypy_wsgiserver


def simple_app(environ, start_response):
    """
    test wsgi app
    """
    response_headers = [('Content-type', 'text/plain')]
    start_response('200 OK', response_headers)
    return ['My Own Hello World!']


s = cherrypy_wsgiserver.CherryPyWSGIServer(("localhost", 8080), simple_app, perfork=1)
s.start()
