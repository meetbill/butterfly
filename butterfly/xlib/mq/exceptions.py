# coding=utf8
"""
# File Name: exceptions.py
# Description:

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class NoSuchMsgError(Exception):
    """
    NoSuchMsgError
    """
    pass


class InvalidMsgOperation(Exception):
    """
    InvalidMsgOperation
    """
    pass


class UnpickleError(Exception):
    """
    UnpickleError
    """
    def __init__(self, message, raw_data, inner_exception=None):
        super(UnpickleError, self).__init__(message, inner_exception)
        self.raw_data = raw_data

class TimeoutFormatError(Exception):
    """
    TimeoutFormatError
    """
    pass
