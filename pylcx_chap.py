__author__ = 'Hk4Fun'
__date__ = '2018/5/4 12:39'

import argparse
import asyncio
import collections

import chap


class lcx:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.connect_id_writer_map = {}

    def disconnect(self, packet, chap):
        connect_id = chap.parse_disconnect(packet)
        writer = self.connect_id_writer_map.pop(connect_id)
        writer.close()


class slave(lcx):
    def __init__(self, args):
        super().__init__()
        local_socket = args.local_socket.split(':', 1)
        self.conn_srv = local_socket[0]
        self.conn_port = chap.base_chap.check_port(local_socket[1])
        self.peer = chap.peer(args, self.loop)  # handshake first
        self.loop.run_until_complete(self.loop.create_task(self.dispatch()))

    async def dispatch(self):
        while True:
            packet = await self.peer.receive_packet()
            if packet['code'] == chap.CONNECT_REQUEST_CODE:
                await self.open_connection(packet)
            elif packet['code'] == chap.DATA_CODE:
                self.r_c2l_s(packet)
            elif packet['code'] == chap.DISCONNECT_CODE:
                self.disconnect(packet, self.peer)

    async def open_connection(self, packet):
        request_id = self.peer.parse_connect_request(packet)
        reader, writer = await asyncio.open_connection(self.conn_srv, self.conn_port, loop=self.loop)
        connect_id = await self.peer.send_connect_response(request_id)
        self.connect_id_writer_map[connect_id] = writer
        self.loop.create_task(self.l_s2r_c(reader, connect_id))

    async def l_s2r_c(self, reader, connect_id):  # local_server2remote_client
        while True:
            local_server_data = await reader.read(4096)
            if local_server_data:
                await self.peer.send_data(local_server_data.decode(), connect_id)
            else:
                if connect_id in self.connect_id_writer_map:  # 防止重复关闭
                    await self.handle_local_server_close(connect_id)
                break

    async def handle_local_server_close(self, connect_id):
        print('local server close, connect_id:', connect_id)
        await self.peer.send_disconnect(connect_id)
        writer = self.connect_id_writer_map.pop(connect_id)
        writer.close()

    def r_c2l_s(self, packet):  # remote_client2local_server
        connect_id, data = self.peer.parse_data(packet)
        writer = self.connect_id_writer_map[connect_id]
        writer.write(bytes(data.encode()))


class server(lcx):
    def __init__(self, args):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.authenticator = chap.authenticator(args, self.loop)  # handshake first
        self.request_id_remote_client_map = {}
        self.start_server()

    def start_server(self):
        coro = asyncio.start_server(self.handle_connect, '0.0.0.0',
                                    self.authenticator.bind_port,
                                    loop=self.loop)
        self.server_ = self.loop.run_until_complete(coro)
        print('listening at 0.0.0.0:{}......'.format(self.authenticator.bind_port))
        self.loop.create_task(self.dispatch())
        self.loop.run_forever()

    async def handle_connect(self, reader, writer):
        peer_host, peer_port, = writer.get_extra_info('peername')
        print('[+]connect from: {}:{}'.format(peer_host, peer_port))
        request_id = await self.authenticator.send_connect_request()
        remote_client = collections.namedtuple('remote_client', ['reader', 'writer'])
        self.request_id_remote_client_map[request_id] = remote_client._make([reader, writer])

    async def dispatch(self):
        while True:
            packet = await self.authenticator.receive_packet()
            if packet['code'] == chap.CONNECT_RESPONSE_CODE:
                self.handle_connect_response(packet)
            elif packet['code'] == chap.DATA_CODE:
                self.l_s2r_c(packet)
            elif packet['code'] == chap.DISCONNECT_CODE:
                self.disconnect(packet, self.authenticator)

    def handle_connect_response(self, packet):
        request_id, connect_id = self.authenticator.parse_connect_response(packet)
        remote_client = self.request_id_remote_client_map.pop(request_id)
        self.connect_id_writer_map[connect_id] = remote_client.writer
        self.loop.create_task(self.r_c2l_s(remote_client.reader, connect_id))

    async def r_c2l_s(self, reader, connect_id):
        while True:
            remote_client_data = await reader.read(4096)
            if remote_client_data:
                await self.authenticator.send_data(remote_client_data.decode(), connect_id)
            else:
                if connect_id in self.connect_id_writer_map:  # 防止重复关闭
                    await self.handle_remote_client_close(connect_id)
                break

    async def handle_remote_client_close(self, connect_id):
        print('remote client close, connect_id:', connect_id)
        await self.authenticator.send_disconnect(connect_id)
        writer = self.connect_id_writer_map.pop(connect_id)
        writer.close()

    def l_s2r_c(self, packet):
        connect_id, data = self.authenticator.parse_data(packet)
        writer = self.connect_id_writer_map[connect_id]
        writer.write(bytes(data.encode()))


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
