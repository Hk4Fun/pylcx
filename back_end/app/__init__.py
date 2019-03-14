import logging
import asyncio
import argparse

# set args
parser = argparse.ArgumentParser(description='async LCX with CHAP')
subparsers = parser.add_subparsers(dest='mode', help='choose a mode to run')

parser_listen = subparsers.add_parser('listen', help='run in listen mode')
parser_listen.add_argument('-p', dest='port', required=True, type=int, help='Port listen for slave side')
parser_listen.add_argument('-a', dest='addr', default='0.0.0.0:8000',
                           help='Address for a web server to manage users, default 0.0.0.0:8000')
parser_listen.add_argument('-v', '--verbose', action='count', dest='level',
                    default=2, help='verbose log (repeat for more verbose)')


parser_slave = subparsers.add_parser('slave', help='run in slave mode')
parser_slave.add_argument('-b', dest='bind', type=int, default=0,
                          help='Open a bind port at remote listen, connected by remote client, '
                               'default 0 (random port)')
parser_slave.add_argument('-l', dest='local', required=True, help='Local server address in format host:port')
parser_slave.add_argument('-r', dest='remote', required=True, help='Remote listen address in format host:port')
parser_slave.add_argument('-u', dest='user', required=True, help='User in format username:password')
parser_slave.add_argument('-v', '--verbose', action='count', dest='level',
                    default=2, help='verbose log (repeat for more verbose)')

args = parser.parse_args()

# set logger
log = logging.getLogger(__file__)
levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
formatter = logging.Formatter('%(asctime)s %(levelname)s %(lineno)d %(message)s', '%H:%M:%S')
log_handler = logging.StreamHandler()
log.setLevel(levels[min(args.level, len(levels) - 1)])
log_handler.setFormatter(formatter)
log.addHandler(log_handler)
log.setLevel(levels[min(args.level, len(levels) - 1)])

# get loop
loop = asyncio.get_event_loop()
