#!/usr/bin/env python3
# -*- coding: utf-8 *-*

from AntNetwork.VisualizerRemote import Vis as VisRemote
from AntNetwork.VisualizerRemote import AntClient as VisClient
import sys
import cProfile
import re
import argparse


def main():
    parser = argparse.ArgumentParser(prog="AntVisualizer")
    parser.add_argument('--server', type=str, default='127.0.0.1')
    args = parser.parse_args()
    print(args)

    client = VisClient(args.server, client=False, teamname='spectator')
    vis = VisRemote(client)
    while True:
        client.update_world()
        vis.update()

if __name__ == "__main__":
    main()
