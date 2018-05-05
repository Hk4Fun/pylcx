__author__ = 'Hk4Fun'
__date__ = '2018/5/4 12:39'

import argparse
import hashlib
import random
import socket
import struct
import asyncio
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


class slave:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def connect(self, host, port):
        self.reader, self.writer = await asyncio.open_connection(host, port, loop=self.loop)


class server:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def listen(self, port):
        pass


class base_chap:

    @classmethod
    def check_port(cls, port):
        port = int(port)
        if not 0 <= port <= 65535:
            raise argparse.ArgumentTypeError('port should be range(0, 65536)')
        return port

    def send_packet(self):
        total_sent = 0
        while total_sent < len(self.packet):
            sent = self.sock.send(self.packet[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent = total_sent + sent

    def receive_packet(self):
        header = self.sock.recv(header_len)
        if header == '':
            raise RuntimeError("socket connection broken")

        (code, identifier, length) = struct.unpack('!BBH', header)
        packet = header

        while len(packet) < length:
            chunk = self.sock.recv(length - len(packet))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            packet = packet + chunk

        (code, identifier, length, data) = struct.unpack('!BBH' + str(length - header_len) + 's', packet)
        return {'code': code,
                'identifier': identifier,
                'length': length,
                'data': data}

    def create_protocol_packet(self):
        data_len = len(self.data)
        packet_len = header_len + data_len

        # Packing format:
        #    ! ==> use network byte order
        #    B ==> encode as a C unsigned char (8 bit character == octect)
        #    s ==> encode as a string character (in particular NNs => encode NN characters)
        #
        pack_format = '!BBH' + str(data_len) + 's'

        if isinstance(self.data, str):
            self.data = bytes(self.data.encode())

        self.packet = struct.pack(pack_format, self.code, self.identifier, packet_len, self.data)

    def start_handhsake(self):
        try:
            self.handshake()
        except ChapError as e:
            print(e)
        finally:
            self.sock.close()

    def handshake(self):
        pass


class peer(base_chap):
    def __init__(self, args):
        chap_socket = args.chap_socket.split(':', 1)
        self.authenticator, self.port = chap_socket[0], base_chap.check_port(chap_socket[1])
        self.identity, self.secret = args.user_pwd.split(':', 1)
        # transmit args
        self.remote_port = args.port
        local_socket = args.local_socket
        self.connect_server, self.connect_port = local_socket[0], base_chap.check_port(local_socket[1])
        self.connect()
        self.start_handhsake()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.authenticator, self.port))

    def parse_challenge(self):
        if self.packet['code'] != CHALLENGE_CODE:
            raise ProtocolException(self.packet['code'])
        self.identifier = self.packet['identifier']
        challenge_len = struct.unpack('!B', bytes((self.packet['data'][0],)))[0]
        self.challenge = self.packet['data'][1:challenge_len + 1]
        print("Processing challenge with identifier:", self.packet['identifier'])

    def send_response(self):
        response_value = hashlib.sha1((chr(self.identifier) + self.secret + str(self.challenge)).encode()).digest()
        response_value_size = struct.pack('!B', len(response_value))
        self.data = response_value_size + response_value + self.identity.encode()
        self.code = RESPONSE_CODE
        self.create_protocol_packet()
        print("Creating response with identifier:", self.identifier)
        self.send_packet()

    def parse_result(self):
        if self.packet['identifier'] != self.identifier:
            raise IdentifierException(self.packet['identifier'])
        if self.packet['code'] != SUCCESS_CODE and self.packet['code'] != FAILURE_CODE:
            raise ProtocolException(self.packet['code'])
        if self.packet['code'] == SUCCESS_CODE:
            self.success = True
            print("Successfully authenticated!")
        elif self.packet['code'] == FAILURE_CODE:
            self.success = False
            print("Could not authenticate. Reason from the authenticator:", self.packet['data'])

    def send_bind_request(self):
        print("Start negotiate Remote Listen's port", self.remote_port)
        self.code, self.data = BIND_REQUEST_CODE, str(self.remote_port)
        self.create_protocol_packet()
        self.send_packet()

    def parse_bind_response(self):
        if self.packet['code'] != BIND_RESPONSE_CODE:
            raise ProtocolException(self.packet['code'])
        if self.packet['identifier'] != self.identifier:
            raise IdentifierException(self.packet['identifier'])
        print('Remote Listen is listening at', int(self.packet['data']))

    def handshake(self):
        self.packet = self.receive_packet()
        self.parse_challenge()
        self.send_response()

        self.packet = self.receive_packet()
        self.parse_result()
        if not self.success: return
        self.send_bind_request()

        self.packet = self.receive_packet()
        self.parse_bind_response()


class authenticator(base_chap):
    def __init__(self, args):
        self.port = args.port
        user_list = {}
        for user in args.user_pwd.split(','):
            identity, secret = user.split(':', 1)
            user_list[identity] = secret
        self.user_list = user_list
        self.listen()
        self.start_handhsake()

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', self.port))  # Host == '' means any local IP address
        print("Listening at 0.0.0.0:", self.port)
        sock.listen(1)
        self.sock, addr = sock.accept()
        print('Socket from ' + str(addr[0]) + ':' + str(addr[1]))

    def send_challenge(self):
        self.identifier = random.randint(0, 255)
        # Create some random challenge, using the hash of a string
        # composed of 60 random integer number in the range
        # [1,100000000]
        self.challenge = hashlib.sha1(''.join(map(str, random.sample(range(10000000), 60))).encode()).digest()
        challenge_size = struct.pack('!B', len(self.challenge))
        self.data = challenge_size + self.challenge
        self.code = CHALLENGE_CODE
        self.create_protocol_packet()
        print("Creating challenge with identifier:", self.identifier)
        self.send_packet()

    def parse_response(self):
        if self.packet['code'] != RESPONSE_CODE:
            raise ProtocolException(self.packet['code'])
        if self.packet['identifier'] != self.identifier:
            raise IdentifierException(self.packet['identifier'])
        response_len = struct.unpack('!B', bytes((self.packet['data'][0],)))[0]
        self.response = self.packet['data'][1:response_len + 1]
        self.identity = self.packet['data'][response_len + 1:]
        print("Processing response with identifier:", self.packet['identifier'])

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
            self.code = SUCCESS_CODE
            self.data = ''
            print('Verify successfully!')
        else:
            self.code = FAILURE_CODE
            self.data = 'Identity or secret is incorrect'
        self.create_protocol_packet()
        self.send_packet()

    def parse_bind_request(self):
        if self.packet['code'] != BIND_REQUEST_CODE:
            raise ProtocolException(self.packet['code'])
        if self.packet['identifier'] != self.identifier:
            raise IdentifierException(self.packet['identifier'])
        self.bind_port = int(self.packet['data'])

    def send_bind_response(self):
        if self.bind_port == 0:
            self.bind_port = random.randint(1025, 65535)
        print('Listening at', self.bind_port)
        self.code = BIND_RESPONSE_CODE
        self.data = str(self.bind_port)
        self.create_protocol_packet()
        self.send_packet()

    def handshake(self):
        self.send_challenge()
        self.packet = self.receive_packet()
        self.parse_response()
        valid = self.verify_response()

        self.send_result(valid)
        if not valid: raise VarifyError()
        self.packet = self.receive_packet()
        self.parse_bind_request()

        self.send_bind_response()


def arg_parse():
    example = '''example: 
            python pylcx_chap.py -m listen -p 8000 -u u1:p1,u2:p2
            python pylcx_chap.py -m slave -r 127.0.0.1:8000 -u u1:p1 -p 8001 -l 127.0.0.1:8002'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='async LCX with CHAP',
                                     epilog=example)
    parser.add_argument('-m', dest='mode', choices=['slave', 'listen'], required=True,
                        help='slave or listen')
    parser.add_argument('-p', dest='port', required=True, type=base_chap.check_port,
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
        authenticator(args)
    elif args.mode == 'slave':
        peer(args)


if __name__ == '__main__':
    main()
