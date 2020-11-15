# coding:utf8
"""
用于生成 reqid
"""
import uuid
import ctypes
import os
import base64
import datetime

from xlib.util import pyDes


class UUID64(object):
    """
    UUID64 Class
    """

    ENC_KEY = "ZDgxN2Q4"

    def __init__(self):
        self._pid = os.getpid()
        # 先取 pid 与低四位按位与(值范围为 0-15)，然后左移动 4 位到高四位
        self._pid_factor = (self._pid & 0x0f) << 4
        self.counter = 0
        self._cipher = pyDes.Des(self.ENC_KEY)

        if uuid._uuid_generate_time:
            buf = ctypes.create_string_buffer(16)
            uuid._uuid_generate_time(buf)
            raw = buf.raw
        else:
            raw = uuid.uuid1().get_bytes()
        self._host_id = raw[-2:]

    def gen(self):
        """
        生成 reqid

            uuid.uuid1(35734e80-08ff-11eb-b0cc-f45c89b7b8f9) -- 基于时间戳:
                            |
                            V
            shortuuid 的 base16 编码后(eg: B8F9BB08FF357341):
                +-----------------------+-------------------+-----------------------+
                |        host_id        |       mid         |          tm           |
                |       (2 bytes)       |     (1 byte)      |       (5 bytes)       |
                +-----------------------+---------+---------+-----------------------+
                |     mac_addr[-2:]     | pid low |time_high| time_low |counter low |
                +-----------------------+---------+---------+----------+------------+
                |(mac_addr:f45c89b7b8f9)|(pid:123)|   11    |          |(counter: 1)|
                |          B8F9         |    B    |    B    | 08FF35734|      1     |
                +-----------------------+---------+---------+----------+------------+
                |                       |         |(1E)B08FF35734(000) |            |
                +-----------------------+---------+--------------------+------------+

            相关函数:
                ord: ord() 以一个字符（长度为1的字符串）作为参数，返回对应的 ASCII 数值, 如 ord('a') 为 97
                chr: chr() 用一个范围在 range（256）内的（就是0～255）整数作参数，返回一个对应的字符, 如 chr(97) 为 'a'
        Returns:
            reqid: (str), 16 字节 example:9602CFF26E1E6FED
        """
        self.counter += 1

        if uuid._uuid_generate_time:
            buf = ctypes.create_string_buffer(16)
            uuid._uuid_generate_time(buf)
            raw = buf.raw
        else:
            raw = uuid.uuid1().get_bytes()

        tm = (raw[4] + raw[5]) + (raw[0] + raw[1]) + chr((ord(raw[2]) & 0xf0) | (self.counter & 0x0f))
        mid = chr(self._pid_factor | (ord(raw[7]) & 0x0f))

        uuid64 = "%s%s%s" % (self._host_id, mid, tm)
        return base64.b16encode(self._cipher.encrypt(uuid64))

    def _get_time_by_shortuuid(self, shortuuid_b16):
        """从 reqid 解码后的 shortuuid 中获取时间戳及格式化的时间字符串
        Args:
            shortuuid_b16:(Str) 'B8F9BB08FF357341'
        Return:
            unix_timestamp, req_datetime
            eg: 1602117777.1360257, '2020-10-08 08:42:57.136026'
        """
        time_hexstr = shortuuid_b16[5:15]
        uuid_timestamp = int("0x1E" + time_hexstr + "000", 16)
        unix_timestamp = (uuid_timestamp - 0x01b21dd213814000) / 1e7
        req_datetime = datetime.datetime.fromtimestamp(unix_timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
        return unix_timestamp, req_datetime

    def decode(self, reqid):
        """解析 reqid
        Args:
            reqid:(Str) reqid
        Returns:
            res_info:(Dict)
            eg:{
                "timestamp": 1602159045.7737217,
                "pid_low": 5,
                "counter_low": 1,
                "mac_addr": "B8F9",
                "datetime": "2020-10-08 20:10:45.773722"
               }
        """
        # b16 解码，然后进行解密
        shortuuid = self._cipher.decrypt(base64.b16decode(reqid))
        # 对 shortuuid 进行 b16 编码
        shortuuid_b16 = base64.b16encode(shortuuid)
        unix_timestamp, req_datetime = self._get_time_by_shortuuid(shortuuid_b16)
        _res_info = {}
        _res_info["mac_addr"] = shortuuid_b16[0:4]
        _res_info["timestamp"] = unix_timestamp
        _res_info["datetime"] = req_datetime
        # counter 的低四位，取值为 0-15
        _res_info["counter_low"] = int("0x0" + shortuuid_b16[15], 16)
        # pid 的低四位，取值为 0-15
        _res_info["pid_low"] = int("0x0" + shortuuid_b16[4], 16)
        return _res_info


if __name__ == "__main__":
    import json
    uuid64 = UUID64()
    reqid = uuid64.gen()
    print "reqid: {reqid}".format(reqid=reqid)
    reqid_info = uuid64.decode(reqid)
    print "reqid_info: {reqid_info}".format(reqid_info=json.dumps(reqid_info))
