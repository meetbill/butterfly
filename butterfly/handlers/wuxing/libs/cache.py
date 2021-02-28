#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34
# Created Time : 2021-02-14 11:25:03

# File Name: cache.py
# Description:
    实际存储在 redis 中的 key 会加 "cache:" 前缀

"""
from xlib import db
from xlib.db.redis import exceptions


class Cache(object):
    """
    wuxing cache
    """
    wuxing_database_name = "wuxing"
    if wuxing_database_name in db.my_caches.keys():
        __wuxing_db = db.my_caches[wuxing_database_name]
        _cache = __wuxing_db.cache()
    else:
        _cache = None

    _del_log_template = "<{key}>del={status}"
    _set_log_template = "<{key}>set={status}"
    _get_log_template = "<{key}>get={status}"

    @classmethod
    def set(cls, subreq, key, value, timeout=None):
        """
        Args:
            subreq  : (object) Request
            key     : (str)
            value   : (str/int/float/dict)
            timeout : (int)
        Returns:
            bool
        """
        if cls._cache is None:
            subreq.log_res.add("cache=false")
            return False
        else:
            connection_kwargs = cls._cache.database.connection_pool.connection_kwargs
            addr = "{host}:{port}".format(host=connection_kwargs["host"], port=connection_kwargs["port"])
            subreq.log_res.add("cache={addr}".format(addr=addr))

        subreq.start_timming()
        try:
            result = cls._cache.set(key, value, timeout)
            subreq.log_res.add(cls._set_log_template.format(key=key, status="OK"))
            subreq.timming("redis_set_cost")
            return result
        except exceptions.TimeoutError as e:
            # 连接超时: "Timeout connecting to server"
            if "connecting" in e.message:
                subreq.log_res.add(cls._set_log_template.format(key=key, status="connection_timeout"))
            else:
                subreq.log_res.add(cls._set_log_template.format(key=key, status="write_timeout"))
        except exceptions.ConnectionError:
            subreq.log_res.add(cls._set_log_template.format(key=key, status="connection_error"))

        subreq.timming("redis_set_cost")
        return False

    @classmethod
    def get(cls, subreq, key):
        """
        Args:
            subreq  : (object) Request
            key     : (str) key
        Returns:
            result
        """
        if cls._cache is None:
            subreq.log_res.add("cache=false")
            return None
        else:
            connection_kwargs = cls._cache.database.connection_pool.connection_kwargs
            addr = "{host}:{port}".format(host=connection_kwargs["host"], port=connection_kwargs["port"])
            subreq.log_res.add("cache={addr}".format(addr=addr))

        subreq.start_timming()
        try:
            result = cls._cache.get(key)
            subreq.log_res.add(cls._get_log_template.format(key=key, status="OK"))
            subreq.timming("redis_get_cost")
            return result
        except exceptions.TimeoutError as e:
            # 连接超时: "Timeout connecting to server"
            if "connecting" in e.message:
                subreq.log_res.add(cls._get_log_template.format(key=key, status="connection_timeout"))
            else:
                subreq.log_res.add(cls._get_log_template.format(key=key, status="read_timeout"))
        except exceptions.ConnectionError:
            subreq.log_res.add(cls._get_log_template.format(key=key, status="connection_error"))

        subreq.timming("redis_get_cost")
        return None

    @classmethod
    def delete(cls, subreq, key):
        """
        Args:
            subreq  : (object) Request
            key     : (str) key
        Returns:
            Bool
        """
        if cls._cache is None:
            subreq.log_res.add("cache=false")
            return False
        else:
            connection_kwargs = cls._cache.database.connection_pool.connection_kwargs
            addr = "{host}:{port}".format(host=connection_kwargs["host"], port=connection_kwargs["port"])
            subreq.log_res.add("cache={addr}".format(addr=addr))

        subreq.start_timming()
        try:
            result = cls._cache.delete(key)
            subreq.log_res.add(cls._del_log_template.format(key=key, status="OK"))
            subreq.timming("redis_del_cost")
            return result
        except exceptions.TimeoutError as e:
            # 连接超时: "Timeout connecting to server"
            if "connecting" in e.message:
                subreq.log_res.add(cls._del_log_template.format(key=key, status="connection_timeout"))
            else:
                subreq.log_res.add(cls._del_log_template.format(key=key, status="delete_timeout"))
        except exceptions.ConnectionError:
            subreq.log_res.add(cls._del_log_template.format(key=key, status="connection_error"))

        subreq.timming("redis_del_cost")
        return False


if __name__ == "__main__":
    from xlib import httpgateway
    from xlib import uuid64

    def gen_req():
        """
        gen req
        """
        ip = "0.0.0.0"
        reqid = uuid64.UUID64().gen()
        wsgienv = {"PATH_INFO": "/echo"}
        req = httpgateway.Request(reqid, wsgienv, ip)
        return req

    def print_log(req):
        """
        打印日志信息
        """
        talk_str = ",".join("%s=%.3f" % (k, v) for k, v in req.log_talk.iteritems())
        print "reqid:{reqid}\ttalk:{talk}\tres:{res}".format(
            reqid=req.reqid,
            talk=talk_str,
            res=",".join(req.log_res))

    req = gen_req()
    print Cache.set(req, 'foo', 'bar', 10)  # Set foo=bar, expiring in 10s.
    print_log(req)

    req = gen_req()
    print Cache.get(req, 'foo')
    print_log(req)

    import time
    time.sleep(10)
    req = gen_req()
    print Cache.get(req, 'foo')
    print_log(req)

    # -------------------------------------------dict
    req = gen_req()
    value_dict = {}
    value_dict["ceshi"] = "test_info"
    print Cache.set(req, 'foo', value_dict, 10)  # Set foo=bar, expiring in 10s.
    print_log(req)

    req = gen_req()
    result = Cache.get(req, 'foo')
    assert result == value_dict
    print_log(req)

    # -------------------------------------------int
    req = gen_req()
    value_int = 20
    print Cache.set(req, 'foo', value_int, 10)  # Set foo=bar, expiring in 10s.
    print_log(req)

    req = gen_req()
    result = Cache.get(req, 'foo')
    assert result == value_int
    print_log(req)

    # -------------------------------------------delete
    print "--------------------------------------delete"
    req = gen_req()
    value_int = 20
    print Cache.set(req, 'foo', value_int, 3600)  # Set foo=bar, expiring in 10s.
    print_log(req)

    req = gen_req()
    result = Cache.get(req, 'foo')
    assert result == value_int
    print_log(req)

    req = gen_req()
    result = Cache.delete(req, 'foo')
    assert result == True
    print_log(req)

    req = gen_req()
    result = Cache.get(req, 'foo')
    assert result is None
    print_log(req)
