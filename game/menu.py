"""Ana menu: karakter, rakip ve zorluk secimi."""

import pygame

from . import audio, screens, settings, sprites, weapons
from .characters import CHARACTERS, CHARACTER_ORDER
from .controller import DIFFICULTY_LABELS, DIFFICULTY_ORDER
from .hud import load_font
from .settings_screen import settings_screen

MODES = ["pve", "pvp", "arcade"]
MODE_LABELS = {"pve": "Tek Kişi (Bot)", "pvp": "2 Kişi (PvP)", "arcade": "Arcade"}


class Menu:
    def __init__(self):
        self.rows = ["mode", "p1", "weapon", "p2", "difficulty"]
        self.row_labels = {"mode": "MOD", "p1": "KARAKTERİN", "weapon": "SİLAH",
                           "p2": "RAKİP", "difficulty": "ZORLUK"}
        self.selected_row = 0
        self.mode_idx = 0
        self.p1_idx = 0
        self.weapon_idx = 0
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
                        audio.play("menu_select")
                        return {
                            "mode": MODES[self.mode_idx],
                            "p1": CHARACTER_ORDER[self.p1_idx],
                            "p1_weapon": weapons.WEAPON_ORDER[self.weapon_idx],
                            "p2": CHARACTER_ORDER[self.p2_idx],
                            "difficulty": DIFFICULTY_ORDER[self.diff_idx],
                        }
                    if e.key == pygame.K_h:   # hareket listesi (secili karakter)
                        if screens.move_list_screen(
                                screen, clock,
                                CHARACTER_ORDER[self.p1_idx]) == "quit":
                            return None
                    if e.key == pygame.K_o:   # ayarlar
                        if settings_screen(screen, clock) == "quit":
                            return None
                        screen = pygame.display.get_surface()
                    if e.key in (pygame.K_UP, pygame.K_w):
                        self.selected_row = (self.selected_row - 1) % len(self.rows)
                        audio.play("menu_move")
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected_row = (self.selected_row + 1) % len(self.rows)
                        audio.play("menu_move")
                    elif e.key in (pygame.K_LEFT, pygame.K_a):
                        self._change(-1)
                        audio.play("menu_move")
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        self._change(1)
                        audio.play("menu_move")
            self._draw(screen)
            pygame.display.flip()
            clock.tick(settings.FPS)

    def _change(self, step: int):
        row = self.rows[self.selected_row]
        if row == "mode":
            self.mode_idx = (self.mode_idx + step) % len(MODES)
        elif row == "p1":
            self.p1_idx = (self.p1_idx + step) % len(CHARACTER_ORDER)
        elif row == "weapon":
            self.weapon_idx = (self.weapon_idx + step) % len(weapons.WEAPON_ORDER)
        elif row == "p2":
            self.p2_idx = (self.p2_idx + step) % len(CHARACTER_ORDER)
        else:
            self.diff_idx = (self.diff_idx + step) % len(DIFFICULTY_ORDER)

    # ------------------------------------------------------------------
    def _row_value(self, row: str) -> str:
        if row == "mode":
            return MODE_LABELS[MODES[self.mode_idx]]
        if row == "p1":
            return CHARACTERS[CHARACTER_ORDER[self.p1_idx]].name
        if row == "weapon":
            return weapons.WEAPONS[weapons.WEAPON_ORDER[self.weapon_idx]].name
        if row == "p2":
            return CHARACTERS[CHARACTER_ORDER[self.p2_idx]].name
        return DIFFICULTY_LABELS[DIFFICULTY_ORDER[self.diff_idx]]

    def _draw_weapon_panel(self, surf, cx):
        wk = weapons.WEAPON_ORDER[self.weapon_idx]
        wd = weapons.WEAPONS[wk]
        py = 578
        ic = weapons.icon(wk, 72)
        surf.blit(ic, ic.get_rect(center=(cx - 150, py)))
        nm = self.font_sub.render(wd.name, True, settings.HP_MAIN)
        surf.blit(nm, nm.get_rect(midleft=(cx - 108, py - 30)))
        stats = [("Hasar", wd.damage_mult), ("Menzil", wd.reach_mult),
                 ("Hız", wd.speed_mult)]
        for i, (lbl, mult) in enumerate(stats):
            by = py - 8 + i * 20
            t = self.font_help.render(lbl, True, settings.WHITE)
            surf.blit(t, t.get_rect(midright=(cx + 2, by)))
            bar = pygame.Rect(cx + 12, by - 7, 150, 14)
            pygame.draw.rect(surf, (48, 48, 64), bar)
            frac = max(0.06, min(1.0, mult - 0.5))   # 0.5->bos, 1.5->dolu
            pygame.draw.rect(surf, settings.SUPER_FILL,
                             (bar.x, bar.y, int(bar.w * frac), bar.h))
            pygame.draw.rect(surf, settings.WHITE, bar, 1)

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
            y = 292 + i * 56
            selected = i == self.selected_row
            color = settings.HP_MAIN if selected else settings.WHITE
            label = self.font_row.render(self.row_labels[row], True, color)
            surf.blit(label, label.get_rect(midright=(cx - 40, y)))
            value = f"◄  {self._row_value(row)}  ►" if selected \
                else self._row_value(row)
            val = self.font_row.render(value, True, color)
            surf.blit(val, val.get_rect(midleft=(cx + 40, y)))
        self._draw_weapon_panel(surf, cx)

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
                if side < 0:   # p1: secili silahi elinde goster
                    bl = weapons.blade(weapons.WEAPON_ORDER[self.weapon_idx], 3.0)
                    surf.blit(bl, bl.get_rect(center=(x + 55, base_y - 150)))
            else:
                body = pygame.Rect(0, 0, data.width, data.height)
                body.midbottom = (x, base_y)
                pygame.draw.rect(surf, data.color, body, border_radius=10)
                pygame.draw.circle(surf, settings.SKIN,
                                   (x, body.top - data.width // 4), data.width // 3)

        helps = [
            "ENTER: Başla   ESC: Çıkış   H: Hareketler   O: Ayarlar   Ok/WASD: Seçim",
            "A/D yürü   W zıpla   S çömel   J yumruk   K tekme   (geri tut = blok)   ESC duraklat",
            "Kombo: çömel+vuruş = alçak · zıpla+vuruş = overhead · isabette zincir (yumruk→tekme)",
        ]
        for i, h in enumerate(helps):
            t = self.font_help.render(h, True, settings.FLOOR_LINE)
            surf.blit(t, t.get_rect(center=(cx, settings.HEIGHT - 82 + i * 26)))
