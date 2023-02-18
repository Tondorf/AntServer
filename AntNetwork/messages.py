#!/usr/bin/env python3
# -*- coding: utf-8 *-*

from AntNetwork.Common import *
from struct import *
import ctypes
import socket

_action = Struct("16B")
_hello = Struct("H16s")
_team = Struct("hH16s")
_object = Struct("BBHH") # typ | cid, ant_id | health, X, Y
_turn = Struct("h")
_word = Struct("H")


def send_action(sock, actions):
    sock.send(_action.pack(*actions[0:ANTS]))


def receive_action(sock, Id):
    try:
        return _action.unpack_from(sock.recv(_action.size))
    except:
        try:
            sock.recv()
        except:
            pass
        print("Error receiving action message from client {}".format(Id))
        return None


def send_hello(sock, typ, name):
    sock.send(_hello.pack(typ, str.encode(name)))


def receive_hello(sock):
    try:
        return _hello.unpack_from(sock.recv(_hello.size))
    except:
        print("Error receiving hello message from socket {}".format(sock.fileno()))
        return -1, None


def send_turn(sock, cid, teams, objects):
    buf = ctypes.create_string_buffer(_turn.size +
                                      _team.size * len(teams) +
                                      _word.size +
                                      _object.size * len(objects))
    _turn.pack_into(buf, 0, cid)
    assert len(teams) == BASES
    offset = _turn.size
    for t in teams:
        _team.pack_into(buf, offset, *t)
        offset += _team.size
    _word.pack_into(buf, offset, len(objects))
    offset += _word.size
    for o in objects:
        try:
            _object.pack_into(buf, offset, *o)
        except:
            print("Error sending turn object: {}".format(o))
            raise
        offset += _object.size

    sock.send(buf)


def receive_turn(sock):
    buf = sock.recv(_turn.size + BASES * _team.size + _word.size)
    (cid,) = _turn.unpack_from(buf)
    teams = []
    offset = _turn.size
    for _ in range(BASES):
        teams.append(_team.unpack_from(buf, offset))
        offset += _team.size

    (numobj,) = _word.unpack_from(buf, offset)

    offset = 0
    buf = sock.recv(_object.size * numobj, socket.MSG_WAITALL)
    objects = []
    for _ in range(numobj):
        objects.append(_object.unpack_from(buf, offset))
        offset += _object.size
    return cid, teams, objects
