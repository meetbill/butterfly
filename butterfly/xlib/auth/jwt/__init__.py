# -*- coding: utf-8 -*-
# flake8: noqa

"""
JSON Web Token implementation

Minimum implementation based on this spec:
http://self-issued.info/docs/draft-jones-json-web-token-01.html
"""


__title = 'pyjwt'
__version = '1.7.1'
__author = 'Jose Padilla'
__license = 'MIT'
__copyright = 'Copyright 2015-2018 Jose Padilla'


from .api_jwt import (
    encode, decode, register_algorithm, unregister_algorithm,
    get_unverified_header, PyJWT
)
from .api_jws import PyJWS
from .exceptions import (
    InvalidTokenError, DecodeError, InvalidAlgorithmError,
    InvalidAudienceError, ExpiredSignatureError, ImmatureSignatureError,
    InvalidIssuedAtError, InvalidIssuerError, ExpiredSignature,
    InvalidAudience, InvalidIssuer, MissingRequiredClaimError,
    InvalidSignatureError,
    PyJWTError,
)
