import asyncio
import hashlib

from . import loop
from .chap import *

#  |local server|<--_--->|local slave|<=====>|remote listen|<------>|remote client|

slave_conn_dict = {}  # key: conn_id      val: writer_for_server


async def connect(host, port, timeout=2):
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port, loop=loop)
            return reader, writer
        except ConnectionRefusedError:
            log.warning('Can not connect {}:{}, try again......'.format(host, port))
            await asyncio.sleep(timeout)


async def slave_do_server(reader, writer, conn_id, writer_for_listen):
    while True:
        try:
            data = await raw_recv('L', reader, writer)
        except Exception:
            return
        if data is not None:
            msg_send('L', writer_for_listen, 'BHS', Cmd.data, conn_id, data)
        else:
            if conn_id in slave_conn_dict:
                slave_conn_dict.pop(conn_id, None)
                msg_send('L', writer_for_listen, 'BHS', Cmd.conn, conn_id, b'0')
            return


async def slave_handshake_listen(remote_host, remote_port, username, password, bind_port=0):
    reader, writer = await connect(remote_host, remote_port)
    msg_send('L', writer, 'BS', Cmd.username, username.encode())
    err, cmd, salt, nonce = await msg_recv('L', reader, writer, 'BSS', Cmd.salt)
    if err:
        writer.close()
        return None, None
    secret = hashlib.md5(password.encode() + salt).hexdigest()
    secret = hashlib.md5(secret.encode() + nonce).hexdigest()
    msg_send('L', writer, 'BSS', Cmd.secret, username.encode(), secret.encode())
    err, cmd, res = await msg_recv('L', reader, writer, 'BS', Cmd.res)
    if err:
        writer.close()
        return None, None
    if res == b'0':
        writer.close()
        return None, None
    msg_send('L', writer, 'BH', Cmd.bind, bind_port)
    _port = bind_port
    err, cmd, bind_port = await msg_recv('L', reader, writer, 'BH', Cmd.bind)
    if err or bind_port == 0:
        log.error('bind port {} already in use'.format(_port))
        writer.close()
        return None, None
    return reader, writer


async def slave_do_listen(remote_host, remote_port, username, password, local_host, local_port, bind_port=0):
    reader, writer = await slave_handshake_listen(remote_host, remote_port, username, password, bind_port)
    if reader is None or writer is None:
        return
    connections = []
    while True:
        err, cmd, conn_id, data = await msg_recv('L', reader, writer, 'BHS', Cmd.conn, Cmd.data)
        if err:  # handle remote listen close
            if connections:
                list(map(lambda conn: conn.cancel(), connections))
            return
        writer_for_server = slave_conn_dict.get(conn_id, None)
        if cmd == Cmd.conn.value:
            state = int(data)
            if state == 1:  # 1-connect
                r, w = await connect(local_host, local_port)
                _, sock_port = w.get_extra_info('sockname')
                log.info('S<L R C open {:5} > {:5}'.format(sock_port, local_port))
                slave_conn_dict[conn_id] = w
                connections.append(loop.create_task(slave_do_server(r, w, conn_id, writer)))
            elif writer_for_server:  # 0-disconnect
                self_host, self_port, = writer_for_server.get_extra_info('sockname')
                log.info('S<L R C shut {:5} > {:5}'.format(self_port, local_port))
                slave_conn_dict.pop(conn_id)
                writer_for_server.close()
        elif cmd == Cmd.data.value:
            if writer_for_server is None:
                msg_send('L', writer, 'BHS', Cmd.conn, conn_id, b'0')
            else:
                raw_send('L', writer_for_server, data)
