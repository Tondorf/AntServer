# AntServer

Framework resides in the `AntNetwork` folder.

Server application (with visualizer) can be invoked with `AntServer.py`

Several sample clients are included (JFS01/02/03, JRaider01).

## Game Documentation

The playfield is pre-defined: 1000x1000 fields.
The playfield contains 16 homebases:
```
--------------------------
|                        |
|  X    X    X    X    X |
|                        |
|  X                   X |
|                        |
|  X                   X |
|                        |
|  X                   X |
|                        |
|  X    X    X    X    X |
|                        |
---------------------------
```

Each homebase is 20x20 fields in size. The distance between two neighbouring homebases is 180 fields, each homebase is 90 fields away from the border.
Upper left corner is (0,0).
Homebases are numbered clockwise, upper left is 0.

The world map is never transferred, it is considered known.
The server opens a TCP/IP server (port: 5000), to which the clients (1 per team) connect.
Clients can be players (teams) or watchers.

In every 'turn', each ant can move one field in each direction in one step.
Two ants that are in different teams automatically fight if they are on adjacent fields.
Each round is timed by the server, only the first message per client is used in every round.
Each round is terminated by the 'turn' message (see below).

Clients send messages to the server to act via the TCP/IP link.
The objects (inhabitants and sugar) are sent with every turn to the clients.

A client connection works as follows:
```
Client                  | Server
                        |
opens connection        |
                        | accept connection
send 'hello' packet     |
                        | answer with 'turn' packet or close connection

loop:
  send 'action' packets |
                        | send 'turn' message as end indicator for each step
end loop
```

Clients which do not answer within a certain period get thrown out.

Format of the 'hello' packet:
```
Offset   Type      Description
0        u16       client type (0=non-team, 1=team)
2        16 chars  team name (if team client, else ignored)
```

Format of the 'turn' packet:
```
Offset       Type      Description
0            i16       Team ID of client
2            Team      Team info for team 1 (ID:0)
.
.
.
15*20+2      Team      Team info for team 16 (ID:15)
322          u16       nr. of Objects
324          Object    Object 1
.
.
.
324+(n-1)*6  Object    Object n
```

Each Team is coded as follows:
```
Offset   Type      Description
0        u16       # sugar at home base
2        u16       # remaining ants
4        16 chars  team name
```

Each Object is coded as follows:
```
Offset   Type    Description
0        u8      upper nibble: object type (0=empty, 1=ant, 2=sugar, 3=ant+sugar), lower nibble: team ID
1        u8      upper nibble: ant ID, lower nibble: ant health (1-10)
2        u16     horizontal (X) coordinate
4        u16     vertical (Y) coordinate
```

The 'action' message:
```
Offset   Type      Description
0        u8        action for ant 0: id of field to move to: 123
                                                             456
.                                                            789
.
.
15       u8        action for ant 15
```

In this scheme, any action for ants not alive anymore are ignored.
If an ant should not move, send a 0 or 5 for this ant.
