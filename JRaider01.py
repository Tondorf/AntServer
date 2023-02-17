#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork as AN
import sys
import math
import random

homebase_coords = [ (AN.BASEDIST * i + AN.BORDER + AN.BASESIZE/2, AN.BORDER + AN.BASESIZE/2) for i in range(5) ] + [
                    (AN.PLAYFIELDSIZE - AN.BORDER - AN.BASESIZE/2, AN.BASEDIST * (i+1) + AN.BORDER + AN.BASESIZE/2) for i in range(4) ] + [
                    (AN.BASEDIST * (3-i) + AN.BORDER + AN.BASESIZE/2, AN.PLAYFIELDSIZE - AN.BORDER - AN.BASESIZE/2) for i in range(4) ] + [
                    (AN.BORDER + AN.BASESIZE/2, AN.BASEDIST * (3-i) + AN.BORDER + AN.BASESIZE/2) for i in range(3) ]

def is_ant(obj):
    return (obj[0] >> 4) & AN.ANT == AN.ANT

def is_sugar(obj):
    return (obj[0] >> 4) & AN.SUGAR == AN.SUGAR

def team(obj):
    return (obj[0] & 0x0f)

def ant_id(obj):
    return (obj[1] >> 4)

def health(obj):
    return (obj[1] & 0x0f)

def coords(obj):
    return (obj[2],obj[3])

def rect_dist(p1, p2):
    return abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])

def get_dir(dist):
    if dist < 0:
        return -1
    elif dist > 0:
        return 1
    return 0

def dir_code(xm,  ym):
    if xm < 0 and ym < 0:
        return 1
    elif xm == 0 and ym < 0:
        return 2
    elif xm > 0 and ym < 0:
        return 3
    elif xm < 0 and ym == 0:
        return 4
    elif xm == 0 and ym == 0:
        return 5
    elif xm > 0 and ym == 0:
        return 6
    elif xm < 0 and ym > 0:
        return 7
    elif xm == 0 and ym > 0:
        return 8
    return 9

def get_move(pos, target):
    xdist = target[0] - pos[0]
    ydist = target[1] - pos[1]
    xmove = get_dir(xdist)
    ymove = get_dir(ydist)

    xdist = abs(xdist)
    ydist = abs(ydist)
    if xdist > ydist:
        if random.randint(0,100) < 5:
            ymove = random.choice([-1,1])
    elif xdist < ydist:
        if random.randint(0,100) < 5:
            xmove = random.choice([-1,1])
    return dir_code(xmove, ymove)

def get_fs_action(mybase, ant, sugar, ants):
    if ant is None:
        return 0
    pos = coords(ant)
    if is_sugar(ant) or health(ant) < 3:
        return get_move(pos, mybase)
    else:
        dist = AN.PLAYFIELDSIZE*2
        adist = AN.PLAYFIELDSIZE*2
        idx = -1
        aidx = -1
        for i, s in enumerate(sugar):
            d = rect_dist(pos, s)
            if d < dist:
                idx = i
                dist = d
        if idx >= 0:
            target = sugar[idx]
            del sugar[idx] # remove targeted sugar piece
            return get_move(pos, target)
    return get_move(pos, mybase)

_raider_target = None
def get_raider_action(mybase, ant, sugar, ants):
    global _raider_target
    if ant is None:
        return 0

    pos = coords(ant)
    if is_sugar(ant) or health(ant) < 5:
        return get_move(pos, mybase)
    else:
        if _raider_target:
            return get_move(pos, coords(_raider_target))
        dist = AN.PLAYFIELDSIZE*2
        idx = -1
        for i, a in enumerate(ants):
            d = rect_dist(pos, coords(a))
            bd = rect_dist(mybase, coords(a))
            if bd < 40 and d < dist and health(a):
                idx = i
                dist = d
        if idx >= 0:
            _raider_target = ants[idx]
            return get_move(pos, coords(_raider_target))
    return get_fs_action(mybase, ant, sugar, ants)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("need IP as first argument")
        sys.exit(1)
    client = AN.AntClient(sys.argv[1], 5000, 'JRaider01', True)
    if len(sys.argv) > 2:
        num_raiders = int(sys.argv[2])
    else:
        num_raiders = 4
    while True:
        Id, teams, objects = client.get_turn()
        mybase = homebase_coords[Id]
        my_ants = [ None for i in range(16) ]
        sugar = []
        ants = []
        for obj in objects:
            if is_ant(obj) and team(obj) == Id:
                my_ants[ant_id(obj)] = obj
            elif is_sugar(obj) and not is_ant(obj):
                sugar.append(coords(obj))
            elif is_ant(obj):
                ants.append(obj)

        _raider_target = None
        client.send_action([ get_fs_action(mybase, ant, sugar, ants) for ant in my_ants ])
