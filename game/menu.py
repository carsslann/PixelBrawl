"""Ana menu: karakter, rakip ve zorluk secimi."""

import pygame

from . import settings, sprites
from .characters import CHARACTERS, CHARACTER_ORDER
from .controller import DIFFICULTY_LABELS, DIFFICULTY_ORDER
from .hud import load_font


class Menu:
    def __init__(self):
        self.rows = ["p1", "p2", "difficulty"]
        self.row_labels = {"p1": "KARAKTERİN", "p2": "RAKİP", "difficulty": "ZORLUK"}
        self.selected_row = 0
        self.p1_idx = 0
        self.p2_idx = 1
        self.diff_idx = 1  # orta
        self.font_title = load_font(88)
        self.font_sub = load_font(24)
        self.font_row = load_font(34)
        self.font_help = load_font(20)
        self._preview_cache: dict = {}  # karakter anahtari -> idle sprite

    def _preview(self, key: str):
        if key not in self._preview_cache:
            self._preview_cache[key] = sprites.load_idle_preview(CHARACTERS[key], 300)
        return self._preview_cache[key]

    # ------------------------------------------------------------------
    def run(self, screen, clock):
        """Secim dict'i dondurur; cikista None."""
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return None
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return None
                    if e.key == pygame.K_RETURN:
                        return {
                            "p1": CHARACTER_ORDER[self.p1_idx],
                            "p2": CHARACTER_ORDER[self.p2_idx],
                            "difficulty": DIFFICULTY_ORDER[self.diff_idx],
                        }
                    if e.key in (pygame.K_UP, pygame.K_w):
                        self.selected_row = (self.selected_row - 1) % len(self.rows)
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_row = (self.selected_row + 1) % len(self.rows)
                    elif e.key in (pygame.K_LEFT, pygame.K_a):
                        self._change(-1)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        self._change(1)
            self._draw(screen)
            pygame.display.flip()
            clock.tick(settings.FPS)

    def _change(self, step: int):
        row = self.rows[self.selected_row]
        if row == "p1":
            self.p1_idx = (self.p1_idx + step) % len(CHARACTER_ORDER)
        elif row == "p2":
            self.p2_idx = (self.p2_idx + step) % len(CHARACTER_ORDER)
        else:
            self.diff_idx = (self.diff_idx + step) % len(DIFFICULTY_ORDER)

    # ------------------------------------------------------------------
    def _row_value(self, row: str) -> str:
        if row == "p1":
            return CHARACTERS[CHARACTER_ORDER[self.p1_idx]].name
        if row == "p2":
            return CHARACTERS[CHARACTER_ORDER[self.p2_idx]].name
        return DIFFICULTY_LABELS[DIFFICULTY_ORDER[self.diff_idx]]

    def _draw(self, surf):
        surf.fill(settings.SKY_TOP)
        cx = settings.WIDTH // 2

        title = self.font_title.render("SOKAK KAVGACISI", True, settings.HP_MAIN)
        shadow = self.font_title.render("SOKAK KAVGACISI", True, settings.BLACK)
        rect = title.get_rect(center=(cx, 150))
        surf.blit(shadow, rect.move(5, 5))
        surf.blit(title, rect)
        sub = self.font_sub.render("çakma street fighter", True, settings.WHITE)
        surf.blit(sub, sub.get_rect(center=(cx, 215)))

        # secim satirlari
        for i, row in enumerate(self.rows):
            y = 330 + i * 70
            selected = i == self.selected_row
            color = settings.HP_MAIN if selected else settings.WHITE
            label = self.font_row.render(self.row_labels[row], True, color)
            surf.blit(label, label.get_rect(midright=(cx - 40, y)))
            value = f"◄  {self._row_value(row)}  ►" if selected \
                else self._row_value(row)
            val = self.font_row.render(value, True, color)
            surf.blit(val, val.get_rect(midleft=(cx + 40, y)))

        # karakter onizleme (secili karakterlerin idle sprite'i)
        base_y = 585
        for idx, side in ((self.p1_idx, -1), (self.p2_idx, 1)):
            key = CHARACTER_ORDER[idx]
            data = CHARACTERS[key]
            x = cx + side * 430
            # zemin golgesi
            shadow = pygame.Surface((150, 26), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
            surf.blit(shadow, shadow.get_rect(center=(x, base_y + 4)))
            sprite = self._preview(key)
            if sprite is not None:
                # p1 sola (merkeze saga) bakar, p2 saga (merkeze sola) bakar
                if side > 0:
                    sprite = pygame.transform.flip(sprite, True, False)
                surf.blit(sprite, sprite.get_rect(midbottom=(x, base_y)))
            else:
                body = pygame.Rect(0, 0, data.width, data.height)
                body.midbottom = (x, base_y)
                pygame.draw.rect(surf, data.color, body, border_radius=10)
                pygame.draw.circle(surf, settings.SKIN,
                                   (x, body.top - data.width // 4), data.width // 3)

        helps = [
            "ENTER: Başla      ESC: Çıkış      Ok tuşları / WASD: Seçim",
            "Oyun içi: A/D yürü   W zıpla   S blok   J yumruk   K tekme   ESC duraklat",
        ]
        for i, h in enumerate(helps):
            t = self.font_help.render(h, True, settings.FLOOR_LINE)
            surf.blit(t, t.get_rect(center=(cx, settings.HEIGHT - 70 + i * 28)))
