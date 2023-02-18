#!/usr/bin/env python
# -*- coding: utf-8 *-*

import sys
import string
import socket
import struct
from enum import Enum
import pygame
from pygame import Rect


PORT = 5000

def myrecv(s, size):  # guttenberged from joe
    data = bytearray()
    while len(data) < size:
        data += s.recv(size - len(data))
    return data


ANT_HEALTH = 10
SUGAR_HEAL = 5
INITIAL_ANTS_PER_TEAM = 10


class World(object):

    __instance = None  # singleton
    nextid = 0

    BASEDIST = 200
    BASESIZE = 20
    BORDER = 90
    WORLD_SIZE = 1000

    ## bases are numerated clockwise where topleft = 0
    ## IMPORTANT: right and bottom boundary arent considered to be a part of the rectangle!!
    HOMEBASES = [Rect(x_y[0]-10, x_y[1]-10, 20, 20) for x_y in [(i * 200 + 100, 100) for i in range(5)]
                    + [(900, 200 * i + 300) for i in range(4)]
                    + [(700 - 200 * i, 900) for i in range(4)]
                    + [(100, 700 - i * 200) for i in range(3)]]
    @staticmethod
    def is_base(x, y):
        for (c, base) in zip(list(range(len(World.HOMEBASES))), World.HOMEBASES):
            if base.collidepoint(x, y):
                return c
        return -1

    def __new__(cls, *args, **kwargs):  # singleton
        if not cls.__instance:
            cls.__instance = super(World, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self):
        self.teams = []
        #self.listener = []
        #self.ants = []
        #self.sugars = [[0 for _ in xrange(WORLD_SIZE)] for _ in xrange(WORLD_SIZE)]
        self.entities = []

    def get_ants(self):
        return [e for e in self.entities if e.isant]

    def get_sugars(self):
        return [e for e in self.entities if e.issugar and not e.isant]

    def get_ants_for_team(self, teamid):
        return [e for e in self.entities if e.isant and e.tid == teamid]

    def get_team_ant(self, teamid, antid):
        return [e for e in self.entities if e.isant and e.tid == teamid and e.antid == antid]

    def search_pos(self, x, y):
        return [e for e in self.entities if e.x == x and e.y == y]


'''
Each Team (20 bytes) is coded as follows:
Offset   Type      Description
0        u16       # sugar at home base
2        u16       # remaining ants
4        16 chars  team name
'''
class Team(object):
    def __init__(self, id=-1, name=''):
        self.__id = id
        self.sugar = 0
        self.ants = INITIAL_ANTS_PER_TEAM
        self.name = name
        self.nextant = 0

    def unpack(self, teamstr):
        self.sugar, self.ants, self.name = struct.unpack('<HH16s', teamstr)

    def pack(self):
        return struct.pack('<HH16s', self.sugar, self.ants, self.name)

    def getid(self):
        return self.__id
    def setid(self, id):
        if id in range(0, 16):
            self.__id = id
    id = property(getid, setid)

    def nextantid(self):
        n=-1
        while True:
            n+=1
            yield n

    def __str__(self):
        return 'T[{},{}A,{}S,{}]'.format(self.__id, self.ants, self.sugar, self.name)


class Entity(object):
    """ Each Object (6 bytes) is coded as follows:
    Offset   Type    Description
    0        u8      upper nibble: object type (0=empty, 1=ant, 2=sugar, 3=ant+sugar), lower nibble: team ID
    1        u8      upper nibble: ant ID, lower nibble: ant health (1-10)
    2        u16     horizontal (X) coordinate
    4        u16     vertical (Y) coordinate
    """

    FMT_STR = '<BBHH'

    def __init__(self, world):
        self.world = world
        self.x = self.y = -1
        self.isant = self.issugar = self.istoxin = False
        self.tid = self.antid = self.anthealth = -1  # ant only

    def unpack(self, objstr):  # client & visu
        objinfo, antinfo, self.x, self.y = struct.unpack(Entity.FMT_STR, objstr)
        entitytype = objinfo >> 4
        self.isant = bool(entitytype % 2)
        self.issugar = bool((entitytype >> 1) % 2)
        self.istoxin = bool((entitytype >> 2) % 2)
        self.tid = objinfo % (2 ** 4) if self.isant else -1
        self.antid = antinfo >> 4 if self.isant else -1
        self.anthealth = antinfo % (2 ** 4) if self.isant else -1

    def pack(self):  # would be used by server
        return struct.pack(Entity.FMT_STR,
                           int(self.isant) + int(self.issugar<<1) << 4 + self.tid,
                           self.antid << 4 + self.anthealth,
                           self.x, self.y)

    def __str__(self):
        if self.isant:
            return 'A{}[{}×{};{}.{}]'.format(('+S' if self.issugar else ''), self.x, self.y, self.tid, self.antid)
        elif self.issugar:
            return 'S[{}×{}]'.format(self.x, self.y)
        elif self.istoxin:
            return 'T[{}×{}]'.format(self.x, self.y)

class AntClient:

    def __init__(self, hostname, client=True, teamname='gAntZ'):
        print("connecting to", hostname)

        self.world = World()
        self.tID = -1

        if len(teamname) > 16:
            teamname = teamname[:16]
        if len(teamname) < 16:
            teamname = teamname + ' ' * (16 - len(teamname))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)  # joe ^^
        try:
            self.sock.connect((hostname, PORT))
        except Exception as e:
            print('cannot connect', e)
            sys.exit(1)
        self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        self.sock.send(struct.pack('<H16s', int(client), teamname.encode('ascii')))

        self.update_world()  # receive first world
        print('received tid %s' % self.tID)

    def update_world(self):
        ''' parse turn packet '''
        self.tID, = struct.unpack('<H', myrecv(self.sock, 2))

        self.world.teams = []
        for tid in range(16):
            newteam = Team(tid)
            newteam.unpack(myrecv(self.sock, 20))  # deserialize team
            self.world.teams.append(newteam)

        num_of_objects, = struct.unpack('<H', myrecv(self.sock, 2))
        #print 'objects:%s' % num_of_objects,

        self.world.entities = []
        for _ in range(num_of_objects):
            newobj = Entity(self.world)
            newobj.unpack(myrecv(self.sock, 6))  # deserialize object
            self.world.entities.append(newobj)
        #print 'ants:%d' % len(filter(lambda e: e.isant and not e.issugar, self.world.entities)),
        #print 'sugars:%d' % len(filter(lambda e: not e.isant and e.issugar, self.world.entities)),
        #print 'ants+sugar:%d' % len(filter(lambda e: e.isant and e.issugar, self.world.entities)),
        #print 'INVALID:%d' % len(filter(lambda e: not e.isant and not e.issugar, self.world.entities))

    def send_actions(self, actions):
        """ send actions """
        assert len(actions) == 16
        self.sock.send(struct.pack('16B', *actions))


class Vis(object):
    size = width, height = 1000 + 380, 1000
    FPS = 60

    class Colors(Enum):
        black    = (  0,   0,   0)
        grey     = (127, 127, 127)
        white    = (255, 255, 255)
        red      = (255,   0,   0)
        redish   = (255,   0, 200)
        green    = (  0, 255,   0)
        greenish = (  0, 255, 255)
        blue     = (  0,   0, 255)
        yellow   = (255, 255,   0)

    teamColors = [
        (0, 110, 110), (240, 0, 0), (0, 240, 0), (160, 0, 80),
        (200, 40, 0), (0, 200, 40), (40, 0, 200), (160, 80, 0),
        (0, 160, 80), (80, 0, 160), (120, 120, 0), (0, 120, 120),
        (120, 0, 120), (80, 160, 0), (0, 80, 160), (240, 0, 0),
    ]

    @staticmethod
    def draw_text(disp, text, font, pos, color):
        label = font.render(text, 1, color)
        posi = label.get_rect(topleft=(pos[0], pos[1]))
        disp.blit(label, posi)

    @staticmethod
    def draw_cross(disp, x, y, color, diag=False, leng=5):
        if not diag:
            pygame.draw.line(disp, color, (x - leng, y), (x + leng, y))
            pygame.draw.line(disp, color, (x, y - leng), (x, y + leng))
        else:
            pygame.draw.line(disp, color, (x - leng, y - leng), (x + leng, y + leng))
            pygame.draw.line(disp, color, (x - leng, y + leng), (x + leng, y - leng))

    def __init__(self, client):
        pygame.init()
        self.font = pygame.font.Font('LiberationMono-Regular.ttf', 18)

        pygame.display.set_caption('Ant!')
        self.DISPLAY = pygame.display.set_mode(self.size)
        self.HomeBaseSurface = pygame.Surface((1001,1000))
        for (c, b) in zip(range(16), World.HOMEBASES):
            pygame.draw.rect(self.HomeBaseSurface, self.teamColors[c], (b.x, b.y, 20, 20))
        pygame.draw.line(self.HomeBaseSurface, self.Colors.white.value, (1000, 0), (1000, 999))

        self.TIMER = pygame.time.Clock()

        self.client = client

    def update(self):
        #self.client.update_world() ### now done outside
        world = self.client.world

        if pygame.event.peek(pygame.QUIT):
            sys.exit()
        pygame.event.clear()

        self.DISPLAY.fill(Vis.Colors.black.value)
        self.DISPLAY.blit(self.HomeBaseSurface, (0, 0))

        for e in world.entities:
            if e.isant and e.istoxin:
                self.DISPLAY.set_at((e.x, e.y), Vis.Colors.greenish.value)
            elif e.isant and e.issugar:
                self.DISPLAY.set_at((e.x, e.y), Vis.Colors.redish.value)
            elif e.istoxin:
                self.DISPLAY.set_at((e.x, e.y), Vis.Colors.green.value)
            elif e.issugar:
                self.DISPLAY.set_at((e.x, e.y), Vis.Colors.white.value)
            elif e.isant:
                self.DISPLAY.set_at((e.x, e.y), Vis.Colors.red.value)
            else:
                print("what is it with this entity?", e)

        self.draw_text(self.DISPLAY, 'AntServer Teams', self.font, (1100, 20), Vis.Colors.white.value)
        self.draw_text(self.DISPLAY, 'ID Ants Score Name', self.font, (1020, 50), Vis.Colors.white.value)
        for t in world.teams:
            name = ''.join([chr(c) for c in t.name if chr(c) in string.printable])
            self.draw_text(self.DISPLAY,
                "{:>2}   {:>2} {:>5} {}".format(t.id, t.ants, t.sugar, name),
                self.font, (1020, 80 + t.id * 20), Vis.teamColors[t.id]
            )

        self.TIMER.tick(self.FPS)
        pygame.display.update()
