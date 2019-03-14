import struct
from enum import Enum, unique

from . import log


#  |local server|<--_--->|local slave|<=====>|remote listen|<------>|remote client|


@unique
class Cmd(Enum):
    username, salt, secret, res, bind, conn, data = range(7)


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
