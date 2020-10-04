# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-10-04 20:03:33

# File Name: __init__.py
# Description:
    nshead 包
"""
import struct
nsead_body_len = 36


class nshead(object):
    """
    # nshead 类定义
    """
    format = "HHI16sIII"
    magic_num = 0xfb709394

    def __init__(self, head={}):
        self.head = {}
        self.head["id"] = head.get("id", 0)
        self.head["version"] = head.get("version", 0)
        self.head["log_id"] = head.get("log_id", 314159268)
        self.head["provider"] = head.get("provider", "pynshead")
        self.head["magic_num"] = self.magic_num
        self.head["reserved"] = head.get("reserved", 0)
        self.head["body_len"] = head.get("body_len", 0)
        self.struct = struct.Struct(self.format)
        self.size = self.struct.size

    def load(self, bin):
        (self.head["id"], self.head["version"], self.head["log_id"], self.head["provider"],
         self.head["magic_num"], self.head["reserved"], self.head["body_len"]) = self.struct.unpack(bin)
        if self.head["magic_num"] != self.magic_num:
            raise UserWarning("magic_num check fail")

    def generate(self):
        return self.struct.pack(self.head["id"], self.head["version"], self.head["log_id"],
                                self.head["provider"], self.head["magic_num"], self.head["reserved"], self.head["body_len"])


def nshead_write(sock, info, custom=None):
    """
    # nshead 发送信息
    # sock 发送的套接字
    # info 发送的信息
    """
    body_len = len(info)
    if custom and isinstance(custom, dict):
        send_nshead = nshead(custom)
    else:
        send_nshead = nshead({'provider': 'pynshead', 'log_id': 1234, 'body_len': body_len})
    send_nshead_info = send_nshead.generate()
    msglen = len(send_nshead_info + info)
    totalsent = 0
    infosent = 0
    while totalsent < msglen:
        sent = sock.send(send_nshead_info + info[infosent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent
        infosent = totalsent - nsead_body_len
    return totalsent


def nshead_read(sock):
    """
    # nshead 接受信息
    # sock 发送的套接字
    """
    msg = ''
    info = sock.recv(nsead_body_len)
    if info == '':
        raise RuntimeError("socket connection broken")
    receive_nshead = nshead()
    receive_nshead.load(info)
    while(len(msg) < receive_nshead.head['body_len']):
        recever_buf = sock.recv(receive_nshead.head['body_len'])
        if recever_buf == '':
            raise RuntimeError("socket connection broken")
        msg = msg + recever_buf
    return msg
