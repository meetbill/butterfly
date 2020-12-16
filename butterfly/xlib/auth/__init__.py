#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2019-08-07 16:53:27

# File Name: auth
# Description:

"""

import os
import threading
import time
import uuid
import traceback
import base64

from xlib.auth import jwt
from conf import config


class Result(object):
    """
    Auth result
    """
    def __init__(self, retcode=None, message=None, token_info=None):
        self.retcode = retcode
        self.err_content = (retcode, {"success": False, "message": message})
        self.token_info = token_info
        self.success = False
        if retcode == 0:
            self.success = True


class JwtManager(object):
    """
    JWT manager

    Attributes:
        JWT_ALGORITHM: JWT 签名算法(HS256/RS256)
        JWT_TOKEN_TTL: Token 有效时间
        _secret: 密钥
    """
    JWT_ALGORITHM = 'HS256'
    JWT_TOKEN_TTL = config.JWT_TOKEN_TTL
    _secret = config.SECRET_KEY

    LOCAL_USER = threading.local()

    @staticmethod
    def _gen_secret():
        """gen secret"""
        secret = os.urandom(16)
        return base64.b64encode(secret).decode('utf-8')

    @classmethod
    def init(cls, secret=None):
        """JwtManager init"""
        # generate a new secret if it does not exist
        if secret is None:
            secret = cls._gen_secret()
        cls._secret = secret

    @classmethod
    def gen_token(cls, username):
        """gen_token
        Args:
            username: 用户名
        Returns:
            token
        """
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
        """decode_token"""
        if not cls._secret:
            cls.init()
        return jwt.decode(token, cls._secret, algorithms=cls.JWT_ALGORITHM)

    @classmethod
    def get_token_from_header(cls, req):
        """get token from butterfly header"""

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
        """set_user"""
        cls.LOCAL_USER.username = token['username']

    @classmethod
    def reset_user(cls):
        """reset_user"""
        cls.set_user({'username': None, 'permissions': None})

    @classmethod
    def get_username(cls):
        """get username"""
        return getattr(cls.LOCAL_USER, 'username', None)


def gen_token(username):
    """gen_token
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
        return Result(retcode=401, message="You are not authorized: Not found token")
    try:
        token_info = JwtManager.decode_token(token)
        return Result(retcode=0, token_info=token_info)
    except jwt.exceptions.ExpiredSignatureError:
        return Result(retcode=401, message="You are not authorized: Token has expired")
    except jwt.exceptions.InvalidTokenError:
        return Result(retcode=401, message="You are not authorized: Failed to decode token")
    except Exception:
        return Result(retcode=401, message=traceback.format_exc())

if __name__ == "__main__":
    # 根据用户名生成用户 token
    token = gen_token("meetbill")
    print "gen_token:{token}".format(token=token)

    # 检验生成的 token 是否有效
    import sys
    sys.path.append("..")
    import httpgateway
    reqid="ceshi"
    wsgienv = {}
    wsgienv["HTTP_AUTHORIZATION"] = "Bearer: {}".format(token)
    ip = "127.0.0.1"
    req = httpgateway.Request(reqid, wsgienv, ip)

    token_check = is_token_valid(req)
    if token_check.success:
        print token_check.token_info
        """
        {
            u'iss': u'butterfly',
            u'iat': 1574092901,
            u'username': u'meetbill',
            u'jti': u'5e7bde9b-1a22-4ad3-b0e8-845cb4dc9459',
            u'exp': 1574121701}
        """
        print "token:OK"
    else:
        print token_check.err_content
