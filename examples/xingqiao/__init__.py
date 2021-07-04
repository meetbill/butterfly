# coding=utf8
"""
# Description:
    workflow

Version: 1.0.1: 2021-06-22
"""
import os
import json
import logging
import traceback
from functools import partial

from conf import config
from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr
from xlib.taskflow import taskflow
from xlib.taskflow import gen_graph
from xlib.taskflow import model
from xlib import db
from xlib.mq import Queue
from xlib.db import peewee
from xlib.db import shortcuts
from xlib.util import shell_util
from xlib.util import pluginbase

__info = "xingqiao"
__version = "1.0.1"

baichuan_connection = db.my_caches["baichuan"]
log = logging.getLogger("butterfly")

# ------------------------------------------------plugin
here = os.path.abspath(os.path.dirname(__file__))
get_path = partial(os.path.join, here)
plugin_base = pluginbase.PluginBase(package='plugin_bus')


class Application(object):
    """Represents a simple example application."""

    def __init__(self):
        self.formatters = {}
        self.source = plugin_base.make_plugin_source(searchpath=[get_path('./plugins')])
        for plugin_name in self.source.list_plugins():
            try:
                plugin = self.source.load_plugin(plugin_name)
                plugin.setup(self)
            except BaseException:
                log.error("module=xingqiao plugin={plugin} err_info=load_plugin failed".format(plugin=plugin_name))

    def register_formatter(self, name, formatter):
        """A function a plugin can use to register a formatter."""
        self.formatters[name] = formatter


@funcattr.api
def create_job(req, job_namespace, job_name, job_type, job_extra=None, job_timeout=None):
    """
    Args:
        req     : Request
    Returns:
        json_status, Content, headers
    """
    isinstance(req, Request)
    plugin_app = Application()
    if job_type not in plugin_app.formatters.keys():
        return "ERR_JOB_TYPE_NOT_EXISTS", {}, [(__info, __version)]

    if job_extra is not None and not isinstance(job_extra, dict):
        return "ERR_JOB_EXTRA_INVALID", {}, [(__info, __version)]

    workflow_class = plugin_app.formatters[job_type]
    try:
        wflow = workflow_class()
        job_id = wflow.create(job_reqid=req.reqid, job_namespace=job_namespace, job_name=job_name, job_type=job_type,
                              job_extra=job_extra, job_timeout=job_timeout)
    except BaseException:
        log.error(traceback.format_exc())
        return "ERR_JOB_CREATE_FAILED", {}, [(__info, __version)]

    job_action(req, job_id)
    return retstat.OK, {"job_id": job_id}, [(__info, __version)]


@funcattr.api
def job_action(req, job_id):
    """
    执行
    """
    msg_id = ""
    is_job_end, task_status_dict = taskflow.is_job_end(job_id)
    if not is_job_end:
        params = {}
        params["job_id"] = job_id
        params_json = json.dumps(params)
        mq_queue = Queue("/xingqiao/job_action", connection=baichuan_connection)
        msg_obj = mq_queue.enqueue(params_json, result_ttl=900)
        msg_id = msg_obj.id
    return retstat.OK, {"job_id": job_id, "msg_id": msg_id, "task_status": task_status_dict}, [(__info, __version)]


@funcattr.api
def list_jobs(req, job_reqid=None, job_id=None, job_name=None,
              job_status=None, job_type=None, ret_stat=None, page_index=1, page_size=10):
    """
    Args:
        state       : (str) job 状态
        page_index  : (int) 页数
        page_size   : (int) 每页显示条数

    Returns:
        {
            'data': {
                'total': 1,
                'list': [
                    {
                        'job_status': u'failed',
                        'job_reqid': u'329FE02D1CF75155',
                        'job_id': 3,
                        'job_retinfo': u'',
                        'c_time': datetime.datetime(2021, 4, 11, 16, 27, 26),
                        'u_time': datetime.datetime(2021, 4, 11, 16, 27, 27),
                        'job_cost': 1.06245994567871,
                        'job_type': u'ping',
                        'ret_stat': 'OK',
                        'job_name': u'ceshi',
                        'job_extra': u'{}'
                    }
                ]
            }
        }

    """
    isinstance(req, Request)
    data = {}
    data_list = []

    job_model = model.Job
    select_list = [
        job_model.job_id,
        job_model.job_namespace,
        job_model.job_reqid,
        job_model.job_name,
        job_model.job_status,
        job_model.job_type,
        job_model.ret_stat,
        job_model.c_time
    ]

    # 如下方式以分页数据返回
    query_cmd = job_model.select(*select_list)
    expressions = []
    if job_reqid is not None:
        expressions.append(peewee.NodeList((job_model.job_reqid, peewee.SQL('='), job_reqid)))

    if job_id is not None:
        expressions.append(peewee.NodeList((job_model.job_id, peewee.SQL('='), int(job_id))))

    if job_name is not None:
        expressions.append(peewee.NodeList((job_model.job_name, peewee.SQL('LIKE'), job_name)))

    if job_status is not None:
        expressions.append(peewee.NodeList((job_model.job_status, peewee.SQL('='), job_status)))

    if job_type is not None:
        expressions.append(peewee.NodeList((job_model.job_type, peewee.SQL('='), job_type)))

    if ret_stat is not None:
        expressions.append(peewee.NodeList((job_model.ret_stat, peewee.SQL('='), ret_stat)))

    if len(expressions):
        query_cmd = query_cmd.where(*expressions)

    record_count = query_cmd.count()
    record_list = query_cmd.order_by(job_model.c_time.desc()).paginate(int(page_index), int(page_size))

    for record in record_list:
        record_dict = shortcuts.model_to_dict(record, only=select_list)
        data_list.append(record_dict)

    data["total"] = record_count
    data["list"] = data_list
    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api
def get_job_detail(req, job_id):
    """
    Returns:
        {
            'data': {
                'job_status': u'failed',
                'job_reqid': u'DEV_DD99CB8BFEE09FAC',
                'job_id': 1,
                'job_retinfo': u'',
                'c_time': datetime.datetime(2021, 4, 11, 17, 31, 59),
                'u_time': datetime.datetime(2021, 4, 11, 17, 32, 4),
                'job_cost': 5.63627195358276,
                'job_type': u'ping',
                'ret_stat': u'OK',
                'job_name': u'ceshi',
                'job_extra': u'{}'
            }
        }
    """
    isinstance(req, Request)
    job = model.Job.get_or_none(job_id=int(job_id))
    if job is None:
        return "ERR_JOB_NOT_EXIST", {"data": {}}, [(__info, __version)]

    job_dict = shortcuts.model_to_dict(job)
    if job_dict["ret_data"] is not None:
        job_dict["ret_data"] = json.loads(job_dict["ret_data"])
    else:
        job_dict["ret_data"] = {}

    return retstat.OK, {"data": job_dict}, [(__info, __version)]


@funcattr.api
def get_tasklist_by_jobid(req, job_id):
    """
    根据 jobid 获取 tasklist
    Returns:
        {
            'data': {
                'list': [
                    {
                        'task_namespace': u'',
                        'task_cmd': u"echo 'Hello World!' > helloWorld.out.txt;",
                        'ret_info': u'',
                        'job_id': 1,
                        'task_id': 1,
                        'ret_code': 0,
                        'task_priority': 0,
                        'task_cost': 0,
                        'task_mem': 2048,
                        'task_core_count': 1,
                        'c_time': datetime.datetime(2021, 4, 11, 17, 31, 59),
                        'task_label': u'easy_task1',
                        'task_dependencies': u'',
                        'task_status': u'finished',
                        'task_extra': u'{}',
                        'u_time': datetime.datetime(2021, 4, 11, 17, 31, 59)
                    },
                    {
                        ...
                    }
                ]
            }
        }
    """
    data = {}
    data_list = []
    record_list = model.Task.select().where(model.Task.job_id == int(job_id))
    for record in record_list:
        task_dict = shortcuts.model_to_dict(record)
        data_list.append(task_dict)

    data["list"] = data_list
    if not len(data_list):
        return "ERR_JOB_NOT_EXIST", {"data": {}}, [(__info, __version)]

    return retstat.OK, {"data": data}, [(__info, __version)]


@funcattr.api_download
def get_graph(req, job_id):
    """
    带参数请求例子

    Args:
        req             : (Object) Request
        job_id          : jobid
    Returns:
    """
    isinstance(req, Request)
    dot_file = os.path.join(config.BASE_DIR, "data/workflow_dot/{job_id}.dot".format(job_id=job_id))
    graph_file = os.path.join(config.BASE_DIR, "data/workflow_dot/{job_id}.png".format(job_id=job_id))
    gen_graph.write_dot_graph(job_id, dot_file)
    cmd = "dot -Tpng {dot_file} -o {graph_file}".format(
        dot_file=dot_file,
        graph_file=graph_file
    )
    shell_util.run(cmd)

    return retstat.OK, {"filename": graph_file, "is_download": True}, [(__info, __version)]
