# coding=utf8
"""
# Author: meetbill(wangbin34)
# Created Time : 2020-02-23 21:40:27
"""
import socket
import random

from xlib.ral import mcpack
from xlib.ral import nshead


def _get_logid():
    """
    获取随机 id 作为 logid
    """
    return random.randint(1, 10000000)


def nshead_client_test(ip, port):
    """
    nshead client 例子
    Args:
        ip  : nshead_server ip
        port: nshead_server port
    """
    # 连接该套接字
    proxy = (ip, int(port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(proxy)

    # 打包
    send_dict = {
        "uname": "wangbin34test1",
        "tk": "wangbin34test1",
        "method": "SETEX",
        "key": "wangbin34",
        "value": "mykey value",
        "seconds": 2000}
    #send_dict = {"uname":"wangbin34test1","tk":"wangbin34test1","method":"GET","key":"wangbin34"}
    send_pack = mcpack.dumps(send_dict)

    # 发送该 mcpack 包
    custom_dict = {}
    custom_dict["log_id"] = _get_logid()
    custom_dict["provider"] = "pynshead"
    nshead.nshead_write(sock, send_pack, custom_dict)

    # 从 sock 读出来 buffer
    recever_buf = nshead.nshead_read(sock)
    result_info = mcpack.loads(recever_buf)
    """
    {'err_no': 0, 'err_msg': 'OK', 'ret': {'wangbin34': 'OK'}}
    """
    sock.close()  # 关闭套接字
    print result_info


if __name__ == '__main__':
    import sys
    import inspect
    if len(sys.argv) < 2:
        print "Usage:"
        for k, v in sorted(globals().items(), key=lambda item: item[0]):
            if inspect.isfunction(v) and k[0] != "_":
                args, __, __, defaults = inspect.getargspec(v)
                if defaults:
                    print sys.argv[0], k, str(args[:-len(defaults)])[1:-1].replace(",", ""), \
                        str(["%s=%s" % (a, b) for a, b in zip(args[-len(defaults):], defaults)])[1:-1].replace(",", "")
                else:
                    print sys.argv[0], k, str(v.func_code.co_varnames[:v.func_code.co_argcount])[1:-1].replace(",", "")
        sys.exit(-1)
    else:
        func = eval(sys.argv[1])
        args = sys.argv[2:]
        try:
            r = func(*args)
        except Exception as e:
            print "Usage:"
            print "\t", "python %s" % sys.argv[1], str(func.func_code.co_varnames[:func.func_code.co_argcount])[
                1:-1].replace(",", "")
            if func.func_doc:
                print "\n".join(["\t\t" + line.strip() for line in func.func_doc.strip().split("\n")])
            print e
            r = -1
            import traceback
            traceback.print_exc()
        if isinstance(r, int):
            sys.exit(r)
