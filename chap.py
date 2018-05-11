__author__ = 'Hk4Fun'
__date__ = '2018/5/5 11:15'

import hashlib
import random
import socket
import struct
import argparse
import sys
import asyncio

from chap_exception import *

# Header = Code (1 Byte) + Identifier (1 Byte ) + Length (2 Byte )
header_len = 4

# Constants used in the protocol fields
# AUTH_REQUEST_CODE = 0x00
CHALLENGE_CODE = 0x01
RESPONSE_CODE = 0x02
SUCCESS_CODE = 0x03
FAILURE_CODE = 0x04
BIND_REQUEST_CODE = 0x05
BIND_RESPONSE_CODE = 0x06
CONNECT_REQUEST_CODE = 0x07
CONNECT_RESPONSE_CODE = 0x08
DATA_CODE = 0x09
DISCONNECT_CODE = 0x10


class base_chap:
    def __init__(self, loop):
        self.connect_id = set()
        self.loop = loop
        self.reader = None
        self.writer = None
        self.identifier = None

    @classmethod
    def check_port(cls, port):
        port = int(port)
        if not 0 <= port <= 65535:
            raise argparse.ArgumentTypeError('port should be range(0, 65536)')
        return port

    def check_identifier(func):
        def wrapper(*args, **kwargs):
            self, packet = args
            if packet['identifier'] != self.identifier:
                raise IdentifierException(packet['identifier'])
            return func(*args, **kwargs)

        return wrapper

    def check_code(code):
        def decorator(func):
            def wrapper(*args, **kwargs):
                _, packet = args
                if packet['code'] != code:
                    raise ProtocolException(packet['code'])
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def send_packet(self, packet):
        self.writer.write(packet)

    async def receive_packet(self):
        try:
            header = await self.reader.readexactly(header_len)
        except asyncio.streams.IncompleteReadError:
            return
        else:
            if header == '': raise RuntimeError("socket connection broken")
            (code, identifier, length) = struct.unpack('!BBH', header)

            packet = header
            chunk = await self.reader.readexactly(length - header_len)
            if chunk == '': raise RuntimeError("socket connection broken")
            packet = packet + chunk

            (code, identifier, length, data) = struct.unpack('!BBH' + str(length - header_len) + 's', packet)
            return {'code': code,
                    'identifier': identifier,
                    'length': length,
                    'data': data}

    def create_protocol_packet(self, code, data):
        data_len = len(data)
        packet_len = header_len + data_len

        # Packing format:
        #    ! ==> use network byte order
        #    B ==> encode as a C unsigned char (8 bit character == octect)
        #    s ==> encode as a string character (in particular NNs => encode NN characters)

        pack_format = '!BBH' + str(data_len) + 's'

        if isinstance(data, str):
            data = bytes(data.encode())

        return struct.pack(pack_format, code, self.identifier, packet_len, data)

    def send_data(self, data, connect_id):
        code = DATA_CODE
        data = connect_id + '#' + data
        self.send_packet(self.create_protocol_packet(code, data))

    @check_code(DATA_CODE)
    @check_identifier
    def parse_data(self, packet):
        connect_id, data = packet['data'].decode().split('#', 1)
        if connect_id not in self.connect_id:
            raise ConnectIdException(connect_id)
        print('Data from connect_id ', connect_id)
        print('Data:', data)
        return connect_id, data

    def send_disconnect(self, connect_id):
        code = DISCONNECT_CODE
        data = connect_id
        self.send_packet(self.create_protocol_packet(code, data))

    @check_code(DISCONNECT_CODE)
    @check_identifier
    def parse_disconnect(self, packet):
        connect_id = packet['data'].decode()
        if connect_id not in self.connect_id:
            raise ConnectIdException(connect_id)
        print('Closing connection connect_id:', connect_id)
        return connect_id


class peer(base_chap):
    def __init__(self, args, loop):
        super().__init__(loop)
        chap_socket = args.chap_socket.split(':', 1)
        self.authenticator, self.port = chap_socket[0], base_chap.check_port(chap_socket[1])
        self.identity, self.secret = args.user_pwd.split(':', 1)
        self.remote_port = args.port
        self.loop.run_until_complete(self.connect())
        self.loop.run_until_complete(self.handshake())

    async def connect(self):
        wait_time = 2
        while True:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.authenticator,
                                                                         self.port, loop=self.loop)
                break
            except ConnectionRefusedError:
                print('Can not connect {}:{}, try again......'.format(self.authenticator, self.port))
                asyncio.sleep(wait_time)

    def parse_challenge(self, packet):
        if packet['code'] != CHALLENGE_CODE:
            raise ProtocolException(packet['code'])
        self.identifier = packet['identifier']
        challenge_len = struct.unpack('!B', bytes((packet['data'][0],)))[0]
        self.challenge = packet['data'][1:challenge_len + 1]
        print("Processing challenge with identifier:", packet['identifier'])

    def send_response(self):
        response_value = hashlib.sha1((chr(self.identifier) + self.secret + str(self.challenge)).encode()).digest()
        response_value_size = struct.pack('!B', len(response_value))
        code = RESPONSE_CODE
        data = response_value_size + response_value + self.identity.encode()
        print("Creating response with identifier:", self.identifier)
        self.send_packet(self.create_protocol_packet(code, data))

    @base_chap.check_identifier
    def parse_result(self, packet):
        if packet['code'] != SUCCESS_CODE and packet['code'] != FAILURE_CODE:
            raise ProtocolException(packet['code'])
        if packet['code'] == SUCCESS_CODE:
            print("Successfully authenticated!")
        elif packet['code'] == FAILURE_CODE:
            print("Could not authenticate. Reason from the authenticator:", packet['data'].decode())
            raise VarifyError()

    def send_bind_request(self):
        print("Start negotiate Remote Listen's port", self.remote_port)
        code, data = BIND_REQUEST_CODE, str(self.remote_port)
        self.send_packet(self.create_protocol_packet(code, data))

    @base_chap.check_code(BIND_RESPONSE_CODE)
    @base_chap.check_identifier
    def parse_bind_response(self, packet):
        print('Remote Listen is listening at', int(packet['data']))

    async def handshake(self):
        try:
            self.parse_challenge(await self.receive_packet())
            self.send_response()

            self.parse_result(await self.receive_packet())
            self.send_bind_request()

            self.parse_bind_response(await self.receive_packet())

        except ChapError as e:
            print(e)
            self.writer.close()
            sys.exit(1)

    @base_chap.check_code(CONNECT_REQUEST_CODE)
    @base_chap.check_identifier
    def parse_connect_request(self, packet):
        request_id = packet['data'].decode()
        print('New connect from Remote Client, request_id ', request_id)
        return request_id

    def send_connect_response(self, request_id, result):
        code = CONNECT_RESPONSE_CODE
        connect_id = '0'
        if result: connect_id = self._generate_connect_id()
        data = request_id + '#' + ['0', '1'][result] + '#' + connect_id
        self.send_packet(self.create_protocol_packet(code, data))
        return connect_id

    def _generate_connect_id(self):
        id = str(random.randint(0, 1000000))
        while id in self.connect_id:
            id = str(random.randint(0, 1000000))
        self.connect_id.add(id)
        return id


class authenticator(base_chap):
    def __init__(self, args, loop):
        super().__init__(loop)
        self.port = args.port
        self.user_list = self._make_user_list(args)
        self.request_id = set()
        self.start_server()

    def _make_user_list(self, args):
        user_list = {}
        for user in args.user_pwd.split(','):
            identity, secret = user.split(':', 1)
            user_list[identity] = secret
        return user_list

    def start_server(self):
        coro = asyncio.start_server(self.handle_connect, '0.0.0.0', self.port, loop=self.loop)
        self.server = self.loop.run_until_complete(coro)
        print('Listening at 0.0.0.0:{}......'.format(self.port))
        self.loop.run_forever()

    async def handle_connect(self, reader, writer):
        self.reader, self.writer = reader, writer
        peer_host, peer_port, = writer.get_extra_info('peername')
        print('Connection from: {}:{}'.format(peer_host, peer_port))
        self.server.close()  # only one chap connection at a time
        await self.handshake()
        self.loop.stop()  # handshake over

    def send_challenge(self):
        self.identifier = random.randint(0, 255)
        # Create some random challenge, using the hash of a string
        # composed of 60 random integer number in the range
        # [1,100000000]
        self.challenge = hashlib.sha1(''.join(map(str, random.sample(range(10000000), 60))).encode()).digest()
        challenge_size = struct.pack('!B', len(self.challenge))
        code = CHALLENGE_CODE
        data = challenge_size + self.challenge
        print("Creating challenge with identifier:", self.identifier)
        self.send_packet(self.create_protocol_packet(code, data))

    @base_chap.check_code(RESPONSE_CODE)
    @base_chap.check_identifier
    def parse_response(self, packet):
        response_len = struct.unpack('!B', bytes((packet['data'][0],)))[0]
        self.response = packet['data'][1:response_len + 1]
        self.identity = packet['data'][response_len + 1:]
        print("Processing response with identifier:", packet['identifier'])

    def verify_response(self):
        print("Verifying response for identifier:", self.identifier)
        user_list = self.user_list
        identity = self.identity.decode()
        if identity in user_list:
            secret = user_list[identity]
            our_value = hashlib.sha1((chr(self.identifier) + secret + str(self.challenge)).encode()).digest()
            if our_value == self.response:
                return True
        return False

    def send_result(self, valid):
        if valid:
            code = SUCCESS_CODE
            data = ''
            print('Verify successfully!')
        else:
            code = FAILURE_CODE
            data = 'Identity or secret is incorrect'
        self.send_packet(self.create_protocol_packet(code, data))

    @base_chap.check_code(BIND_REQUEST_CODE)
    @base_chap.check_identifier
    def parse_bind_request(self, packet):
        self.bind_port = int(packet['data'])

    def send_bind_response(self):
        if self.bind_port == 0:
            self.bind_port = random.randint(1025, 65535)
        code = BIND_RESPONSE_CODE
        data = str(self.bind_port)
        self.send_packet(self.create_protocol_packet(code, data))

    async def handshake(self):
        try:
            self.send_challenge()
            self.parse_response(await self.receive_packet())
            valid = self.verify_response()

            self.send_result(valid)
            if not valid: raise VarifyError()
            self.parse_bind_request(await self.receive_packet())

            self.send_bind_response()
        except ChapError as e:
            print(e)

    def send_connect_request(self):
        code = CONNECT_REQUEST_CODE
        request_id = self._generate_request_id()
        data = request_id
        self.send_packet(self.create_protocol_packet(code, data))
        return request_id

    def _generate_request_id(self):
        id = str(random.randint(0, 1000000))
        while id in self.request_id:
            id = str(random.randint(0, 1000000))
        self.request_id.add(id)
        return id

    @base_chap.check_code(CONNECT_RESPONSE_CODE)
    @base_chap.check_identifier
    def parse_connect_response(self, packet):
        request_id, result, connect_id = packet['data'].decode().split('#', 2)
        if request_id not in self.request_id:
            raise RequestIdException(request_id)
        result = int(result)
        if result:
            self.connect_id.add(connect_id)
            print('Connect to Local Server successfully! Connect_id:', connect_id)
        else:
            print('Connect to Local Server failed!')
        return request_id, result, connect_id
