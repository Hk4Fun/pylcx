# coding=utf-8
__author__ = 'Hk4Fun'
__date__ = '2018/3/17 14:42'

"""
@usage:
./pylcx.py stream1 stream2
stream 为：l:port 或 c:host:port
l:port 表示监听指定的本地端口
c:host:port 表示监听远程指定的端口
"""

import socket
import sys
import asyncio

streams = [None, None]  # 存放需要进行数据转发的两个数据流（都是 SocketObj）
loop = asyncio.get_event_loop()


def usage():
    print('Usage: python pylcx.py stream1 stream2\nstream: l:port or c:host:port')


async def get_another_stream(num):
    """
    从streams获取另外一个流对象，如果当前为空，则等待
    """
    num = 0 if num == 1 else 1
    while True:
        if streams[num] == 'quit':
            print('can not connect to the target, quit now!')
            sys.exit(1)
        elif streams[num]:
            return streams[num]
        else:
            await asyncio.sleep(1)


async def transmit(num, s1, s2):
    """
    交换两个流的数据
    """
    try:
        while True:
            buff = await loop.sock_recv(s1, 10000)
            if len(buff) == 0:  # 对端关闭连接，读不到数据
                print('connect closed.')
                break
            print(buff)
            await loop.sock_sendall(s2, buff)
    except:
        print('connect closed.')

    s1.shutdown(socket.SHUT_RDWR)
    s1.close()
    s2.shutdown(socket.SHUT_RDWR)
    s2.close()

    streams[0], streams[1] = None, None
    print('{} CLOSED'.format(num))


async def server(port, num):
    """
    处理服务情况，num 为流编号（第 0 号还是第 1 号）
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.setblocking(False)  # 设置非阻塞
    srv.bind(('0.0.0.0', port))
    print('listening on {}......'.format(port))
    srv.listen(10)

    while True:
        conn, addr = await loop.sock_accept(srv)
        print('[+]connect from: {}'.format(addr))
        streams[num] = conn  # 放入本端流对象
        another_stream = await get_another_stream(num)  # 获取另一端流对象
        loop.create_task(transmit(num, conn, another_stream))


async def connect(host, port, num):
    """处理连接，num 为流编号（第 0 号还是第 1 号）
    @note: 如果连接不到远程，会 sleep 2s，最多尝试 30次（共1分钟）
    """
    wait_time = 2
    try_num = 30
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.setblocking(False)  # 设置非阻塞
    while True:
        if try_num == 0:
            streams[num] = 'quit'
            print('[-]can not connect {}:{}, quit now!'.format(host, port))
            sys.exit(1)
        try:
            print('[*]connecting {}:{} ......'.format(host, port))
            await loop.sock_connect(conn, (host, port))
            break
        except Exception:
            print('[-]can not connect {}:{}, try again......'.format(host, port))
            try_num -= 1
            asyncio.sleep(wait_time)

    print('[+]connect to {}:{} successfully!'.format(host, port))
    streams[num] = conn  # 放入本端流对象
    another_stream = await get_another_stream(num)  # 获取另一端流对象
    loop.create_task(transmit(num, conn, another_stream))


def main():
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)
    args = [sys.argv[1], sys.argv[2]]
    for i in [0, 1]:
        arg = args[i].split(':')
        if len(arg) == 2 and (arg[0] == 'l' or arg[0] == 'L'):  # l:port
            loop.create_task(server(int(arg[1]), i))
        elif len(arg) == 3 and (arg[0] == 'c' or arg[0] == 'C'):  # c:host:port
            loop.create_task(connect(arg[1], int(arg[2]), i))
        else:
            usage()
            sys.exit(1)
    try:
        loop.run_forever()
    except Exception:
        print('CLOSE')


if __name__ == '__main__':
    main()
