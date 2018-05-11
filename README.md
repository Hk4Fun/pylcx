![pylcx_chap][1]

- 使用`asyncio`的`async`和`await`，全程异步非阻塞，需要python3.5以上

- `Remote Listen`初始只向内开启一个监听端口,向外的监听端口由`Local Slave`在端口监听请求消息中指定, 如果消息中的端口参数为0,表示由`Remote Listen`随机选择一个端口,由端口监听应答消息回应给`Local Slave`.
 
- `Remote Listen`执行:
python listen.py -p 8000 -u u1:p1,u2:p2
参数说明
-p 指定向内的监听端口
-u 指定用户名和密码,用户名和密码之间通过冒号隔开,多个用户之间用逗号隔开

- `Local Slave`执行:
python slave.py -r 127.0.0.1:8000 -u u1:p1 -p 8001 -l 127.0.0.1:8002
参数说明
-r 指定`Remote Listen`向内的监听地址,地址和端口用冒号隔开
-u 指定用户名和密码,用户名和密码之间通过冒号隔开
-p 指定需要`Remote Listen`开启的端口,可以设置为0,由`Remote Listen`随机选择
-l 指定`Local Server`的监听地址,地址和端口用冒号隔开

- `Local Server`监听8002端口, `Remote Client`连接8001端口后,会建立与`Local Server`之间的双向数据流.

- 为了不混乱socket，`Remote Listen`同一时间只与一个`Local Slave`进行chap握手验证和转发数据流

- `utils/pylcx.py`没有加入chap，但足够简洁；`utils/lcx_test.py`是针对`pylcx_chap.py`的测试

- 关于asyncio在windows上的一个bug：
  http://stackoverflow.com/questions/27480967/why-does-the-asyncios-event-loop-suppress-the-keyboardinterrupt-on-windows
  https://github.com/python/asyncio/issues/191
  https://bugs.python.org/issue23057
  

  [1]: http://ox186n2j0.bkt.clouddn.com/pylcx_chap.png "pylcx_chap"