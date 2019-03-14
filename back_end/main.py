import argparse
import asyncio

from app import loop, log


def main():
    parser = argparse.ArgumentParser(description='async LCX with CHAP')
    subparsers = parser.add_subparsers(dest='mode', help='choose a mode to run')

    parser_listen = subparsers.add_parser('listen', help='run in listen mode')
    parser_listen.add_argument('-p', dest='port', required=True, type=int, help='Port listen for slave side')
    parser_listen.add_argument('-a', dest='addr', default='0.0.0.0:8000',
                               help='Address for a web server to manage users, default 0.0.0.0:8000')

    parser_slave = subparsers.add_parser('slave', help='run in slave mode')
    parser_slave.add_argument('-b', dest='bind', type=int, default=0,
                              help='Open a bind port at remote listen, connected by remote client, '
                                   'default 0 (random port)')
    parser_slave.add_argument('-l', dest='local', required=True, help='Local server address in format host:port')
    parser_slave.add_argument('-r', dest='remote', required=True, help='Remote listen address in format host:port')
    parser_slave.add_argument('-u', dest='user', required=True, help='User in format username:password')
    args = parser.parse_args()
    server = None
    try:
        if args.mode == 'listen':
            from app.listen import listen_do_slave
            from app.server import sanic_app, db
            # start server
            coro = asyncio.start_server(listen_do_slave, '0.0.0.0', args.port, loop=loop)
            server = loop.run_until_complete(coro)
            log.info('S L:R C bind 0.0.0.0:{}'.format(args.port))
            # start sanic_app
            app_host, app_port = args.addr.split(':')
            asyncio.ensure_future(sanic_app.create_server(host=app_host, port=int(app_port)), loop=loop)
            loop.run_forever()
        elif args.mode == 'slave':
            from app.slave import slave_do_listen
            local_host, local_port = args.local.split(':', 1)
            remote_host, remote_port = args.remote.split(':', 1)
            username, password = args.user.split(':', 1)
            loop.run_until_complete(slave_do_listen(remote_host, remote_port, username, password,
                                                    local_host, local_port, args.bind))
        else:
            parser.print_help()
    except KeyboardInterrupt:
        if args.mode == 'listen':
            server.close()
            loop.run_until_complete(server.wait_closed())
        log.info('bye ~')
    finally:
        if args.mode == 'listen':
            db.close()
        loop.close()


if __name__ == '__main__':
    main()
