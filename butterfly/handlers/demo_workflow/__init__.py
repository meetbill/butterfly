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
        self.addTask("easy_task1", "echo 'Hello World!'")
        self.addTask("easy_task2", "sleep 20", dependencies="easy_task1")

@funcattr.api
def helloworld(req):
    """
    Args:
        req     : Request
    Returns:
        json_status, Content, headers
    """
    isinstance(req, Request)
    wflow = HelloWorkflow()
    retval = wflow.run(dataDirRoot="data/workflow/{jobid}".format(jobid=req.reqid),
            isQuiet=True,
            job_reqid = req.reqid,
            job_name = "ceshi"
            )
    if retval == 0:
        return retstat.OK, {}, [(__info, __version)]
    else:
        return retstat.ERR, {}, [(__info, __version)]
