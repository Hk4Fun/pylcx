import asyncio
import random
import hashlib
from collections import namedtuple

from sanic import Sanic
from sanic.response import json, file
from sanic.views import HTTPMethodView
from sanic_cors import CORS
from sanic_jwt import Initialize
from sanic_jwt.exceptions import AuthenticationFailed
from sanic_jwt.decorators import scoped, inject_user
import aiomysql

from .settings import *
from .listen import port_traffic_dict
from . import loop, log

User = namedtuple('User', ['user_id', 'scope'])
User.to_dict = User._asdict
# connect db
db_coro = aiomysql.connect(host=db_host, port=db_port, user=db_user,
                           password=db_pwd, db=db_name, loop=loop, autocommit=True)
db = loop.run_until_complete(db_coro)
log.info('db connect success')


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


sanic_app = Sanic()
CORS(sanic_app)
Initialize(sanic_app,
           authenticate=authenticate,
           secret=SECRET_KEY,
           add_scopes_to_payload=lambda user: user.scope,
           retrieve_user=retrieve_user)


@sanic_app.get("/")
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


@sanic_app.websocket('/online_users')
async def online(request, ws):
    online_users = len(port_traffic_dict)
    await ws.send(str(online_users))
    while True:
        await asyncio.sleep(TIMEOUT)
        if len(port_traffic_dict) != online_users:
            online_users = len(port_traffic_dict)
            await ws.send(str(online_users))


sanic_app.static('/js', './static/js')
sanic_app.static('/fonts', './static/fonts')
sanic_app.static('/css', './static/css')
sanic_app.static('/favicon.ico', './static/favicon.ico')
sanic_app.add_route(UserView.as_view(), '/user')
sanic_app.add_route(UsersView.as_view(), '/users')
sanic_app.add_route(DetailView.as_view(), '/detail')
sanic_app.add_route(OnlineUsersView.as_view(), '/online')
