'''
Created on Feb 28, 2014

@author: jh
'''

import socket
from .messages import *

class AntClient(object):
    '''
    classdocs
    '''

    def __init__(self, host, port=5000, name='', actor=True):
        '''
        Constructor
        '''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self.s.connect((host, port))
        
        self.id = -1
        
        send_hello(self.s, actor, name)
        
    def get_turn(self):
        turn = receive_turn(self.s)
        self.id = turn[0]
        return turn
    
    def send_action(self, actions):
        send_action(self.s, actions)
        
    