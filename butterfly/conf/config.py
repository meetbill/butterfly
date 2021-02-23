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
"""
# wuxing/ruqi use default database
"""
DATABASES = {
    "default": "mysql+retrypool://root:password@127.0.0.1:3306/test?max_connections=300&stale_timeout=300",
    }

# Redis
"""
# eg1:"redis://[[username]:[password]]@localhost:6379/0"
# eg2:"redis://@localhost:6379/0?socket_timeout=2&socket_connect_timeout=1&retry_on_timeout=true"
"""
CACHES = {
    "default": "redis://@localhost:6379/0",
    # for cache: connect_timeout 100ms, read_timeout 200ms
    #"wuxing": "redis://@localhost:6379/0?socket_timeout=0.2&socket_connect_timeout=0.1&retry_on_timeout=false",
    # for mq: connect_timeout 500ms, read_timeout 2000ms
    #"baichuan": "redis://@localhost:6379/0?socket_timeout=2&socket_connect_timeout=0.5&retry_on_timeout=false",
    }

# Local Cache
diskcache_dir = "data/diskcache"

# Auth
SECRET_KEY = None           # If it is None, a key will be randomly generated each time butterfly is started
JWT_TOKEN_TTL = 28800       # default 8 hours

# Scheduler
scheduler_name="Scheduler1" # Scheduler name, Used to perform historical queries
scheduler_store="memory"    # ("mysql"/"memory")
