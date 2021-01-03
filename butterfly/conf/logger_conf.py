#coding:utf8
"""
初始化配置日志

acclog : Butterfly 访问日志
errlog : Butterfly 错误日志
initlog: Butterfly 启动相关信息
"""

from xlib import logger
from conf import config

# 通用 logging 初始化
logger.init_log(config.PATH_COMMON_LOG)
# Butterfly logger 日志初始化
logger.init_bf_log(config.PATH_COMMON_BF_LOG)

critlog = logger.LoggerBase(config.PATH_CRIT_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)

errlog = logger.LoggerBase(config.PATH_ERR_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)

warninglog = logger.LoggerBase(config.PATH_WARNING_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)

infolog = logger.LoggerBase(config.PATH_INFO_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)

acclog = logger.LoggerBase(config.PATH_ACC_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)

initlog = logger.LoggerBase(config.PATH_INIT_LOG, False, config.LOG_SIZE_LIMIT, config.LOG_BATCH_WRITE)
