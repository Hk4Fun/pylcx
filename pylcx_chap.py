__author__ = 'Hk4Fun'
__date__ = '2018/5/4 12:39'

import argparse
import socket
import asyncio
import sys

import chap


class lcx:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def transmit(self, from_s, to_s):
        while True:
            buff = await self.loop.sock_recv(from_s, 7)
            if len(buff) == 0:  # 对端关闭连接，读不到数据
                print('connect closed.')
                break
            print(buff)
            await self.loop.sock_sendall(to_s, buff)


class slave(lcx):
    def __init__(self, args):
        super().__init__()
        local_socket = args.local_socket.split(':', 1)
        conn_srv = local_socket[0]
        conn_port = chap.base_chap.check_port(local_socket[1])
        peer = chap.peer(args)  # handshake first
        self.chap_sock = peer.sock
        self.chap_sock.setblocking(False)  # remember to set non-block
        self.loop.create_task(self.connect(conn_srv, conn_port))
        self.loop.run_forever()

    async def connect(self, host, port):
        wait_time = 2
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.setblocking(False)
        while True:
            try:
                print('[*]connecting {}:{} ......'.format(host, port))
                await self.loop.sock_connect(conn, (host, port))
                break
            except Exception:
                print('[-]can not connect {}:{}, try again......'.format(host, port))
                asyncio.sleep(wait_time)
        print('[+]connect to {}:{} successfully!'.format(host, port))
        self.loop.create_task(self.transmit(self.chap_sock, conn))
        self.loop.create_task(self.transmit(conn, self.chap_sock))


class server(lcx):
    def __init__(self, args):
        super().__init__()
        authenticator = chap.authenticator(args)  # handshake first
        self.chap_sock = authenticator.sock
        self.chap_sock.setblocking(False)  # remember to set non-block
        self.loop.create_task(self.listen(authenticator.bind_port))
        self.loop.run_forever()

    async def listen(self, port):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.setblocking(False)
        srv.bind(('0.0.0.0', port))
        print('listening at {}......'.format(port))
        srv.listen()

        while True:
            conn, addr = await self.loop.sock_accept(srv)
            print('[+]connect from: {}'.format(addr))
            self.loop.create_task(self.transmit(conn, self.chap_sock))
            self.loop.create_task(self.transmit(self.chap_sock, conn))


def arg_parse():
    example = '''example: 
            python pylcx_chap.py -m listen -p 8000 -u u1:p1,u2:p2
            python pylcx_chap.py -m slave -r 127.0.0.1:8000 -u u1:p1 -p 8001 -l 127.0.0.1:8002'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='async LCX with CHAP',
                                     epilog=example)
    parser.add_argument('-m', dest='mode', choices=['slave', 'listen'], required=True,
                        help='slave or listen')
    parser.add_argument('-p', dest='port', required=True, type=chap.base_chap.check_port,
                        help='inner listen port for CHAP or Remote Listen to open port, random port if 0')
    parser.add_argument('-u', dest='user_pwd', required=True,
                        help='username:password, use comma to separate')
    parser.add_argument('-r', dest='chap_socket',
                        help="addr:port, Remote Listen's inner socket for CHAP")
    parser.add_argument('-l', dest='local_socket',
                        help="addr:port, Local Server's socket to connect")
    return parser.parse_args()


def main():
    args = arg_parse()
    if args.mode == 'listen':
        server(args)
    elif args.mode == 'slave':
        slave(args)


if __name__ == '__main__':
    main()
