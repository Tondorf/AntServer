#!/usr/bin/env python3
# -*- coding: utf-8 *-*

from AntNetwork.Server import AntServer
import sys
import cProfile
import re
import argparse


def main():
    parser = argparse.ArgumentParser(prog="AntServer")
    parser.add_argument("-f", "--fullscreen", action="store_true", default=False)
    parser.add_argument("-n", "--no-display", action="store_true", default=False)
    parser.add_argument("-t", "--tournament", action="store_true", default=False)
    parser.add_argument("-m", "--max-rounds", type=int, default=0)
    parser.add_argument("-p", "--profiling", action="store_true", default=False)
    args = parser.parse_args()
    print(args)

    server = AntServer(not args.no_display, args.fullscreen, args.tournament)
    if args.profiling:
        cProfile.run("server.run(100)")
    else:
        server.run(args.max_rounds)


if __name__ == "__main__":
    main()
