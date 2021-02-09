from __future__ import absolute_import

from threading import Event

from xlib.apscheduler.schedulers.base import BaseScheduler, STATE_STOPPED
from xlib.apscheduler.util import TIMEOUT_MAX


class BlockingScheduler(BaseScheduler):
    """
    A scheduler that runs in the foreground
    (:meth:`~apscheduler.schedulers.base.BaseScheduler.start` will block).
    """
    _event = None

    def start(self, *args, **kwargs):
        """
        start scheduler
        """
        # https://github.com/agronholm/apscheduler/issues/441
        if self._event is None or self._event.is_set():
            self._event = Event()
        super(BlockingScheduler, self).start(*args, **kwargs)
        self._main_loop()

    def shutdown(self, wait=True):
        """
        shutdown scheduler
        """
        super(BlockingScheduler, self).shutdown(wait)
        self._event.set()

    def _main_loop(self):
        wait_seconds = TIMEOUT_MAX
        while self.state != STATE_STOPPED:
            self._event.wait(wait_seconds)
            self._event.clear()
            wait_seconds = self._process_jobs()

    def wakeup(self):
        """
        wakeup
        """
        self._event.set()
