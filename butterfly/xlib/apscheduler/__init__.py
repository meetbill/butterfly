# coding=utf8
"""
# Description:
    基于 2.1.2 开发(2020-12-2)
    基于 3.6.3 开发(2020-12-25)
        # Removed
        ## 执行器
        apscheduler/executors/tornado.py
        apscheduler/executors/twisted.py
        apscheduler/executors/gevent.py
        apscheduler/executors/asyncio.py
        apscheduler/executors/base_py3.py
        ## 调度器
        apscheduler/schedulers/tornado.py
        apscheduler/schedulers/twisted.py
        apscheduler/schedulers/qt.py
        apscheduler/schedulers/asyncio.py
        apscheduler/schedulers/gevent.py
        ## 作业存储
        apscheduler/jobstores/rethinkdb.py
        apscheduler/jobstores/zookeeper.py
        apscheduler/jobstores/mongodb.py
        apscheduler/jobstores/sqlalchemy.py
        apscheduler/jobstores/redis.py

        ## other
        timezone

        # Changed
        apscheduler/util.py
            datetime_to_utc_timestamp => datetime_to_timestamp
            utc_timestamp_to_datetime => timestamp_to_datetime

        # Added
        apscheduler/models
        apscheduler/manager
    3.7.0(2021-02-09)
        合并 3.7.0 部分代码
            * https://github.com/agronholm/apscheduler/issues/362
            * https://github.com/agronholm/apscheduler/issues/466
            * https://github.com/agronholm/apscheduler/issues/441
            * https://github.com/agronholm/apscheduler/issues/441
            * https://github.com/agronholm/apscheduler/pull/416
            * https://github.com/agronholm/apscheduler/pull/363

+scheduler(new thread)--------------------------------------------------------------------------------------+
|+job manager---------------+       + _main_loop-----------------------------------------------------------+|
||                          |       |+process_jobs------------------------------------------------+ +-----+||
||(add)                     |       ||(1) Get all jobs (tuple(jobstore.jobs))                     | |     |||
||EVENT_JOBSTORE_JOB_ADDED  |       ||(2) Computes the scheduled run times                        | |     |||
||(unschedule_job)          | event ||    run_times is a list(run_times = job._get_run_times(now))|+|sleep|||
||EVENT_JOBSTORE_JOB_REMOVED|------->|    Example: [datetime.datetime(2020, 11, 29, 0, 17, 58)]   | |     |||
||                          |       ||(3) executor                                                | |     |||
||                          |       ||    _threadpool.submit(self._run_job, job, run_times)       | |     |||
||                          |       |+--------------------------+---------------------------------+ +-----+||
|+------------+-------------+       +---------------------------|------------------------------------------+|
|             |                                                 |                                           |
+-------------|-------------------------------------------------|--------^----------------------------------+
              |                                                 |        |
              |                                                 |        |
+job store----V---------------------------------------+         |        |
|+job------------+ +job--------------+ +job----------+|         |        |
||+trigger------+| |+trigger--------+| |+trigger----+||         |        |
|||SimpleTrigger|| ||IntervalTrigger|| ||CronTrigger||| ........|........|..............................job store
||+-------------+| |+---------------+| |+-----------+||         |        |
|+---------------+ +-----------------+ +-------------+|         |        |
|                                                     |         |        |
|        +DB ------------------------------+          |         |        | EVENT_JOB_EXECUTED
|        |          table(ruqi)            |          |         |        | EVENT_JOB_ERROR
|        +---------------------------------+          |         |        | EVENT_JOB_MISSED
+-----------------------------------------------------+         |        |
                                                                |        |
                                    +submit job and executor----|--------+-------------+
                                    | +_run_job(scheduler)------V-+      +threadpool-+ |
                                    | |+job------+                |  put |+queue----+| |
                                    | ||job.func |                |----->||         || |
                                    | |+---------+                |      |+---------+| |
                                    | +---------------------------+      +-----^-----+ |................executor
                                    |                                          |get    |
                                    | +_run_jobs(threadpool new thread)--------------+ |
                                    | | exe _run_job(self, job, run_times)(scheduler)| |
                                    | +----------------------------------------------+ |
                                    +--------------------------------------------------+

"""
