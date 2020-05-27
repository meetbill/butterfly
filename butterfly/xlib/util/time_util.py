#!/usr/bin/python
# coding=utf8
"""
# Author: wangbin34(meetbill)
# Created Time : 2020-02-22 11:45:54

# File Name: time_util.py
# Description:
    time util api

               +-----------+
               |struct_time| 结构化的时间
               +---^-------^
                / /       \ \ localtime（本地时区的 struct_time ---- time.localtime() # time.struct_time(tm_year=2020, tm_mon=2, tm_mday=22, tm_hour=12, tm_min=12, tm_sec=54, tm_wday=5, tm_yday=53, tm_isdst=0))
      strftime/ /     mktime\ \  gmtime (UTC 时区的 struct_time)
            / / strptime      \ \
    +-------V--+              +V--------+
    |format_str|              |timestamp| (time.time() # 时间戳:1582344742.146092)
    +----------+              +---------+
  格式化的字符串时间            时间戳
"""
import time


def get_current_time():
    """
    get cur time(timestamp)
    """
    return int(time.time())


def get_current_time_normal_format():
    """
    get cur time format
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def get_current_time_day_format():
    """
    get cur time format
    """
    return time.strftime("%Y-%m-%d", time.localtime())


def get_current_time_cons_format():
    """
    get cur time format 2
    """
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def time2timestamp(time_str):
    """
    str to timestamp
    """
    return int(time.mktime(time.strptime(time_str, '%Y-%m-%d %H:%M:%S')))


def time2timestamp_with_format(time_str, format_str):
    """
    str to timestamp with format
    """
    return int(time.mktime(time.strptime(time_str, format_str)))


def timestamp2time_str(timestamp):
    """
    timestamp 2 str
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def timestamp2time_str_day(timestamp):
    """
    timestamp 2 str
    """
    return time.strftime("%Y-%m-%d", time.localtime(timestamp))


def timestamp2time_str_with_format(timestamp, format_str):
    """
    timestamp 2 str

    Args:
        timestamp: timestamp
        format_str: time format
                    %Y-%m-%d %H:%M:%S
                    %Y%m%d%H%M%S
    """
    return time.strftime(format_str, time.localtime(timestamp))


def round_up_hour(hour):
    """
    round up hour to half or integer
    eg. 1.2 -> 2; 0.4 -> 1; 1.8 -> 2
    params: hour
    return near_hour
    """
    near_hour = round(hour)
    near_hour = int(near_hour)
    if hour < near_hour:
        return near_hour
    return near_hour + 1


if __name__ == "__main__":
    time_str = "2018102510"
    int_time2 = time2timestamp_with_format(time_str, "%Y%m%d%H")
    print int_time2
    int_time = get_current_time()
    str_time = get_current_time_normal_format()
    strs_time = timestamp2time_str(int_time2)
    print strs_time
