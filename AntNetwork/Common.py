#!/usr/bin/env python3
# -*- coding: utf-8 *-*

TICK_TARGET = 20

ANT = 1
SUGAR = 2
ANTSUGAR = 3
HOMEBASE = 4

BASEDIST = 200
BASESIZE = 20
BORDER = 90
PLAYFIELDSIZE = 1000

ANTID_SHIFT = 4
HEALTH_SHIFT = 8
ID_SHIFT = 12

CLEARANTMASK = ~ANT
CLEARANTSUGAR = CLEARANTMASK & ~SUGAR
CLEARSUGARMASK = 0xfff0 | ~SUGAR

STARTDELAY = 20.0

def index(x, y):
    return x + y * PLAYFIELDSIZE

def coord(idx):
    return (int(idx % PLAYFIELDSIZE), int(idx // PLAYFIELDSIZE))

def antPrint(args):
    print("\n"+args)
