#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill
# Created Time : 2019-08-07 16:53:27

# File Name: auth
# Description:

"""

from base64 import b64encode
import os
import threading
import time
import uuid
import traceback

import jwt


class Result(object):
    """
    Auth result
    """
    def __init__(self, retcode=None, err_info=None,token_info=None):
        self.retcode = retcode
        self.err_content = (retcode,{"stat": "ERR", "err_info": err_info})
        self.token_info = token_info
        self.success = False
        if retcode == 0:
            self.success = True


class JwtManager(object):
    JWT_TOKEN_TTL = 28800  # default 8 hours
    JWT_ALGORITHM = 'HS256'
    _secret = None

    LOCAL_USER = threading.local()

    @staticmethod
    def _gen_secret():
        secret = os.urandom(16)
        return b64encode(secret).decode('utf-8')

    @classmethod
    def init(cls, secret=None):
        # generate a new secret if it does not exist
        if secret is None:
            secret = cls._gen_secret()
        cls._secret = secret

    @classmethod
    def gen_token(cls, username):
        if not cls._secret:
            cls.init()
        ttl = cls.JWT_TOKEN_TTL
        ttl = int(ttl)
        now = int(time.time())
        payload = {
            'iss': 'butterfly',
            'jti': str(uuid.uuid4()),
            'exp': now + ttl,
            'iat': now,
            'username': username
        }
        return jwt.encode(payload, cls._secret, algorithm=cls.JWT_ALGORITHM)

    @classmethod
    def decode_token(cls, token):
        if not cls._secret:
            cls.init()
        return jwt.decode(token, cls._secret, algorithms=cls.JWT_ALGORITHM)

    @classmethod
    def get_token_from_header(cls, req):
        # header = authorization
        auth_header = ('HTTP_AUTHORIZATION' in req.wsgienv and [req.wsgienv['HTTP_AUTHORIZATION']] or [None])[0]
        if auth_header is not None:
            scheme, params = auth_header.split(' ', 1)
            # ("Authorization","Bearer: {}".format(token))
            if scheme.lower() == 'bearer:':
                return params
        return None

    @classmethod
    def set_user(cls, token):
        cls.LOCAL_USER.username = token['username']

    @classmethod
    def reset_user(cls):
        cls.set_user({'username': None, 'permissions': None})

    @classmethod
    def get_username(cls):
        return getattr(cls.LOCAL_USER, 'username', None)


def gen_token(username):
    """
    Args:
        username:username
    Returns:
        token
    """
    return JwtManager.gen_token(username)


def is_token_valid(req):
    """
    Args:
        req: Request
    Returns:
        Result:(instance)
    """
    # 从 req 中获取 token
    JwtManager.reset_user()
    token = JwtManager.get_token_from_header(req)
    if not token:
        return Result(retcode=401, err_info="You are not authorized")
    try:
        token_info = JwtManager.decode_token(token)
        return Result(retcode=0,token_info=token_info)
    except jwt.exceptions.ExpiredSignatureError:
        return Result(retcode=401, err_info="Token has expired")
    except jwt.exceptions.InvalidTokenError:
        return Result(retcode=401, err_info="Failed to decode token")
    except Exception:
        return Result(retcode=401, err_info=traceback.format_exc())

if __name__ == "__main__":
    token = gen_token("meetbill")
    print "gen_token:{token}".format(token=token)
    import sys
    sys.path.append("..")
    import httpgateway
    reqid="ceshi"
    wsgienv = {}
    wsgienv["HTTP_AUTHORIZATION"] = "Bearer: {}".format(token)
    ip = "127.0.0.1"
    req = httpgateway.Request(reqid, wsgienv, ip)
    token_status = is_token_valid(req)
    if token_status.success:
        print token_status.token_info
        print "token:OK"
    else:
        print token_status.err_content