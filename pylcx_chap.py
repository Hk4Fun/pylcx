__author__ = 'Hk4Fun'
__date__ = '2018/5/4 12:39'

import argparse
import asyncio
import collections
import signal
import functools
import sys

import chap
import chap_exception

class lcx:
    def __init__(self, loop):
        self.loop = loop
        self.connect_id_writer_map = {}
        self.chap = chap.base_chap(self.loop)

    async def dispatch(self):
        try:
            while True:
                packet = await self.chap.receive_packet()
                if packet:
                    if packet['code'] == chap.CONNECT_REQUEST_CODE:
                        await self.open_connection(packet)
                    elif packet['code'] == chap.CONNECT_RESPONSE_CODE:
                        self.handle_connect_response(packet)
                    elif packet['code'] == chap.DATA_CODE:
                        self.chap_transmit(packet)
                    elif packet['code'] == chap.DISCONNECT_CODE:
                        self.disconnect(packet)
                    else:
                        raise chap_exception.ProtocolException(packet['code'])
                else:
                    print('Connection closed!')
                    return
        except chap_exception.ProtocolException:
            return

    def chap_transmit(self, packet):
        connect_id, data = self.chap.parse_data(packet)
        writer = self.connect_id_writer_map[connect_id]
        writer.write(bytes(data.encode()))

    async def data_transmit(self, reader, connect_id):
        while True:
            data = await reader.read(4096)
            if data:
                self.chap.send_data(data.decode(), connect_id)
            else:
                if connect_id in self.connect_id_writer_map:  # prevent reclosing
                    self.handle_close(connect_id)
                break

    def handle_close(self, connect_id):
        if isinstance(self, slave):
            print('local server close, connect_id:', connect_id)
        elif isinstance(self, server):
            print('remote client close, connect_id:', connect_id)
        self.chap.send_disconnect(connect_id)
        writer = self.connect_id_writer_map.pop(connect_id)
        writer.close()

    def disconnect(self, packet):
        connect_id = self.chap.parse_disconnect(packet)
        writer = self.connect_id_writer_map.pop(connect_id)
        writer.close()

    async def open_connection(self, packet):
        raise NotImplementedError

    def handle_connect_response(self, packet):
        raise NotImplementedError


class slave(lcx):
    def __init__(self, args, loop):
        super().__init__(loop)
        local_socket = args.local_socket.split(':', 1)
        self.conn_srv = local_socket[0]
        self.conn_port = chap.base_chap.check_port(local_socket[1])
        self.chap = self.peer = chap.peer(args, self.loop)  # handshake first
        self.loop.run_until_complete(self.loop.create_task(self.dispatch()))

    async def open_connection(self, packet):
        request_id = self.peer.parse_connect_request(packet)
        try:
            reader, writer = await asyncio.open_connection(self.conn_srv, self.conn_port, loop=self.loop)
        except ConnectionRefusedError:
            print('connect local server {}:{} failed!'.format(self.conn_srv, self.conn_port))
            self.peer.send_connect_response(request_id, False)
        else:
            connect_id = self.peer.send_connect_response(request_id, True)
            self.connect_id_writer_map[connect_id] = writer
            self.loop.create_task(self.data_transmit(reader, connect_id))


class server(lcx):
    def __init__(self, args, loop):
        super().__init__(loop)
        self.request_id_remote_client_map = {}
        self.chap = self.authenticator = chap.authenticator(args, self.loop)  # handshake first
        self.start_server()

    def start_server(self):
        try:
            coro = asyncio.start_server(self.handle_connect, '0.0.0.0',
                                        self.authenticator.bind_port,
                                        loop=self.loop)
        except AttributeError: # self.authenticator.bind_port
            return
        else:
            self.server = self.loop.run_until_complete(coro)
            print('listening at 0.0.0.0:{}......'.format(self.authenticator.bind_port))
            self.loop.run_until_complete(self.dispatch())

    def handle_connect(self, reader, writer):
        peer_host, peer_port, = writer.get_extra_info('peername')
        print('[+]connection from: {}:{}'.format(peer_host, peer_port))
        request_id = self.authenticator.send_connect_request()
        remote_client = collections.namedtuple('remote_client', ['reader', 'writer'])
        self.request_id_remote_client_map[request_id] = remote_client._make([reader, writer])

    def handle_connect_response(self, packet):
        request_id, result, connect_id = self.authenticator.parse_connect_response(packet)
        remote_client = self.request_id_remote_client_map.pop(request_id)
        if result:
            self.connect_id_writer_map[connect_id] = remote_client.writer
            self.loop.create_task(self.data_transmit(remote_client.reader, connect_id))
        else:
            remote_client.writer.close()


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


def stopper(signame, loop):
    print("Got CTRL+C, stopping...")
    for task in asyncio.Task.all_tasks():
        task.cancel()
    loop.stop()
    loop.remove_signal_handler(signal.SIGINT)
    sys.exit()


def main():
    loop = asyncio.get_event_loop()
    # https://bugs.python.org/issue23057
    # https://github.com/python/asyncio/issues/191
    loop.add_signal_handler(getattr(signal, 'SIGINT'), functools.partial(stopper, 'SIGINT', loop))
    args = arg_parse()

    if args.mode == 'listen':
        server(args, loop)
    elif args.mode == 'slave':
        slave(args, loop)


if __name__ == '__main__':
    main()
