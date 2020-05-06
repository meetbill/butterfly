#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2020-01-10 21:31:41

# File Name: report.py
# Description:

    v1.0.1 : 2020-01-10
    v1.0.2 : 2020-05-07
    --------------- modify acc.log field
"""
__info = "report"
__version = "1.0.2"

import os
import json
import re

from xlib.httpgateway import Request
from xlib import retstat
from xlib import template


def log_pattern():
    '''
    log_pattern:

    log:
        {
            'DATE': '2020-01-09',
            'TIME': '16:32:59',
            'PID': '17607',
            'CODE_INFO': 'httpgateway.py:232',
            'HOST': '127.0.0.1',
            'REQID': '684485748A2B8AAE',
            'METHOD': 'GET'
            'PATH': 'static/vendor/jquery/flot/jquery.flot.pie.js',
            'COST': '0.000533',
            'STATUS': '200',
            'USERNAME': '-',
            'STAT': 'stat:',
            'PARAMS': 'params:'
            'EXTRA': 'error_msg:\tres:',
        }
    '''
    # Snippet, thanks to http://www.seehuhn.de/blog/52
    parts = [
        r'(?P<DATE>\S+)',               # date      eg.:2019-08-12
        r'(?P<TIME>\S+)',               # time      eg.:09:22:47
        r'(?P<PID>\S+)',                # pid       eg.:41442
        r'(?P<CODE_INFO>\S+)',          # code_info eg.:httpgateway.py:185
        r'(?P<HOST>\S+)',               # host      eg.:127.0.0.1
        r'(?P<REQID>\S+)',              # reqid     eg.:CACE332C8F5E39F8
        r'(?P<METHOD>\S+)',             # reqid     eg.:GET
        r'(?P<PATH>\S+)',               # path      eg.:/x/ping
        r'(?P<COST>\S+)',               # cost time eg.:0.002147
        r'(?P<STATUS>\S+)',             # status    eg.:200(careful, can be 'OK'/'ERR')
        r'(?P<USERNAME>\S+)',           # username  eg.:meetbill (or -)
        r'(?P<STAT>\S+)',               # stat
        r'(?P<PARAMS>\S+)',             # params
        r'(?P<EXTRA>.*)',               # extra(log_params_str, req.error_str, ",".join(req.log_res))
    ]
    return re.compile(r'\s+'.join(parts) + r'\s*\Z')


def analysis_log(infile):
    """
    输出统计字典
    > day_data: 用于输出柱状图
    > total_data: 用于输出概览信息，以及饼图

    Args:
        infile: input file
    Returns:
        log_data: (dict)
    Examples:
        {
            'day_data':[('2020-01-08', { 'hits': 1 }),
                ('2020-01-09', { 'hits': 2 }),
                ('2020-01-10', {'hits': 4 })],
            'total_data': {
                    'status': {
                            '200': 7
                    },
                    'hits': 7,
                    'users': {
                            'wangbin34': 6,
                            'meetbill': 1
                    },
                    'authpath': {
                            '/task/taskchain-list': 4,
                            '/task/taskchain': 1,
                            '/app/list': 1,
                            '/apply/list': 1
                    }
            }
        }
    """
    pattern = log_pattern()

    day_data = {}
    total_data = {'hits': 0, 'status': {}, 'users': {}, 'authpath': {}}
    filesize = os.path.getsize(infile)
    blocksize = 10485760  # 10MB
    with open(infile, 'r') as fhandler:
        # 只取 10 MB以内日志
        if filesize > blocksize:
            maxseekpoint = (filesize // blocksize)
            fhandler.seek((maxseekpoint - 1) * blocksize)

        for line in fhandler.readlines()[1:]:
            m = pattern.match(line)
            res = m.groupdict()

            # 不将报表请求记录在日常访问中
            if res["PATH"].startswith("/report") or res["PATH"] == "/favicon.ico":
                continue
            _day = res["DATE"]
            # 设置每天的默认值
            day_data.setdefault(_day, {'hits': 0})
            day_data[_day]['hits'] += 1

            # 统计总数据
            total_data['status'].setdefault(res["STATUS"], 0)
            total_data['users'].setdefault(res["USERNAME"], 0)
            if res["PATH"].startswith("/auth/verification") and res["PARAMS"].startswith("params:uri:"):
                # params:uri:/task/taskchain-list?page_index=0
                url = res["PARAMS"][11:].split("?")[0]
                total_data['authpath'].setdefault(url, 0)
                total_data['authpath'][url] += 1
            total_data['hits'] += 1
            total_data['status'][res["STATUS"]] += 1
            total_data['users'][res["USERNAME"]] += 1

    log_data = {}
    # 将 key:value 转为为 (key, value) 的 list 并根据 key 进行排序
    log_data["day_data"] = sorted(day_data.items(), key=lambda x: x[0])
    log_data["total_data"] = total_data
    return log_data


def log(req):
    """
    输出 Butterfly 访问日志分析
    """
    isinstance(req, Request)
    tpl_dict = analysis_log("./logs/acc.log")
    req.timming("analysis_log")
    with open("./templates/report_log.tpl", "r") as f:
        text_src = f.read()
    rule_dict = {"tojson": json.dumps}
    t = template.Templite(text_src, rule_dict)
    text = t.render(tpl_dict)
    req.timming("template_output")
    return retstat.HTTP_OK, text, [("Content-Type", "text/html")]
