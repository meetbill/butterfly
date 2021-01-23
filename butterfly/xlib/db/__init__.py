#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-05-27 14:49:50

# File Name: __init__.py
# Description:
    封装管理 MySQL/Redis 相关接口

"""
try:
    from urlparse import parse_qsl, unquote, urlparse
except ImportError:
    # Python 3.0
    from urllib.parse import parse_qsl, unquote, urlparse

from xlib.db import peewee
from xlib.db import redisorm
from xlib.db.pool import PooledMySQLDatabase
from xlib.db.shortcuts import ReconnectMixin
from conf import config


###############################################################
# MySQL
###############################################################

class RetryPooledMySQLDatabase(ReconnectMixin, PooledMySQLDatabase):
    """
    retry connect
    """
    pass


schemes = {
    'mysql': peewee.MySQLDatabase,
    'mysql+pool': PooledMySQLDatabase,
    'mysql+retrypool': RetryPooledMySQLDatabase,
    'sqlite': peewee.SqliteDatabase,
}


def _parseresult_to_dict(parsed, unquote_password=False):

    # urlparse in python 2.6 is broken so query will be empty and instead
    # appended to path complete with '?'
    path_parts = parsed.path[1:].split('?')
    try:
        query = path_parts[1]
    except IndexError:
        query = parsed.query

    connect_kwargs = {'database': path_parts[0]}
    if parsed.username:
        connect_kwargs['user'] = parsed.username
    if parsed.password:
        connect_kwargs['password'] = parsed.password
        if unquote_password:
            connect_kwargs['password'] = unquote(connect_kwargs['password'])
    if parsed.hostname:
        connect_kwargs['host'] = parsed.hostname
    if parsed.port:
        connect_kwargs['port'] = parsed.port

    # Adjust parameters for MySQL.
    if parsed.scheme == 'mysql' and 'password' in connect_kwargs:
        connect_kwargs['passwd'] = connect_kwargs.pop('password')
    elif 'sqlite' in parsed.scheme and not connect_kwargs['database']:
        connect_kwargs['database'] = ':memory:'

    # Get additional connection args from the query string
    qs_args = parse_qsl(query, keep_blank_values=True)
    for key, value in qs_args:
        if value.lower() == 'false':
            value = False
        elif value.lower() == 'true':
            value = True
        elif value.isdigit():
            value = int(value)
        elif '.' in value and all(p.isdigit() for p in value.split('.', 1)):
            try:
                value = float(value)
            except ValueError:
                pass
        elif value.lower() in ('null', 'none'):
            value = None

        connect_kwargs[key] = value

    return connect_kwargs


def connect(url, unquote_password=False, **connect_params):
    """
    MySQL connect

    Args:
        url: url config
             Example: "mysql+retrypool://root:password@127.0.0.1:3306/test?max_connections=300&stale_timeout=300"
    Returns:
        instance
    """
    parsed = urlparse(url)
    connect_kwargs = _parseresult_to_dict(parsed, unquote_password)
    connect_kwargs.update(connect_params)
    database_class = schemes.get(parsed.scheme)

    if database_class is None:
        if database_class in schemes:
            raise RuntimeError('Attempted to use "%s" but a required library '
                               'could not be imported.' % parsed.scheme)
        else:
            raise RuntimeError('Unrecognized or unsupported scheme: "%s".' %
                               parsed.scheme)

    return database_class(**connect_kwargs)


my_databases = {}
for database_name in config.DATABASES.keys():
    my_databases[database_name] = connect(url=config.DATABASES[database_name])

class BaseModel(peewee.Model):
    """Common base model"""
    class Meta(object):
        """Meta class"""
        database = my_databases["default"]

###############################################################
# Redis
###############################################################
my_caches = {}
for cache_name in config.CACHES.keys():
    my_caches[cache_name] = redisorm.Database.from_url(config.CACHES[cache_name])

class RedisModel(redisorm.Model):
    """
    Common Redis base model
    """
    _database_ = my_caches["default"]

if __name__ == "__main__":
    mysql_config_url = "mysql+pool://root:password@127.0.0.1:3306/test?max_connections=300&stale_timeout=300"
    parsed = urlparse(mysql_config_url)
    """_parseresult_to_dict(parsed)
    {
        'database': 'test',
        'host': '127.0.0.1',
        'user': 'root',
        'stale_timeout': 300,
        'password': 'password',
        'port': 3306,
        'max_connections': 300
    }
    """
    print _parseresult_to_dict(parsed)
