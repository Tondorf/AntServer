#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import math

TICK_TARGET = 20 * 10 * 5

# NOTHING = 0  # implicit, duh...
ANT = 1
SUGAR = 2
HOMEBASE = 4
ATOMICWASTE = 8

ANT_WITH_SUGAR = ANT | SUGAR
ANT_WITH_WASTE = ANT | ATOMICWASTE

BASEDIST = 200
BASESIZE = 20
BORDER = 90
PLAYFIELDSIZE = 1000

STARTDELAY = 20.0
ANT_MAX_HEALTH = 10
POINTS_FOR_KILL = 10  # 32
SPAWN_SUGAR_ON_DEAD_ANT = False

ANTID_SHIFT = 4
HEALTH_SHIFT = 8
ID_SHIFT = 12

CLEARANTMASK = ~ANT
CLEARANTSUGAR = CLEARANTMASK & ~SUGAR
CLEARANTWASTE = CLEARANTMASK & ~ATOMICWASTE
CLEARSUGARMASK = 0xFFF0 | ~SUGAR
CLEARWASTEMASK = 0xFFF0 | ~ATOMICWASTE


def index(x, y):
    """maps from 1000x1000 to 1000000"""
    return x + y * PLAYFIELDSIZE


def coord(idx):
    """maps from 1000000 to 1000x1000"""
    return (int(idx % PLAYFIELDSIZE), int(idx // PLAYFIELDSIZE))


def valid_index(idx):
    return idx >= 0 and idx <= (PLAYFIELDSIZE * PLAYFIELDSIZE) - 1


def valid_coord(x, y):
    if x < 0 or x >= PLAYFIELDSIZE:
        return False
    if y < 0 or y >= PLAYFIELDSIZE:
        return False
    return True


def honor_bounds(x):
    return max(0, min(x, PLAYFIELDSIZE - 1))


def dist(p1, p2):
    p1x, p1y = p1
    p2x, p2y = p2
    return math.sqrt((p1x - p2x) ** 2 + (p1y - p2y) ** 2)


def antPrint(args):
    print("\n" + args)
