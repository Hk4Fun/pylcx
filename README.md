# pylcx

![](http://ww1.sinaimg.cn/large/006giLD5ly1g12m241nh0j31gq0tnmzz.jpg)

基于 **CHAP 协议**的**多用户异步**端口转发工具，提供 Web 端的管理和监控平台，实现基于时长和流量的配额管理，实时统计用户使用流量情况并生成详单，以图表的形式展示于前端

协议：增强型CHAP协议

前端：vue.js + vuex + vue-router + vue-cli + axios + element-ui +  v-chart

后端：asyncio + sanic + sanic_cors + sanic_jwt + aiomysql

## 整体架构

### 单用户模式（BS架构，sanic 和 mysql 都在Remote Listen）



![](http://ww1.sinaimg.cn/large/006giLD5ly1g12mgmtglrj30vt0giq5h.jpg)



### 多用户模式（图中省去BS架构图，具体见上图）



![](http://ww1.sinaimg.cn/large/006giLD5ly1g12micy12lj30yc0mf77y.jpg)



## 协议设计

### 初始协议



![](http://ww1.sinaimg.cn/large/006giLD5ly1g12mb89dgdj30va0lctg3.jpg)



### 增强型 CHAP 协议（修改握手部分）



![](http://ww1.sinaimg.cn/large/006giLD5gy1g12ogh3dopj310v0mwade.jpg)

## 参数说明

```
(back_end) root@iZ2zehx50rbasf3o9jdehaZ:~/pylcx/back_end# python main.py -h
usage: main.py [-h] {listen,slave} ...

async LCX with CHAP

positional arguments:
  {listen,slave}  choose a mode to run
    listen        run in listen mode
    slave         run in slave mode

optional arguments:
  -h, --help      show this help message and exit
```



```
(back_end) root@iZ2zehx50rbasf3o9jdehaZ:~/pylcx/back_end# python main.py listen -h
usage: main.py listen [-h] -p PORT [-a ADDR] [-v]

optional arguments:
  -h, --help     show this help message and exit
  -p PORT        Port listen for slave side
  -a ADDR        Address for a web server to manage users, default
                 0.0.0.0:8000
  -v, --verbose  verbose log (repeat for more verbose)
```



```
(back_end) root@iZ2zehx50rbasf3o9jdehaZ:~/pylcx/back_end# python main.py slave -h
usage: main.py slave [-h] [-b BIND] -l LOCAL -r REMOTE -u USER [-v]

optional arguments:
  -h, --help     show this help message and exit
  -b BIND        Open a bind port at remote listen, connected by remote
                 client, default 0 (random port)
  -l LOCAL       Local server address in format host:port
  -r REMOTE      Remote listen address in format host:port
  -u USER        User in format username:password
  -v, --verbose  verbose log (repeat for more verbose)
```



## 主要模块

![](http://ww1.sinaimg.cn/large/006giLD5ly1g12md7xpoxj30ih0ft74y.jpg)

`main.py` : 程序入口，读取命令行参数并配置日志

`chap.py` : 协议底层的数据读写模块

`listen.py` : remote listen 的核心模块

`slave.py` : local slave 的核心模块

`server.py` : sanic app 的核心模块

用户密码使用 MD5 加盐加密存储，协议的握手使用随机因子防止重放攻击

前后端分离，后端使用 Sanic 提供 RESTful API，并使用 JWT 进行跨域认证

协议和双向端口转发都基于 asyncio 实现，且数据库使用 aiomysql，整个后端异步非阻塞





