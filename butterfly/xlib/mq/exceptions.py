# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class NoSuchMsgError(Exception):
    pass


class InvalidMsgOperation(Exception):
    pass


class UnpickleError(Exception):
    def __init__(self, message, raw_data, inner_exception=None):
        super(UnpickleError, self).__init__(message, inner_exception)
        self.raw_data = raw_data

class TimeoutFormatError(Exception):
    pass
