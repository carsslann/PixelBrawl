"""Yardimci tam-ekran gorunumler: hareket listesi (move list) ve mac arasi
pankartlar. Menu/duraklatmadan cagrilir; kendi kucuk dongusunu kosar."""

import pygame

from . import settings
from .characters import CHARACTERS, character_moves
from .hud import load_font


def move_list_screen(screen, clock, char_key: str):
    """Bir karakterin hareket + kombo listesini gosterir; tusa basinca doner."""
    data = CHARACTERS[char_key]
    moves, combos = character_moves(char_key)
    f_title = load_font(56)
    f_head = load_font(28)
    f_row = load_font(24)
    f_hint = load_font(20)

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                return "back"

        screen.fill(settings.SKY_TOP)
        cx = settings.WIDTH // 2
        title = f_title.render(f"{data.name} — HAREKETLER", True, settings.HP_MAIN)
        sh = f_title.render(f"{data.name} — HAREKETLER", True, settings.BLACK)
        r = title.get_rect(center=(cx, 70))
        screen.blit(sh, r.move(3, 3))
        screen.blit(title, r)

        # sol sutun: hareketler
        x = 150
        y = 150
        head = f_head.render("HAREKETLER", True, settings.WHITE)
        screen.blit(head, (x, y))
        y += 44
        for name, cmd in moves:
            n = f_row.render(name, True, settings.WHITE)
            c = f_row.render(cmd, True, settings.HP_MAIN)
            screen.blit(n, (x, y))
            screen.blit(c, (x + 320, y))
            y += 34

        # sag sutun: kombolar
        x2 = settings.WIDTH // 2 + 120
        y2 = 150
        head2 = f_head.render("KOMBOLAR", True, settings.WHITE)
        screen.blit(head2, (x2, y2))
        y2 += 44
        for name, seq in combos:
            n = f_row.render(name, True, settings.SUPER_FILL)
            screen.blit(n, (x2, y2))
            y2 += 30
            s = f_row.render("   " + seq, True, settings.WHITE)
            screen.blit(s, (x2, y2))
            y2 += 38

        hint = f_hint.render("Bir tuşa bas — geri dön", True, settings.FLOOR_LINE)
        screen.blit(hint, hint.get_rect(center=(cx, settings.HEIGHT - 40)))
        pygame.display.flip()
        clock.tick(settings.FPS)


def banner_screen(screen, clock, lines, frames=150, sub=""):
    """Kisa bilgi pankarti (arcade gecis/bitis). frames sonra ya da tusla doner."""
    f_big = load_font(72)
    f_sub = load_font(30)
    t = 0
    while t < frames:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN and t > 20:
                return "next"
        screen.fill(settings.SKY_TOP)
        cx, cy = settings.WIDTH // 2, settings.HEIGHT // 2 - 30
        for i, line in enumerate(lines):
            g = f_big.render(line, True, settings.HP_MAIN)
            s = f_big.render(line, True, settings.BLACK)
            r = g.get_rect(center=(cx, cy + i * 80))
            screen.blit(s, r.move(3, 3))
            screen.blit(g, r)
        if sub:
            ss = f_sub.render(sub, True, settings.WHITE)
            screen.blit(ss, ss.get_rect(center=(cx, cy + len(lines) * 80 + 20)))
        pygame.display.flip()
        clock.tick(settings.FPS)
        t += 1
    return "next"
