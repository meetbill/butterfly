# coding=utf8
"""
# Description:
    workflow
"""

from xlib.httpgateway import Request
from xlib import retstat
from xlib.middleware import funcattr
from xlib.pyflow import WorkflowRunner

__info = "demo"
__version = "1.0.1"


class HelloWorkflow(WorkflowRunner):
    """
    a workflow is defined by overloading the WorkflowRunner.workflow() method:
    """

    def workflow(self):
        """
        The output for this task will be written to the file helloWorld.out.txt
        """
        self.addTask("easy_task1", "echo 'Hello World!' > helloWorld.out.txt; sleep 20")
        self.addTask("easy_task2", "sleep 20", dependencies="easy_task1")


@funcattr.api
def helloworld(req, jobid=None):
    """
    Args:
        req     : Request
        jobid   : (String) 若 jobid 不是 None，则会继续 jobid 的任务
    Returns:
        json_status, Content, headers
    """
    isinstance(req, Request)
    wflow = HelloWorkflow()
    if jobid is None:
        retval = wflow.run(dataDirRoot="data/workflow/{jobid}".format(jobid=req.reqid), isQuiet=True)
    else:
        retval = wflow.run(dataDirRoot="data/workflow/{jobid}".format(jobid=jobid), isContinue=True, isQuiet=True)
    if retval == 0:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR, {}, [(__info, __version)]
