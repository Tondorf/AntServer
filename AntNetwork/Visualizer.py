#!/usr/bin/env python3
# -*- coding: utf-8 *-*

import string
from enum import Enum
from AntNetwork.Common import *

try:
    import pygame
except:
    have_pygame = False
else:
    have_pygame = True


class Colors(Enum):
    black    = (  0,   0,   0)
    grey     = (127, 127, 127)
    white    = (255, 255, 255)
    red      = (255,   0,   0)
    redish   = (255,   0, 200)
    green    = (  0, 255,   0)
    greenish = (  0, 255, 255)
    blue     = (  0,   0, 255)
    yellow   = (255, 255,   0)


class Visualizer:

    size = width, height = 1000 + 380, 1000
    FPS = 60

    # teamColors = [(0, 110, 110), (240, 0, 0), (0, 240, 0), (160, 0, 80),
    #               (200, 40, 0), (0, 200, 40), (40, 0, 200), (160, 80, 0),
    #               (0, 160, 80), (80, 0, 160), (120, 120, 0), (0, 120, 120),
    #               (120, 0, 120), (80, 160, 0), (0, 80, 160), (240, 0, 0)
    # ]

    def __init__(self, fullscreen):
        if have_pygame:
            pygame.init()
            if fullscreen:
                opts = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
            else:
                opts = 0
            pygame.display.set_caption('AntServer')
            self.screen = pygame.display.set_mode([self.width, self.height], opts)
            self.font = pygame.font.Font('LiberationMono-Regular.ttf', 18)
            #self.draw()

    @staticmethod
    def draw_text(disp, text, font, pos, color):
        label = font.render(text, 1, color)
        posi = label.get_rect(topleft=(pos[0], pos[1]))
        disp.blit(label, posi)

    def draw(self, teams, playfield):
        if not have_pygame:
            return

        self.screen.fill(Colors.black.value)
        for i, field in list(playfield.items()):  # for every pixel:
            if field == 0:
                continue
            if field & ANT_WITH_TOXIN == ANT_WITH_TOXIN:
                self.screen.set_at(coord(i), Colors.greenish.value)
            elif field & ANT_WITH_SUGAR == ANT_WITH_SUGAR:
                self.screen.set_at(coord(i), Colors.redish.value)
            elif field & TOXIN == TOXIN:
                self.screen.set_at(coord(i), Colors.green.value)
            elif field & SUGAR == SUGAR:
                self.screen.set_at(coord(i), Colors.white.value)
            elif field & ANT == ANT:
                self.screen.set_at(coord(i), Colors.red.value)
            elif field & HOMEBASE == HOMEBASE:
                self.screen.set_at(coord(i), Colors.grey.value)

        self.draw_text(self.screen, 'AntServer Teams', self.font, (1100, 20), Colors.white.value)
        self.draw_text(self.screen, 'ID Ants Score Name', self.font, (1020, 50), Colors.red.value)
        for id, t in enumerate(teams):
            score, ants, name = t
            name = ''.join([chr(c) for c in name if chr(c) in string.printable])
            self.draw_text(self.screen, "{:>2}   {:>2} {:>5} {}".format(id, ants, score, name),
                self.font, (1020, 80 + id * 20), Colors.white.value)

        pygame.display.flip()
