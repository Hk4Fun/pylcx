import asyncio

from app import loop, log, args, parser


def main():
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
