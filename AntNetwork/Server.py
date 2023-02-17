#!/usr/bin/env python3
# -*- coding: utf-8 *-*

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
from AntNetwork.Visualizer import Visualizer
from AntNetwork.Common import *

try:
    import pygame
except:
    have_pygame = False
    print("pygame not installed! visualizer will not work!")
else:
    have_pygame = True


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
    class Client():
        """a client as it's seen from the server"""
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
                used = [c.id for c in self.server.clients]
                IDs = list(range(16))
                free = sorted(set(IDs) - set(used))
                if not len(free):
                    antPrint("Game is FULL, cannot add new client")
                    self.s.close()
                    self.server.clients.remove(self)
                    return
                #random.shuffle(free)
                self.id = free[0]
                self.server.build_lookup()
                self.server.place_ants(self.id)
            self.hello_received = True
            antPrint('Hello received from client {}: {}'.format(self.id, self.name.rstrip(b'\0')))

        def fileno(self):
            return self.s.fileno()

        def set_action(self, action):
            self.action = action
            # antPrint("Action {}: {}".format(self.id, action))

        def get_action(self):
            action = self.action
            self.action = None
            return action

        def remove(self):
            for ant in list(self.ants.values()):
                field = index(*ant)
                self.server.set_playfield(field, self.server.get_playfield(field) & CLEARANTMASK)

    def set_playfield(self, idx, value):
        if value == 0:
            if idx in self.playfield:
                del self.playfield[idx]
        else:
            self.playfield[idx] = value

    def get_playfield(self, idx):
        if idx in self.playfield:
            return self.playfield[idx]
        else:
            return 0

    def place_homebase(self, xpos, ypos):
        for x in range(BASESIZE):
            for y in range(BASESIZE):
                self.set_playfield(index(xpos + x, ypos + y), HOMEBASE)

    def place_sugar_cube(self, xpos, ypos, radius):
        for x in range(radius):
            for y in range(radius):
                self.set_playfield(index(xpos + x, ypos + y), SUGAR)

    def place_sugars_randomly(self, num, dim):
        for i in range(num):
            min = BORDER + BASESIZE + BASEDIST
            max = PLAYFIELDSIZE - BORDER - BASESIZE - BASEDIST - dim
            xpos = random.randint(min, max)
            ypos = random.randint(min, max)
            self.place_sugar_cube(xpos, ypos, dim)

    def __init__(self, do_visualizer=True, fullscreen=False, tournament=False, port=5000):
        self.playfield = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen(1)
        self.clients = []
        self.build_lookup()
        self.do_visualizer = do_visualizer
        self.tournament = tournament
        self.open = True
        if self.tournament:
            self.started = False
        else:
            self.started = True
        self.server_start = time.time()

        self.homebase_coords = [ (BASEDIST * i + BORDER + BASESIZE//2, BORDER + BASESIZE//2) for i in range(5) ] + [
                                 (PLAYFIELDSIZE - BORDER - BASESIZE//2, BASEDIST * (i+1) + BORDER + BASESIZE//2) for i in range(4) ] + [
                                 (BASEDIST * (3-i) + BORDER + BASESIZE//2, PLAYFIELDSIZE - BORDER - BASESIZE//2) for i in range(4) ] + [
                                 (BORDER + BASESIZE//2, BASEDIST * (3-i) + BORDER + BASESIZE//2) for i in range(3) ]
        for x, y in self.homebase_coords:
            self.place_homebase(x - BASESIZE // 2, y - BASESIZE // 2)
            print("Homebase at {},{}".format(x, y))
        self.place_sugars_randomly(3, 10)

        if self.do_visualizer:
            self.vis = Visualizer(fullscreen)


    def build_lookup(self):
        self.lookup = [-1 for i in range(16)]
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
        return max(0, min(x, PLAYFIELDSIZE - 1))

    def dist(self, p1, p2):
        xdist = p1[0] - p2[0]
        ydist = p1[1] - p2[1]
        dist = math.sqrt(xdist * xdist + ydist * ydist)
        return dist

    def do_action(self, Id, actions):
        if actions == None:
            return
        idx = self.lookup[Id]
        if idx >= 0:
            client = self.clients[idx]
            if client.id != Id:
                antPrint("\n-------------- Wrong client ---------------")
            for idx, action in enumerate(actions):
                if action > 9 or action == 0 or action == 5:
                    continue
                antpos = client.ants.get(idx, None)
                if antpos:
                    x, y = antpos
                    newx, newy = (x + _move[action][0], y + _move[action][1])
                    oldfield = index(x, y)
                    newx = self.clamp(newx)
                    newy = self.clamp(newy)
                    newfield = index(newx, newy)
                    if self.can_move(oldfield, newfield):
                        client.ants[idx] = (newx, newy)
                        self.set_playfield(newfield, (self.get_playfield(newfield) & 0x0f) | (self.get_playfield(oldfield) & ~HOMEBASE))
                        self.set_playfield(oldfield, self.get_playfield(oldfield) & CLEARANTSUGAR & 0x0f)
                        # check for sugar return
                        if self.get_playfield(newfield) & (HOMEBASE | SUGAR) == (HOMEBASE | SUGAR) and self.dist(self.homebase_coords[Id], (newx, newy)) < 20.0:
                            client.sugar += 1
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
                field = index(x, y)
                health = self.get_health(field)
                #antPrint("Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip(b"\0"), ant[0], ant[1], health))
                if health <= 0:
                    antPrint("Ant of team {}:{} WAS ALEADY DEAD!".format(c.id, c.name.strip(b"\0")))
                for nx, ny in _move:
                    neigh = index(x + nx, y + ny)
                    if neigh >= 0 and neigh < (PLAYFIELDSIZE * PLAYFIELDSIZE) and neigh != field:
                        if self.get_playfield(neigh) & ANT == ANT and self.get_team(neigh) != c.id:
                            health -= 1
                            if health == 0:
                                foe = self.clients[self.lookup[self.get_team(neigh)]]
                                antPrint("Ant of team {}:{} killed by team {}:{}".format(c.id, c.name.strip(b"\0"), foe.id, foe.name.strip(b"\0")))
                                foe.sugar += 32
                if health <= 0:
                    health = 0
                self.set_health(field, health)
        # and now, remove dead ants
        for c in self.clients:
            ants = list(c.ants.items())[:]
            for idx, ant in ants:
                field = index(*ant)
                health = self.get_health(field)
                # antPrint("Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip(b"\0"), ant[0], ant[1], health))
                if health <= 0:
                    self.set_playfield(field, self.get_playfield(field) & CLEARANTMASK)
                    antPrint("Ant of team {}:{} killed. Remaining ants: {}".format(c.id, c.name.strip(b"\0"), len(c.ants)))
                    del c.ants[idx]
                    self.set_playfield(field, self.get_playfield(field) | SUGAR)
                    for off in [1, -1, 1 + PLAYFIELDSIZE, -1 - PLAYFIELDSIZE]:
                        place = field + off
                        if place >= 0 and place <= (PLAYFIELDSIZE * PLAYFIELDSIZE) - 1:
                            self.set_playfield(place, self.get_playfield(place) | SUGAR)

    def get_teams(self):
        teams = [(0, 0, b'') for i in range(16)]
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
                idx = index(xpos + x, ypos + y)
                ant_id = x + y * 4
                self.set_playfield(idx, self.get_playfield(idx) | (ANT + (ant_id << ANTID_SHIFT) + (10 << HEALTH_SHIFT) + (Id << ID_SHIFT)))
                client.ants[ant_id] = (xpos + x, ypos + y)

    def save_scores(self):
        if self.tournament:
            f = open("/var/www/scores/AntServerScores.txt", "a")
            f.write("# Round {}\n".format(datetime.now().ctime()))
            for idx in self.lookup:
                if idx == -1:
                    f.write("\t\t\n")
                else:
                    f.write("{}\t{}\t{}\n".format(self.clients[idx].name.strip(b"\0"), self.clients[idx].sugar, len(self.clients[idx].ants)))

    _downcount = 1000

    def get_objects(self):
        objects = []
        sugarcount = 0
        for i, field in list(self.playfield.items()):
            if field != 0:
                if field & ANTSUGAR != 0:
                    if field & SUGAR == SUGAR:
                        sugarcount += 1
                    o1 = ((field & ANTSUGAR) << 4) | ((field >> ID_SHIFT) & 0x0f)
                    o2 = (((field >> ANTID_SHIFT) & 0x0f) << 4) | ((field >> HEALTH_SHIFT) & 0x0f)
                    o3, o4 = coord(i)
                    objects.append((o1, o2, o3, o4))
        if sugarcount == 0: # no sugar in the game anymore
            self._downcount -= 1
            if self._downcount <= 0:
                self.save_scores()
                sys.exit()
        else:
            self._downcount = 1000
        return objects

    def handle_client_inputs(self):
        # loop for handling network clients via select
        while True:
            rlist, _, _ = select.select([self.server] + self.clients, [], [], 0.0)
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

    def notify_clients(self, teams, objects):
        for c in self.clients:
            if c.hello_received:
                try:
                    send_turn(c.s, c.id, teams, objects)
                except Exception as e:
                    antPrint('Removing client {} ({})\n{}'.format(c.id, e, traceback.format_exc()))
                    c.remove()
                    self.clients.remove(c)
                    self.build_lookup()

    def run(self, maxturns=0):
        turn = 0
        running = True

        # MAIN GAME LOOP
        while running:
            if self.tournament and not self.started:
                if time.time() > self.server_start + STARTDELAY:
                    self.open = False
                    self.started = True
                    antPrint("Tournament started!")
            sleep(1/TICK_TARGET)  # round time

            self.handle_client_inputs()

            if self.started:
                for c in self.clients:
                    if c.actor:
                        self.do_action(c.id, c.get_action())

            self.update()

            teams = self.get_teams()
            objects = self.get_objects()

            self.notify_clients(teams, objects)

            if self.do_visualizer:
                self.vis.draw(self.playfield)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

            sys.stderr.write('\rtick={} objects={}'.format(turn, len(self.playfield)))
            turn += 1
            if maxturns > 0 and turn >= maxturns:
                self.save_scores()
                sys.exit()
