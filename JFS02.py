#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork as AN
from AntNetwork.Client import AntClient
import sys
import math
import random

from Jcommon import *


def get_move(pos, target):
    xdist = target[0] - pos[0]
    ydist = target[1] - pos[1]
    xmove = get_dir(xdist)
    ymove = get_dir(ydist)

    xdist = abs(xdist)
    ydist = abs(ydist)
    if xdist > ydist:
        if random.randint(0, 100) < 5:
            ymove = random.choice([-1, 1])
    elif xdist < ydist:
        if random.randint(0, 100) < 5:
            xmove = random.choice([-1, 1])
    return dir_code(xmove, ymove)


def get_action(mybase, ant, sugar, ants):
    if ant is None:
        return 0
    has_sugar, pos = ant
    if has_sugar:
        return get_move(pos, mybase)
    else:
        dist = AN.PLAYFIELDSIZE * 2
        adist = AN.PLAYFIELDSIZE * 2
        idx = -1
        aidx = -1
        for i, s in enumerate(sugar):
            d = rect_dist(pos, s)
            if d < dist:
                idx = i
                dist = d
        if idx >= 0:
            target = sugar[idx]
            del sugar[idx]  # remove targeted sugar piece
            return get_move(pos, target)
        for i, s in enumerate(ants):
            d = rect_dist(pos, s)
            if d < adist:
                aidx = i
                adist = d
        if aidx >= 0 and dist < 2 * adist:
            return get_move(pos, ants[aidx])
    return random.randint(1, 9)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("need IP as first argument")
        sys.exit(1)
    client = AntClient(sys.argv[1], 5000, "JFS02", True)
    while True:
        Id, teams, objects = client.get_turn()
        mybase = homebase_coords[Id]
        my_ants = [None for i in range(16)]
        sugar = []
        ants = []
        for obj in objects:
            if is_ant(obj) and team(obj) == Id:
                my_ants[ant_id(obj)] = (is_sugar(obj), coords(obj))
            elif is_sugar(obj) and not is_ant(obj):
                sugar.append(coords(obj))
            elif is_sugar(obj):
                ants.append(coords(obj))

        client.send_action([get_action(mybase, ant, sugar, ants) for ant in my_ants])
