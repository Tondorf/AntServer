#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork as AN
from AntNetwork.Client import AntClient
import sys
import math
import random

from SampleBotCommon import *


from SampleBot02 import get_move


def get_action(mybase, ant, sugar, ants):
    if ant is None:
        return 0
    pos = coords(ant)
    if is_sugar(ant) or health(ant) < 3:
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
        dist = AN.PLAYFIELDSIZE * 2
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
    return get_action(mybase, ant, sugar, ants)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("need IP as first argument")
        sys.exit(1)
    client = AntClient(sys.argv[1], 5000, "SampleBot04", True)
    if len(sys.argv) > 2:
        num_raiders = int(sys.argv[2])
    else:
        num_raiders = 4
    while True:
        Id, teams, objects = client.get_turn()
        mybase = homebase_coords[Id]
        my_ants = [None for i in range(16)]
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
        client.send_action([get_raider_action(mybase, ant, sugar, ants) for ant in my_ants])
