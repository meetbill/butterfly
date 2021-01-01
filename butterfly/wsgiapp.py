# coding:utf8
"""
路由处理及 wsgigw 定义
"""

from xlib import httpgateway

from conf import logger_conf
from conf import config
from xlib import urls
from xlib.apscheduler import manager

# ********************************************************
# * Route                                                *
# ********************************************************
route = urls.Route(logger_conf.initlog, logger_conf.errlog)
# 自动将 handlers 目录加 package 自动注册
route.autoload_handler("handlers")
# 手动添加注册(访问 /ping ,则会自动转到 apidemo.ping)
# route.addapi("/ping", apidemo.ping, True, True)
apicube = route.get_route()

# ********************************************************
# * Schedule                                             *
# ********************************************************
if config.scheduler_store != "none":
    scheduler = manager.Scheduler(logger_conf.initlog, logger_conf.errlog, jobstore_alias=config.scheduler_store)
    scheduler.start()
else:
    scheduler = None

# 用于处理 application 中 environ
wsgigw = httpgateway.WSGIGateway(
    httpgateway.get_func_name,
    logger_conf.errlog,
    logger_conf.acclog,
    apicube,
    config.STATIC_PATH,
    config.STATIC_PREFIX,
    scheduler
)


def application(environ, start_response):
    """
    The main WSGI application.

    Args:
        environ: The HTTP application environment
        start_response: The application to run when the handling of the request is done
    Returns:
        The response as a list of lines
    """
    try:
        status, headders, content = wsgigw.process(environ)
        start_response(status, headders)
        return content
    except BaseException:
        start_response("500 Internal Server Error", [("GateWayError", "UnknownException")])
        return ()


if __name__ == '__main__':
    from xlib import logger as _logger
    _logger.set_debug_verbose()

    import sys
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000
    print "[Debug][Single-Threaded] HTTP listening on 0.0.0.0:%s..." % port
    import wsgiref.simple_server

    httpd = wsgiref.simple_server.make_server('', port, application)
    httpd.serve_forever()
