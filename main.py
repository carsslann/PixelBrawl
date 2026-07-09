"""Sokak Kavgacisi — cakma street fighter (Pygame).

Baslatmak icin: run.bat  (veya: py main.py)
"""

import pygame

from game import audio, match, settings
from game.menu import Menu


def main():
    pygame.init()
    screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
    pygame.display.set_caption("Sokak Kavgacısı")
    clock = pygame.time.Clock()
    audio.init()
    audio.play_music(vol=0.3)

    while True:
        selection = Menu().run(screen, clock)
        if selection is None:
            break
        result = match.run(screen, clock, selection)
        if result == "quit":
            break

    pygame.quit()


if __name__ == "__main__":
    main()
