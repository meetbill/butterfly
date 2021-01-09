# coding=utf8
"""
Butterfly main
"""

import os
import sys

reload(sys)
sys.setdefaultencoding('utf8')

# ********************************************************
# * Third lib                                            *
# ********************************************************
if os.path.exists('third'):
    cur_path = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(0, os.path.join(cur_path, 'third'))

import wsgiapp
from xlib.cherrypy_wsgiserver import CherryPyWSGIServer
from conf import config


if __name__ == '__main__':
    server = CherryPyWSGIServer(
        config.SERVER_LISTEN_ADDR,
        wsgiapp.application,
        config.SERVER_THREAD_NUM,
        perfork=1)
    server.start()
