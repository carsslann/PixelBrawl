"""Sokak Kavgacisi — cakma street fighter (Pygame).

Baslatmak icin: run.bat  (veya: py main.py)
"""

import pygame

from game import audio, config, match, settings
from game.menu import Menu


def main():
    pygame.init()
    screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
    pygame.display.set_caption("Sokak Kavgacısı")
    clock = pygame.time.Clock()
    audio.init()
    cfg = config.load()                    # ses seviyeleri + tuslar uygulanir
    if cfg.get("fullscreen"):
        screen = pygame.display.set_mode(
            (settings.WIDTH, settings.HEIGHT), pygame.FULLSCREEN)
    audio.play_music(vol=1.0)              # gercek ses config.music_vol ile

    while True:
        selection = Menu().run(screen, clock)
        screen = pygame.display.get_surface()   # ayarlar tam ekrani degistirebilir
        if selection is None:
            break
        result = match.run(screen, clock, selection)
        screen = pygame.display.get_surface()
        if result == "quit":
            break

    pygame.quit()


if __name__ == "__main__":
    main()
