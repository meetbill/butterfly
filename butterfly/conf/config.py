# coding:utf8
"""
Butterfly config
"""

SERVER_LISTEN_ADDR = ("0.0.0.0", 8585)
SERVER_THREAD_NUM = 16

# Log
LOG_SIZE_LIMIT = 1024 * 1024 * 2
LOG_BATCH_WRITE = 0
PATH_INIT_LOG = "logs/init.log"
PATH_ACC_LOG = "logs/acc.log"
PATH_INFO_LOG = "logs/info.log"
PATH_WARNING_LOG = "logs/warning.log"
PATH_ERR_LOG = "logs/err.log"
PATH_CRIT_LOG = "logs/crit.log"
PATH_COMMON_LOG = "logs/common.log"
PATH_COMMON_BF_LOG = "logs/common_bf.log"

# static
STATIC_PATH = "static"
STATIC_PREFIX="static"

# DB
mysql_config_url="mysql+retrypool://root:password@127.0.0.1:3306/test?max_connections=300&stale_timeout=300"
redis_config_url="redis://@localhost:6379/0"  # "redis://[[username]:[password]]@localhost:6379/0"

# Local Cache
diskcache_dir = "data/diskcache"

# Auth
SECRET_KEY = None        # If it is None, a key will be randomly generated each time butterfly is started
JWT_TOKEN_TTL = 28800    # default 8 hours

# Scheduler
scheduler_name="Scheduler1"# Scheduler name, Used to perform historical queries
scheduler_store="none"    # ("none"/"mysql"/"memory") ; if set none, the schedule is not run
