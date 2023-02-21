#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork as AN

homebase_coords = (
    [
        (AN.BASEDIST * i + AN.BORDER + AN.BASESIZE / 2, AN.BORDER + AN.BASESIZE / 2)
        for i in range(5)
    ]
    + [
        (
            AN.PLAYFIELDSIZE - AN.BORDER - AN.BASESIZE / 2,
            AN.BASEDIST * (i + 1) + AN.BORDER + AN.BASESIZE / 2,
        )
        for i in range(4)
    ]
    + [
        (
            AN.BASEDIST * (3 - i) + AN.BORDER + AN.BASESIZE / 2,
            AN.PLAYFIELDSIZE - AN.BORDER - AN.BASESIZE / 2,
        )
        for i in range(4)
    ]
    + [
        (
            AN.BORDER + AN.BASESIZE / 2,
            AN.BASEDIST * (3 - i) + AN.BORDER + AN.BASESIZE / 2,
        )
        for i in range(3)
    ]
)


def is_ant(obj):
    return (obj[0] >> 4) & AN.ANT == AN.ANT


def is_sugar(obj):
    return (obj[0] >> 4) & AN.SUGAR == AN.SUGAR


def is_toxin(obj):
    return (obj[0] >> 4) & AN.TOXIN == AN.TOXIN


def team(obj):
    return obj[0] & 0x0F


def ant_id(obj):
    return obj[1] >> 4


def health(obj):
    return obj[1] & 0x0F


def coords(obj):
    return (obj[2], obj[3])


def rect_dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def get_dir(dist):
    if dist < 0:
        return -1
    elif dist > 0:
        return 1
    return 0


def dir_code(xm, ym):
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
