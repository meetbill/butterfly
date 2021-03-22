#
# pyFlow - a lightweight parallel task engine
#
# Copyright (c) 2012-2017 Illumina, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#

"""
This script wraps workflow tasks for execution on local or remote
hosts.  It is responsible for adding log decorations to task's stderr
output (which is diverted to a file), and writing task state transition
and error information to the wrapper's stderr, which becomes the
task's 'signal' file from pyflow's perspective. The signal file is
used to determine task exit status, total runtime, and queue->run
state transition when pyflow is run in SGE mode.
"""

import datetime
import os
import subprocess
import sys
import time


scriptName = "pyflowTaskWrapper.py"


def getTracebackStr():
    """
    traceback str
    """
    import traceback
    return traceback.format_exc()


def getExceptionMsg():
    """
    Exception msg
    """
    return ("[ERROR] Unhandled Exception in pyflowTaskWrapper\n" + getTracebackStr())


def timeStampToTimeStr(ts):
    """
    converts timeStamp (time.time()) output to timeStr
    """
    return datetime.datetime.utcfromtimestamp(ts).isoformat()


def timeStrNow():
    """
    timestr
    """
    return timeStampToTimeStr(time.time())


def hardFlush(ofp):
    """
    hardFlush
    """
    ofp.flush()
    if ofp.isatty():
        return
    os.fsync(ofp.fileno())


def isWindows():
    """
    returns
        bool
    """
    import platform
    return (platform.system().find("Windows") > -1)


class SimpleFifo(object):
    """
    Store up to last N objects, not thread safe.
    Note extraction does not follow any traditional fifo interface
    """

    def __init__(self, size):
        self._size = int(size)
        assert (self._size > 0)
        self._data = [None] * self._size
        self._head = 0
        self._occup = 0
        self._counter = 0

    def count(self):
        """
        Get the total number of adds for this fifo
        """
        return self._counter

    def add(self, obj):
        """
        add obj to fifo, and return obj for convenience
        """
        self._data[self._head] = obj
        self._counter += 1
        if self._occup < self._size:
            self._occup += 1
        self._head += 1
        if self._head == self._size:
            self._head = 0
        assert (self._head < self._size)
        return obj

    def get(self):
        """
        return an array of the fifo contents
        """
        retval = []
        current = (self._head + self._size) - self._occup
        for _ in range(self._occup):
            while current >= self._size:
                current -= self._size
            retval.append(self._data[current])
            current += 1
        return retval


class StringBling(object):
    """
    StringBling
    """
    def __init__(self, runid, taskStr):
        def getHostName():
            """
            get hostname
            """
            import socket
            # return socket.gethostbyaddr(socket.gethostname())[0]
            return socket.getfqdn()

        self.runid = runid
        self.taskStr = taskStr
        self.hostname = getHostName()

    def _writeMsg(self, ofp, msg, taskStr, writeFilter=None):
        """
        log a possibly multi-line message with decoration:
        """
        if writeFilter is None:
            writeFilter=lambda x: x

        prefix = "[%s] [%s] [%s] [%s] " % (timeStrNow(), self.hostname, self.runid, taskStr)
        if msg[-1] == "\n":
            msg = msg[:-1]
        for line in msg.split("\n"):
            ofp.write(writeFilter(prefix + line + "\n"))
        hardFlush(ofp)

    def transfer(self, inos, outos, writeFilter=None):
        """
        This function is used to decorate the stderr stream from the launched task itself
        """
        if writeFilter is None:
            writeFilter=lambda x: x
        #
        # write line-read loop this way to workaround python bug:
        # http://bugs.python.org/issue3907
        #
        while True:
            line = inos.readline()
            if not line:
                break
            self._writeMsg(outos, line, self.taskStr, writeFilter)

    def wrapperLog(self, log_os, msg):
        """
        Used by the wrapper to decorate each msg line with a prefix. The decoration
        is similar to that for the task's own stderr, but we prefix the task with
        'pyflowTaskWrapper' to differentiate the source.
        """
        self._writeMsg(log_os, msg, "pyflowTaskWrapper:" + self.taskStr)


def getParams(paramsFile):
    """
    get params
    """
    import pickle

    paramhash = pickle.load(open(paramsFile))

    class Params(object):
        """
        params
        """
        pass
    params = Params()
    for (k, v) in paramhash.items():
        setattr(params, k, v)
    return params


def main():
    """
    main
    """

    usage = """

Usage: %s runid taskid parameter_pickle_file

The parameter pickle file contains all of the task parameters required by the wrapper

""" % (scriptName)

    def badUsage(msg=None):
        """
        bad usage
        """
        sys.stderr.write(usage)
        if msg is not None:
            sys.stderr.write(msg)
            exitval = 1
        else:
            exitval = 2
        hardFlush(sys.stderr)
        sys.exit(exitval)

    def checkExpectArgCount(expectArgCount):
        """
        check Expect Arg Count
        """
        if len(sys.argv) == expectArgCount:
            return
        badUsage("Incorrect argument count, expected: %i observed: %i\n" % (expectArgCount, len(sys.argv)))

    runid = "unknown"
    taskStr = "unknown"

    if len(sys.argv) > 2:
        runid = sys.argv[1]
        taskStr = sys.argv[2]

    bling = StringBling(runid, taskStr)

    # send a signal for wrapper start as early as possible to help ensure hostname is logged
    pffp = sys.stderr
    bling.wrapperLog(pffp, "[wrapperSignal] wrapperStart")

    checkExpectArgCount(4)

    picklefile = sys.argv[3]

    # try multiple times to read the argument file in case of NFS delay:
    #
    retryDelaySec = 30
    maxTrials = 3
    for _ in range(maxTrials):
        if os.path.exists(picklefile):
            break
        time.sleep(retryDelaySec)

    if not os.path.exists(picklefile):
        badUsage("First argument does not exist: " + picklefile)

    if not os.path.isfile(picklefile):
        badUsage("First argument is not a file: " + picklefile)

    # add another multi-trial loop on the pickle load operation --
    # on some filesystems the file can appear to exist but not
    # be fully instantiated yet:
    #
    for t in range(maxTrials):
        try:
            params = getParams(picklefile)
        except BaseException:
            if (t + 1) == maxTrials:
                raise
            time.sleep(retryDelaySec)
            continue
        break

    if params.cmd is None:
        badUsage("Invalid TaskWrapper input: task command set to NONE")

    if params.cwd == "" or params.cwd == "None":
        params.cwd = None

    toutFp = open(params.outFile, "a")
    terrFp = open(params.errFile, "a")

    # always keep last N lines of task stderr:
    fifo = SimpleFifo(40)

    isWin = isWindows()

    # Present shell as arg list with Popen(shell=False), so that
    # we minimize quoting/escaping issues for 'cmd' itself:
    #
    fullcmd = []
    if (not isWin) and params.isShellCmd:
        # TODO shell selection should be configurable somewhere:
        shell = ["/bin/bash", "--noprofile", "-o", "pipefail"]
        fullcmd = shell + ["-c", params.cmd]
    else:
        fullcmd = params.cmd

    retval = 1

    isShell = isWin

    try:
        startTime = time.time()
        bling.wrapperLog(pffp, "[wrapperSignal] taskStart")
        # turn off buffering so that stderr is updated correctly and its timestamps
        # are more accurate:
        # TODO: is there a way to do this for stderr only?
        proc = subprocess.Popen(
            fullcmd,
            stdout=toutFp,
            stderr=subprocess.PIPE,
            shell=isShell,
            bufsize=1,
            cwd=params.cwd,
            env=params.env)
        bling.transfer(proc.stderr, terrFp, fifo.add)
        retval = proc.wait()

        elapsed = (time.time() - startTime)

        # communication back to pyflow:
        bling.wrapperLog(pffp, "[wrapperSignal] taskExitCode %i" % (retval))

        # communication to human-readable log:
        msg = "Task: '%s' exit code: '%i'" % (taskStr, retval)
        bling.wrapperLog(terrFp, msg)

        if retval == 0:
            # communication back to pyflow:
            bling.wrapperLog(pffp, "[wrapperSignal] taskElapsedSec %i" % (int(elapsed)))

            # communication to human-readable log:
            msg = "Task: '%s' complete." % (taskStr)
            msg += " elapsedSec: %i" % (int(elapsed))
            msg += " elapsedCoreSec: %i" % (int(elapsed * params.nCores))
            msg += "\n"
            bling.wrapperLog(terrFp, msg)
        else:
            # communication back to pyflow:
            tailMsg = fifo.get()
            bling.wrapperLog(pffp, "[wrapperSignal] taskStderrTail %i" % (1 + len(tailMsg)))
            pffp.write("Last %i stderr lines from task (of %i total lines):\n" % (len(tailMsg), fifo.count()))
            for line in tailMsg:
                pffp.write(line)
            hardFlush(pffp)

    except KeyboardInterrupt:
        msg = "[ERROR] Keyboard Interupt, shutting down task."
        bling.wrapperLog(terrFp, msg)
        sys.exit(1)
    except BaseException:
        msg = getExceptionMsg()
        bling.wrapperLog(terrFp, msg)
        raise

    sys.exit(retval)


if __name__ == "__main__":
    main()
