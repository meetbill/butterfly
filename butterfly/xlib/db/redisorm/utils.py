# coding=utf8
"""
# File Name: util.py
# Description:

"""
import os
import re
import sys


PY3 = sys.version_info[0] == 3

if PY3:
    unicode_type = str
    basestring_type = (str, bytes)
    def exception_message(exc):
        """
        Return exe message
        """
        return exc.args[0]
else:
    unicode_type = unicode
    basestring_type = basestring
    def exception_message(exc):
        """
        Return exe message
        """
        return exc.message


def encode(s):
    """
    encode
    """
    return s.encode('utf-8') if isinstance(s, unicode_type) else s


def decode(s):
    """
    decode
    """
    return s.decode('utf-8') if isinstance(s, bytes) else s


def decode_dict(d):
    """
    Decode dict
    """
    accum = {}
    for key in d:
        accum[decode(key)] = decode(d[key])
    return accum


def safe_decode_list(l):
    """
    Return a list
    """
    return [i.decode('raw_unicode_escape') if isinstance(i, bytes) else i
            for i in l]


def decode_dict_keys(d):
    """
    decode_dict_keys
    """
    accum = {}
    for key in d:
        accum[decode(key)] = d[key]
    return accum


def make_python_attr(s):
    """
    make_python_attr
    """
    if isinstance(s, bytes):
        s = decode(s)
    s = re.sub('[^\w]+', '_', s)
    if not s:
        raise ValueError('cannot construct python identifer from "%s"' % s)
    if s[0].isdigit():
        s = '_' + s
    return s.lower()


class Memoize(dict):
    """
    Memoize class
    """
    def __init__(self, fn):
        self._fn = fn

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self._fn(*key)
        return result


@Memoize
def load_stopwords(stopwords_file):
    """
    load_stopwords from file
    """
    path, filename = os.path.split(stopwords_file)
    if not path:
        path = os.path.dirname(__file__)
    filename = os.path.join(path, filename)
    if not os.path.exists(filename):
        return

    with open(filename) as fh:
        return fh.read()
