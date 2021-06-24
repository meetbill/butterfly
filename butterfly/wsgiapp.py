# coding:utf8
"""
(1) 路由处理及 wsgigw 定义
(2) 根据配置文件配置，进行启动【百川】worker
"""
import threading
import Queue as queue

from xlib import httpgateway
from conf import logger_conf
from conf import config
from xlib import urls

# for baichuan worker
from xlib.mq import worker
from xlib import db
from xlib.apscheduler import manager
from xlib.apscheduler.triggers.interval import IntervalTrigger
from xlib.util import concurrent

# ********************************************************
# * Route                                                *
# ********************************************************
route = urls.Route(logger_conf.initlog, logger_conf.errlog)
# 自动将 handlers 目录加 package 自动注册
route.autoload_handler("handlers")
# 手动添加注册(访问 /ping ,则会自动转到 apidemo.ping)
# route.addapi("/ping", apidemo.ping, True, True)
apicube = route.get_route()


# 用于处理 application 中 environ
wsgigw = httpgateway.WSGIGateway(
    httpgateway.get_func_name,
    logger_conf.errlog,
    logger_conf.acclog,
    apicube,
    config.STATIC_PATH,
    config.STATIC_PREFIX
)

# ********************************************************
# * Baichuan                                             *
# ********************************************************
if "baichuan" in db.my_caches.keys():
    class BoundedThreadPoolExecutor(concurrent.ThreadPoolExecutor):
        """
        有界线程池
        """

        def __init__(self, max_workers=None, thread_name_prefix=''):
            # Python2
            super(BoundedThreadPoolExecutor, self).__init__(max_workers, thread_name_prefix)
            self._work_queue = queue.Queue(max_workers * 2)

    # 10 个线程
    pool = BoundedThreadPoolExecutor(10)

    baichuan_connection = db.my_caches["baichuan"]
    queues = apicube.keys()
    worker = worker.Worker(queues=queues, connection=baichuan_connection,
                           acclog=logger_conf.acclog, errlog=logger_conf.errlog,
                           pool=pool, apicube=apicube)
    worker.init()

    # 设置每 1 分钟发送心跳
    interval_cron_dict = {}
    interval_cron_dict["seconds"] = 60
    interval_trigger = IntervalTrigger(seconds=interval_cron_dict["seconds"],)
    manager.original_scheduler.add_job(
        func=worker.heartbeat,
        trigger=interval_trigger,
        jobstore="memory",
        misfire_grace_time=30,
    )

    # 设置每 15 分钟进行删除无效 worker
    interval_cron_dict = {}
    interval_cron_dict["seconds"] = 900
    interval_trigger = IntervalTrigger(seconds=interval_cron_dict["seconds"],)
    manager.original_scheduler.add_job(
        func=worker.clean_registries,
        trigger=interval_trigger,
        jobstore="memory",
        misfire_grace_time=30,
    )

    # 启动单独线程进行单独拉取队列中任务
    worker_main = threading.Thread(target=worker.work)
    worker_main.setDaemon(True)
    worker_main.start()

# 将调度程序进行启动
manager.scheduler.start()

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
