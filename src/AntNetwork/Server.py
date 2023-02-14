'''
Created on Feb 28, 2014

@author: jh

The playfield is pre-defined: 1000x1000 fields. The playfield contains 16 homebases:

--------------------------
|                        |
|  X    X    X    X    X |
|                        |
|  X                   X |
|                        |
|  X                   X |
|                        |
|  X                   X |
|                        |
|  X    X    X    X    X |
|                        |
---------------------------

Each homebase is 20x20 fields in size. The distance between two neighbouring homebases is
180 fields, each homebase is 90 fields away from the border.
Upper left corner is (0,0). Homebases are numbered clockwise, upper left is 0.

The world map is never transferred, it is considered known.
The server opens a TCP/IP server (port: 5000), to which the clients (1 per team) connect.
Clients can be players (teams) or watchers.

In every 'turn', each ant can move one field in each direction in one step. Two ants that are in direct
neighborhood automatically fight if they are on neighboring fields.
Each round is timed by the server, only the first message per client is used in every round. Each round
is terminated by the 'turn' message (see below).

Clients send messages to the server to act via the TCP/IP link.
The objects (inhabitants and sugar) are sent with every turn to the clients.


A client connection works as follows:

Client                Server
opens connection
                      accept connection
send 'hello' packet
                      answer with 'turn' packet or close connection
loop:
send 'action' packets
                      send 'turn' message as end indicator for each step.
end loop

Clients which do not answer within a certain period get thrown out.

Format of the 'hello' packet:

Offset   Type      Description
0        u16       client type (0=non-team, 1=team)
2        16 chars  team name (if team client, else ignored)

Format of the 'turn' packet:

Offset       Type      Description
0            i16       Team ID of client
2            Team      Team info for team 1 (ID:0)
...
15*20+2      Team      Team info for team 16 (ID:15)
322          u16       nr. of Objects
324          Object    Object 1
...
324+(n-1)*6  Object    Object n

Each Team is coded as follows:

Offset   Type      Description
0        u16       # sugar at home base
2        u16       # remaining ants
4        16 chars  team name

Each Object is coded as follows:

Offset   Type    Description
0        u8      upper nibble: object type (0=empty, 1=ant, 2=sugar, 3=ant+sugar), lower nibble: team ID
1        u8      upper nibble: ant ID, lower nibble: ant health (1-10)
2        u16     horizontal (X) coordinate
4        u16     vertical (Y) coordinate

The 'action' message:
Offset   Type      Description
0        u8        action for ant 0: id of field to move to: 123
                                                             456
...                                                          789
15       u8        action for ant 15

In this scheme, any action for ants not alive any more are ignored. If an ant should not move,
send a 0, 5, (or any number > 9) for this ant.

'''

from random import randint
import math
from . import messages
import socket
import select
import sys
from AntNetwork.messages import *
from time import sleep
import traceback
from datetime import datetime
import time
import random

try:
    import pygame
    have_pygame = True
except:
    have_pygame = False

#have_pygame = False

ANT=1
SUGAR=2
ANTSUGAR=3
HOMEBASE=4

BASEDIST=200
BASESIZE=20
BORDER=90
PLAYFIELDSIZE=1000

ANTID_SHIFT = 4
HEALTH_SHIFT = 8
ID_SHIFT = 12

CLEARANTMASK  = ~ANT
CLEARANTSUGAR = CLEARANTMASK & ~SUGAR
CLEARSUGARMASK = 0xfff0 | ~SUGAR

STARTDELAY=20.0

_move = ( (0,0),
          (-1,-1),
          (0,-1),
          (1,-1),
          (-1,0),
          (0,0),
          (1,0),
          (-1,1),
          (0,1),
          (1,1) )

class AntServer(object):
    '''
    classdocs
    '''

    class Client():
        def __init__(self, s, server):
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
            self.id = -1
            self.s = s
            self.name = ''
            self.actor = False
            self.hello_received = False
            self.action = None
            self.sugar = 0
            self.ants = {}
            self.server = server

        def hello(self, hello_msg):
            typ, self.name = hello_msg
            self.actor = typ != 0
            if self.actor:
                used_ids = [ c.id for c in self.server.clients ]
                self.id = -1
                ids = [ i for i in range(16) ]
                #random.shuffle(ids)
                for i in ids:
                    if i not in used_ids:
                        self.id = i
                        break
                if self.id == -1:
                    self.s.close()
                    self.clients.remove(self)

                self.server.build_lookup()
                self.server.place_ants(self.id)
            self.hello_received = True
            print('Hello received from client {}: {}'.format(self.id, self.name))

        def fileno(self):
            return self.s.fileno()

        def set_action(self, action):
            self.action = action
            #print "Action {}: {}".format(self.id, action)

        def get_action(self):
            action = self.action
            self.action = None
            return action

        def remove(self):
            for ant in list(self.ants.values()):
                field = self.server.index(*ant)
                self.server.set_playfield(field, self.server.get_playfield(field) & CLEARANTMASK)

    def set_playfield(self, index, value):
        if value == 0:
            if index in self.playfield:
                del self.playfield[index]
        else:
            self.playfield[index] = value

    def get_playfield(self, index):
        if index in self.playfield:
            return self.playfield[index]
        else:
            return 0

    def index(self, x, y):
        return x + y * PLAYFIELDSIZE

    def coord(self, index):
        return (index % PLAYFIELDSIZE, index // PLAYFIELDSIZE)

    def place_homebase(self, xpos, ypos):
        for x in range(20):
            for y in range(20):
                self.set_playfield(self.index(x+xpos, y+ypos), HOMEBASE)

    def place_sugar(self, num, size):
        for i in range(num):
            min = BORDER+BASESIZE+BASEDIST
            max = PLAYFIELDSIZE - BORDER - BASESIZE - BASEDIST - math.sqrt(size)
            xpos = randint(min, max)
            ypos = randint(min, max)
            sz = int(math.sqrt(size))
            for x in range(sz):
                for y in range(sz):
                    self.set_playfield(self.index(x+xpos, y+ypos), SUGAR)

    def __init__(self, display = True, fullscreen=False, tournament=False, port=5000):
        '''
        Constructor
        '''
        self.playfield = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen(1)
        self.clients = []
        self.build_lookup()
        self.display = display
        self.tournament = tournament
        self.open=True
        if self.tournament:
            self.started = False
        else:
            self.started = True
        self.server_start = time.time()

        self.homebase_coords = [ (BASEDIST * i + BORDER + BASESIZE/2, BORDER + BASESIZE/2) for i in range(5) ] + [
                                 (PLAYFIELDSIZE - BORDER - BASESIZE/2, BASEDIST * (i+1) + BORDER + BASESIZE/2) for i in range(4) ] + [
                                 (BASEDIST * (3-i) + BORDER + BASESIZE/2, PLAYFIELDSIZE - BORDER - BASESIZE/2) for i in range(4) ] + [
                                 (BORDER + BASESIZE/2, BASEDIST * (3-i) + BORDER + BASESIZE/2) for i in range(3) ]
        for x, y in self.homebase_coords:
            self.place_homebase(x-BASESIZE/2,y-BASESIZE/2)
            print("Homebase at {},{}".format(x,y))
        self.place_sugar(3,100)

        if have_pygame and self.display:
            pygame.init()
            if fullscreen:
                opts = pygame.FULLSCREEN|pygame.DOUBLEBUF|pygame.HWSURFACE
            else:
                opts = 0
            self.screen = pygame.display.set_mode([1280,1024], opts)
            self.draw()

    def draw(self):
        if not have_pygame or not self.display:
            return

        self.screen.fill((0,0,0))
        for i, field in list(self.playfield.items()):    # for every pixel:
            if field == 0:
                continue
            if field & ANTSUGAR == ANTSUGAR:
                self.screen.set_at(self.coord(i), (255,255,0))
            elif field & SUGAR == SUGAR:
                self.screen.set_at(self.coord(i), (0,255,0))
            elif field & ANT == ANT:
                self.screen.set_at(self.coord(i), (255,0,0))
            elif field & HOMEBASE == HOMEBASE:
                self.screen.set_at(self.coord(i), (100,100,100))

        pygame.display.flip()

    def build_lookup(self):
        self.lookup = [ -1 for i in range(16) ]
        for idx, c in enumerate(self.clients):
            if c.id >= 0:
                self.lookup[c.id] = idx

    def accept_client(self):
        s, _ = self.server.accept()
        if self.open:
            s.setblocking(0)
            self.clients.append(self.Client(s, self))
            self.build_lookup()
        else:
            s.close()

    def can_move(self, old, new):
        has_sugar = self.get_playfield(old) & SUGAR == SUGAR
        if new in self.playfield:
            if self.get_playfield(new) & ANT == ANT or (has_sugar and self.get_playfield(new) & SUGAR == SUGAR):
                return False
        return True

    def clamp(self, x):
        return max(0, min(x, PLAYFIELDSIZE-1))

    def dist(self, p1, p2):
        xdist = p1[0]-p2[0]
        ydist = p1[1]-p2[1]
        dist = math.sqrt(xdist*xdist + ydist*ydist)
        return dist

    def do_action(self, Id, actions):
        if actions == None:
            return
        idx = self.lookup[Id]
        if idx >= 0:
            client = self.clients[idx]
            if client.id != Id:
                print("\n-------------- Wrong client ---------------")
            for idx, action in enumerate(actions):
                if action > 9 or action == 0 or action == 5:
                    continue
                antpos = client.ants.get(idx, None)
                if antpos:
                    x,y = antpos
                    newx, newy = (x+_move[action][0], y+_move[action][1])
                    oldfield = self.index(x,y)
                    newx = self.clamp(newx)
                    newy = self.clamp(newy)
                    newfield = self.index(newx,newy)
                    if self.can_move(oldfield, newfield):
                        client.ants[idx] = (newx,newy)
                        self.set_playfield(newfield, (self.get_playfield(newfield) & 0x0f ) | (self.get_playfield(oldfield) & ~HOMEBASE))
                        self.set_playfield(oldfield, self.get_playfield(oldfield) & CLEARANTSUGAR & 0x0f)
                        # check for sugar return
                        if self.get_playfield(newfield) & (HOMEBASE|SUGAR) == (HOMEBASE|SUGAR) and self.dist(self.homebase_coords[Id], (newx, newy)) < 20.0:
                            client.sugar+=1
                            self.set_playfield(newfield, self.playfield[newfield] & CLEARSUGARMASK)

                        if self.get_playfield(newfield) & HOMEBASE == HOMEBASE and self.dist(self.homebase_coords[Id], (newx, newy)) < 20.0:
                            self.set_health(newfield, 10)


    def get_health(self, field):
        return (self.get_playfield(field) >> HEALTH_SHIFT) & 0x0f

    def get_team(self, field):
        return (self.get_playfield(field) >> ID_SHIFT) & 0x0f

    def set_health(self, field, health):
        mask = ~(0x0f << HEALTH_SHIFT)
        self.set_playfield(field, (self.get_playfield(field) & mask) | (health << HEALTH_SHIFT))

    def update(self):
        # calculate in-fight results
        for c in self.clients:
            for ant in list(c.ants.values()):
                x, y = ant
                field = self.index(x, y)
                health = self.get_health(field)
#                print"Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip("\0"), ant[0], ant[1], health)
                if health <= 0:
                    print("Ant of team {}:{} WAS ALEADY DEAD!".format(c.id, c.name.strip("\0")))
                for nx, ny in _move:
                    neigh = self.index(x+nx, y+ny)
                    if neigh >= 0 and neigh < (PLAYFIELDSIZE*PLAYFIELDSIZE) and neigh != field:
                        if self.get_playfield(neigh) & ANT == ANT and self.get_team(neigh) != c.id:
                            health -= 1
                            if health == 0:
                                foe = self.clients[self.lookup[self.get_team(neigh)]]
                                print("Ant of team {}:{} killed by team {}:{}".format(c.id, c.name.strip("\0"), foe.id, foe.name.strip("\0")))
                                foe.sugar += 32
                if health <= 0:
                    health = 0
                self.set_health(field, health)
        # and now, remove dead ants
        for c in self.clients:
            ants = list(c.ants.items())[:]
            for idx, ant in ants:
                field = self.index(*ant)
                health = self.get_health(field)
#                print"Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip("\0"), ant[0], ant[1], health)
                if health <= 0:
                    self.set_playfield(field, self.get_playfield(field) & CLEARANTMASK)
                    print("Ant of team {}:{} killed. Remaining ants: {}".format(c.id, c.name.strip("\0"), len(c.ants)))
                    del c.ants[idx]
                    self.set_playfield(field, self.get_playfield(field) | SUGAR)
                    for off in [ 1, -1, 1+PLAYFIELDSIZE, -1-PLAYFIELDSIZE ]:
                        place = field+off
                        if place >= 0 and place <= (PLAYFIELDSIZE*PLAYFIELDSIZE)-1:
                            self.set_playfield(place, self.get_playfield(place) | SUGAR)

    def get_teams(self):
        teams = [ (0, 0, '') for i in range(16) ]
        for c in self.clients:
            if c.id >= 0:
                teams[c.id] = (c.sugar, len(c.ants), c.name)
        return teams

    def place_ants(self, Id):
        xpos, ypos = self.homebase_coords[Id]
        xpos -= 2
        ypos -= 2

        client = self.clients[self.lookup[Id]]
        for x in range(4):
            for y in range(4):
                index = self.index(xpos + x, ypos + y)
                ant_id = x + y*4
                self.set_playfield(index, self.get_playfield(index) | (ANT + (ant_id << ANTID_SHIFT) + (10 << HEALTH_SHIFT) + (Id << ID_SHIFT)))
                client.ants[ant_id] = (xpos + x, ypos + y)

    def save_scores(self):
        if self.tournament:
            f = open("/var/www/scores/AntServerScores.txt",  "a")
            f.write("# Round {}\n".format(datetime.now().ctime()))
            for idx in self.lookup:
                if idx == -1:
                    f.write("\t\t\n")
                else:
                    f.write("{}\t{}\t{}\n".format(self.clients[idx].name.strip("\0"),  self.clients[idx].sugar,  len(self.clients[idx].ants)))

    _DOWNCOUNT=1000
    _downcount=1000
    def get_objects(self):

        objects = []
        sugar = 0
        for i, field in list(self.playfield.items()):
            if field != 0:
                if field & ANTSUGAR != 0:
                    if field & SUGAR == SUGAR:
                        sugar += 1
                    o1 = ((field & ANTSUGAR) << 4) | ((field >> ID_SHIFT) & 0x0f)
                    o2 = (((field >> ANTID_SHIFT) & 0x0f) << 4) | ((field >> HEALTH_SHIFT) & 0x0f)
                    o3, o4 = self.coord(i)
                    objects.append((o1,o2,o3,o4))
        if sugar == 0:
            self._downcount -= 1
            if self._downcount <= 0:
                self.save_scores()
                sys.exit()
        else:
            self._downcount=self._DOWNCOUNT
        return objects

    def run(self, maxturns=0):
        turn = 0
        while True:
            if self.tournament and not self.started:
                if time.time() > self.server_start + STARTDELAY:
                    self.open = False
                    self.started = True
                    print("Tournament started!")
            sleep(0.05) # round time

            while True:
                rlist, _, _ = select.select([ self.server ] + self.clients, [], [], 0.0)
                if len(rlist) == 0:
                    break
                for c in rlist:
                    if c == self.server:
                        self.accept_client()
                    else:
                        if c.hello_received:
                            action = receive_action(c.s, c.id)
                            if action:
                                c.set_action(action)
                            else:
                                c.remove()
                                self.clients.remove(c)
                                self.build_lookup()
                        else:
                            c.hello(receive_hello(c.s))
            if self.started:
                for c in self.clients:
                    if c.actor:
                        self.do_action(c.id, c.get_action())

            self.update()

            teams = self.get_teams()
            objects = self.get_objects()

            for c in self.clients:
                if c.hello_received:
                    try:
                        send_turn(c.s, c.id, teams, objects)
                    except Exception as e:
                        print('Removing client {} ({})\n{}'.format(c.id, e, traceback.format_exc()))
                        c.remove()
                        self.clients.remove(c)
                        self.build_lookup()

            self.draw()
            sys.stderr.write('\r{}'.format(turn))
            turn += 1
            if maxturns > 0 and turn >= maxturns:
                self.save_scores()
                sys.exit()
