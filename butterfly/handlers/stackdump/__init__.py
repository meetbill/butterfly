#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2021-04-09 12:01:08

# File Name: __init__.py
# Description:
    Showing the stack trace

    https://stackoverflow.com/questions/132058/showing-the-stack-trace-from-a-running-python-application

# Version:
    1.0.1(20210409)

"""
import os
import sys
import time
import threading
import traceback

from conf import config
from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr

__info = "stackdump"
__version = "1.0.1"


@funcattr.api
def stackdump(req):
    """
    stack dump
    """
    isinstance(req, Request)
    now = time.localtime()
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", now)
    path_stack_log = os.path.join(config.BASE_DIR, "logs/stack.log")
    with open(path_stack_log, "a") as dumpfp:
        athreads = threading.enumerate()
        tnames = [(th.getName()) for th in athreads]

        frames = None
        try:
            frames = sys._current_frames()
        except AttributeError:
            # python version < 2.5
            pass

        id2name = {}
        try:
            id2name = dict([(th.ident, th.getName()) for th in athreads])
        except AttributeError:
            # python version < 2.6
            pass

        dumpfp.write("----------------------------------------------------------------\n")
        dumpfp.write("dump_time={cur_time} reqid={reqid}\n".format(
            cur_time=cur_time, reqid=req.reqid))
        if (frames is None) or (len(tnames) > 50):
            dumpfp.write("ActiveThreadCount: %i\n" % (len(tnames)))
            dumpfp.write("KnownActiveThreadNames:\n")
            for name in tnames:
                dumpfp.write("  %s\n" % (name))
            dumpfp.write("\n")
            return

        dumpfp.write("1 ActiveThreadCount: %i\n" % (len(frames)))
        dumpfp.write("2 KnownActiveThreadNames:\n")
        for name in tnames:
            dumpfp.write("  %s\n" % (name))
        dumpfp.write("\n")

        dumpfp.write("3 ThreadInfo:\n")
        for tid, stack in frames.items():
            dumpfp.write("Thread: %d %s\n" % (tid, id2name.get(tid, "NAME_UNKNOWN")))
            for filename, lineno, name, line in traceback.extract_stack(stack):
                dumpfp.write('File: "%s", line %d, in %s\n' % (filename, lineno, name))
                if line is not None:
                    dumpfp.write("  %s\n" % (line.strip()))
            dumpfp.write("\n")
        dumpfp.write("\n")
    return retstat.OK, {}, [(__info, __version)]
