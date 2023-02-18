#!/usr/bin/env python3
# -*- coding: utf-8 *-*

from AntNetwork.Common import *

try:
    import pygame
except:
    have_pygame = False
else:
    have_pygame = True


class Visualizer:
    def __init__(self, fullscreen):
        if have_pygame:
            pygame.init()
            if fullscreen:
                opts = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
            else:
                opts = 0
            pygame.display.set_caption('AntServer')
            self.screen = pygame.display.set_mode([1280, 1024], opts)
            #self.draw()

    def draw(self, playfield):
        if not have_pygame:
            return

        self.screen.fill((0, 0, 0))
        for i, field in list(playfield.items()):  # for every pixel:
            if field == 0:
                continue
            if field & ANT_WITH_SUGAR == ANT_WITH_SUGAR:
                self.screen.set_at(coord(i), (255, 255, 0))
            elif field & SUGAR == SUGAR:
                self.screen.set_at(coord(i), (0, 255, 0))
            elif field & ANT == ANT:
                self.screen.set_at(coord(i), (255, 0, 0))
            elif field & HOMEBASE == HOMEBASE:
                self.screen.set_at(coord(i), (100, 100, 100))

        pygame.display.flip()
