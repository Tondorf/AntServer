#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork
from PIL import Image
import sys
import cProfile
import re


def show_playfield(server):
    img = Image.new("RGB", (1000, 1000), "black")  # create a new black image
    pixels = img.load()  # create the pixel map

    for i in range(img.size[0]):  # for every pixel:
        for j in range(img.size[1]):
            color = pixels[i, j]
            field = server.playfield[server.index(i, j)]
            if field & AntNetwork.ANTSUGAR == AntNetwork.ANTSUGAR:
                color = (255, 255, 0)
            elif field & AntNetwork.SUGAR == AntNetwork.SUGAR:
                color = (0, 255, 0)
            elif field & AntNetwork.ANT == AntNetwork.ANT:
                color = (255, 0, 0)
            elif field & AntNetwork.HOMEBASE == AntNetwork.HOMEBASE:
                color = (100, 100, 100)
            pixels[i, j] = color
    img.show()


if __name__ == "__main__":
    fullscreen = False
    if "--fullscreen" in sys.argv:
        fullscreen = True
    display = True
    if "--no-display" in sys.argv:
        display = False

    tournament = False
    if "--tournament" in sys.argv:
        tournament = True

    maxrounds = 5000
    for arg in sys.argv:
        match = re.match("--maxrounds=([0-9]+)", arg)
        if match:
            maxrounds = int(match.group(1))
            print("MAX:", maxrounds)
    server = AntNetwork.AntServer(display, fullscreen, tournament)
    if "--profile" in sys.argv:
        cProfile.run("server.run(100)")
    else:
        server.run(maxrounds)
