# coding=utf8
"""
# Description:
    apscheduler: 3.6.3

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

# Removed
## 执行器
apscheduler/executors/tornado.py
apscheduler/executors/twisted.py
apscheduler/executors/gevent.py
apscheduler/executors/asyncio.py
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
timezone

# Changed
apscheduler/util.py
  datetime_to_utc_timestamp => datetime_to_timestamp
  utc_timestamp_to_datetime => timestamp_to_datetime

# Added
apscheduler/models
apscheduler/manager
"""
