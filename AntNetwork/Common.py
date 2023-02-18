#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import math

TICK_TARGET = 20 * 10 * 5

# NOTHING = 0  # implicit, duh...
ANT = 1
SUGAR = 2
TOXIN = 4
HOMEBASE = 8

ANT_WITH_SUGAR = ANT | SUGAR
ANT_WITH_TOXIN = ANT | TOXIN

BASEDIST = 200
BASESIZE = 20
BORDER = 90
PLAYFIELDSIZE = 1000

STARTDELAY = 20.0
ANT_MAX_HEALTH = 10
POINTS_FOR_KILL = 10  # 32
SPAWN_SUGAR_ON_DEAD_ANT = False
INIT_PATCHES_SUGAR_CNT = 12
INIT_PATCHES_SUGAR_SIZE = 5
INIT_PATCHES_TOXIN_CNT = 6
INIT_PATCHES_TOXIN_SIZE = 5

# TYP_SHIFT = 0  # implicit, duh...
ANTID_SHIFT = 4
HEALTH_SHIFT = 8
ID_SHIFT = 12

CLEARANTMASK = ~ANT
CLEARANTSUGAR = CLEARANTMASK & ~SUGAR
CLEARANTTOXIN = CLEARANTMASK & ~TOXIN
CLEARANTSUGARTOXIN = CLEARANTMASK & ~SUGAR & ~TOXIN
CLEARSUGARMASK = 0xFFF0 | ~SUGAR
CLEARTOXINMASK = 0xFFF0 | ~TOXIN

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
