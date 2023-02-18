#!/usr/bin/env python3
# -*- coding: utf-8 *-*

from AntNetwork.Server import AntServer
# from AntNetwork.VisualizerRemote import Vis as VisRemote
# from AntNetwork.VisualizerRemote import AntClient as VisClient
import sys
import cProfile
import re
import argparse


def main():
    parser = argparse.ArgumentParser(prog="AntServer")
    parser.add_argument("-t", "--tournament", action="store_true", default=False)
    parser.add_argument("-m", "--max-rounds", type=int, default=0)
    parser.add_argument("-p", "--profiling", action="store_true", default=False)
    args = parser.parse_args()
    print(args)

    server = AntServer(args.tournament)

    if args.profiling:
        cProfile.run("server.run(100)")
    else:
        server.run(args.max_rounds)

if __name__ == "__main__":
    main()
