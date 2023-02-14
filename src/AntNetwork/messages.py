'''
Created on Feb 28, 2014

@author: jh
'''

from struct import *
import ctypes
import socket 

_action = Struct("16B")
_hello = Struct("H16s")
_team = Struct("HH16s")
_object = Struct("BBHH")
_turn = Struct("h")
_word = Struct("H")

def send_action(sock, actions):
    sock.send(_action.pack(actions[0],
                            actions[1],
                            actions[2],
                            actions[3],
                            actions[4],
                            actions[5],
                            actions[6],
                            actions[7],
                            actions[8],
                            actions[9],
                            actions[10],
                            actions[11],
                            actions[12],
                            actions[13],
                            actions[14],
                            actions[15]
                            ))

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
    sock.send(_hello.pack(typ, name))

def receive_hello(sock):
    try:
        return _hello.unpack_from(sock.recv(_hello.size))
    except:
        print("Error receiving hello message from socket {}".format(sock.fileno()))
        return (0, "-error-")
    
def send_turn(sock, Id, teams, objects):
    buf = ctypes.create_string_buffer(_turn.size +
                                      _team.size * len(teams) + 
                                      _word.size + 
                                      _object.size * len(objects))
    _turn.pack_into(buf, 0, Id)
    offset = _turn.size
    if len(teams) != 16:
        raise Exception
    for t in teams:
        _team.pack_into(buf, offset, t[0], t[1], t[2])
        offset += _team.size
    _word.pack_into(buf, offset, len(objects))
    offset += _word.size
    for o in objects:
        try:
            _object.pack_into(buf, offset, o[0], o[1], o[2], o[3])
        except:
            print("Error sending turn object: {}".format(o))
            raise
        offset += _object.size
    
    sock.send(buf)

def receive_turn(sock):
    buf = sock.recv(_turn.size + 16 * _team.size + _word.size)
    Id, = _turn.unpack_from(buf)
    teams = []
    offset = _turn.size
    for _ in range(16):
        teams.append(_team.unpack_from(buf, offset))
        offset += _team.size
    
    numobj, = _word.unpack_from(buf, offset)
    
    offset = 0
    buf = sock.recv(_object.size * numobj, socket.MSG_WAITALL)    
    objects = []
    for _ in range(numobj):
        objects.append(_object.unpack_from(buf, offset))
        offset += _object.size
    return (Id, teams, objects)