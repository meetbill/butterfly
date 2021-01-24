#!/usr/bin/python
# coding=utf8
"""
# File Name: pool.py
# Description:
    执行器线程池/进程池管理
"""
from abc import abstractmethod
from xlib.util import concurrent

from xlib.apscheduler.executors.base import BaseExecutor, run_job


class BasePoolExecutor(BaseExecutor):
    """
    BasePoolExecutor class
    """
    @abstractmethod
    def __init__(self, pool):
        super(BasePoolExecutor, self).__init__()
        self._pool = pool

    def _do_submit_job(self, job, run_times):
        def callback(f):
            """
            job callback func
            """
            exc, tb = (f.exception_info() if hasattr(f, 'exception_info') else
                       (f.exception(), getattr(f.exception(), '__traceback__', None)))
            if exc:
                self._run_job_error(job.id, exc, tb)
            else:
                self._run_job_success(job.id, f.result())

        f = self._pool.submit(run_job, job, job._jobstore_alias, run_times, self._logger.name)
        f.add_done_callback(callback)

    def shutdown(self, wait=True):
        """
        pool shutdown func
        """
        self._pool.shutdown(wait)


class ThreadPoolExecutor(BasePoolExecutor):
    """
    An executor that runs jobs in a concurrent.futures thread pool.

    Plugin alias: ``threadpool``

    :param max_workers: the maximum number of spawned threads.
    """

    def __init__(self, max_workers=10):
        pool = concurrent.ThreadPoolExecutor(int(max_workers))
        super(ThreadPoolExecutor, self).__init__(pool)


class ProcessPoolExecutor(BasePoolExecutor):
    """
    An executor that runs jobs in a concurrent.futures process pool.

    Plugin alias: ``processpool``

    :param max_workers: the maximum number of spawned processes.
    """

    def __init__(self, max_workers=10):
        pool = concurrent.ProcessPoolExecutor(int(max_workers))
        super(ProcessPoolExecutor, self).__init__(pool)
