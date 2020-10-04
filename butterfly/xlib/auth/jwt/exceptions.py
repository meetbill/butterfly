# coding=utf8
"""
# Description
    JWT 异常
"""
class PyJWTError(Exception):
    """
    Base class for all exceptions
    """
    pass


class InvalidTokenError(PyJWTError):
    """
    无效 token
    """
    pass


class DecodeError(InvalidTokenError):
    """
    解码 token 异常
    """
    pass


class InvalidSignatureError(DecodeError):
    """
    无效签名
    """
    pass


class ExpiredSignatureError(InvalidTokenError):
    """
    签名过期
    exp 指过期时间，在生成 token 时，可以设置该 token 的有效时间，如果我们设置 1 天过期，1 天后我们再解析此 token 会抛出
    jwt.exceptions.ExpiredSignatureError: Signature has expired
    """
    pass


class InvalidAudienceError(InvalidTokenError):
    """
    audience：签发的受众群体，若 encode payload 中添加 'aud' 字段，则可针对该字段校验
    参数类型：str

    若 aud 校验失败，则抛出 jwt.InvalidAudienceError
    """
    pass


class InvalidIssuerError(InvalidTokenError):
    """
    issuer: 发布者，若 encode payload 中添加 'iss' 字段，则可针对该字段校验
    参数类型：str

    若 iss 校验失败，则抛出 jwt.InvalidIssuerError
    """
    pass


class InvalidIssuedAtError(InvalidTokenError):
    """
    iat 指的是 token 的开始时间，如果当前时间在开始时间之前则抛出
    jwt.exceptions.InvalidIssuedAtError: Issued At claim (iat) cannot be in the future.
    """
    pass


class ImmatureSignatureError(InvalidTokenError):
    """
    nbf 类似于 token 的 lat ，它指的是该 token 的生效时间，如果使用但是没到生效时间则抛出
    jwt.exceptions.ImmatureSignatureError: The token is not yet valid (nbf)
    """
    pass


class InvalidKeyError(PyJWTError):
    """
    无效的 key
    """
    pass


class InvalidAlgorithmError(InvalidTokenError):
    """
    无效算法异常
    如: InvalidAlgorithmError('Algorithm not supported')
    """
    pass


class MissingRequiredClaimError(InvalidTokenError):
    """
    缺少关键 key 异常
    """
    def __init__(self, claim):
        self.claim = claim

    def __str__(self):
        return 'Token is missing the "%s" claim' % self.claim


# Compatibility aliases (deprecated)
ExpiredSignature = ExpiredSignatureError
InvalidAudience = InvalidAudienceError
InvalidIssuer = InvalidIssuerError
