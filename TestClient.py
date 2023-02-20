#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import AntNetwork
import AntNetwork.Client

import sys

if __name__ == "__main__":
    client = AntNetwork.Client.AntClient(sys.argv[1], 5000, "TestClient", True)
    while True:
        client.send_action((1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 5, 6, 7))
        Id, teams, objects = client.get_turn()
        ants = 0
        for t in teams:
            ants += t[1]
        print("ID: {}".format(Id))
        print("Teams: {}".format(len(teams)))
        print("Objects: {} ({} ants)".format(len(objects), ants))
        for obj in sorted(objects):
            if (obj[0] >> 4) & 1 == 1:
                print(obj[0] >> 4, obj[0] & 0x0F, obj[1] >> 4, obj[1] & 0x0F)
