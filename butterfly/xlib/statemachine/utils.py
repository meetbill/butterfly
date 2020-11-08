#!/usr/bin/python
# coding=utf8
"""
国际化处理
"""
from __future__ import absolute_import, unicode_literals


try:
    from django.utils.translation import ugettext
except Exception:
    def ugettext(text):
        """ 没有 django 包的话，则直接返回原字符串
        Args:
            text
        Returns
            text
        """
        return text
