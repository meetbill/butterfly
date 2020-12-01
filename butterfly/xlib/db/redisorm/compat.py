# -*- coding: utf-8 -*-
import sys

# --- py3k compatibility (copied and inspired by six)
PY3 = sys.version_info[0] == 3
if PY3:
    xrange = range
    text = str
    binary = bytes

    def b(s):
        return s.encode("latin-1")
else:
    xrange = xrange
    text = unicode
    binary = str

    def b(s):
        return str(s)


def u(b):
    if isinstance(b, binary):
        return b.decode('latin-1')
    return b
