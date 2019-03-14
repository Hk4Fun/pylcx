import random
import asyncio
import time
import hashlib

from . import loop

port_traffic_dict = {}  # key: bind_port     val: traffic object

from .server import db
from .chap import *

#  |local server|<--_--->|local slave|<=====>|remote listen|<------>|remote client|

last_conn_id = 0
listen_bind_dict = {}  # key: bind_port   val: writer_for_slave, reader_for_slave
listen_conn_dict = {}  # key: conn_id     val: writer_for_client, reader_for_slave


class Traffic:
    def __init__(self, user_id, username, quota, used, host, bind_port):
        self.user_id = user_id
        self.username = username
        self.quota = quota
        self.used = used
        self.upload = self.download = 0
        self.login_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.logout_time = None
        self.host = host
        self.bind_port = bind_port

    def __repr__(self):
        return 'Traffic(user_id={}, username={}, quota={}, used={}, host={}, bind_port={})' \
            .format(self.user_id, self.username, self.quota, self.used, self.host, self.bind_port)

    def is_overflow(self):
        return self.used > self.quota


async def logout(traffic):
    traffic.logout_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    async with db.cursor() as cur:
        await cur.execute("insert into detail(user_id, host, bind_port, login_time, logout_time, upload, download) "
                          "values(%s,inet_aton(%s),%s,%s,%s,%s,%s) ",
                          [traffic.user_id, traffic.host, traffic.bind_port,
                           traffic.login_time, traffic.logout_time,
                           traffic.upload, traffic.download])


async def listen_do_client(reader, writer):
    _, peer_port, = writer.get_extra_info('peername')
    _, sock_port, = writer.get_extra_info('sockname')
    log.info('S L R<C open {} < {}'.format(sock_port, peer_port))
    writer_for_slave, reader_for_slave = listen_bind_dict[sock_port]

    global last_conn_id
    last_conn_id += 1
    conn_id = last_conn_id

    msg_send('R', writer_for_slave, 'BHS', Cmd.conn, conn_id, b'1')
    listen_conn_dict[conn_id] = writer, reader_for_slave
    while True:
        data = await raw_recv('R', reader, writer)
        traffic = port_traffic_dict[sock_port]
        if data is None or traffic.is_overflow():
            if traffic.is_overflow():
                log.info('username {}: insufficient traffic'.format(traffic.username))
            if conn_id in listen_conn_dict:
                msg_send('R', writer_for_slave, 'BHS', Cmd.conn, conn_id, b'0')
                listen_conn_dict.pop(conn_id)
            writer.close()
            return
        else:
            traffic.upload += len(data) / 1024 / 1024
            traffic.used += len(data)
            msg_send('R', writer_for_slave, 'BHS', Cmd.data, conn_id, data)


async def listen_handshake_slave(reader, writer):
    peer_host, peer_port, = writer.get_extra_info('peername')
    sock_host, sock_port, = writer.get_extra_info('sockname')

    err, cmd, username = await msg_recv('R', reader, writer, 'BS', Cmd.username)
    if err:
        writer.close()
        return None, None

    async with db.cursor() as cur:
        await cur.execute("SELECT id, salt, quota FROM user WHERE username = %s", [username])
        res = await cur.fetchone()
    if not res:
        log.warning('S L<R C shut {} < {} username:{} not exists'.format(peer_port, sock_port, username))
        writer.close()
        return None, None
    user_id, salt, quota = res
    async with db.cursor() as cur:
        await cur.execute("SELECT sum(upload) + sum(download) FROM detail WHERE user_id = %s", [user_id])
        used, = await cur.fetchone()
    if not used:
        used = 0
    if used > quota:
        log.warning('S L<R C shut {} < {} username {}: insufficient traffic'.format(peer_port, sock_port, username))
        writer.close()
        return None, None
    salt = salt.encode()
    nonce = str(random.randint(100000, 999999)).encode()
    msg_send('R', writer, 'BSS', Cmd.salt, salt, nonce)

    err, cmd, username, secret = await msg_recv('R', reader, writer, 'BSS', Cmd.secret)
    if err:
        writer.close()
        return None, None
    async with db.cursor() as cur:
        await cur.execute("SELECT secret FROM user WHERE username = %s", [username])
        secret2 = (await cur.fetchone())[0]
    if secret != hashlib.md5(secret2.encode() + nonce).hexdigest().encode():
        msg_send('R', writer, 'BS', Cmd.res, '0'.encode())
        writer.close()
        return
    msg_send('R', writer, 'BS', Cmd.res, '1'.encode())

    err, cmd, bind_port = await msg_recv('R', reader, writer, 'BH', Cmd.bind)
    if err:
        return None, None

    coro = asyncio.start_server(listen_do_client, '0.0.0.0', bind_port, loop=loop)
    try:
        server = await asyncio.wait_for(asyncio.ensure_future(coro), None)
    except OSError:  # address(bind port) already in use
        msg_send('R', writer, 'BH', Cmd.bind, 0)
        return None, None
    else:
        bind_port = server.sockets[0].getsockname()[1]
        listen_bind_dict[bind_port] = writer, reader
        port_traffic_dict[bind_port] = Traffic(user_id, username, quota, used, peer_host, bind_port)
        msg_send('R', writer, 'BH', Cmd.bind, bind_port)
        return server, bind_port


async def listen_do_slave(reader, writer):
    server, bind_port = await listen_handshake_slave(reader, writer)
    if server is None:
        return
    while True:
        err, cmd, conn_id, data = await msg_recv('R', reader, writer, 'BHS', Cmd.conn, Cmd.data)
        if err:
            close_list = [(id, w, r) for id, (w, r) in listen_conn_dict.items()]
            for conn_id, writer_for_client, reader_for_slave in close_list:
                if reader_for_slave == reader:
                    writer_for_client.close()
                    listen_conn_dict.pop(conn_id)
            await logout(port_traffic_dict[bind_port])
            listen_bind_dict.pop(bind_port)
            port_traffic_dict.pop(bind_port)
            server.close()
            await server.wait_closed()
            return

        writer_for_client, _ = listen_conn_dict.get(conn_id, (None, None))
        if writer_for_client:
            _, client_port = writer_for_client.get_extra_info('peername')
            if cmd == Cmd.conn.value:
                state = int(data)
                if state == 0:
                    log.info('S L R>C shut {:5} > {:5}'.format(bind_port, client_port))
                    listen_conn_dict.pop(conn_id)
                    writer_for_client.close()
            elif cmd == Cmd.data.value:
                traffic = port_traffic_dict[bind_port]
                if traffic.is_overflow():
                    log.info('username {}: insufficient traffic'.format(traffic.username))
                    if conn_id in listen_conn_dict:
                        msg_send('R', writer, 'BHS', Cmd.conn, conn_id, b'0')
                        writer_for_client.close()
                        listen_conn_dict.pop(conn_id)
                else:
                    traffic.download += len(data) / 1024 / 1024
                    traffic.used += len(data)
                    raw_send('R', writer_for_client, data)
