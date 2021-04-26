#!/usr/bin/python
# coding=utf8
"""
translate
"""
from __future__ import absolute_import, unicode_literals


try:
    from django.utils.translation import ugettext
except Exception:
    def ugettext(text):
        """
        If there is no Django package, the original string will be returned directly

        Args:
            text
        Returns
            text
        """
        return text
