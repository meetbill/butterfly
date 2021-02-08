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
    v1.0.3 : 2021-02-08
    --------------- modify acc.log field
"""
__info = "demo"
__version = "1.0.3"

import os
import json
import re

from xlib.httpgateway import Request
from xlib import retstat
from xlib import template


def log_pattern():
    '''
    Returns:
        pattern

    Examples: r"/index/(?P<num>\d*)/(?P<nid>\d*)"
                (1) (?P<num>\d*) 是将后面匹配的 \d* 数据，取一个组名
                    这个组名必须是唯一的，不重复的，没有特殊符号，函数可以获得这个组名下的数据
                (2) [\S]表示，非空白就匹配
                (3) [\s]表示，空白匹配, 等价于 [ \f\n\r\t\v]
    '''
    # Snippet, thanks to http://www.seehuhn.de/blog/52
    parts = [
        r'(?P<DATE>\S+)',               # date      eg.:2019-08-12
        r'(?P<TIME>\S+)',               # time      eg.:09:22:47
        r'(?P<PID>\S+)',                # pid       eg.:41442
        r'(?P<CODE_INFO>\S+)',          # code_info eg.:httpgateway.py:185
        r'(?P<HOST>\S+)',               # host      eg.:127.0.0.1
        r'(?P<REQID>\S+)',              # reqid     eg.:CACE332C8F5E39F8
        r'(?P<METHOD>\S+)',             # method    eg.:GET
        r'(?P<PATH>\S+)',               # path      eg.:/x/ping
        r'cost:(?P<COST>\S+)',          # cost time eg.:0.002147
        r'stat:(?P<STAT>\S+)',          # status    eg.:200(careful, can be 'OK'/'ERR')
        r'user:(?P<USER>\S+)',          # username  eg.:meetbill (or -)
        r'talk:(?P<TALK>\S*)',          # talk      eg.:ceshi1=404.443,ceshi2=101.594
        r'params:(?P<PARAMS>\S*)',      # params    eg.:str_info=hello
        r'error_msg:(?P<ERROR_MSG>.*)',  # error_msg eg.:API Processing Exception
        r'res:(?P<RES>.*)',             # result    eg.:ceshi2=5.4,ceshi1=5.3
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
            """
            res Examples:
                {
                    'DATE': '2021-02-08',
                    'TIME': '19:42:10',
                    'PID': '79363',
                    'CODE_INFO': '/meetbill/Butterfly/xlib/httpgateway.py:258',
                    'HOST': '127.0.0.1',
                    'REQID': '093149D61AEE5847',
                    'METHOD': 'GET',
                    'PATH': '/demo_api/hello',
                    'COST': '0.506213',
                    'STAT': 'OK',
                    'USER': '-',
                    'TALK': 'ceshi1=404.443,ceshi2=101.594',
                    'PARAMS': 'str_info=hello',
                    'ERROR_MSG': '',
                    'RES': 'ceshi2=5.4,ceshi1=5.3',
                }
            """
            res = m.groupdict()

            # 不将报表请求记录在日常访问中
            if res["PATH"].startswith("/report") or res["PATH"] == "/favicon.ico":
                continue

            _day = res["DATE"]
            # 设置每天的默认值
            day_data.setdefault(_day, {'hits': 0})
            day_data[_day]['hits'] += 1

            # 统计总数据
            total_data['status'].setdefault(res["STAT"], 0)
            total_data['users'].setdefault(res["USER"], 0)
            if res["PATH"].startswith("/auth/verification") and res["PARAMS"].startswith("uri="):
                # uri:/task/taskchain-list?page_index=0
                url = res["PARAMS"][4:].split("?")[0]
                total_data['authpath'].setdefault(url, 0)
                total_data['authpath'][url] += 1
            total_data['hits'] += 1
            total_data['status'][res["STAT"]] += 1
            total_data['users'][res["USER"]] += 1

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
