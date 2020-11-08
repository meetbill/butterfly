# coding=utf8
"""
# File Name: optionfile.py
# Description:

"""
from ._compat import PY2

if PY2:
    import ConfigParser as configparser
else:
    import configparser


class Parser(configparser.RawConfigParser):
    """
    解析配置
    """
    def __init__(self, **kwargs):
        kwargs['allow_no_value'] = True
        configparser.RawConfigParser.__init__(self, **kwargs)

    def __remove_quotes(self, value):
        quotes = ["'", "\""]
        for quote in quotes:
            if len(value) >= 2 and value[0] == value[-1] == quote:
                return value[1:-1]
        return value

    def get(self, section, option):
        """
        获取配置
        """
        value = configparser.RawConfigParser.get(self, section, option)
        return self.__remove_quotes(value)
