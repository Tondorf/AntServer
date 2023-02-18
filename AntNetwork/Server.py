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


_move = {
    0: (0,0),
    1: (-1,-1),
    2: (0,-1),
    3: (1,-1),
    4: (-1,0),
    5: (0,0),
    6: (1,0),
    7: (-1,1),
    8: (0,1),
    9: (1,1)
}


class Coord:
    def vals2int(typ, ant_id, health, cid):
        assert typ in [ANT, SUGAR, TOXIN, HOMEBASE, ANT_WITH_SUGAR, ANT_WITH_TOXIN]
        assert ant_id < 16
        assert health < 16
        assert cid < 16
        return (cid << ID_SHIFT) + (health << HEALTH_SHIFT) + (ant_id << ANTID_SHIFT) + typ

    def homebase(cid):
        return Coord.vals2int(HOMEBASE, 0, 0, cid)

    def typ(num):
        return num & 0xF
    def ant_id(num):
        return num >> ANTID_SHIFT & 0xF
    def health(num):
        return num >> HEALTH_SHIFT & 0xF
    def cid(num):
        return num >> ID_SHIFT & 0xF

    def int2vals(num):
        return Coord.typ(num), Coord.ant_id(num), Coord.health(num), Coord.cid(num)


class AntServer(object):

    class Client:
        """a client as it's seen from the server"""
        def __init__(self, s, server):
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
            self.id = -1
            self.s = s
            self.name = ''
            self.actor = False
            self.hello_received = False
            self.action = None
            self.score = 0
            self.ants = {}
            self.server = server

        def hello(self, typ, name):
            self.name = name
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
            self.server.clients.remove(self)
            self.server.build_lookup()

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

    def place_homebase(self, cid, xpos, ypos):
        for x in range(BASESIZE):
            for y in range(BASESIZE):
                self.set_playfield(index(xpos + x, ypos + y), Coord.homebase(cid))

    def place_entity_cube(self, xpos, ypos, radius, material=SUGAR):
        for x in range(radius):
            for y in range(radius):
                idx = index(xpos + x, ypos + y)
                self.set_playfield(idx, self.get_playfield(idx) | material)

    def place_random_patches(self, num, dim, material=SUGAR):
        for i in range(num):
            min = BORDER + BASESIZE + BASEDIST
            max = PLAYFIELDSIZE - BORDER - BASESIZE - BASEDIST - dim
            xpos = random.randint(min, max)
            ypos = random.randint(min, max)
            self.place_entity_cube(xpos, ypos, dim, material)

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
        for cid, (x, y) in enumerate(self.homebase_coords):
            self.place_homebase(cid, x - BASESIZE // 2, y - BASESIZE // 2)
            print("Homebase for cid {} at {},{}".format(cid, x, y))
        self.place_random_patches(INIT_PATCHES_SUGAR_CNT, INIT_PATCHES_SUGAR_SIZE, SUGAR)
        self.place_random_patches(INIT_PATCHES_TOXIN_CNT, INIT_PATCHES_TOXIN_SIZE, TOXIN)
        ### DEBUG!!!
        self.place_entity_cube(100, 100, 2, TOXIN)

        if self.do_visualizer:
            self.vis = Visualizer(fullscreen)

    def build_lookup(self):
        """this is a mapping from client id (ordering from bases, so, more like the base id)
           to the index/position in the self.clients lists"""
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

    def do_action(self, cid, actions):
        """perform the move actions from the clients and handle the consequences"""
        if actions == None or not actions:
            return
        idx = self.lookup[cid]
        if idx >= 0:
            client = self.clients[idx]
            if client.id != cid:
                antPrint("\n-------------- Wrong client ---------------")
            # iterate over 16 actions, there is always exactly 1 per ant
            for idx, action in enumerate(actions):
                if action > 9 or action == 0 or action == 5:
                    continue
                antpos = client.ants.get(idx, None)
                if antpos:
                    x, y = antpos
                    oldfield = index(x, y)
                    # determine new position according to transmitted action
                    newfield = index(honor_bounds(x + _move[action][0]), honor_bounds(y + _move[action][1]))
                    if self.can_move(oldfield, newfield):
                        # if allowed: actually move the ant
                        client.ants[idx] = coord(newfield)
                        # new field: perform move = copy value from old field (but not homebase)
                        self.set_playfield(newfield, (self.get_playfield(newfield) & 0x0f) | (self.get_playfield(oldfield) & ~HOMEBASE))
                        # old field: remove ant (and potential sugar/toxin)
                        self.set_playfield(oldfield, self.get_playfield(oldfield) & CLEARANTSUGARTOXIN & 0x0F)

                        # check for sugar brought to a base
                        # you CAN bring sogar to foreign bases to award points to this team, this would be stupid, but nothing stops you
                        if self.get_playfield(newfield) & (HOMEBASE | SUGAR) == (HOMEBASE | SUGAR):
                            cid = Coord.cid(self.get_playfield(newfield))
                            self.clients[self.lookup[cid]].score += 1 # award point to team of base
                            self.set_playfield(newfield, self.playfield[newfield] & CLEARSUGARMASK) # remove sugar from world

                        # check for toxin brought to a base
                        # you CAN bring toxin to your own base and receive the penalty, this would be stupid, but nothing stops you
                        if self.get_playfield(newfield) & (HOMEBASE | TOXIN) == (HOMEBASE | TOXIN):
                            cid = Coord.cid(self.get_playfield(newfield))
                            self.clients[self.lookup[cid]].score -= 1
                            self.set_playfield(newfield, self.playfield[newfield] & CLEARTOXINMASK)

                        # replenish ant health if at home
                        homebase = self.get_playfield(newfield) & HOMEBASE == HOMEBASE
                        own_base = Coord.cid(self.get_playfield(newfield)) == cid
                        if homebase and own_base and self.get_health(newfield) < ANT_MAX_HEALTH:
                            antPrint("Replenishing cid={} ant={} health to maximum".format(cid, idx))
                            self.set_health(newfield, ANT_MAX_HEALTH)

    def get_health(self, field):
        return Coord.health(self.get_playfield(field))

    def get_team(self, field):
        return Coord.cid(self.get_playfield(field))

    def set_health(self, field, health):
        mask = ~(0x0f << HEALTH_SHIFT)
        self.set_playfield(field, (self.get_playfield(field) & mask) | (health << HEALTH_SHIFT))

    def let_ants_fight(self):
        """iterate over all clients and ants and check for dead ants"""
        for c in self.clients:
            for ant in list(c.ants.values()):
                x, y = ant
                field = index(x, y)
                health = self.get_health(field)
                #antPrint("Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip(b"\0"), ant[0], ant[1], health))
                if health <= 0:
                    antPrint("Ant of team {}:{} WAS ALEADY DEAD!".format(c.id, c.name.strip(b"\0")))
                for nx, ny in _move.values():
                    neigh = index(x + nx, y + ny)
                    if valid_index(neigh) and neigh != field:
                        if self.get_playfield(neigh) & ANT == ANT and self.get_team(neigh) != c.id:
                            health -= 1
                            if health == 0:
                                foe = self.clients[self.lookup[self.get_team(neigh)]]
                                antPrint("Ant {}:{} killed by {}:{}".format(c.id, c.name.strip(b"\0"), foe.id, foe.name.strip(b"\0")))
                                # award points for killing
                                foe.score += POINTS_FOR_KILL
                self.set_health(field, max(0, health))

    def handle_dead_ants(self):
        for c in self.clients:
            ants = list(c.ants.items())[:]
            for idx, ant in ants:
                field = index(*ant)
                health = self.get_health(field)
                # antPrint("Ant of team {}:{} is at {},{}, health {}".format(c.id, c.name.strip(b"\0"), ant[0], ant[1], health))
                if health <= 0:
                    self.set_playfield(field, self.get_playfield(field) & CLEARANTMASK)
                    del c.ants[idx]
                    antPrint("Team {} lost an ant, remaining ant count: {}".format(c.name.strip(b"\0"), len(c.ants)))
                    if SPAWN_SUGAR_ON_DEAD_ANT:
                        # spawn a "+" of 5 sugars surrounding the now-dead ant"
                        for off in [0, 1, -1, 1 + PLAYFIELDSIZE, -1 - PLAYFIELDSIZE]:
                            place = field + off
                            if valid_index(place):
                                self.set_playfield(place, self.get_playfield(place) | SUGAR)

    def get_teams(self):
        teams = [(0, 0, b'') for i in range(16)]
        for c in self.clients:
            if c.id >= 0:
                teams[c.id] = (c.score, len(c.ants), c.name)
        return teams

    def place_ants(self, cid):
        xpos, ypos = self.homebase_coords[cid]
        xpos -= 2
        ypos -= 2

        client = self.clients[self.lookup[cid]]
        for x in range(4):
            for y in range(4):
                idx = index(xpos + x, ypos + y)
                ant_id = x + y * 4
                new_val = Coord.vals2int(ANT, ant_id, ANT_MAX_HEALTH, cid)
                self.set_playfield(idx, self.get_playfield(idx) | new_val)
                client.ants[ant_id] = coord(idx)

    def save_scores(self):
        if self.tournament:
            f = open("/var/www/scores/AntServerScores.txt", "a")
            f.write("# Round {}\n".format(datetime.now().ctime()))
            for idx in self.lookup:
                if idx == -1:
                    f.write("\t\t\n")
                else:
                    f.write("{}\t{}\t{}\n".format(self.clients[idx].name.strip(b"\0"), self.clients[idx].score, len(self.clients[idx].ants)))

    _downcount = 1000

    def get_objects(self):
        objects = []
        sugarcount = 0
        for i, field in list(self.playfield.items()):
            if field != 0:
                if field & ANT_WITH_SUGAR != 0:
                    if Coord.typ(field) & SUGAR == SUGAR:
                        sugarcount += 1
                    o1 = Coord.typ(field) << 4 | Coord.cid(field)
                    o2 = Coord.ant_id(field) << 4 | Coord.health(field)
                    objects.append((o1, o2) + coord(i))
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
                    else:
                        typ, name = receive_hello(c.s)
                        if typ >= 0:
                            c.hello(typ, name)

    def notify_clients(self, teams, objects):
        for c in self.clients:
            if c.hello_received:
                try:
                    send_turn(c.s, c.id, teams, objects)
                except Exception as e:
                    antPrint('Removing client {} ({})\n{}'.format(c.id, e, traceback.format_exc()))
                    c.remove()

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
            sleep(1 / TICK_TARGET)  # round time

            self.handle_client_inputs()

            if self.started:
                for c in self.clients:
                    if c.actor:
                        self.do_action(c.id, c.get_action())

            self.let_ants_fight()

            self.handle_dead_ants()

            teams = self.get_teams()
            objects = self.get_objects()
            self.notify_clients(teams, objects)

            if self.do_visualizer:
                self.vis.draw(teams, self.playfield)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

            sys.stderr.write('\rtick={} objects={}'.format(turn, len(self.playfield)))
            turn += 1
            if maxturns > 0 and turn >= maxturns:
                self.save_scores()
                running = False
