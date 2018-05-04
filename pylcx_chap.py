__author__ = 'Hk4Fun'
__date__ = '2018/5/4 12:39'

import argparse
import hashlib
import random
import sys
import socket
import struct
import time
import asyncio
import logging

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


class ProtocolException(Exception):
    def __init__(self, error_code):
        super().__init__(self)
        self.error_code = error_code

    def __str__(self):
        return 'Error packet code {}'.format(self.error_code)


class IdentifierException(Exception):
    def __init__(self, error_id):
        super().__init__(self)
        self.error_id = error_id

    def __str__(self):
        return 'Error identifier {}'.format(self.error_id)


def connect(config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((config['authenticator'], int(config['port'])))
    return sock


def listen(config):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = int(config['port'])
    sock.bind(('', port))  # Host == '' means any local IP address
    print("Listening at 0.0.0.0:", port)
    sock.listen(10)
    conn, addr = sock.accept()
    print('Socket from ' + str(addr[0]) + ':' + str(addr[1]))
    return conn


def send_packet(sock, packet):
    totalsent = 0
    while totalsent < len(packet):
        sent = sock.send(packet[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent


def receive_packet(sock):
    header = sock.recv(header_len)
    if header == '':
        raise RuntimeError("socket connection broken")

    (code, identifier, length) = struct.unpack('!BBH', header)
    packet = header

    while len(packet) < length:
        chunk = sock.recv(length - len(packet))
        if chunk == '':
            raise RuntimeError("socket connection broken")
        packet = packet + chunk

    (code, identifier, length, data) = struct.unpack('!BBH' + str(length - header_len) + 's', packet)
    return {'code': code,
            'identifier': identifier,
            'length': length,
            'data': data}


def create_protocol_packet(code, identifier, data):
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

    packet = struct.pack(pack_format, code, identifier, packet_len, data)

    return packet


def create_challenge():
    identifier = random.randint(0, 255)
    # Create some random challenge, using the hash of a string
    # composed of 60 random integer number in the range
    # [1,100000000]
    hash = hashlib.sha1(''.join(map(str, random.sample(range(10000000), 60))).encode())
    challenge_value = hash.digest()
    challenge_value_size = struct.pack('!B', len(challenge_value))
    data = challenge_value_size + challenge_value
    print("Creating challenge with identifier:", identifier)
    packet = create_protocol_packet(CHALLENGE_CODE, identifier, data)
    return (packet, identifier, challenge_value)


def process_challenge(challenge_packet):
    challenge_len = struct.unpack('!B', bytes((challenge_packet['data'][0],)))[0]
    challenge = challenge_packet['data'][1:challenge_len + 1]
    print("Processing challenge with identifier:", challenge_packet['identifier'])

    return {'identifier': challenge_packet['identifier'],
            'challenge': challenge, }


def create_response(config, challenge):
    hash = hashlib.sha1((chr(challenge['identifier']) + config['secret'] + str(challenge['challenge'])).encode())
    response_value = hash.digest()
    response_value_size = struct.pack('!B', len(response_value))
    identity = config['identity'].encode()
    data = response_value_size + response_value + identity
    print("Creating response with identifier:", challenge['identifier'])
    return create_protocol_packet(RESPONSE_CODE, challenge['identifier'], data)


def process_response(response_packet):
    response_len = struct.unpack('!B', bytes((response_packet['data'][0],)))[0]
    response = response_packet['data'][1:response_len + 1]
    identity = response_packet['data'][response_len + 1:]
    print("Processing response with identifier:", response_packet['identifier'])
    return {'identifier': response_packet['identifier'],
            'response': response,
            'identity': identity}


def verify_response(config, response_data, identifier, challenge):
    print("Verifying response for identifier:", identifier)
    user_list = config['user_list']
    identity = response_data['identity'].decode()
    if identity in user_list:
        secret = user_list[identity]
        hash = hashlib.sha1((chr(identifier) + secret + str(challenge)).encode())
        our_value = hash.digest()
        if our_value == response_data['response']:
            return True
    return False


def create_result(config, response_data, challenge_identifier, challenge):
    if verify_response(config, response_data, challenge_identifier, challenge):
        code = SUCCESS_CODE
        data = ''
    else:
        code = FAILURE_CODE
        data = 'Identity or secret is incorrect'
    return create_protocol_packet(code, challenge_identifier, data), code


def create_bind_request(config, challenge_data):
    remote_port = config['remote_port']
    print("Start negotiate Remote Listen's port", remote_port)
    return create_protocol_packet(BIND_REQUEST_CODE, challenge_data['identifier'], str(remote_port))


def create_bind_response(packet):
    port = int(packet['data'])
    if port == 0:
        port = random.randint(1025, 65535)
    print('Listening at', port)
    return create_protocol_packet(BIND_RESPONSE_CODE, packet['identifier'], str(port))


def peer(config):
    sock = connect(config)
    try:
        packet = receive_packet(sock)
        if packet['code'] != CHALLENGE_CODE:
            raise ProtocolException(packet['code'])

        challenge_data = process_challenge(packet)
        packet = create_response(config, challenge_data)
        send_packet(sock, packet)
        packet = receive_packet(sock)

        if packet['identifier'] != challenge_data['identifier']:
            raise IdentifierException(packet['identifier'])

        if packet['code'] != SUCCESS_CODE and packet['code'] != FAILURE_CODE:
            raise ProtocolException(packet['code'])

        if packet['code'] == SUCCESS_CODE:
            print("Successfully authenticated!")
            packet = create_bind_request(config, challenge_data)
            send_packet(sock, packet)
            packet = receive_packet(sock)
            if packet['code'] != BIND_RESPONSE_CODE:
                raise ProtocolException(packet['code'])

            if packet['identifier'] != challenge_data['identifier']:
                raise IdentifierException(packet['identifier'])

            print('Remote Listen is listening at', int(packet['data']))

        if packet['code'] == FAILURE_CODE:
            print("Could not authenticate. Reason from the authenticator:", packet['data'])

    except ProtocolException as e:
        print(e)
    except IdentifierException as e:
        print(e)
    finally:
        sock.close()


def authenticator(config):
    sock = listen(config)
    try:
        (packet, challenge_identifier, challenge) = create_challenge()
        send_packet(sock, packet)
        packet = receive_packet(sock)
        if packet['code'] != RESPONSE_CODE:
            raise ProtocolException(packet['code'])

        if packet['identifier'] != challenge_identifier:
            raise IdentifierException(packet['identifier'])

        response_data = process_response(packet)
        packet, code = create_result(config, response_data, challenge_identifier, challenge)
        send_packet(sock, packet)

        if code != SUCCESS_CODE:
            print('Verify failed!')
            return

        print('Verify successfully!')
        packet = receive_packet(sock)
        if packet['code'] != BIND_REQUEST_CODE:
            raise ProtocolException(packet['code'])

        if packet['identifier'] != challenge_identifier:
            raise IdentifierException(packet['identifier'])

        packet = create_bind_response(packet)
        send_packet(sock, packet)

    except ProtocolException as e:
        print(e)
    except IdentifierException as e:
        print(e)
    finally:
        sock.close()


def check_port(port):
    port = int(port)
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError('port should be range(0, 65536)')
    return port


def parse_args():
    example = '''example: 
        python pylcx_chap.py -m listen -p 8000 -u u1:p1,u2:p2
        python pylcx_chap.py -m slave -r 127.0.0.1:8000 -u u1:p1 -p 8001 -l 127.0.0.1:8002'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='async LCX with CHAP',
                                     epilog=example)
    parser.add_argument('-m', dest='mode', choices=['slave', 'listen'], required=True,
                        help='slave or listen')
    parser.add_argument('-p', dest='port', required=True, type=check_port,
                        help='inner listen port for CHAP or Remote Listen to open port, random port if 0')
    parser.add_argument('-u', dest='user_pwd', required=True,
                        help='username:password, use comma to separate')
    parser.add_argument('-r', dest='chap_socket',
                        help="addr:port, Remote Listen's inner socket for CHAP")
    parser.add_argument('-l', dest='local_socket',
                        help="addr:port, Local Server's socket to connect")
    return parser.parse_args()


def load_config(args):
    config = {}
    if args.mode == 'listen':
        config['port'] = args.port
        user_list = {}
        for user in args.user_pwd.split(','):
            identity, secret = user.split(':', 1)
            user_list[identity] = secret
        config['user_list'] = user_list
    elif args.mode == 'slave':
        chap_socket = args.chap_socket.split(':', 1)
        config['authenticator'], config['port'] = chap_socket[0], check_port(chap_socket[1])
        config['identity'], config['secret'] = args.user_pwd.split(':', 1)
        # transmit args
        config['remote_port'] = args.port
        local_socket = args.local_socket
        config['connect_server'], config['connect_port'] = local_socket[0], check_port(local_socket[1])
    return config


def main():
    args = parse_args()
    config = load_config(args)
    if args.mode == 'listen':
        authenticator(config)
    elif args.mode == 'slave':
        peer(config)


if __name__ == '__main__':
    main()
