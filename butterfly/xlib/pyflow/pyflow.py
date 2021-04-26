#!/usr/bin/env python
# coding=utf8
"""
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
"""
__author__ = 'Christopher Saunders'
__version__ = "1.0.1"


import copy
import datetime
import os
import re
import subprocess
import sys
import threading
import time
import traceback

from xlib.pyflow.pyflowConfig import siteConfig
from xlib.pyflow import model
from xlib.util import host_util


moduleDir = os.path.abspath(os.path.dirname(__file__))


# minimum python version
#
pyver = sys.version_info
if pyver[0] != 2 or (pyver[0] == 2 and pyver[1] < 4):
    raise Exception("pyflow module has only been tested for python versions [2.4,3.0)")

# problem python versions:
#
# Internal interpreter deadlock issue in python 2.7.2:
# http://bugs.python.org/issue13817
# ..is so bad that pyflow can partially, but not completely, work around it -- so issue a warning for this case.
if pyver[0] == 2 and pyver[1] == 7 and pyver[2] == 2:
    raise Exception(
        "Python interpreter errors in python 2.7.2 may cause a pyflow workflow hang or crash.")


# The line below is a workaround for a python 2.4/2.5 bug in
# the subprocess module.
#
# Bug is described here: http://bugs.python.org/issue1731717
# Workaround is described here: http://bugs.python.org/issue1236
#
subprocess._cleanup = lambda: None


# In python 2.5 or greater, we can lower the per-thread stack size to
# improve memory consumption when a very large number of jobs are
# run. Below it is lowered to 256Kb (compare to linux default of
# 8Mb).
#
try:
    threading.stack_size(min(256 * 1024, threading.stack_size))
except AttributeError:
    # Assuming this means python version < 2.5
    pass


def getPythonVersion():
    """
    python version
    """
    python_version = sys.version_info
    return ".".join([str(i) for i in python_version])


pythonVersion = getPythonVersion()


def cleanEnv():
    """
    clear bash functions out of the env
    """

    ekeys = os.environ.keys()
    for key in ekeys:
        if key.endswith("()"):
            del os.environ[key]


# utility values and functions:
#

def ensureDir(d):
    """
    make directory if it doesn't already exist, raise exception if
    something else is in the way:
    """
    if os.path.exists(d):
        if not os.path.isdir(d):
            raise Exception("Can't create directory: %s" % (d))
    else:
        os.makedirs(d)


#
# time functions -- note there's an additional copy in the pyflow wrapper script:
#
# all times in pyflow are utc (never local) and printed to iso8601
#
def timeStampToTimeStr(ts):
    """
    converts time.time() output to timenow() string
    """
    return datetime.datetime.utcfromtimestamp(ts).isoformat()


def timeStrNow():
    """
    time str
    """
    return timeStampToTimeStr(time.time())


def isInt(x):
    """
    is int
    """
    return isinstance(x, (int, long))


def isString(x):
    """
    is string
    """
    return isinstance(x, basestring)


def isIterable(x):
    """
    isIterable
    """
    return (getattr(x, '__iter__', False) != False)


def lister(x):
    """
    Convert input into a list, whether it's already iterable or
    not. Make an exception for individual strings to be returned
    as a list of one string, instead of being chopped into letters
    Also, convert None type to empty list:
    """
    # special handling in case a single string is given:
    if x is None:
        return []
    if (isString(x) or (not isIterable(x))):
        return [x]
    return list(x)


def setzer(x):
    """
    convert user input into a set, handling the pathological case
    that you have been handed a single string, and you don't want
    a set of letters:
    """
    return set(lister(x))


class LogState(object):
    """
    A simple logging enum
    """
    INFO = 1
    WARNING = 2
    ERROR = 3

    @classmethod
    def toString(cls, logState):
        """
        to string
        """
        if logState == cls.INFO:
            return "INFO"
        if logState == cls.WARNING:
            return "WARNING"
        if logState == cls.ERROR:
            return "ERROR"

        raise Exception("Unknown log state: " + str(logState))


# allow fsync to be globally turned off
class LogGlobals(object):
    """
    Log globals
    """
    isFsync = True


def hardFlush(ofp):
    """
    hard flush
    """
    ofp.flush()
    if ofp.isatty():
        return
    # fsync call has been reported to consistently fail in some contexts (rsh?)
    # so allow OSError
    if not LogGlobals.isFsync:
        return
    try:
        os.fsync(ofp.fileno())
    except OSError:
        LogGlobals.isFsync = False


def log(ofpList, msgList, linePrefix=None):
    """
    General logging function.

    @param ofpList: A container of file objects to write to

    @param msgList: A container of (or a single) multi-line log message
               string. Final newlines are not required

    @param linePrefix: A prefix to add before every line. This will come
                  *after* the log function's own '[time] [hostname]'
                  prefix.

    @return: Returns a boolean tuple of size ofpList indicating the success of
      writing to each file object
    """
    msgList = lister(msgList)
    ofpList = setzer(ofpList)
    retval = [True] * len(ofpList)
    for msg in msgList:
        # strip final trailing newline if it exists:
        if (len(msg) > 0) and (msg[-1] == "\n"):
            msg = msg[:-1]
        linePrefixOut = "[%s] [%s]" % (timeStrNow(), siteConfig.getHostName())
        if linePrefix is not None:
            linePrefixOut += " " + linePrefix
        # split message into prefixable lines:
        for i, ofp in enumerate(ofpList):
            # skip io streams which have failed before:
            if not retval[i]:
                continue
            try:
                for line in msg.split("\n"):
                    ofp.write("%s %s\n" % (linePrefixOut, line))
                hardFlush(ofp)
            except IOError:
                retval[i] = False
    return retval


def getThreadName():
    """
    get Thread name
    """
    return threading.currentThread().getName()


def isMainThread():
    """
    isMainThread
    """
    return (getThreadName == "MainThread")


def getTracebackStr():
    """
    get traceback str
    """
    return traceback.format_exc()


def getExceptionMsg():
    """
    get Exception msg
    """

    msg = ("Unhandled Exception in %s\n" % (getThreadName())) + getTracebackStr()
    if msg[-1] == "\n":
        msg = msg[:-1]
    return msg.split("\n")


def cmdline():
    """
    cmdline
    """
    return " ".join(sys.argv)


def boolToStr(b):
    """
    bool to str
    """
    return str(int(b))


def argToBool(x):
    """
    convert argument of unknown type to a bool:
    """
    class FalseStrings(object):
        """
        FalseStrings
        """
        val = ("", "0", "false", "f", "no", "n", "off")

    if isinstance(x, basestring):
        return (x.lower() not in FalseStrings.val)
    return bool(x)


namespaceSep = "+"


def namespaceJoin(a, b):
    """
    join two strings with a separator only if a exists
    """
    if a == "":
        return b
    elif b == "":
        return a
    return a + namespaceSep + b


def namespaceTypeLabel(namespace):
    """
    Provide a consistent naming scheme to users for embedded workflows
    """
    if namespace == "":
        return "master workflow"
    else:
        return "sub-workflow"


def namespaceLabel(namespace):
    """
    Provide a consistent naming scheme to users for embedded workflows
    """
    if namespace == "":
        return "master workflow"
    else:
        return "sub-workflow '%s'" % (namespace)


class ExpWaiter(object):
    """
    Convenience object to setup exponentially increasing wait/polling times
    """

    def __init__(self, startSec, factor, maxSec, event=None):
        """
        optionally allow an event to interrupt wait cycle
        """
        assert (startSec > 0.)
        assert (factor > 1.)
        assert (maxSec >= startSec)
        self.startSec = startSec
        self.factor = factor
        self.maxSec = maxSec
        self.event = event

        self.sec = self.startSec
        self.isMax = False

    def reset(self):
        """
        reset
        """
        self.sec = self.startSec

    def wait(self):
        """
        wait
        """
        if self.event is None:
            time.sleep(self.sec)
        else:
            self.event.wait(self.sec)
        if self.isMax:
            return
        self.sec = min(self.sec * self.factor, self.maxSec)
        self.isMax = (self.sec == self.maxSec)
        assert self.sec <= self.maxSec


def lockMethod(f):
    """
    method decorator acquires/releases object's lock
    """

    def wrapped(self, *args, **kw):
        """
        wrapped func
        """
        if not hasattr(self, "lock"):
            self.lock = threading.RLock()

        self.lock.acquire()
        try:
            return f(self, *args, **kw)
        finally:
            self.lock.release()
    return wrapped


class Bunch(object):
    """
    generic struct with named argument constructor
    """

    def __init__(self, **kwds):
        self.__dict__.update(kwds)


#######################################################################
#
# these functions are written out to a utility script which allows users
# to make a dot graph from their current state directory output. We
# keep it in pyflow as working code so that pyflow can call sections of it.
#


def getTaskInfoDepSet(s):
    """
    getTaskInfoDepSet
    """
    # reconstruct dependencies allowing for extraneous whitespace in the file:
    s = s.strip()
    if s == "":
        return []
    return set([d.strip() for d in s.split(",")])


class TaskNodeConstants(object):
    """
    TaskNodeConstants
    """

    validRunstates = ("finished", "started", "queued", "waiting", "failed")


################################################################
#
# workflowRunner Helper Classes:
#
#


class Command(object):
    """
    Commands can be presented as strings or argument lists (or none)
    """

    def __init__(self, cmd, cwd, env=None):
        # 1: sanitize/error-check cmd
        if ((cmd is None) or
            (cmd == "") or
                (isIterable(cmd) and len(cmd) == 0)):
            self.cmd = None
            self.type = "none"
        elif isString(cmd):
            self.cmd = Command.cleanStr(cmd)
            self.type = "str"
        elif isIterable(cmd):
            self.cmd = []
            for i, s in enumerate(cmd):
                if not (isString(s) or isInt(s)):
                    raise Exception("Argument: \
                            '%s' from position %i in argument list command is not a string or integer. \
                            Full command: '%s'" %
                                    (str(s), (i + 1), " ".join([str(s) for s in cmd])))
                self.cmd.append(Command.cleanStr(s))
            self.type = "list"
        else:
            raise Exception("Invalid task command: '%s'" % (str(cmd)))

        # 2: sanitize cwd
        self.cwd = ""
        if cwd is not None and cwd != "":
            self.cwd = os.path.abspath(cwd)
            if os.path.exists(self.cwd) and not os.path.isdir(self.cwd):
                raise Exception("Cwd argument is not a directory: '%s', provided for command '%s'" % (cwd, str(cmd)))

        # copy env:
        self.env = env

    def __repr__(self):
        if self.cmd is None:
            return ""
        if self.type == "str":
            return self.cmd
        return " ".join(self.cmd)

    @staticmethod
    def cleanStr(s):
        """
        cleanStr
        """
        if isInt(s):
            s = str(s)
        if "\n" in s:
            raise Exception("Task command/argument contains newline characters: '%s'" % (s))
        return s.strip()


class StoppableThread(threading.Thread):
    """
    Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.

    Note that this is a very new thread base class for pyflow, and most
    threads do not (yet) check their stopped status.

    """

    _stopAll = threading.Event()

    def __init__(self, *args, **kw):
        threading.Thread.__init__(self, *args, **kw)
        self._stop = threading.Event()

    def stop(self):
        "thread specific stop method, may be overridden to add async thread-specific kill behavior"
        self._stop.set()

    @staticmethod
    def stopAll():
        "quick global stop signal for threads that happen to poll stopped() very soon after event"
        StoppableThread._stopAll.set()

    def stopped(self):
        """
        stopped
        """
        return (StoppableThread._stopAll.isSet() or self._stop.isSet())


class ModeInfo(object):
    """
    Stores default values associated with each runmode: local...
    """

    def __init__(self, defaultCores, defaultMemMbPerCore, defaultIsRetry):
        self.defaultCores = defaultCores
        self.defaultMemMbPerCore = defaultMemMbPerCore
        self.defaultIsRetry = defaultIsRetry


class RunMode(object):
    """
    Run mode
    """

    data = {"local": ModeInfo(defaultCores=1,
                              defaultMemMbPerCore=siteConfig.defaultHostMemMbPerCore,
                              defaultIsRetry=False),
            }


class RetryParam(object):
    """
    parameters pertaining to task retry behavior
    """
    allowed_modes = ["nonlocal", "all"]

    def __init__(self, run_mode, retry_max, wait, window, retry_mode):
        if retry_mode not in self.allowed_modes:
            raise Exception("Invalid retry mode parameter '%s'. Accepted retry modes are {%s}."
                            % (retry_mode, ",".join(self.allowed_modes)))

        self._retry_max = retry_max
        self.wait = wait
        self.window = window
        self._retry_mode = retry_mode
        self._run_mode = run_mode

        self._finalize()
        self.validate()

    def _finalize(self):
        """
        decide whether to turn retry off based on retry and run modes:
        """
        if (self._retry_mode == "nonlocal") and \
                (not RunMode.data[self._run_mode].defaultIsRetry):
            self.max = 0
        else:
            self.max = int(self._retry_max)

    def validate(self):
        """
        check that the public parameters are valid
        """
        def nonNegParamCheck(val, valLabel):
            """
            param check
            """
            if val < 0:
                raise Exception("Parameter %s must be non-negative" % valLabel)

        nonNegParamCheck(self.max, "retryMax")
        nonNegParamCheck(self.wait, "retryWait")
        nonNegParamCheck(self.window, "retryWindow")

    def getTaskCopy(self, retry_max, wait, window, retry_mode):
        """
        return a deepcopy of the class customized for each individual task for
        any retry parameters which are not None
        """
        taskself = copy.deepcopy(self)

        if retry_max is not None:
            taskself._retry_max = retry_max
        if wait is not None:
            taskself.wait = wait
        if window is not None:
            taskself.window = window
        if retry_mode is not None:
            taskself._retry_mode = retry_mode

        taskself._finalize()
        taskself.validate()
        return taskself


class RunningTaskStatus(object):
    """
    simple object allowing remote task threads to communicate their
    status back to the TaskManager
    """

    def __init__(self, isFinishedEvent):
        self.isFinishedEvent = isFinishedEvent
        self.isComplete = threading.Event()
        self.errorCode = 0

        # errorMessage is filled in by sub-workflow
        # and command-line tasks.
        #
        # Sub-workflows use this to convey whether they have
        # failed (1) because of failures of their own tasks or (2)
        # because of an exception in the sub-workflow code, in which
        # case the exception message and stacktrace are provided.
        #
        # command tasks use this to report the stderr tail of a failing
        # task
        #
        self.errorMessage = ""

        # only used by sub-workflows to indicate that all tasks have been specified
        self.isSpecificationComplete = threading.Event()


class BaseTaskRunner(StoppableThread):
    """
    Each individual command-task or sub workflow task
    is run on its own thread using a class inherited from
    BaseTaskRunner
    """

    def __init__(self, runStatus, taskStr, sharedFlowLog, setRunstate):
        StoppableThread.__init__(self)
        self.setDaemon(True)
        self.taskStr = taskStr
        self.setName("TaskRunner-Thread-%s" % (taskStr))
        self.runStatus = runStatus
        self._sharedFlowLog = sharedFlowLog
        self.lock = threading.RLock()

        # allows taskRunner to update between queued and running status:
        self._setRunstate = setRunstate

        # this is moved into the ctor now, so that a race condition that would double-launch a task
        # is now not possible (however unlikely it was before):
        self.setInitialRunstate()

    def run(self):
        """
        BaseTaskRunner's run() method ensures that we can
        capture exceptions which might occur in this thread.
        Do not override this method -- instead define the core
        logic for the task run operation in '_run()'

        Note that for sub-workflow tasks we're interpreting raw
        client python code on this thread, so exceptions are
        *very likely* here -- this is not a corner case.
        """
        retval = 1
        retmsg = ""
        try:
            (retval, retmsg) = self._run()
        except WorkflowRunner._AbortWorkflowException:
            # This indicates an intended workflow interruption.
            # send a retval of 1 but not an error message
            pass
        except BaseException:
            retmsg = getExceptionMsg()
        self.runStatus.errorCode = retval
        self.runStatus.errorMessage = retmsg
        # this indicates that this specific task has finished:
        self.runStatus.isComplete.set()
        # this indicates that *any* task has just finished, so
        # taskmanager can stop polling and immediately sweep
        self.runStatus.isFinishedEvent.set()
        return retval

    def setRunstate(self, *args, **kw):
        """
        set Runstate
        """
        if self._setRunstate is None:
            return
        self._setRunstate(*args, **kw)

    def setInitialRunstate(self):
        """
        set Runstate
        """
        self.setRunstate("started")

    def flowLog(self, msg, logState):
        """
        flow log
        """
        linePrefixOut = "[TaskRunner:%s]" % (self.taskStr)
        self._sharedFlowLog(msg, linePrefix=linePrefixOut, logState=logState)

    def infoLog(self, msg):
        """
        info log
        """
        self.flowLog(msg, logState=LogState.INFO)

    def warningLog(self, msg):
        """
        warning log
        """
        self.flowLog(msg, logState=LogState.WARNING)

    def errorLog(self, msg):
        """
        error log
        """
        self.flowLog(msg, logState=LogState.ERROR)


class WorkflowTaskRunner(BaseTaskRunner):
    """
    Manages a sub-workflow task
    """

    def __init__(self, runStatus, taskStr, workflow, sharedFlowLog, setRunstate):
        BaseTaskRunner.__init__(self, runStatus, taskStr, sharedFlowLog, setRunstate)
        self.workflow = workflow

    def _run(self):
        namespace = self.workflow._getNamespace()
        nstLabel = namespaceTypeLabel(namespace)
        self.infoLog("Starting task specification for %s" % (nstLabel))
        self.workflow._setRunning(True)
        self.workflow.workflow()
        self.workflow._setRunning(False)
        self.runStatus.isSpecificationComplete.set()
        self.infoLog("Finished task specification for %s" % (nstLabel))
        retval = self.workflow._waitForTasksCore(namespace, isVerbose=False)
        retmsg = ""
        return (retval, retmsg)


class CommandTaskRunner(BaseTaskRunner):
    """
    Parent to local TaskRunner specializations for command tasks
    """

    taskWrapper = os.path.join(moduleDir, "pyflowTaskWrapper.py")

    def __init__(self, runStatus, runid, taskStr, cmd, nCores, memMb, retry, isDryRun,
                 outFile, errFile, tmpDir, schedulerArgList,
                 sharedFlowLog, setRunstate):
        """
        @param outFile: stdout file
        @param errFile: stderr file
        @param tmpDir: location to write files containing output from
                  the task wrapper script (and not the wrapped task)
        """
        BaseTaskRunner.__init__(self, runStatus, taskStr, sharedFlowLog, setRunstate)

        self.cmd = cmd
        self.nCores = nCores
        self.memMb = memMb
        self.retry = retry
        self.isDryRun = isDryRun
        self.outFile = outFile
        self.errFile = errFile
        self.tmpDir = tmpDir
        self.schedulerArgList = schedulerArgList
        self.runid = runid
        self.taskStr = taskStr
        if not os.path.isfile(self.taskWrapper):
            raise Exception("Can't find task wrapper script: %s" % self.taskWrapper)

    def initFileSystemItems(self):
        """
        initFileSystemItems
        """
        import pickle

        ensureDir(self.tmpDir)
        self.wrapFile = os.path.join(self.tmpDir, "pyflowTaskWrapper.signal.txt")

        # setup all the data to be passed to the taskWrapper and put this in argFile:
        taskInfo = {'nCores': self.nCores,
                    'outFile': self.outFile, 'errFile': self.errFile,
                    'cwd': self.cmd.cwd, 'env': self.cmd.env,
                    'cmd': self.cmd.cmd, 'isShellCmd': (self.cmd.type == "str")}

        argFile = os.path.join(self.tmpDir, "taskWrapperParameters.pickle")
        f = open(argFile, "w")
        pickle.dump(taskInfo, f)
        f.flush()
        f.close()

        self.wrapperCmd = [self.taskWrapper, self.runid, self.taskStr, argFile]

    def _run(self):
        """
        Outer loop of _run() handles task retry behavior:
        """

        # these initialization steps only need to happen once:
        self.initFileSystemItems()

        startTime = time.time()
        retries = 0
        retInfo = Bunch(retval=1, taskExitMsg="", isAllowRetry=False)

        while not self.stopped():
            if retries:
                self.infoLog("Retrying task: '%s'. Total prior task failures: %i" % (self.taskStr, retries))

            if self.isDryRun:
                self.infoLog("Dryrunning task: '%s' task arg list: [%s]" % (
                    self.taskStr, ",".join(['"%s"' % (s) for s in self.getFullCmd()])))
                retInfo.retval = 0
            else:
                self.runOnce(retInfo)

            if retInfo.retval == 0:
                break
            if retries >= self.retry.max:
                break
            elapsed = (time.time() - startTime)
            if (self.retry.window > 0) and \
               (elapsed >= self.retry.window):
                break
            if self.stopped():
                break
            if not retInfo.isAllowRetry:
                break
            retries += 1
            self.warningLog(
                "Task: '%s' failed but qualifies for retry. \
                        Total task failures (including this one): %i. Task command: '%s'" %
                (self.taskStr, retries, str(
                    self.cmd)))
            retInfo = Bunch(retval=1, taskExitMsg="", isAllowRetry=False)
            time.sleep(self.retry.wait)

        return (retInfo.retval, retInfo.taskExitMsg)

    def getExitMsg(self):
        """
        Attempt to extract exit message from a failed command task, do not complain in
        case of any errors in task signal file for this case.
        """
        msgSize = None
        wrapFp = open(self.wrapFile)
        for line in wrapFp:
            w = line.strip().split()
            if (len(w) < 6) or (w[4] != "[wrapperSignal]"):
                break
            if w[5] == "taskStderrTail":
                if (len(w) == 7):
                    msgSize = int(w[6])
                break

        taskExitMsg = ""
        if msgSize is not None:
            i = 0
            for line in wrapFp:
                if i >= msgSize:
                    break
                taskExitMsg += line
                i += 1
        wrapFp.close()
        return taskExitMsg

    def getWrapFileResult(self):
        """
        When the task is theoretically done, go and read the task wrapper to
        see the actual task exit code. This is required because:

        1) On all systems, we can distinguish between a conventional task error
        and other problems, such as (a) linux OOM killer (b) exception in the
        task wrapper itself (c) filesystem failures.
        """

        def checkWrapFileExit(result):
            """
            return isError=True on error in file format only, missing or incomplete file
            is not considered an error and the function should not return an error for this
            case.
            """

            if not os.path.isfile(self.wrapFile):
                return

            for line in open(self.wrapFile):
                # an incomplete line indicates that the file is still being written:
                if len(line) == 0 or line[-1] != '\n':
                    return

                w = line.strip().split()

                if len(w) < 6:
                    result.isError = True
                    return
                if (w[4] != "[wrapperSignal]"):
                    result.isError = True
                    return
                if w[5] == "taskExitCode":
                    if (len(w) == 7):
                        result.taskExitCode = int(w[6])
                    return

        retryCount = 8
        retryDelaySec = 30

        wrapResult = Bunch(taskExitCode=None, isError=False)

        totalDelaySec = 0
        for trialIndex in range(retryCount):
            # if the problem occurs at 0 seconds don't bother with a warning, but
            # if we've gone through a full retry cycle, then the filesystem delay is
            # getting unusual and should be a warning:
            if trialIndex > 1:
                msg = "No complete signal file found after %i seconds, retrying after delay. Signal file path: '%s'" % (
                    totalDelaySec, self.wrapFile)
                self.flowLog(msg, logState=LogState.WARNING)

            if trialIndex != 0:
                time.sleep(retryDelaySec)
                totalDelaySec += retryDelaySec

            checkWrapFileExit(wrapResult)
            if wrapResult.isError:
                break
            if wrapResult.taskExitCode is not None:
                break

        return wrapResult

    def getWrapperErrorMsg(self):
        """
        getWrapperErrorMsg
        """
        if os.path.isfile(self.wrapFile):
            stderrList = open(self.wrapFile).readlines()
            taskExitMsg = ["Anomalous task wrapper stderr output. Wrapper signal file: '%s'" % (self.wrapFile),
                           "Logging %i line(s) of task wrapper log output below:" % (len(stderrList))]
            linePrefix = "[taskWrapper-stderr]"
            taskExitMsg.extend([linePrefix + " " + line for line in stderrList])
        else:
            taskExitMsg = ["Anomalous task wrapper condition: Wrapper signal file is missing: '%s'" % (self.wrapFile)]

        return taskExitMsg


class LocalTaskRunner(CommandTaskRunner):
    """
    Local task runner
    """

    def getFullCmd(self):
        """
        get full cmd
        """
        return [sys.executable] + self.wrapperCmd

    def runOnce(self, retInfo):
        """
        run once
        """
        wrapFp = open(self.wrapFile, "w")
        proc = subprocess.Popen(self.getFullCmd(), stdout=wrapFp, stderr=subprocess.STDOUT, shell=False, bufsize=1)
        self.infoLog("Task initiated on local node")
        retInfo.retval = proc.wait()
        wrapFp.close()

        wrapResult = self.getWrapFileResult()

        if (wrapResult.taskExitCode is None) or (wrapResult.taskExitCode != retInfo.retval):
            retInfo.taskExitMsg = self.getWrapperErrorMsg()
            retInfo.retval = 1
            return retInfo
        elif retInfo.retval != 0:
            retInfo.taskExitMsg = self.getExitMsg()

        retInfo.isAllowRetry = True

        # success! (taskWrapper, but maybe not for the task...)
        return retInfo


class TaskManager(StoppableThread):
    """
    This class runs on a separate thread from workflowRunner,
    launching jobs based on the current state of the TaskDAG
    """

    def __init__(self, cdata, tdag):
        """
        @param cdata: data from WorkflowRunner instance which will be
                 constant during the lifetime of the TaskManager,
                 should be safe to lookup w/o locking
        @param tdag: task graph
        """
        StoppableThread.__init__(self)
        # parameter copy:
        self._cdata = cdata
        self.tdag = tdag
        # thread settings:
        self.setDaemon(True)
        self.setName("TaskManager-Thread")
        # lock is used for function (harvest), which is checked by
        # the WorkflowRunner under (literally) exceptional circumstances only
        self.lock = threading.RLock()
        # rm configuration:
        self.freeCores = self._cdata.param.nCores
        self.freeMemMb = self._cdata.param.memMb
        self.runningTasks = {}

        # This is used to track 'pyflow mutexes' -- for each key only a single
        # task can run at once. Key is set to True if mutex is occupied.
        self.taskMutexState = {}

    def run(self):
        """
        TaskManager runs so long as there are outstanding jobs
        """

        try:
            cleanEnv()
            while not self._isTerm():
                # update status of running jobs
                self.tdag.isFinishedEvent.clear()
                self.harvestTasks()
                # try to launch jobs:
                if self.stopped():
                    continue
                self._startTasks()
                self.tdag.isFinishedEvent.wait(5)
        except BaseException:
            msg = getExceptionMsg()
            self._flowLog(msg, logState=LogState.ERROR)
            self._cdata.setTaskManagerException()

    def _getCommandTaskRunner(self, task):
        """
        assist launch of a command-task
        """

        # shortcuts:
        payload = task.payload
        param = self._cdata.param

        if payload.cmd.cmd is None:
            # Note these should have been marked off by the TaskManager already:
            raise Exception("Attempting to launch checkpoint task: %s" % (task.fullLabel()))

        # mark task resources as occupied:
        if self.freeCores != "unlimited":
            if (self.freeCores < payload.nCores):
                raise Exception("Not enough free cores to launch task")
            self.freeCores -= payload.nCores

        if self.freeMemMb != "unlimited":
            if (self.freeMemMb < payload.memMb):
                raise Exception("Not enough free memory to launch task")
            self.freeMemMb -= payload.memMb

        if payload.mutex is not None:
            self.taskMutexState[payload.mutex] = True

        TaskRunner = None
        if param.mode == "local" or payload.isCmdMakePath:
            TaskRunner = LocalTaskRunner
        else:
            raise Exception("Can't support mode: '%s'" % (param.mode))

        #
        # TODO: find less hacky way to handle make tasks:
        #
        taskRetry = payload.retry

        if payload.isCmdMakePath:
            taskRetry = copy.deepcopy(payload.retry)
            taskRetry.window = 0

            if param.mode == "local":
                launchCmdList = ["make", "-j", str(payload.nCores)]
            else:
                raise Exception("Can't support mode: '%s'" % (param.mode))

            launchCmdList.extend(["-C", payload.cmd.cmd])
            payload.launchCmd = Command(launchCmdList, payload.cmd.cwd, payload.cmd.env)

        #
        # each commandTaskRunner requires a unique tmp dir to write
        # wrapper signals to. TaskRunner will create this directory -- it does not bother to destroy it right now:
        #

        # split the task id into two parts to keep from adding too many files to one directory:
        tmpDirId1 = "%03i" % ((int(task.id) / 1000))
        tmpDirId2 = "%03i" % ((int(task.id) % 1000))
        taskRunnerTmpDir = os.path.join(self._cdata.wrapperLogDir, tmpDirId1, tmpDirId2)

        return TaskRunner(task.runStatus, self._cdata.getRunid(),
                          task.fullLabel(), payload.launchCmd,
                          payload.nCores, payload.memMb,
                          taskRetry, param.isDryRun,
                          self._cdata.taskStdoutFile,
                          self._cdata.taskStderrFile,
                          taskRunnerTmpDir,
                          param.schedulerArgList,
                          self._cdata.flowLog,
                          task.setRunstate)

    def _getWorkflowTaskRunner(self, task):
        """
        assist launch of a workflow-task
        """
        return WorkflowTaskRunner(task.runStatus, task.fullLabel(), task.payload.workflow,
                                  self._cdata.flowLog, task.setRunstate)

    def _launchTask(self, task):
        """
        launch a specific task
        """

        if task.payload.type() == "command":
            trun = self._getCommandTaskRunner(task)
        else:
            assert 0

        self._infoLog(
            "2 Launching %s: '%s' from %s" %
            (task.payload.desc(),
             task.fullLabel(),
             namespaceLabel(
                task.namespace)))
        trun.start()
        self.runningTasks[task] = trun

    @lockMethod
    def _startTasks(self):
        """
        Determine what tasks, if any, can be started

        Note that the lock is here to protect self.runningTasks
        """

        # Trace through DAG, completing any empty-command checkpoints
        # found with all dependencies completed, then report everything
        # else with completed dependencies that's ready to run
        (ready, completed) = self.tdag.getReadyTasks()
        for node in completed:
            if self.stopped():
                return
            self._infoLog("Completed %s: '%s' launched from %s" %
                          (node.payload.desc(), node.fullLabel(), namespaceLabel(node.namespace)))

        # Task submission could be shutdown, eg. in response to a task error, so check for this state and stop if so
        # TODO can this be moved above workflow launch?
        if (not self._cdata.isTaskSubmissionActive()):
            return

        # start command task launch:
        ready_commands = [r for r in ready if r.payload.type() == "command"]
        ready_commands.sort(key=lambda t: (t.payload.priority, t.payload.nCores), reverse=True)
        for task in ready_commands:
            if self.stopped():
                return

            # global core and memory restrictions:
            if ((self.freeCores != "unlimited") and (task.payload.nCores > self.freeCores)):
                continue
            if ((self.freeMemMb != "unlimited") and (task.payload.memMb > self.freeMemMb)):
                continue

            # all command tasks must obey separate mutex restrictions:
            if ((task.payload.mutex is not None) and
                (task.payload.mutex in self.taskMutexState) and
                    (self.taskMutexState[task.payload.mutex])):
                continue

            self._launchTask(task)

    def _removeTaskFromRunningSet(self, task):
        """
        Given a running task which is already shown to be finished running, remove it from the running set, and
        recover allocated resources.
        """
        assert(task in self.runningTasks)

        # shortcut:

        # recover core and memory allocations:
        if task.payload.type() == "command":
            if self.freeCores != "unlimited":
                self.freeCores += task.payload.nCores
            if self.freeMemMb != "unlimited":
                self.freeMemMb += task.payload.memMb

            if task.payload.mutex is not None:
                self.taskMutexState[task.payload.mutex] = False

        del self.runningTasks[task]

    @lockMethod
    def harvestTasks(self):
        """
        Check the set of running tasks to see if they've completed and update
        Node status accordingly:
        """
        notrunning = set()
        for task in self.runningTasks.keys():
            if self.stopped():
                break
            trun = self.runningTasks[task]
            if not task.runStatus.isComplete.isSet():
                if trun.isAlive():
                    continue
                # if not complete and thread is dead then we don't know what happened, very bad!:
                task.errorstate = 1
                task.errorMessage = "Thread: '%s', has stopped without a traceable cause" % (trun.getName())
            else:
                task.errorstate = task.runStatus.errorCode
                task.errorMessage = task.runStatus.errorMessage

            if task.errorstate == 0:
                task.setRunstate("finished")
            else:
                task.setRunstate("failed")

            notrunning.add(task)

            if not task.isError():
                self._infoLog("3 Completed %s: '%s' launched from %s" %
                              (task.payload.desc(), task.fullLabel(), namespaceLabel(task.namespace)))
            else:
                msg = task.getTaskErrorMsg()

                if self._cdata.isTaskSubmissionActive():
                    # if this is the first error in the workflow, then
                    # we elaborate a bit on the workflow's response to
                    # the error.
                    msg.extend(["Shutting down task submission. Waiting for remaining tasks to complete."])

                self._errorLog(msg)
                # Be sure to send notifications *before* setting error
                # bits, because the WorkflowRunner may decide to
                # immediately shutdown all tasks and pyflow threads on
                # the first error:
                self._cdata.setTaskError(task)

        # recover task resources:
        for task in notrunning:
            self._removeTaskFromRunningSet(task)

    @lockMethod
    def cancelTaskTree(self, task):
        """
        Cancel a task and all of its children, without labeling the canceled tasks as errors

        A canceled task will not be stopped if it is already running (this is planned for the future), but will
        be unqueued if it is waiting, and put into the waiting/ignored state unless it has already completed.
        """

        # Recursively cancel child tasks:
        for child in task.children:
            self.cancelTaskTree(child)

        # In theory we would like to cancel running tasks, but this will take considerable extra development,
        # for now runningTasks will need to be ignored:
        if task in self.runningTasks:
            return

        #            # some of the logic required for running task cancelation:
        #            taskRunner = self.runningTasks[task]
        #            taskRunner.stop()
        #            self._removeTaskFromRunningSet(task)

        self._infoLog(
            "Canceling %s '%s' from %s" %
            (task.payload.desc(),
             task.fullLabel(),
             namespaceLabel(
                task.namespace)))

        self.tdag.cancelTask(task)

    @lockMethod
    def stop(self):
        StoppableThread.stop(self)
        for trun in self.runningTasks.values():
            trun.stop()

    @lockMethod
    def _areTasksDead(self):
        for trun in self.runningTasks.values():
            if trun.isAlive():
                return False
        return True

    def _isTerm(self):
        # check for explicit thread stop request (presumably from the workflowManager):
        # if this happens we exit the polling loop
        #
        if self.stopped():
            while True:
                if self._areTasksDead():
                    return True
                time.sleep(1)

        # check for "regular" termination conditions:
        if (not self._cdata.isTaskSubmissionActive()):
            return (len(self.runningTasks) == 0)
        else:
            if self.tdag.isRunComplete():
                if (len(self.runningTasks) != 0):
                    raise Exception(
                        "Inconsistent TaskManager state: workflow appears complete but there are still running tasks")
                return True
            elif self.tdag.isRunExhausted():
                return True
            else:
                return False

    def _flowLog(self, msg, logState):
        linePrefixOut = "[TaskManager]"
        # if linePrefix is not None : linePrefixOut+=" "+linePrefix
        self._cdata.flowLog(msg, linePrefix=linePrefixOut, logState=logState)

    def _infoLog(self, msg):
        self._flowLog(msg, logState=LogState.INFO)

    def _errorLog(self, msg):
        self._flowLog(msg, logState=LogState.ERROR)


# payloads are used to manage the different
# possible actions attributed to task nodes:
#
class CmdPayload(object):
    """
    CmdPayload class
    """

    def __init__(self, fullLabel, cmd, nCores, memMb, priority,
                 isCmdMakePath=False, isTaskStable=True,
                 mutex=None, retry=None):
        self.cmd = cmd
        self.nCores = nCores
        self.memMb = memMb
        self.priority = priority
        self.isCmdMakePath = isCmdMakePath
        self.isTaskStable = isTaskStable
        self.isTaskEphemeral = False
        self.mutex = mutex
        self.retry = retry

        # launch command includes make/qmake wrapper for Make path commands:
        self.launchCmd = cmd

        if (cmd.cmd is None) and ((nCores != 0) or (memMb != 0)):
            raise Exception("Null tasks should not have resource requirements. task: '%s'" % (fullLabel))

    def type(self):
        """
        type
        """
        return "command"

    def desc(self):
        """
        desc
        """
        return "command task"


class TaskNode(object):
    """
    Represents an individual task in the task graph
    """

    def __init__(self, job_id, lock, init_id, namespace, label, payload, isContinued, isFinishedEvent):
        self.job_id = job_id
        self.lock = lock
        self.id = init_id
        self.namespace = namespace
        self.label = label
        self.payload = payload
        self.isContinued = isContinued

        # if true, do not execute this task or honor it as a dependency for child tasks
        self.isIgnoreThis = False

        # if true, set the ignore state for all children of this task to true
        self.isIgnoreChildren = False

        # if true, this task and its dependents will be automatically marked as completed (until
        # a startFromTasks node is found)
        self.isAutoCompleted = False

        # task is reset to waiting runstate in a continued run
        self.isReset = False

        self.parents = set()
        self.children = set()
        self.runstateUpdateTimeStamp = time.time()
        if self.isContinued:
            self.runstate = "finished"
        else:
            self.runstate = "waiting"
        self.errorstate = 0

        # errorMessage is used by sub-workflow tasks, but not by command taks:
        self.errorMessage = ""

        self._task_id = model.Task.insert(
            job_id=job_id,
            task_label=self.label,
            task_cmd=self.payload.cmd.cmd
        ).execute()

        # This is a link to the live status object updated by TaskRunner:
        self.runStatus = RunningTaskStatus(isFinishedEvent)
        self._running_time = 0

    def __str__(self):
        msg = "TASK id: %s state: %s error: %i" % (self.fullLabel(), self.runstate, self.errorstate)
        return msg

    def fullLabel(self):
        """
        full label
        """
        return namespaceJoin(self.namespace, self.label)

    @lockMethod
    def isDone(self):
        "task has gone as far as it can"
        return ((self.runstate == "failed") or (self.runstate == "finished"))

    @lockMethod
    def isError(self):
        "true if an error occurred in this node"
        return ((self.errorstate != 0) or (self.runstate == "failed"))

    @lockMethod
    def isComplete(self):
        "task completed without error"
        return ((self.errorstate == 0) and (self.runstate == "finished"))

    @lockMethod
    def isReady(self):
        "task is ready to be run"
        retval = ((self.runstate == "waiting") and (self.errorstate == 0) and (not self.isIgnoreThis))
        if retval:
            for p in self.parents:
                if p.isIgnoreThis:
                    continue
                if not p.isComplete():
                    retval = False
                    break
        return retval

    def _isDeadWalker(self, searched):
        "recursive helper function for isDead()"

        # the fact that you're still searching means that it must have returned False last time:
        if self in searched:
            return False
        searched.add(self)

        if self.isError():
            return True
        if self.isComplete():
            return False
        for p in self.parents:
            if p._isDeadWalker(searched):
                return True
        return False

    @lockMethod
    def isDead(self):
        """
        If true, there's no longer a point to waiting for this task,
        because it either has an error or there is an error in an
        upstream dependency
        """

        # searched is used to restrict the complexity of this
        # operation on large graphs:
        searched = set()
        return self._isDeadWalker(searched)

    @lockMethod
    def setRunstate(self, runstate, updateTimeStamp=None):
        """
        updateTimeStamp is only supplied in the case where the state
        transition time is interestingly different than the function
        call time. This can happen with the state update comes from
        a polling function with a long poll interval.
        """
        if runstate not in TaskNodeConstants.validRunstates:
            raise Exception("Can't set TaskNode runstate to %s" % (runstate))

        if updateTimeStamp is None:
            self.runstateUpdateTimeStamp = time.time()
        else:
            self.runstateUpdateTimeStamp = updateTimeStamp

        if runstate == "started":
            self._running_time = time.time()

        if runstate == "finished" or runstate == "failed":
            _cost = time.time() - self._running_time
        else:
            _cost = 0

        model.Task.update({
            'task_status': runstate,
            'task_cost': _cost,
            'u_time': datetime.datetime.now()}
        ).where(model.Task.task_id == self._task_id).execute()
        self.runstate = runstate

    @lockMethod
    def getTaskErrorMsg(self):
        """
        generate consistent task error message from task state
        """

        if not self.isError():
            return []

        msg = "Failed to complete %s: '%s' launched from %s" % (
            self.payload.desc(), self.fullLabel(), namespaceLabel(self.namespace))
        if self.payload.type() == "command":
            msg += ", error code: %s, command: '%s'" % (str(self.errorstate), str(self.payload.launchCmd))
        else:
            assert 0

        msg = lister(msg)

        if self.errorMessage != "":
            msg2 = ["Error Message:"]
            msg2.extend(lister(self.errorMessage))
            linePrefix = "[%s] " % (self.fullLabel())
            for i in range(len(msg2)):
                msg2[i] = linePrefix + msg2[i]
            msg.extend(msg2)

        return msg


class TaskDAG(object):
    """
    Holds all tasks and their dependencies.

    Also responsible for task state persistence/continue across
    interrupted runs. Object is accessed by both the workflow and
    taskrunner threads, so it needs to be thread-safe.
    """

    def __init__(self, isContinue, isForceContinue, isDryRun,
                 workflowClassName,
                 startFromTasks, ignoreTasksAfter, resetTasks,
                 flowLog):
        """
        No other object/thread gets to access the taskStateFile, so file locks
        are not required (but thread locks are)
        """

        # If isConintue is true, this is a run which is continuing from a previous interrupted state.
        self.isContinue = isContinue
        self.isForceContinue = isForceContinue
        self.isDryRun = isDryRun
        self.workflowClassName = workflowClassName
        self.startFromTasks = startFromTasks
        self.ignoreTasksAfter = ignoreTasksAfter
        self.resetTasks = resetTasks
        self.flowLog = flowLog

        # unique id for each task in each run -- not persistent across continued runs:
        self.taskId = 0

        # as tasks are added, occasionally spool task info to disk, and record the last
        # task index written + 1
        self.lastTaskIdWritten = 0

        # it will be easier for people to read the task status file if
        # the tasks are in approximately the same order as they were
        # added by the workflow:
        self.addOrder = []
        self.labelMap = {}
        self.headNodes = set()
        self.tailNodes = set()
        self.lock = threading.RLock()

        # this event can be used to optionally accelerate the task cycle
        # when running in modes where task can set this event on completion
        # (ie. local mode), if this isn't set the normal polling
        # cycle applies
        self.isFinishedEvent = threading.Event()

    @lockMethod
    def isTaskPresent(self, namespace, label):
        """
        Returns:
            bool
        """
        return ((namespace, label) in self.labelMap)

    @lockMethod
    def getTask(self, namespace, label):
        """
        Get task
        """
        if (namespace, label) in self.labelMap:
            return self.labelMap[(namespace, label)]
        return None

    @lockMethod
    def getHeadNodes(self):
        "all tasks with no parents"
        return list(self.headNodes)

    @lockMethod
    def getTailNodes(self):
        "all tasks with no (runnable) children"
        return list(self.tailNodes)

    @lockMethod
    def getAllNodes(self, namespace=""):
        "get all nodes in this namespace"
        retval = []
        for (taskNamespace, taskLabel) in self.addOrder:
            if namespace != taskNamespace:
                continue
            node = self.labelMap[(taskNamespace, taskLabel)]
            if node.isIgnoreThis:
                continue
            retval.append(node)
        return retval

    @lockMethod
    def cancelTask(self, task):
        """
        Cancel task
        """
        # Nothing to do if task is already done
        if task.isDone():
            return

        # Nothing to do if task is already ignored
        if task.isIgnoreThis:
            return

        # Can't cancel a task with uncanceled children:
        for child in task.children:
            assert(child.isIgnoreThis)

        task.runstate = "waiting"
        task.isIgnoreThis = True

        if task in self.tailNodes:
            self.tailNodes.remove(task)

        for parent in task.parents:
            isTailNode = True
            for child in parent.children:
                if not child.isIgnoreThis:
                    isTailNode = False
                    break

            if isTailNode:
                self.tailNodes.add(parent)

    def _isRunExhaustedNode(self, node, searched):

        # the fact that you're still searching means that it must have returned true last time:
        if node in searched:
            return True
        searched.add(node)

        if not node.isIgnoreThis:
            if not node.isDone():
                return False
            if node.isComplete():
                for c in node.children:
                    if not self._isRunExhaustedNode(c, searched):
                        return False
        return True

    @lockMethod
    def isRunExhausted(self):
        """
        Returns true if the run is as complete as possible due to errors
        """

        # searched is used to restrict the complexity of this
        # operation on large graphs:
        searched = set()
        for node in self.getHeadNodes():
            if not self._isRunExhaustedNode(node, searched):
                return False
        return True

    @lockMethod
    def isRunComplete(self):
        "returns true if run is complete and error free"
        for node in self.labelMap.values():
            if node.isIgnoreThis:
                continue
            if not node.isComplete():
                return False
        return True

    def _getReadyTasksFromNode(self, node, ready, searched):
        "helper function for getReadyTasks"

        if node.isIgnoreThis:
            return

        if node in searched:
            return
        searched.add(node)

        if node.isReady():
            ready.add(node)
        else:
            if not node.isComplete():
                for c in node.parents:
                    self._getReadyTasksFromNode(c, ready, searched)

    @lockMethod
    def getReadyTasks(self):
        """
        Go through DAG from the tail nodes and find all tasks which
        have all prerequisites completed:
        """

        completed = self.markCheckPointsComplete()
        ready = set()
        # searched is used to restrict the complexity of this
        # operation on large graphs:
        searched = set()
        for node in self.getTailNodes():
            self._getReadyTasksFromNode(node, ready, searched)
        return (list(ready), list(completed))

    def _markCheckPointsCompleteFromNode(self, node, completed, searched):
        "helper function for markCheckPointsComplete"

        if node.isIgnoreThis:
            return

        if node in searched:
            return
        searched.add(node)

        if node.isComplete():
            return

        for c in node.parents:
            self._markCheckPointsCompleteFromNode(c, completed, searched)

        def isCheckpointTask(task):
            """
            Returns:
                bool
            """
            return (task.payload.type() == "command") and (task.payload.cmd.cmd is None)

        if node.isReady() and isCheckpointTask(node):
            node.setRunstate("finished")
            completed.add(node)

    @lockMethod
    def markCheckPointsComplete(self):
        """
        Traverse from tail nodes up, marking any checkpoint tasks
        that are ready as complete, return set of newly completed tasks:
        """
        completed = set()
        # 'searched' set is used to restrict the complexity of this
        # operation on large graphs:
        searched = set()
        for node in self.getTailNodes():
            self._markCheckPointsCompleteFromNode(node, completed, searched)
        return completed

    @lockMethod
    def addTask(self, job_id, namespace, label, payload, dependencies, isContinued=False):
        """
        Add new task to the task DAG

        @param isContinued If true, the task is being read from state history while resuming an interrupted run
        """

        # We should not expect to see isContinued task input unless this is a continued workflow:
        assert(not (isContinued and (not self.isContinue)))

        # internal data structures use the task namespace and label separately, but for logging we
        # create one string:
        fullLabel = namespaceJoin(namespace, label)

        # first check to see if task exists in DAG already, this is not allowed unless
        # we are continuing a previous run, in which case it's allowed once:
        if not isContinued and self.isTaskPresent(namespace, label):
            if self.isContinue and self.labelMap[(namespace, label)].isContinued:
                # confirm that task is a match, flip off the isContinued flag and return:
                task = self.labelMap[(namespace, label)]
                parentLabels = set([p.label for p in task.parents])
                excPrefix = "Task: '%s' does not match previous definition defined" % (
                    fullLabel)
                if task.payload.type() != payload.type():
                    msg = excPrefix + " New/old payload type: '%s'/'%s'" % (payload.type(), task.payload.type())
                    raise Exception(msg)
                if payload.isTaskStable:
                    if (payload.type() == "command") and (str(task.payload.cmd) != str(payload.cmd)):
                        msg = excPrefix + " New/old command: '%s'/'%s'" % (str(payload.cmd), str(task.payload.cmd))
                        if self.isForceContinue:
                            self.flowLog(msg, logState=LogState.WARNING)
                        else:
                            raise Exception(msg)
                    if (parentLabels != set(dependencies)):
                        msg = excPrefix + \
                            " New/old dependencies: '%s'/'%s'" % (",".join(dependencies), ",".join(parentLabels))
                        if self.isForceContinue:
                            self.flowLog(msg, logState=LogState.WARNING)
                        else:
                            raise Exception(msg)
                if payload.type() == "command":
                    task.payload.cmd = payload.cmd
                    task.payload.isCmdMakePath = payload.isCmdMakePath

                # Deal with resuming ephemeral tasks
                if payload.isTaskEphemeral:
                    def doesTaskHaveFinishedChildren(task):
                        """
                        # Check for completed children (completed children, but not incomplete children, must have been
                        # entered by this point in a continued run:
                        """
                        for child in task.children:
                            if child.isComplete():
                                return True
                        return False

                    if not doesTaskHaveFinishedChildren(task):
                        task.setRunstate("waiting")
                        task.payload.isTaskEphemeral = True

                task.isContinued = False
                return
            else:
                raise Exception("Task: '%s' is already in TaskDAG" % (fullLabel))

        task = TaskNode(
            job_id,
            self.lock,
            self.taskId,
            namespace,
            label,
            payload,
            isContinued,
            self.isFinishedEvent,
        )

        self.taskId += 1

        self.addOrder.append((namespace, label))
        self.labelMap[(namespace, label)] = task

        # ------------------------------------------------------------------save db
        dependencies_list = list(dependencies)
        dependencies_str = ",".join(dependencies_list)
        model.Task.update({
            'task_dependencies': dependencies_str,
            'u_time': datetime.datetime.now()
        }).where(model.Task.task_id == task._task_id).execute()

        for d in dependencies:
            parent = self.getTask(namespace, d)
            if parent is task:
                raise Exception("Task: '%s' cannot specify its own task label as a dependency" % (fullLabel))
            if parent is None:
                raise Exception("Dependency: '%s' for task: '%s' does not exist in TaskDAG" %
                                (namespaceJoin(namespace, d), fullLabel))
            task.parents.add(parent)
            parent.children.add(task)

        if isContinued:
            isReset = False
            if label in self.resetTasks:
                isReset = True
            else:
                for p in task.parents:
                    if p.isReset:
                        isReset = True
                        break
            if isReset:
                task.setRunstate("waiting")
                task.isReset = True

        # determine if this is an ignoreTasksAfter node
        if label in self.ignoreTasksAfter:
            task.isIgnoreChildren = True

        # determine if this is an ignoreTasksAfter descendant
        for p in task.parents:
            if p.isIgnoreChildren:
                task.isIgnoreThis = True
                task.isIgnoreChildren = True
                break

        # update headNodes
        if len(task.parents) == 0:
            self.headNodes.add(task)

        # update isAutoCompleted:
        if (self.startFromTasks and
                (label not in self.startFromTasks)):
            task.isAutoCompleted = True
            for p in task.parents:
                if not p.isAutoCompleted:
                    task.isAutoCompleted = False
                    break

            #  in case of no-parents, also check sub-workflow node
            if task.isAutoCompleted and (len(task.parents) == 0) and (namespace != ""):
                wval = namespace.rsplit(namespaceSep, 1)
                if len(wval) == 2:
                    (workflowNamespace, workflowLabel) = wval
                else:
                    workflowNamespace = ""
                    workflowLabel = wval[0]
                workflowParent = self.labelMap[(workflowNamespace, workflowLabel)]
                if not workflowParent.isAutoCompleted:
                    task.isAutoCompleted = False

        if task.isAutoCompleted:
            task.setRunstate("finished")

        # update tailNodes:
        if not task.isIgnoreThis:
            self.tailNodes.add(task)
            for p in task.parents:
                if p in self.tailNodes:
                    self.tailNodes.remove(p)

        # check dependency runState consistency:
        if task.isDone():
            for p in task.parents:
                if p.isIgnoreThis:
                    continue
                if p.isComplete():
                    continue
                raise Exception("Task: '%s' has invalid continuation state. Task dependencies are incomplete")

    @lockMethod
    def getTaskStatus(self):
        """
        Enumerate status of command tasks (but look at sub-workflows to determine if specification is complete)
        """

        val = Bunch(waiting=0, queued=0, started=0, finished=0, failed=0, isAllSpecComplete=True,
                    longestQueueSec=0, longestRunSec=0, longestQueueName="", longestRunName="")

        currentSec = time.time()
        for (namespace, label) in self.addOrder:
            node = self.labelMap[(namespace, label)]
            # special check just for workflow tasks:

            taskTime = int(currentSec - node.runstateUpdateTimeStamp)

            if node.runstate == "waiting":
                val.waiting += 1
            elif node.runstate == "queued":
                val.queued += 1
                if val.longestQueueSec < taskTime:
                    val.longestQueueSec = taskTime
                    val.longestQueueName = node.fullLabel()
            elif node.runstate == "started":
                val.started += 1
                if val.longestRunSec < taskTime:
                    val.longestRunSec = taskTime
                    val.longestRunName = node.fullLabel()
            elif node.runstate == "finished":
                val.finished += 1
            elif node.runstate == "failed":
                val.failed += 1

        return val

    @lockMethod
    def setupContinuedWorkflow(self):
        """
        Take care of all continuation specific setup activities. Read previous task state files if they exist
        and initialize taskDAG to reflect all tasks which have already been completed. Update task state files
        to reflect completed tasks only.
        """

        # Ensure that state file notifiers have been initialized as a precondition to this step, because
        # we create new tasks while reading the info file, and the state file notifiers are copied from
        # this object into the individual tasks.
        #
        pass


# workflowRunner:
#


class DataDirException(Exception):
    """
    Special exception used for the case where pyflow data dir is already in use
    """

    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg


class WorkflowRunnerThreadSharedData(object):
    """
    All data used by the WorkflowRunner which will be constant over
    the lifetime of a TaskManager instance. All of the information in
    this class will be accessed by both threads without locking.
    """

    def __init__(self):
        self.lock = threading.RLock()
        self.pid = os.getpid()
        self.runcount = 0
        self.cwd = os.path.abspath(os.getcwd())

        self.markFile = None

        # we potentially have to log before the logfile is setup (eg
        # an exception is thrown reading run parameters), so provide
        # an explicit notification that there's no log file:
        self.flowLogFp = None

        self.warningLogFp = None
        self.errorLogFp = None

        self.resetRun()

        # two elements required to implement a nohup-like behavior:
        self.isHangUp = threading.Event()
        self._isStderrAlive = True

    @staticmethod
    def _validateFixParam(param):
        """
        validate and refine raw run() parameters for use by workflow
        """

        param.schedulerArgList = lister(param.schedulerArgList)
        if param.successMsg is not None:
            if not isString(param.successMsg):
                raise Exception("successMsg argument to WorkflowRunner.run() is not a string")

        # create combined task retry settings manager:
        param.retry = RetryParam(param.mode,
                                 param.retryMax,
                                 param.retryWait,
                                 param.retryWindow,
                                 param.retryMode)

        # setup resource parameters
        if param.nCores is None:
            param.nCores = RunMode.data[param.mode].defaultCores

        # ignore total available memory settings in non-local modes:
        if param.mode != "local":
            param.memMb = "unlimited"

        if param.nCores != "unlimited":
            param.nCores = int(param.nCores)
            if param.nCores < 1:
                raise Exception(
                    "Invalid run mode nCores argument: %s. Value must be 'unlimited' or an integer no less than 1" %
                    (param.nCores))

        if param.memMb is None:
            if param.nCores == "unlimited":
                param.memMb = "unlimited"
            mpc = RunMode.data[param.mode].defaultMemMbPerCore
            if mpc == "unlimited":
                param.memMb = "unlimited"
            else:
                param.memMb = mpc * param.nCores
        elif param.memMb != "unlimited":
            param.memMb = int(param.memMb)
            if param.memMb < 1:
                raise Exception(
                    "Invalid run mode memMb argument: %s. Value must be 'unlimited' or an integer no less than 1" %
                    (param.memMb))

        # verify/normalize input settings:
        if param.mode not in RunMode.data.keys():
            raise Exception("Invalid mode argument '%s'. Accepted modes are {%s}."
                            % (param.mode, ",".join(RunMode.data.keys())))

    def _setCustomLogs(self):
        if (self.warningLogFp is None) and (self.param.warningLogFile is not None):
            self.warningLogFp = open(self.param.warningLogFile, "w")

        if (self.errorLogFp is None) and (self.param.errorLogFile is not None):
            self.errorLogFp = open(self.param.errorLogFile, "w")

    def setupNewRun(self, param):
        """
        setup
        """
        self.param = param

        # setup log file-handle first, then run the rest of parameter validation:
        # (hold this file open so that we can still log if pyflow runs out of filehandles)
        self.param.dataDir = os.path.abspath(self.param.dataDir)
        logDir = os.path.join(self.param.dataDir, "logs")
        ensureDir(logDir)
        self.flowLogFile = os.path.join(logDir, "pyflow_log.txt")
        self.flowLogFp = open(self.flowLogFile, "a")

        # run remaining validation
        self._validateFixParam(self.param)

        #  initial per-run data
        self.taskErrors = set()  # this set actually contains every task that failed -- tasks contain all of their own error info
        self.isTaskManagerException = False

        # create data directory if it does not exist
        ensureDir(self.param.dataDir)

        # check whether a process already exists:
        self.markFile = os.path.join(self.param.dataDir, "active_pyflow_process.txt")
        if os.path.exists(self.markFile):
            # Non-conventional logging situation -- another pyflow process is possibly using this same data directory, so we want
            # to log to stderr (even if the user has set isQuiet) and not interfere with the other process's log
            self.flowLogFp = None
            self.param.isQuiet = False
            msg = ["Can't initialize pyflow run because the data directory appears to be in use by another process.",
                   "\tData directory: '%s'" % (self.param.dataDir),
                   "\tIt is possible that a previous process was abruptly interrupted and did not clean up properly.",
                   "\tTo determine if this is the case, please refer to the file '%s'" % (self.markFile),
                   "\tIf this file refers to a non-running process, delete the file and relaunch pyflow,",
                   "\totherwise, specify a new data directory. ",
                   "\tAt the API-level this can be done with the dataDirRoot option."]
            self.markFile = None  # this keeps pyflow from deleting this file, as it normally would on exit
            raise DataDirException(msg)
        else:
            mfp = open(self.markFile, "w")
            msg = """
This file provides details of the pyflow instance currently using this data directory.
During normal pyflow run termination (due to job completion, error, SIGINT, etc...),
this file should be deleted. If this file is present it should mean either:
(1) the data directory is still in use by a running workflow
(2) a sudden job failure occurred that prevented normal run termination

The associated pyflow job details are as follows:
"""
            mfp.write(msg + "\n")
            for line in self.getInfoMsg():
                mfp.write(line + "\n")
            mfp.write("\n")
            mfp.close()

        # setup other instance data:
        self.runcount += 1

        # initialize directories
        self.wrapperLogDir = os.path.join(logDir, "tmp", "taskWrapperLogs")
        ensureDir(self.wrapperLogDir)

        self.taskStdoutFile = os.path.join(logDir, "pyflow_tasks_stdout_log.txt")
        self.taskStderrFile = os.path.join(logDir, "pyflow_tasks_stderr_log.txt")
        self._setCustomLogs()

    def resetRun(self):
        """
        Anything that needs to be cleaned up at the end of a run

        Right now this just make sure we don't log to the previous run's log file
        """
        self.flowLogFile = None
        self.param = None
        if self.flowLogFp is not None:
            self.flowLogFp.close()
            self.flowLogFp = None

        if self.warningLogFp is not None:
            self.warningLogFp.close()
            self.warningLogFp = None

        if self.errorLogFp is not None:
            self.errorLogFp.close()
            self.errorLogFp = None

        if self.markFile is not None:
            if os.path.exists(self.markFile):
                os.unlink(self.markFile)

        self.markFile = None

    def getRunid(self):
        """
        Get runid
        """
        return "%s_%s" % (self.pid, self.runcount)

    @lockMethod
    def setTaskError(self, task):
        """
        Set task error
        """
        self.taskErrors.add(task)

    @lockMethod
    def isTaskError(self):
        """
        Returns:
            bool
        """
        return (len(self.taskErrors) != 0)

    def isTaskSubmissionActive(self):
        """
        wait() pollers need to know if task submission has been
        shutdown to implement sane behavior.
        """
        return (not self.isTaskError())

    @lockMethod
    def setTaskManagerException(self):
        """
        TaskManager Exception
        """
        self.isTaskManagerException = True

    @lockMethod
    def flowLog(self, msg, linePrefix=None, logState=LogState.INFO):
        """
        flow log
        """
        linePrefixOut = "[%s]" % (self.getRunid())
        if linePrefix is not None:
            linePrefixOut += " " + linePrefix

        if (logState == LogState.ERROR) or (logState == LogState.WARNING):
            linePrefixOut += " [" + LogState.toString(logState) + "]"

        ofpList = []
        isAddStderr = (
            self._isStderrAlive and (
                (self.flowLogFp is None) or (
                    self.param is None) or (
                    not self.param.isQuiet)))
        if isAddStderr:
            ofpList.append(sys.stderr)
        if self.flowLogFp is not None:
            ofpList.append(self.flowLogFp)

        # make a last ditch effort to open the special error logs if these are not available already:
        try:
            self._setCustomLogs()
        except BaseException:
            pass

        if (self.warningLogFp is not None) and (logState == LogState.WARNING):
            ofpList.append(self.warningLogFp)
        if (self.errorLogFp is not None) and (logState == LogState.ERROR):
            ofpList.append(self.errorLogFp)

        if len(ofpList) == 0:
            return
        retval = log(ofpList, msg, linePrefixOut)

        # check if stderr stream failed. If so, turn it off for the remainder of run (assume terminal hup):
        if isAddStderr and (not retval[0]):
            if self.isHangUp.isSet():
                self._isStderrAlive = False

    def getInfoMsg(self):
        """
        return a string array with general stats about this run
        """

        msg = ["%s\t%s" % ("pyFlowClientWorkflowClass:", self.param.workflowClassName),
               "%s\t%s" % ("pyFlowVersion:", __version__),
               "%s\t%s" % ("pythonVersion:", pythonVersion),
               "%s\t%s" % ("Runid:", self.getRunid()),
               "%s\t%s UTC" % ("RunStartTime:", self.param.logRunStartTime),
               "%s\t%s UTC" % ("NotificationTime:", timeStrNow()),
               "%s\t%s" % ("HostName:", siteConfig.getHostName()),
               "%s\t%s" % ("WorkingDir:", self.cwd),
               "%s\t%s" % ("DataDir:", self.param.dataDir),
               "%s\t'%s'" % ("ProcessCmdLine:", cmdline())]
        return msg


class WorkflowRunner(object):
    """
    This object is designed to be inherited by a class in
    client code. This inheriting class can override the
    L{workflow()<WorkflowRunner.workflow>} method to define the
    tasks that need to be run and their dependencies.

    The inheriting class defining a workflow can be executed in
    client code by calling the WorkflowRunner.run() method.
    This method provides various run options such as whether
    to run locally.
    """

    _maxWorkflowRecursion = 30
    """
    This limit protects against a runaway forkbomb in case a
    workflow task recursively adds itself w/o termination:
    """

    def run(self,
            mode="local",
            dataDirRoot=".",
            isContinue=False,
            isForceContinue=False,
            nCores=None,
            memMb=None,
            isDryRun=False,
            retryMax=2,
            retryWait=90,
            retryWindow=360,
            retryMode="nonlocal",
            updateInterval=0,
            schedulerArgList=None,
            isQuiet=False,
            warningLogFile=None,
            errorLogFile=None,
            successMsg=None,
            startFromTasks=None,
            ignoreTasksAfter=None,
            resetTasks=None,
            job_reqid="",
            job_name=""
            ):
        """
        Call this method to execute the workflow() method overridden
        in a child class and specify the resources available for the
        workflow to run.

        Task retry behavior: Retry attempts will be made per the
        arguments below for distributed workflow runs (eg. run
        mode). Note this means that retries will be attempted for
        tasks with an 'isForceLocal' setting during distributed runs.

        Task error behavior: When a task error occurs the task
        manager stops submitting new tasks and allows all currently
        running tasks to complete. Note that in this case 'task error'
        means that the task could not be completed after exhausting
        attempted retries.

        Workflow exception behavior: Any exceptions thrown from the
        python code of classes derived from WorkflowRunner will be
        logged and trigger notification . The exception
        will not come down to the client's stack. In sub-workflows the
        exception is handled exactly like a task error (ie. task
        submission is shut-down and remaining tasks are allowed to
        complete). An exception in the master workflow will lead to
        workflow termination without waiting for currently running
        tasks to finish.

        @return: 0 if all tasks completed successfully and 1 otherwise

        @param mode: Workflow run mode. Current options are (local)

        @param dataDirRoot: All workflow data is written to
                       {dataDirRoot}/pyflow.data/ These include
                       workflow/task logs, persistent task state data,
                       and summary run info. Two workflows cannot
                       simultaneously use the same dataDir.

        @param isContinue: If True, continue workflow from a previous
                      incomplete run based on the workflow data
                      files. You must use the same dataDirRoot as a
                      previous run for this to work.  Set to 'Auto' to
                      have the run continue only if the previous
                      dataDir exists.  (default: False)

        @param isForceContinue: Only used if isContinue is not False. Normally
                           when isContinue is run, the commands of
                           completed tasks are checked to ensure they
                           match. When isForceContinue is true,
                           failing this check is reduced from an error
                           to a warning

        @param nCores: Total number of cores available, or 'unlimited'
                  (default: 1 for local mode)

        @param memMb: Total memory available (in megabytes), or 'unlimited'

        @param isDryRun: List the commands to be executed without running
                    them. Note that recursive and dynamic workflows
                    will potentially have to account for the fact that
                    expected files will be missing -- here 'recursive
                    workflow' refers to any workflow which uses the
                    addWorkflowTask() method, and 'dynamic workflow'
                    refers to any workflow which uses the
                    waitForTasks() method. These types of workflows
                    can query this status with the isDryRun() to make
                    accomadations.  (default: False)

        @param retryMax: Maximum number of task retries

        @param retryWait: Delay (in seconds) before resubmitting task

        @param retryWindow: Maximum time (in seconds) after the first task
                       submission in which retries are allowed. A value of
                       zero or less puts no limit on the time when retries
                       will be attempted. Retries are always allowed (up to
                       retryMax times), for failed make jobs.

        @param retryMode: Modes are 'nonlocal' and 'all'. For 'nonlocal'
                retries are not attempted in local run mode. For 'all'
                retries are attempted for any run mode. The default mode
                is 'nonolocal'.

        @param updateInterval: How often (in minutes) should pyflow log a
                          status update message summarizing the run
                          status.  Set this to zero or less to turn
                          the update off.

        @param schedulerArgList: A list of arguments can be specified to be
                            passed on to an external scheduler when non-local
                            modes are used

        @param isQuiet: Don't write any logging output to stderr (but still write
                   log to pyflow_log.txt)

        @param warningLogFile: Replicate all warning messages to the specified file. Warning
                            messages will still appear in the standard logs, this
                            file will contain a subset of the log messages pertaining to
                            warnings only.

        @param errorLogFile: Replicate all error messages to the specified file. Error
                            messages will still appear in the standard logs, this
                            file will contain a subset of the log messages pertaining to
                            errors only. It should be empty for a successful run.

        @param successMsg: Provide a string containing a custom message which
                           will be prepended to pyflow's standard success
                           notification. This message will appear in the log
                           and any configured notifications. The
                           message may contain linebreaks.

        @param startFromTasks: A task label or container of task labels. Any tasks which
                               are not in this set or descendants of this set will be marked as
                               completed.
        @type startFromTasks: A single string, or set, tuple or list of strings

        @param ignoreTasksAfter: A task label or container of task labels. All descendants
                                 of these task labels will be ignored.
        @type ignoreTasksAfter: A single string, or set, tuple or list of strings

        @param resetTasks: A task label or container of task labels. These tasks and all
                           of their descendants will be reset to the "waiting" state to be re-run.
                           Note this option will only affect a workflow which has been continued
                           from a previous run. This will not override any nodes altered by the
                           startFromTasks setting in the case that both options are used together.
        @type resetTasks: A single string, or set, tuple or list of strings
        """

        # ---------------------------------------------------------- save data to MySQL
        self._running_time = time.time()
        job_id = model.Job.insert(job_runner=host_util.server_name,
                                  job_reqid=job_reqid,
                                  job_name=job_name,
                                  job_type=self.__class__.__name__,
                                  ).execute()
        self._job_id = job_id

        # Setup pyflow signal handlers:
        #
        inHandlers = Bunch(isSet=False)

        class SigTermException(Exception):
            """
            SigTerm exception
            """
            pass

        def sigtermHandler(_signum, _frame):
            """
            signal handler
            """
            raise SigTermException

        def sighupHandler(_signum, _frame):
            """
            signal handler
            """
            self._warningLog(
                ("pyflow recieved hangup signal. pyflow will continue, "
                 "but this signal may still interrupt running tasks."))
            # tell cdata to turn off any tty writes:
            self._cdata().isHangUp.set()

        def set_pyflow_sig_handlers():
            """
            signal handler
            """
            import signal
            if not inHandlers.isSet:
                inHandlers.sigterm = signal.getsignal(signal.SIGTERM)
                inHandlers.sighup = signal.getsignal(signal.SIGHUP)
                inHandlers.isSet = True
            try:
                signal.signal(signal.SIGTERM, sigtermHandler)
                signal.signal(signal.SIGHUP, sighupHandler)
            except ValueError:
                if isMainThread():
                    raise
                else:
                    self._warningLog(
                        "pyflow has not been initialized on main thread, all custom signal handling disabled")

        def unset_pyflow_sig_handlers():
            """
            Signal handler
            """
            import signal
            if not inHandlers.isSet:
                return
            try:
                signal.signal(signal.SIGTERM, inHandlers.sigterm)
                signal.signal(signal.SIGHUP, inHandlers.sighup)
            except ValueError:
                if isMainThread():
                    raise
                else:
                    pass

        # if return value is somehow not set after this then something bad happened, so init to 1:
        retval = 1
        try:
            set_pyflow_sig_handlers()

            def exceptionMessaging(prefixMsg=None):
                """
                Exception messaging
                """
                msg = lister(prefixMsg)
                eMsg = lister(getExceptionMsg())
                msg.extend(eMsg)
                self._notify(msg, logState=LogState.ERROR)

            try:
                self.runStartTimeStamp = time.time()
                self.updateInterval = int(updateInterval)
                # a container to haul all the run() options around in:
                param = Bunch(mode=mode,
                              dataDir=dataDirRoot,
                              isContinue=isContinue,
                              isForceContinue=isForceContinue,
                              nCores=nCores,
                              memMb=memMb,
                              isDryRun=isDryRun,
                              retryMax=retryMax,
                              retryWait=retryWait,
                              retryWindow=retryWindow,
                              retryMode=retryMode,
                              logRunStartTime=timeStampToTimeStr(self.runStartTimeStamp),
                              workflowClassName=self._whoami(),
                              schedulerArgList=schedulerArgList,
                              isQuiet=isQuiet,
                              warningLogFile=warningLogFile,
                              errorLogFile=errorLogFile,
                              successMsg=successMsg,
                              startFromTasks=setzer(startFromTasks),
                              ignoreTasksAfter=setzer(ignoreTasksAfter),
                              resetTasks=setzer(resetTasks))
                retval = self._runWorkflow(param)

            except SigTermException:
                msg = "Received termination signal, shutting down running tasks..."
                self._killWorkflow(msg)
            except KeyboardInterrupt:
                msg = "Keyboard Interrupt, shutting down running tasks..."
                self._killWorkflow(msg)
            except DataDirException as e:
                # Special exception for when pyflow directory can't be initialized.
                # A killWorkflow is not needed for this case, because no workflow
                # could be started.
                self._notify(e.msg, logState=LogState.ERROR)
            except BaseException:
                # For unhandled/unknown exceptions, catch here to write some supplemental
                # data (thread name, etc.) before releasing the exception down the stack
                exceptionMessaging()
                raise

        finally:
            # last set: disconnect the workflow log:
            self._cdata().resetRun()
            unset_pyflow_sig_handlers()

        # ---------------------------------------------------------- save data to MySQL
        if retval == 0:
            _job_status = "finished"
        else:
            _job_status = "failed"
        _cost = time.time() - self._running_time

        model.Job.update({
            'job_status': _job_status,
            'job_retcode': retval,
            'job_cost': _cost,
            'u_time': datetime.datetime.now()
        }).where(model.Job.job_id == self._job_id).execute()

        return retval

    # protected methods which can be called within the workflow method:

    def addTask(self, label, command=None, cwd=None, env=None, nCores=1,
                memMb=None,
                dependencies=None, priority=0,
                isCommandMakePath=False, isTaskStable=True,
                mutex=None,
                retryMax=None, retryWait=None, retryWindow=None, retryMode=None):
        """
        Add task to workflow, including resource requirements and
        specification of dependencies. Dependency tasks must already
        exist in the workflow.

        @return: The 'label' argument is returned without modification.


        @param label: A string used to identify each task. The label must
                 be composed of only ascii letters, digits,
                 underscores and dashes (ie. /[A-Za-z0-9_-]+/). The
                 label must also be unique within the workflow, and
                 non-empty.

        @param command: The task command. Commands can be: (1) a shell
                 string (2) an iterable container of strings (argument
                 list) (3) None. In all cases strings must not contain
                 newline characters. A single string is typically used
                 for commands that require shell features (such as
                 pipes), an argument list can be used for any other
                 commands, this is often a useful way to simplify
                 quoting issues or to submit extremely long
                 commands. The default command (None), can be used to
                 create a 'checkpoint', ie. a task which does not run
                 anything, but provides a label associated with the
                 completion of a set of dependencies.

        @param cwd: Specify current working directory to use for
                 command execution. Note that if submitting the
                 command as an argument list (as opposed to a shell
                 string) the executable (arg[0]) is searched for
                 before changing the working directory, so you cannot
                 specify the executable relative to the cwd
                 setting. If submitting a shell string command this
                 restriction does not apply.

        @param env: A map of environment variables for this task, for
                 example 'env={"PATH": "/usr/bin"}'. When env is set
                 to None (the default) the environment of the pyflow
                 client process is used.

        @param nCores: Number of cpu threads required

        @param memMb: Amount of memory required (in megabytes)

        @param dependencies: A task label or container of task labels specifying all dependent
                        tasks. Dependent tasks must already exist in
                        the workflow.
        @type dependencies: A single string, or set, tuple or list of strings


        @param priority: Among all tasks which are eligible to run at
                 the same time, launch tasks with higher priority
                 first. this value can be set from[-100,100]. Note
                 that this will strongly control the order of task
                 launch on a local run, but will only control task
                 submission order to a secondary scheduler (like
                 sge). All jobs with the same priority are already
                 submitted in order from highest to lowest nCores
                 requested, so there is no need to set priorities to
                 replicate this behavior. The taskManager can start
                 executing tasks as soon as each addTask() method is
                 called, so lower-priority tasks may be launched first
                 if they are specified first in the workflow.

        @param isCommandMakePath: If true, command is assumed to be a
                 path containing a makefile. It will be run using
                 make/qmake according to the run's mode and the task's
                 isForceLocal setting

        @param isTaskStable: If false, indicates that the task command
                 and/or dependencies may change if the run is
                 interrupted and restarted. A command marked as
                 unstable will not be checked to make sure it matches
                 its previous definition during run continuation.
                 Unstable examples: command contains a date/time, or
                 lists a set of files which are deleted at some point
                 in the workflow, etc.

        @param mutex: Provide an optional id associated with a pyflow
                 task mutex. For all tasks with the same mutex id, no more
                 than one will be run at once. Id name must follow task id
                 restrictions. Mutex ids are global across all recursively
                 invoked workflows.
                 Example use case: This feature has been added as a simpler
                 alternative to file locking, to ensure sequential, but not
                 ordered, access to a file.

        @param retryMax: The number of times this task will be retried
                 after failing. If defined, this overrides the workflow
                 retryMax value.

        @param retryWait: The number of seconds to wait before relaunching
                 a failed task. If defined, this overrides the workflow
                 retryWait value.

        @param retryWindow: The number of seconds after job submission in
                 which retries will be attempted for non-make jobs. A value of
                 zero or less causes retries to be attempted anytime after
                 job submission. If defined, this overrides the workflow
                 retryWindow value.

        @param retryMode: Modes are 'nonlocal' and 'all'. For 'nonlocal'
                retries are not attempted in local run mode. For 'all'
                retries are attempted for any run mode. If defined, this overrides
                the workflow retryMode value.
        """
        if memMb is None:
            memMb = siteConfig.defaultTaskMemMb

        self._requireInWorkflow()

        # Canceled plans to add deferred dependencies:
        # # deferredDependencies -- A container of labels specifying dependent
        # #                         tasks which have not yet been added to the
        # #                         workflow. In this case the added task will
        # #                         wait for the dependency to be defined *and*
        # #                         complete. Avoid these in favor or regular
        # #                         dependencies if possible.

        # sanitize bools:
        isCommandMakePath = argToBool(isCommandMakePath)

        # sanitize ints:
        nCores = int(nCores)
        memMb = int(memMb)
        priority = int(priority)
        if (priority > 100) or (priority < -100):
            raise Exception("priority must be an integer in the range [-100,100]")

        # sanity check label:
        WorkflowRunner._checkTaskLabel(label)

        fullLabel = namespaceJoin(self._getNamespace(), label)

        # verify/sanitize command:
        cmd = Command(command, cwd, env)

        # deal with command/resource relationship:
        if cmd.cmd is None:
            nCores = 0
            memMb = 0
        else:
            if nCores <= 0:
                raise Exception("Unexpected core requirement for task: '%s' nCores: %i" % (fullLabel, nCores))
            if memMb <= 0:
                raise Exception(
                    "Unexpected memory requirement for task: '%s' memory: %i (megabytes)" %
                    (fullLabel, memMb))

        if (self._cdata().param.nCores != "unlimited") and (nCores > self._cdata().param.nCores):
            raise Exception("Task core requirement exceeds full available resources")

        if (self._cdata().param.memMb != "unlimited") and (memMb > self._cdata().param.memMb):
            raise Exception("Task memory requirement exceeds full available resources")

        # check that make path commands point to a directory:
        #
        if isCommandMakePath:
            if cmd.type != "str":
                raise Exception("isCommandMakePath is set, but no path is provided in task: '%s'" % (fullLabel))
            cmd.cmd = os.path.abspath(cmd.cmd)

        # sanitize mutex option
        if mutex is not None:
            WorkflowRunner._checkTaskLabel(mutex)

        task_retry = self._cdata().param.retry.getTaskCopy(retryMax, retryWait, retryWindow, retryMode)

        # private _addTaskCore gets hijacked in recursive workflow submission:
        #
        payload = CmdPayload(
            fullLabel,
            cmd,
            nCores,
            memMb,
            priority,
            isCommandMakePath,
            isTaskStable,
            mutex,
            task_retry)
        self._addTaskCore(self._getNamespace(), label, payload, dependencies)
        return label

    def waitForTasks(self, labels=None):
        """
        Wait for a list of tasks to complete.

        @return: In case of an error in a task being waited for, or in
                 one of these task's dependencies, the function returns 1.
                 Else return 0.

        @param labels: Container of task labels to wait for. If an empty container is
                  given or no list is provided then wait for all
                  outstanding tasks to complete.
        @type labels: A single string, or set, tuple or list of strings
        """

        self._requireInWorkflow()

        return self._waitForTasksCore(self._getNamespace(), labels)

    def isTaskComplete(self, taskLabel):
        """
        Query if a specific task is in the workflow and completed without error.

        This can assist workflows with providing
        stable interrupt/resume behavior.

        @param taskLabel: A task string

        @return: Completion status of task
        """

        result = self._isTaskCompleteCore(self._getNamespace(), taskLabel)

        # Complete = (Done and not Error)
        return (result[0] and not result[1])

    def isTaskDone(self, taskLabel):
        """
        Query if a specific task is in the workflow and is done, with or without error

        This can assist workflows with providing
        stable interrupt/resume behavior.

        @param taskLabel: A task string

        @return: A boolean tuple specifying (task is done, task finished with error)
        """

        return self._isTaskCompleteCore(self._getNamespace(), taskLabel)

    def cancelTaskTree(self, taskLabel):
        """
        Cancel the given task and all of its dependencies.

        A canceled task will not be stopped if it is already running (this is planned for the future), but will
        be unqueued if it is waiting, and put into the waiting/ignored state unless it has already completed.
        Canceled tasks will not be treated as errors.
        """
        self._cancelTaskTreeCore(self._getNamespace(), taskLabel)

    def getRunMode(self):
        """
        Get the current run mode

        This can be used to access the current run mode from
        within the workflow function. Although the runmode should
        be transparent to client code, this is occasionally needed
        to hack workarounds.

        @return: Current run mode
        """

        self._requireInWorkflow()

        return self._cdata().param.mode

    def getNCores(self):
        """
        Get the current run core limit

        This function can be used to access the current run's core
        limit from within the workflow function. This can be useful
        to eg. limit the number of cores requested by a single task.

        @return: Total cores available to this workflow run
        @rtype: Integer value or 'unlimited'
        """

        self._requireInWorkflow()

        return self._cdata().param.nCores

    def limitNCores(self, nCores):
        """
        Takes an task nCores argument and reduces it to
        the maximum value allowed for the current run.

        @param nCores: Proposed core requirement

        @return: Min(nCores,Total cores available to this workflow run)
        """

        self._requireInWorkflow()

        nCores = int(nCores)
        runNCores = self._cdata().param.nCores
        if runNCores == "unlimited":
            return nCores
        return min(nCores, runNCores)

    def getMemMb(self):
        """
        Get the current run's total memory limit (in megabytes)

        @return: Memory limit in megabytes
        @rtype: Integer value or 'unlimited'
        """

        self._requireInWorkflow()

        return self._cdata().param.memMb

    def limitMemMb(self, memMb):
        """
        Takes a task memMb argument and reduces it to
        the maximum value allowed for the current run.

        @param memMb: Proposed task memory requirement in megabytes

        @return: Min(memMb,Total memory available to this workflow run)
        """

        self._requireInWorkflow()

        memMb = int(memMb)
        runMemMb = self._cdata().param.memMb
        if runMemMb == "unlimited":
            return memMb
        return min(memMb, runMemMb)

    def isDryRun(self):
        """
        Get isDryRun flag value.

        When the dryrun flag is set, no commands are actually run. Querying
        this flag allows dynamic workflows to correct for dry run behaviors,
        such as tasks which do no produce expected files.

        @return: DryRun status flag
        """

        self._requireInWorkflow()

        return self._cdata().param.isDryRun

    def isWorkflowStopping(self):
        """
        Return true if the workflow is in the process of stopping

        Usually the workflow is stopped due to a task error. The goal of this behavior is
        to allow currently running tasks to complete but not launch any new tasks.

        It is not essential that a workflow check this method and respond by stopping workflow
        execution unless it implements some type of potentially infinite loop dependent on task
        outcome.
        """
        return (not self._cdata().isTaskSubmissionActive())

    @staticmethod
    def runModeDefaultCores(mode):
        """
        Get the default core limit for run mode (local,..)

        @param mode: run mode, as specified in L{the run() method<WorkflowRunner.run>}

        @return: Default maximum number of cores for mode

        @rtype: Either 'unlimited', or a string
                 representation of the integer limit
        """

        return str(RunMode.data[mode].defaultCores)

    def flowLog(self, msg, logState=LogState.INFO):
        """
        Send a message to the WorkflowRunner's log.

        @param msg: Log message
        @type msg: A string or an array of strings. String arrays will be separated by newlines in the log.
        @param logState: Message severity, defaults to INFO.
        @type logState: A value in pyflow.LogState.{INFO,WARNING,ERROR}
        """

        self._requireInWorkflow()

        linePrefixOut = "[%s]" % (self._cdata().param.workflowClassName)
        self._cdata().flowLog(msg, linePrefix=linePrefixOut, logState=logState)

    # Protected methods for client derived-class override:

    def workflow(self):
        """
        Workflow definition defined in child class

        This method should be overridden in the class derived from
        L{WorkflowRunner} to specify the actual workflow logic. Client
        code should not call this method directly.
        """
        pass

    # private methods:

    # special workflowRunner Exception used to terminate workflow() function
    # if a ctrl-c is issued

    class _AbortWorkflowException(Exception):
        pass

    def _flowLog(self, msg, logState):
        linePrefixOut = "[WorkflowRunner]"
        self._cdata().flowLog(msg, linePrefix=linePrefixOut, logState=logState)

    def _infoLog(self, msg):
        self._flowLog(msg, logState=LogState.INFO)

    def _warningLog(self, msg):
        self._flowLog(msg, logState=LogState.WARNING)

    def _errorLog(self, msg):
        self._flowLog(msg, logState=LogState.ERROR)

    def _whoami(self):
        # returns name of *derived* class
        return self.__class__.__name__

    def _getNamespaceList(self):
        try:
            return self._namespaceList
        except AttributeError:
            self._namespaceList = []
            return self._namespaceList

    def _getNamespace(self):
        return namespaceSep.join(self._getNamespaceList())

    def _appendNamespace(self, names):
        names = lister(names)
        for name in names:
            # check against runaway recursion:
            if len(self._getNamespaceList()) >= WorkflowRunner._maxWorkflowRecursion:
                raise Exception(
                    "Recursive workflow invocation depth exceeds maximum allowed depth of %i" %
                    (WorkflowRunner._maxWorkflowRecursion))
            WorkflowRunner._checkTaskLabel(name)
            self._getNamespaceList().append(name)

    # flag used to request the termination of all task submission:
    #
    _allStop = threading.Event()

    @staticmethod
    def _stopAllWorkflows():
        # request all workflows stop task submission:
        WorkflowRunner._allStop.set()

    @staticmethod
    def _isWorkflowStopped():
        # check whether a global signal has been give to stop all workflow submission
        # this should only be true when a ctrl-C or similar event has occurred.
        return WorkflowRunner._allStop.isSet()

    def _addTaskCore(self, namespace, label, payload, dependencies):
        # private core addTask routine for hijacking
        # fromWorkflow is the workflow instance used to launch the task
        #

        # add workflow task to the task-dag, and launch a new taskrunner thread
        # if one isn't already running:
        if self._isWorkflowStopped():
            raise WorkflowRunner._AbortWorkflowException

        self._infoLog(
            "1 Adding %s '%s' to %s" %
            (payload.desc(),
             namespaceJoin(
                namespace,
                label),
                namespaceLabel(namespace)))

        # add task to the task-dag, and launch a new taskrunner thread
        # if one isn't already running:
        dependencies = setzer(dependencies)
        self._tdag.addTask(self._job_id, namespace, label, payload, dependencies)
        self._startTaskManager()

    def _getWaitStatus(self, namespace, labels, status):
        # update and return two values:
        # (1) isAllTaskDone -- are all tasks done (ie. error or complete state
        # (2) retval -- this is set to one if any tasks have errors
        #

        def updateStatusFromTask(task, status):
            """
            Update status
            """
            if not task.isDone():
                status.isAllTaskDone = False
            elif not task.isComplete():
                status.retval = 1

            if status.retval == 0 and (not self._cdata().isTaskSubmissionActive()):
                status.retval = 1

            if status.retval == 0 and task.isDead():
                status.retval = 1

        if len(labels) == 0:
            if namespace == "":
                if self._tdag.isRunExhausted() or (not self._tman.isAlive()):
                    if not self._tdag.isRunComplete():
                        status.retval = 1
                else:
                    status.isAllTaskDone = False
            else:
                for task in self._tdag.getAllNodes(namespace):
                    updateStatusFromTask(task, status)
        else:
            for l in labels:
                if not self._tdag.isTaskPresent(namespace, l):
                    raise Exception("Task: '%s' is not in taskDAG" % (namespaceJoin(namespace, l)))
                task = self._tdag.getTask(namespace, l)
                updateStatusFromTask(task, status)

    def _waitForTasksCore(self, namespace, labels=None, isVerbose=True):
        labels = setzer(labels)
        if isVerbose:
            msg = "Pausing %s until completion of" % (namespaceLabel(namespace))
            if len(labels) == 0:
                self._infoLog(msg + " its current tasks")
            else:
                self._infoLog(msg + " task(s): %s" % (",".join([namespaceJoin(namespace, l) for l in labels])))

        class WaitStatus(object):
            """
            WaitStatus class
            """

            def __init__(self):
                self.isAllTaskDone = True
                self.retval = 0

        ewaiter = ExpWaiter(1, 1.7, 15)
        while True:
            if self._isWorkflowStopped():
                raise WorkflowRunner._AbortWorkflowException
            status = WaitStatus()
            self._getWaitStatus(namespace, labels, status)
            if status.isAllTaskDone or (status.retval != 0):
                break
            ewaiter.wait()

        if isVerbose:
            msg = "Resuming %s" % (namespaceLabel(namespace))
            self._infoLog(msg)
        return status.retval

    def _isTaskCompleteCore(self, namespace, taskLabel):
        """
        @return: A boolean tuple specifying (task is done, task finished with error)
        """

        if not self._tdag.isTaskPresent(namespace, taskLabel):
            return (False, False)

        # Run a task harvest just before checking the task status
        # to help ensure the status is up to date
        self._tman.harvestTasks()

        task = self._tdag.getTask(namespace, taskLabel)
        return (task.isDone(), task.isError())

    def _cancelTaskTreeCore(self, namespace, taskLabel):
        if not self._tdag.isTaskPresent(namespace, taskLabel):
            return
        task = self._tdag.getTask(namespace, taskLabel)
        self._tman.cancelTaskTree(task)

    @staticmethod
    def _checkTaskLabel(label):
        # sanity check label:
        if not isinstance(label, basestring):
            raise Exception("Task label is not a string")
        if label == "":
            raise Exception("Task label is empty")
        if not re.match("^[A-Za-z0-9_-]+$", label):
            raise Exception("Task label is invalid due to disallowed characters. Label: '%s'" % (label))

    def _startTaskManager(self):
        # Start a new task manager if one isn't already running. If it is running
        # provide a hint that a new task has just been added to the workflow.
        #
        if (self._tman is not None) and (self._tman.isAlive()):
            self._tdag.isFinishedEvent.set()
            return
        if not self._cdata().isTaskManagerException:
            self._tman = TaskManager(self._cdata(), self._tdag)
            self._tman.start()

    def _notify(self, msg, logState):
        # msg is printed to log AND sent to any other requested
        # notification systems:
        self._flowLog(msg, logState)

    def _killWorkflow(self, errorMsg):
        self._notify(errorMsg, logState=LogState.ERROR)
        self._shutdownAll(timeoutSec=10)
        sys.exit(1)

    def _shutdownAll(self, timeoutSec):
        # Try to shut down the task manager, all command-tasks,
        # and all sub-workflow tasks.
        #
        if (self._tman is None) or (not self._tman.isAlive()):
            return
        StoppableThread.stopAll()
        self._stopAllWorkflows()
        self._tman.stop()
        for _ in range(timeoutSec):
            time.sleep(1)
            if not self._tman.isAlive():
                self._infoLog("Task shutdown complete")
                return
        self._infoLog("Task shutdown timed out")

    def _cdata(self):
        # We're doing this convoluted setup only to avoid having a
        # ctor for ease of use by the client. See what pyFlow goes
        # through for you client code??
        #
        try:
            return self._constantData
        except AttributeError:
            self._constantData = WorkflowRunnerThreadSharedData()
            return self._constantData

    # TODO: Better definition of the status thread shutdown at the end of a pyflow run to
    # prevent race conditions -- ie. what happens if the status update is running while
    # pyflow is shutting down? Every method called by the status updater should be safety
    # checked wrt this issue.
    #

    def _runUpdate(self, runStatus):
        while True:
            time.sleep(self.updateInterval * 60)

            status = self._tdag.getTaskStatus()
            isSpecComplete = (runStatus.isSpecificationComplete.isSet() and status.isAllSpecComplete)
            report = []
            report.append("===== " + self._whoami() + " StatusUpdate =====")
            report.append("Workflow specification is complete?: %s" % (str(isSpecComplete)))
            report.append("Task status (waiting/queued/started/finished/failed): %i/%i/%i/%i/%i"
                          % (status.waiting, status.queued, status.started, status.finished, status.failed))
            report.append("Longest ongoing queued task time (hrs): %.4f" % (status.longestQueueSec / 3600.))
            report.append("Longest ongoing queued task name: '%s'" % (status.longestQueueName))
            report.append("Longest ongoing running task time (hrs): %.4f" % (status.longestRunSec / 3600.))
            report.append("Longest ongoing running task name: '%s'" % (status.longestRunName))

            report = ["[StatusUpdate] " + line for line in report]
            self._infoLog(report)

    def _runWorkflow(self, param):
        #
        # Primary workflow logic when nothing goes wrong:
        #
        self._setupWorkflow(param)
        self._initMessage()

        runStatus = RunningTaskStatus(self._tdag.isFinishedEvent)

        # start status update reporter:
        #
        # TODO: stop this thread at end of run
        #
        if(self.updateInterval > 0):
            hb = threading.Thread(target=WorkflowRunner._runUpdate, args=(self, runStatus))
            hb.setDaemon(True)
            hb.setName("StatusUpdate-Thread")
            hb.start()

        # run workflow() function on a separate thread, using exactly
        # the same method we use for sub-workflows:
        #
        # TODO: move the master workflow further into the code path used by sub-workflows,
        # so that we aren't replicating polling and error handling code in this function:
        #
        trun = WorkflowTaskRunner(runStatus, "masterWorkflow", self, self._cdata().flowLog, None)
        trun.start()
        # can't join() because that blocks SIGINT
        ewaiter = ExpWaiter(1, 1.7, 15, runStatus.isComplete)

        def isWorkflowRunning():
            """
            Return true so long as the primary workflow threads (TaskRunner and TaskManager)
            are still alive
            """
            return trun.isAlive() or ((self._tman is not None) and self._tman.isAlive())

        while isWorkflowRunning():
            ewaiter.wait()

        if not runStatus.isComplete.isSet():
            # if not complete then we don't know what happened, very bad!:
            runStatus.errorCode = 1
            runStatus.errorMessage = "Thread: '%s', has stopped without a traceable cause" % (trun.getName())

        return self._evalWorkflow(runStatus)

    def _setupWorkflow(self, param):
        cdata = self._cdata()

        # setup instance user parameters:
        cdata.setupNewRun(param)

        # setup other instance data:
        self._tdag = TaskDAG(cdata.param.isContinue, cdata.param.isForceContinue, cdata.param.isDryRun,
                             cdata.param.workflowClassName,
                             cdata.param.startFromTasks, cdata.param.ignoreTasksAfter, cdata.param.resetTasks,
                             self._flowLog)
        self._tman = None

        if cdata.param.isContinue:
            # Make workflow changes required when resuming after an interrupt, where the client has requested the
            # workflow continue from where it left off (ie. 'isContinued')
            self._tdag.setupContinuedWorkflow()

    def _initMessage(self):
        param = self._cdata().param  # shortcut
        msg = ["Init---------------------------------------------"]
        msg.append("Initiating pyFlow run")
        msg.append("pyFlowClientWorkflowClass: %s" % (param.workflowClassName))
        msg.append("pyFlowVersion: %s" % (__version__))
        msg.append("pythonVersion: %s" % (pythonVersion))
        msg.append("WorkingDir: '%s'" % (self._cdata().cwd))
        msg.append("ProcessCmdLine: '%s'" % (cmdline()))

        parammsg = ["mode: %s" % (param.mode),
                    "nCores: %s" % (str(param.nCores)),
                    "memMb: %s" % (str(param.memMb)),
                    "dataDir: %s" % (str(param.dataDir)),
                    "isDryRun: %s" % (str(param.isDryRun)),
                    "isContinue: %s" % (str(param.isContinue)),
                    "isForceContinue: %s" % (str(param.isForceContinue)),
                    ]
        for i in range(len(parammsg)):
            parammsg[i] = "[RunParameters] " + parammsg[i]
        msg += parammsg
        msg.append("Init---------------------------------------------end")
        self._infoLog(msg)

    def _getTaskErrorsSummaryMsg(self, isForceTaskHarvest=False):
        # isForceHarvest means we try to force an update of the shared
        # taskError information in case this thread is ahead of the
        # task manager.
        if isForceTaskHarvest:
            if (self._tman is not None) and (self._tman.isAlive()):
                self._tman.harvestTasks()

        if not self._cdata().isTaskError():
            return []
        # this case has already been in the TaskManager @ first error occurrence:
        msg = ["Worklow terminated due to the following task errors:"]
        for task in self._cdata().taskErrors:
            msg.extend(task.getTaskErrorMsg())
        return msg

    def _evalWorkflow(self, masterRunStatus):

        isError = False
        if self._cdata().isTaskError():
            msg = self._getTaskErrorsSummaryMsg()
            self._errorLog(msg)
            isError = True

        if masterRunStatus.errorCode != 0:
            eMsg = lister(masterRunStatus.errorMessage)
            if (len(eMsg) > 1) or (len(eMsg) == 1 and eMsg[0] != ""):
                msg = ["Failed to complete master workflow, error code: %s" % (str(masterRunStatus.errorCode))]
                msg.append("errorMessage:")
                msg.extend(eMsg)
                self._notify(msg, logState=LogState.ERROR)
            isError = True

        if self._cdata().isTaskManagerException:
            self._errorLog("Workflow terminated due to unhandled exception in TaskManager")
            isError = True

        if (not isError) and (not self._tdag.isRunComplete()):
            msg = "Workflow terminated with unknown error condition"
            self._notify(msg, logState=LogState.ERROR)
            isError = True

        if isError:
            return 1

        elapsed = int(time.time() - self.runStartTimeStamp)
        msg = []
        if self._cdata().param.successMsg is not None:
            msg.extend([self._cdata().param.successMsg, ""])
        msg.extend(["Workflow successfully completed all tasks",
                    "Elapsed time for full workflow: %s sec" % (elapsed)])
        self._notify(msg, logState=LogState.INFO)

        return 0

    def _requireInWorkflow(self):
        """
        check that the calling method is being called as part of a pyflow workflow() method only
        """
        if not self._getRunning():
            raise Exception(
                "Method must be a (call stack) descendant of WorkflowRunner workflow() method (via run() method)")

    def _initRunning(self):
        try:
            assert(self._isRunning >= 0)
        except AttributeError:
            self._isRunning = 0

    @lockMethod
    def _setRunning(self, isRunning):
        self._initRunning()
        if isRunning:
            self._isRunning += 1
        else:
            self._isRunning -= 1

    @lockMethod
    def _getRunning(self):
        self._initRunning()
        return (self._isRunning > 0)


if __name__ == "__main__":
    help(WorkflowRunner)
