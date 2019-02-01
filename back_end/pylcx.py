import logging
import argparse
import random
import hashlib
import struct
import asyncio
import time
from enum import Enum, unique
from collections import namedtuple

import aiomysql
from sanic import Sanic
from sanic.response import json, file
from sanic.views import HTTPMethodView
from sanic_cors import CORS
from sanic_jwt import Initialize
from sanic_jwt.exceptions import AuthenticationFailed
from sanic_jwt.decorators import scoped, inject_user

#  |local server|<--_--->|local slave|<=====>|remote listen|<------>|remote client|

db_host = '127.0.0.1'
db_port = 3306
db_user = 'hk4fun'
db_pwd = 'hk4fun'
db_name = 'pylcx'

listen_bind_dict = {}  # key: bind_port   val: writer_for_slave, reader_for_slave
listen_conn_dict = {}  # key: conn_id     val: writer_for_client, reader_for_slave
slave_conn_dict = {}  # key: conn_id      val: writer_for_server
port_traffic_dict = {}  # key: bind_port     val: traffic object
TIMEOUT = 5  # use websocket to send online users
SECRET_KEY = '123qweasdzxc<>?'

last_conn_id = 0
loop = asyncio.get_event_loop()
User = namedtuple('User', ['user_id', 'scope'])
User.to_dict = User._asdict


async def authenticate(request):
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    login_as = request.json.get('login_as', None)

    if not username or not password:
        raise AuthenticationFailed("Missing username or password.")

    async with db.cursor() as cur:
        await cur.execute("SELECT id, salt, secret, is_admin FROM user WHERE username=%s", [username])
        res = await cur.fetchone()

    if res is None:
        raise AuthenticationFailed("Username or password incorrect")

    id, salt, secret, is_admin = res
    check_secret = hashlib.md5(password.encode() + salt.encode()).hexdigest()

    if check_secret != secret:
        raise AuthenticationFailed("Username or password incorrect")

    if login_as == 'user':
        return User(user_id=id, scope=['user'])
    elif login_as == 'admin':
        if is_admin:
            return User(user_id=id, scope=['admin'])
        else:
            raise AuthenticationFailed("Username or password incorrect")
    else:
        raise AuthenticationFailed("Username or password incorrect")


async def retrieve_user(request, payload):
    user_id = payload.get('user_id', None)
    if user_id:
        async with db.cursor() as cur:
            await cur.execute("SELECT is_admin FROM user WHERE id=%s", [user_id])
            res = await cur.fetchone()
        if res is not None:
            is_admin, = res
            return User(user_id=user_id, scope=('admin' if is_admin else 'user'))


app = Sanic()
CORS(app)
Initialize(app,
           authenticate=authenticate,
           secret=SECRET_KEY,
           add_scopes_to_payload=lambda user: user.scope,
           retrieve_user=retrieve_user)
app.static('/js', './static/js')
app.static('/fonts', './static/fonts')
app.static('/css', './static/css')
app.static('/favicon.ico', './static/favicon.ico')


@unique
class Cmd(Enum):
    username, salt, secret, res, bind, conn, data = range(7)


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


@app.get("/")
async def index(request):
    return await file('index.html')


class UserView(HTTPMethodView):
    @staticmethod
    @inject_user()
    @scoped(['user', 'admin'], require_all=False)
    async def get(request, user):
        id = request.raw_args.get('id', None)
        if id is None:
            return json({})
        if user.scope == 'user' and user.user_id != int(id):
            return json({})
        res = {}
        async with db.cursor() as cur:
            await cur.execute("SELECT username, quota, is_admin FROM user WHERE id=%s", [id])
            row = await cur.fetchone()
        if row:
            username, quota, is_admin = row
            res = {"id": id, "username": username, 'quota': quota, 'is_admin': is_admin}
        else:
            return json({})

        async with db.cursor() as cur:
            await cur.execute("SELECT sum(upload) as total_upload, "
                              "sum(download) as total_download, "
                              "sum(timestampdiff(minute, login_time, logout_time)) as online_time "
                              "FROM detail WHERE user_id=%s", [id])
            data = await cur.fetchone()
        if data == (None, None, None):
            total_upload = total_download = online_time = 0
        else:
            total_upload, total_download, online_time = data
        res.update({'total_upload': total_upload, 'total_download': total_download,
                    'used': total_upload + total_download, 'online_time': online_time})
        return json(res)

    @staticmethod
    @scoped(['admin'])
    async def post(request):
        username = request.json.get('username', None)
        async with db.cursor() as cur:
            await cur.execute("SELECT id from user where username=%s", [username])
            res = await cur.fetchone()
        if res:
            return json({'id': None, 'err': 'username already exists'})
        password = request.json.get('password', None)
        salt = ''.join(random.choice('qwertyuiopasdfghjklzxcvbnm1234567890') for _ in range(32))
        secret = hashlib.md5(password.encode() + salt.encode()).hexdigest()
        quota = float(request.json.get('quota', None))
        is_admin = int(request.json.get('is_admin', None))
        async with db.cursor() as cur:
            await cur.execute("INSERT INTO user(username, salt, secret, quota, is_admin) VALUES(%s,%s,%s,%s,%s)",
                              [username, salt, secret, quota, is_admin])
            await cur.execute("SELECT LAST_INSERT_ID()")
            id = (await cur.fetchone())[0]
        return json({"id": id})

    @staticmethod
    @scoped(['admin'])
    async def delete(request):
        id = request.raw_args.get('id', None)
        if id:
            async with db.cursor() as cur:
                await cur.execute("DELETE FROM user WHERE id = %s", [id])
            return json({"delete": "ok"})
        else:
            return json({"delete": "error"})

    @staticmethod
    @scoped(['admin'])
    async def put(request):
        user_id = request.raw_args.get('id', None)
        quota = request.json.get('quota', None)
        if not user_id or not quota:
            return json({"edit": "error"})
        else:
            async with db.cursor() as cur:
                await cur.execute("UPDATE user SET quota=%s WHERE id = %s", [quota, user_id])
            return json({"edit": "ok"})

    @staticmethod
    @scoped(['user', 'admin'], require_all=False)
    async def options(request):
        return json({})


class UsersView(HTTPMethodView):
    decorators = [scoped(['admin'])]

    async def get(self, request):
        async with db.cursor() as cur:
            await cur.execute("SELECT id, username, quota, is_admin FROM user order by id")
            res = await cur.fetchall()
        user_list = []
        for row in res:
            id, username, quota, is_admin = row
            user_list.append({'id': id, 'username': username, 'quota': quota, 'is_admin': is_admin})
        async with db.cursor() as cur:
            await cur.execute("SELECT sum(upload) as total_upload, "
                              "sum(download) as total_download, "
                              "sum(timestampdiff(minute, login_time, logout_time)) as online_time "
                              "FROM detail group by user_id order by user_id")
            res = await cur.fetchall()
        for idx, user in enumerate(user_list):
            if idx >= len(res):
                total_upload = total_download = online_time = 0
            else:
                total_upload, total_download, online_time = res[idx]
            user.update({'total_upload': total_upload, 'total_download': total_download,
                         'used': total_upload + total_download, 'online_time': online_time})
        return json({"users": user_list})

    async def delete(self, request):
        async with db.cursor() as cur:
            await cur.execute("DELETE FROM user")
        return json({"delete all": "OK"})

    async def options(self, request):
        return json({})


class OnlineUsersView(HTTPMethodView):
    decorators = [scoped(['admin'])]

    async def get(self, request):
        res = []
        for user in port_traffic_dict.values():
            res.append({'id': user.user_id, 'username': user.username,
                        'host': user.host, 'bind_port': user.bind_port,
                        'upload': user.upload, 'download': user.download,
                        'login_time': user.login_time})
        return json({"online_users": res})

    async def options(self, request):
        return json({})


class DetailView(HTTPMethodView):
    decorators = [scoped(['user', 'admin'], require_all=False)]

    async def get(self, request):
        user_id = request.raw_args['id']
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT login_time, logout_time,"
                " timestampdiff(minute, login_time, logout_time),"
                " upload, download, upload + download, inet_ntoa(host), bind_port "
                "from detail where user_id=%s", [user_id])
            res = await cur.fetchall()
        detail_list = []
        for row in res:
            login_time, logout_time, online_time, upload, download, used, host, bind_port = row
            login_time = login_time.strftime("%Y-%m-%d %H:%M:%S")
            logout_time = logout_time.strftime("%Y-%m-%d %H:%M:%S")
            detail_list.append({'host': host, 'login_time': login_time,
                                'logout_time': logout_time, 'online_time': online_time,
                                'upload': upload, 'download': download, 'used': used, 'bind_port': bind_port})
        return json({'detail': detail_list})

    async def options(self, request):
        return json({})


@app.websocket('/online_users')
async def online(request, ws):
    online_users = len(port_traffic_dict)
    await ws.send(str(online_users))
    while True:
        await asyncio.sleep(TIMEOUT)
        if len(port_traffic_dict) != online_users:
            online_users = len(port_traffic_dict)
            await ws.send(str(online_users))


app.add_route(UserView.as_view(), '/user')
app.add_route(UsersView.as_view(), '/users')
app.add_route(DetailView.as_view(), '/detail')
app.add_route(OnlineUsersView.as_view(), '/online')


async def msg_recv(role, reader, writer, fmt, *expect_cmds):
    direct_dict = {'L': '<', 'R': '>'}
    direct = direct_dict[role]
    result = [True] + [None] * len(fmt)

    peer_host, peer_port, = writer.get_extra_info('peername')
    self_host, self_port, = writer.get_extra_info('sockname')

    try:
        data = await reader.readexactly(2)
        if not data:
            log.error('S L{}R C recv {:5} < {:5} err EOF msg_len'.format(direct, self_port, peer_port))
            writer.close()
            return result
        msg_len, = struct.unpack('!H', data)
        if not msg_len:
            log.error('S L{}R C recv {:5} < {:5} err ZERO msg_len'.format(direct, self_port, peer_port))
            writer.close()
            return result

        msg = await reader.readexactly(msg_len)
        if not msg:
            log.error('S L{}R C recv {:5} < {:5} err EOF msg_body'.format(direct, self_port, peer_port))
            writer.close()
            return result
        if Cmd(int(msg[0])) not in expect_cmds:
            log.error('S L{}R C recv {:5} < {:5} err cmd {} expect {}'.format(direct, self_port, peer_port,
                                                                              Cmd(int(msg[0])).name,
                                                                              expect_cmds))
            writer.close()
            return result
    except Exception as e:
        log.warning('S L{}R C shut {:5} < {:5} exc {}'.format(direct, self_port, peer_port, e.args))
        writer.close()
        return result

    unpack_dict = {'B': 1, 'H': 2}
    pos = 0
    try:
        for i, c in enumerate(fmt):
            if c == 'S':
                s_len, = struct.unpack('!H', msg[pos:pos + 2])
                pos += 2
                s_val, = struct.unpack('!{}s'.format(s_len), msg[pos:pos + s_len])
                pos += s_len
                result[i + 1] = s_val
            else:
                v_len = unpack_dict[str(c)]
                v_val, = struct.unpack('!' + str(c), msg[pos:pos + v_len])
                pos += v_len
                result[i + 1] = v_val
    except Exception as e:
        log.error('S L{}R C recv {:5} < {:5} exc {}'.format(direct, self_port, peer_port, e.args))
        writer.close()
        return

    log.info('S L{}R C {} {:5} < {:5} {}'.format(direct, Cmd(int(msg[0])).name, self_port, peer_port, result[2:]))
    result[0] = False
    return result


def msg_send(role, writer, fmt, *args):
    direct_dict = {'L': '>', 'R': '<'}
    direct = direct_dict[role]

    peer_host, peer_port, = writer.get_extra_info('peername')
    self_host, self_port, = writer.get_extra_info('sockname')

    log.info('S L{}R C {} {:5} > {:5} {}'.format(direct, args[0].name, self_port, peer_port, args[1:]))

    struct_fmt = '!'
    struct_args = []
    for i, c in enumerate(fmt):
        if c == 'S':
            struct_fmt += 'H{}s'.format(len(args[i]))
            struct_args.extend([len(args[i]), args[i]])
        else:
            struct_fmt += str(c)
            struct_args.append(args[i] if i != 0 else args[i].value)

    data = struct.pack(struct_fmt, *struct_args)
    msg = struct.pack('!H', len(data)) + data
    writer.write(msg)


async def raw_recv(role, reader, writer):
    direct_dict = {'L': ('>', ' '), 'R': (' ', '<')}
    direct = direct_dict[role]

    _, peer_port, = writer.get_extra_info('peername')
    _, self_port, = writer.get_extra_info('sockname')

    try:
        data = await reader.read(65530)  # max data_content is 65528 = 65535 - 1(cmd) - 2(conn_id) -2(data_len)
        if not data:
            log.info('S{}L R{}C shut {} < {}'.format(direct[0], direct[1], self_port, peer_port))
            writer.close()
            return
    except Exception as e:
        log.error('S{}L R{}C shut {} < {} exc {}'.format(direct[0], direct[1], self_port, peer_port, e.args))
        writer.close()
        raise
    else:
        log.info('S{}L R{}C recv {} < {} {}'.format(direct[0], direct[1], self_port, peer_port, data))
        return data


def raw_send(role, writer, data):
    direct_dict = {'L': ('<', ' '), 'R': (' ', '>')}
    direct = direct_dict[role]

    _, peer_port, = writer.get_extra_info('peername')
    _, self_port, = writer.get_extra_info('sockname')

    log.info('S{}L R{}C send {} > {} {}'.format(direct[0], direct[1], self_port, peer_port, data))
    writer.write(data)


async def connect(host, port, timeout=2):
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port, loop=loop)
            return reader, writer
        except ConnectionRefusedError:
            log.warning('Can not connect {}:{}, try again......'.format(host, port))
            await asyncio.sleep(timeout)


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
            traffic.upload += len(data)  # / 1024 / 1024
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
                    traffic.download += len(data)  # / 1024 / 1024
                    traffic.used += len(data)
                    raw_send('R', writer_for_client, data)


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


def set_log():
    global log
    log = logging.getLogger(__file__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(lineno)d %(message)s', '%H:%M:%S')
    log_handler = logging.StreamHandler()
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(formatter)
    log.addHandler(log_handler)
    log.setLevel(logging.DEBUG)


def set_arg():
    global args
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
    return parser


def main():
    set_log()
    parser = set_arg()
    server = None
    try:
        if args.mode == 'listen':
            coro = asyncio.start_server(listen_do_slave, '0.0.0.0', args.port, loop=loop)
            server = loop.run_until_complete(coro)
            log.info('S L:R C bind 0.0.0.0:{}'.format(args.port))

            global db
            coro = aiomysql.connect(host=db_host, port=db_port, user=db_user,
                                    password=db_pwd, db=db_name, loop=loop, autocommit=True)
            db = loop.run_until_complete(coro)
            log.info('db connect success')

            app_host, app_port = args.addr.split(':')
            asyncio.ensure_future(app.create_server(host=app_host, port=int(app_port)))
            loop.run_forever()
        elif args.mode == 'slave':
            local_host, local_port = args.local.split(':', 1)
            remote_host, remote_port = args.remote.split(':', 1)
            username, password = args.user.split(':', 1)
            loop.run_until_complete(
                slave_do_listen(remote_host, remote_port, username, password, local_host, local_port, args.bind))
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
