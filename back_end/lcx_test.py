import argparse
import asyncio
import logging

client_data = b'ABCDEFG'
server_data = b'1234567'

async def client_do_listen(bind_host, bind_port):
    sock_port = '-----'
    try:
        reader, writer = await asyncio.open_connection(bind_host, bind_port, loop=loop)
        sock_host, sock_port, = writer.get_extra_info('sockname')
        log.info('S L R<C open {:5} > {:5}'.format(sock_port, bind_port))

        log.info('S L R<C data {:5} > {:5} {}'.format(sock_port, bind_port, client_data))
        writer.write(client_data)
        data = await reader.readexactly(len(server_data))
        if data != server_data:
            log.error('S L R>C data {:5} < {:5} {} error server_data {}'.format(sock_port, bind_port, data, server_data))
            writer.close()
            return

        log.info('S L R>C data {:5} < {:5} {}'.format(sock_port, bind_port, data))

        if args.shut_mode == 'c':
            log.info('S L R<C shut {:5} > {:5}'.format(sock_port, bind_port))
            writer.close()
            return
        data = await reader.read(1)
        if not data:
            log.info('S L R>C shut {:5} < {:5}'.format(sock_port, bind_port))

    except Exception as e:
        log.info('S L R>C shut {:5} < {:5} exc {}'.format(sock_port, bind_port, e.args))


async def server_do_slave(reader, writer):
    peer_host, peer_port, = writer.get_extra_info('peername')
    sock_host, sock_port, = writer.get_extra_info('sockname')
    log.info('S<L R C open {:5} < {:5}'.format(sock_port, peer_port))

    try:
        log.info('S>L R C data {:5} > {:5} {}'.format(sock_port, peer_port, server_data))
        writer.write(server_data)
        data = await reader.readexactly(len(client_data))
        if data != client_data:
            log.error('S<L R C data {:5} < {:5} {} error client_data {}'.format(sock_port, peer_port, data, client_data))
            writer.close()
            return

        log.info('S<L R C data {:5} < {:5} {}'.format(sock_port, peer_port, data))

        if args.shut_mode == 's':
            log.info('S>L R C shut {:5} > {:5}'.format(sock_port, peer_port))
            writer.close()
            return
        data = await reader.read(1)
        if not data:
            log.info('S<L R C shut {:5} < {:5}'.format(sock_port, peer_port))

    except Exception as e:
        log.info('S<L R C shut {:5} < {:5} exc {}'.format(sock_port, peer_port, e.args))


# log_fmt = logging.Formatter('%(lineno)-3d %(levelname)7s %(funcName)-16s %(message)s')
log_fmt = logging.Formatter('%(lineno)-3d %(levelname)7s %(message)s')
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(log_fmt)
log = logging.getLogger(__file__)
log.addHandler(log_handler)
log.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description='asyncio lcx test.')
parser.add_argument('-b', dest='bind_addr', required=True, help='Bind address in remote-listen')
parser.add_argument('-l', dest='server_port', required=True, type=int, help='Local-server port')
parser.add_argument('-s', dest='shut_mode', required=True, help='Shut mode, c:client s:server')
parser.add_argument('-t', dest='test_times', type=int, default=10, help='Times for remote-client connect remote-listen')

args = parser.parse_args()
log.info('='*77)

loop = asyncio.get_event_loop()

coro = 	asyncio.start_server(server_do_slave, '0.0.0.0', args.server_port, loop=loop)
server = loop.run_until_complete(coro)
log.info('S:L R C bind {:5}'.format(args.server_port))

bind_host, bind_port = args.bind_addr.split(':', 1)

# task_list = []
# for t in range(args.test_times):
#     task = loop.create_task(client_do_listen(bind_host, bind_port))
#     task_list.append(task)

# loop.run_until_complete(asyncio.wait([client_do_listen(bind_host, bind_port) for i in range(args.test_times)]))

loop.run_until_complete(asyncio.gather(*[client_do_listen(bind_host, bind_port) for i in range(args.test_times)]))

log.info('all test over')

try:
    loop.run_forever()
except KeyboardInterrupt:
    log.info('bye ~')
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
