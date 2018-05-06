__author__ = 'Hk4Fun'
__date__ = '2018/5/5 11:15'

import hashlib
import random
import socket
import struct
import argparse
import sys

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


class ChapError(Exception):
    pass


class ProtocolException(ChapError):
    def __init__(self, error_code):
        super().__init__(self)
        self.error_code = error_code

    def __str__(self):
        return 'Error packet code {}'.format(self.error_code)


class IdentifierException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error identifier {}'.format(self.error_id)


class VarifyError(ChapError):
    def __init__(self, ):
        super().__init__(self)

    def __str__(self):
        return 'Identity or secret is incorrect'


class ConnectIdException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error connect_id {}'.format(self.error_id)


class RequestIdException(ChapError):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error connect_id {}'.format(self.error_id)


class base_chap:
    def __init__(self, loop):
        self.connect_id = set()
        self.loop = loop
        self.sock = None
        self.identifier = None

    @classmethod
    def check_port(cls, port):
        port = int(port)
        if not 0 <= port <= 65535:
            raise argparse.ArgumentTypeError('port should be range(0, 65536)')
        return port

    async def send_packet(self, packet):
        await self.loop.sock_sendall(self.sock, packet)

    async def receive_packet(self):
        header = await self.loop.sock_recv(self.sock, header_len)
        if header == '':
            raise RuntimeError("socket connection broken")
        (code, identifier, length) = struct.unpack('!BBH', header)

        packet = header
        chunk = await self.loop.sock_recv(self.sock, length - header_len)
        if chunk == '':
            raise RuntimeError("socket connection broken")
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
        #
        pack_format = '!BBH' + str(data_len) + 's'

        if isinstance(data, str):
            data = bytes(data.encode())

        return struct.pack(pack_format, code, self.identifier, packet_len, data)

    async def send_data(self, data, connect_id):
        code = DATA_CODE
        data = connect_id + '#' + data
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_data(self, packet):
        if packet['code'] != DATA_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        connect_id, data = packet['data'].decode().split('#', 1)
        if connect_id not in self.connect_id:
            raise ConnectIdException(connect_id)
        print('Data from connect_id ', connect_id)
        return connect_id, data

    async def send_disconnect(self, connect_id):
        code = DISCONNECT_CODE
        data = connect_id
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_disconnect(self, packet):
        if packet['code'] != DISCONNECT_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
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
        self.loop.run_until_complete(self.loop.create_task(self.connect()))
        self.loop.run_until_complete(self.loop.create_task(self.handshake()))

    async def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        await self.loop.sock_connect(self.sock, (self.authenticator, self.port))

    def parse_challenge(self, packet):
        if packet['code'] != CHALLENGE_CODE:
            raise ProtocolException(packet['code'])
        self.identifier = packet['identifier']
        challenge_len = struct.unpack('!B', bytes((packet['data'][0],)))[0]
        self.challenge = packet['data'][1:challenge_len + 1]
        print("Processing challenge with identifier:", packet['identifier'])

    async def send_response(self):
        response_value = hashlib.sha1((chr(self.identifier) + self.secret + str(self.challenge)).encode()).digest()
        response_value_size = struct.pack('!B', len(response_value))
        code = RESPONSE_CODE
        data = response_value_size + response_value + self.identity.encode()
        print("Creating response with identifier:", self.identifier)
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_result(self, packet):
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        if packet['code'] != SUCCESS_CODE and packet['code'] != FAILURE_CODE:
            raise ProtocolException(packet['code'])
        if packet['code'] == SUCCESS_CODE:
            print("Successfully authenticated!")
        elif packet['code'] == FAILURE_CODE:
            print("Could not authenticate. Reason from the authenticator:", packet['data'].decode())
            raise VarifyError()

    async def send_bind_request(self):
        print("Start negotiate Remote Listen's port", self.remote_port)
        code, data = BIND_REQUEST_CODE, str(self.remote_port)
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_bind_response(self, packet):
        if packet['code'] != BIND_RESPONSE_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        print('Remote Listen is listening at', int(packet['data']))

    async def handshake(self):
        try:
            self.parse_challenge(await self.receive_packet())
            await self.send_response()

            self.parse_result(await self.receive_packet())
            await self.send_bind_request()

            self.parse_bind_response(await self.receive_packet())

        except ChapError as e:
            print(e)
            self.sock.close()
            sys.exit(1)

    def parse_connect_request(self, packet):
        if packet['code'] != CONNECT_REQUEST_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        request_id = packet['data'].decode()
        print('New connect from Remote Client, request_id ', request_id)
        return request_id

    async def send_connect_response(self, request_id):
        code = CONNECT_RESPONSE_CODE
        connect_id = self.generate_connect_id()
        data = request_id + '#' + connect_id
        await self.send_packet(self.create_protocol_packet(code, data))
        return connect_id

    def generate_connect_id(self):
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
        self.listen()
        self.loop.run_until_complete(self.handshake())

    def _make_user_list(self, args):
        user_list = {}
        for user in args.user_pwd.split(','):
            identity, secret = user.split(':', 1)
            user_list[identity] = secret
        return user_list

    def listen(self):
        self.srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srvsock.bind(('', self.port))  # Host == '' means any local IP address
        print("Listening at 0.0.0.0:", self.port)
        self.srvsock.listen(1)

    async def send_challenge(self):
        self.identifier = random.randint(0, 255)
        # Create some random challenge, using the hash of a string
        # composed of 60 random integer number in the range
        # [1,100000000]
        self.challenge = hashlib.sha1(''.join(map(str, random.sample(range(10000000), 60))).encode()).digest()
        challenge_size = struct.pack('!B', len(self.challenge))
        code = CHALLENGE_CODE
        data = challenge_size + self.challenge
        print("Creating challenge with identifier:", self.identifier)
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_response(self, packet):
        if packet['code'] != RESPONSE_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
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

    async def send_result(self, valid):
        if valid:
            code = SUCCESS_CODE
            data = ''
            print('Verify successfully!')
        else:
            code = FAILURE_CODE
            data = 'Identity or secret is incorrect'
        await self.send_packet(self.create_protocol_packet(code, data))

    def parse_bind_request(self, packet):
        if packet['code'] != BIND_REQUEST_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        self.bind_port = int(packet['data'])

    async def send_bind_response(self):
        if self.bind_port == 0:
            self.bind_port = random.randint(1025, 65535)
        code = BIND_RESPONSE_CODE
        data = str(self.bind_port)
        await self.send_packet(self.create_protocol_packet(code, data))

    async def handshake(self):
        while True:
            self.sock, addr = self.srvsock.accept()
            self.sock.setblocking(False)
            print('Socket from ' + str(addr[0]) + ':' + str(addr[1]))
            try:
                await self.send_challenge()
                self.parse_response(await self.receive_packet())
                valid = self.verify_response()

                await self.send_result(valid)
                if not valid: raise VarifyError()
                self.parse_bind_request(await self.receive_packet())

                await self.send_bind_response()
                break
            except ChapError as e:
                print(e)

    async def send_connect_request(self):
        code = CONNECT_REQUEST_CODE
        request_id = self.generate_request_id()
        data = request_id
        await self.send_packet(self.create_protocol_packet(code, data))
        return request_id

    def generate_request_id(self):
        id = str(random.randint(0, 1000000))
        while id in self.request_id:
            id = str(random.randint(0, 1000000))
        self.request_id.add(id)
        return id

    def parse_connect_response(self, packet):
        if packet['code'] != CONNECT_RESPONSE_CODE:
            raise ProtocolException(packet['code'])
        if packet['identifier'] != self.identifier:
            raise IdentifierException(packet['identifier'])
        request_id, connect_id = packet['data'].decode().split('#', 1)
        if request_id not in self.request_id:
            raise RequestIdException(request_id)
        self.connect_id.add(connect_id)
        print('Connect to Local Server successfully! Connect_id:', connect_id)
        return request_id, connect_id
