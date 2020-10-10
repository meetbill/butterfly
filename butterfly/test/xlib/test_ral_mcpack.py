#!/usr/bin/python
# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-10 10:43:43

# File Name: test_ral_mcpack.py
# Description:

"""

from xlib.ral import mcpack

def test_mcpack():
    """test mcpack"""
    send_dict = {"uname":"test","tk":"test","method":"SETEX","key":"meetbill", "value":"mykey value", "seconds" : 200}
    # 打包
    send_pack = mcpack.dumps(send_dict)
    # 解包
    send_unpack = mcpack.loads(send_pack)
    assert send_dict == send_unpack

