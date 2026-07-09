"""HUD: can barlari, sure, round isaretleri ve pankartlar."""

import pygame

from . import settings, sprites

BAR_W = 460
BAR_H = 30
BAR_Y = 34
EDGE = 40           # ekran kenar bosluğu
PORTRAIT = 64       # portre kutusu boyu
BAR_X = EDGE + PORTRAIT + 8   # can barinin dis kenari (portreye yer)


def load_font(size: int, bold: bool = True) -> pygame.font.Font:
    """Turkce karakterler icin sistem fontu (arial); yoksa varsayilan."""
    try:
        font = pygame.font.SysFont("arial", size, bold=bold)
        if font is not None:
            return font
    except Exception:
        pass
    return pygame.font.Font(None, size)


class HUD:
    def __init__(self, p1, p2, difficulty_label: str = ""):
        self.p1, self.p2 = p1, p2
        self.difficulty_label = difficulty_label
        # hasar sonrasi geriden eriyen bar degerleri
        self.lag = [float(p1.data.max_health), float(p2.data.max_health)]
        self.font_timer = load_font(52)
        self.font_name = load_font(22)
        self.font_small = load_font(18)
        self.font_banner = load_font(84)
        self.font_sub = load_font(30)
        self.portraits = [self._make_portrait(p1.data),
                          self._make_portrait(p2.data)]

    @staticmethod
    def _make_portrait(data):
        box = PORTRAIT
        surf = pygame.Surface((box, box))
        surf.fill((28, 28, 40))
        try:
            idle = sprites.load_idle_preview(data, 150)
            if idle is None:
                raise ValueError
            w, h = idle.get_size()
            crop = idle.subsurface(pygame.Rect(
                int(w * 0.18), int(h * 0.10), int(w * 0.64), int(h * 0.46))).copy()
            surf.blit(pygame.transform.smoothscale(crop, (box - 8, box - 8)), (4, 4))
        except Exception:
            pygame.draw.circle(surf, settings.SKIN, (box // 2, box // 2), box // 3)
        pygame.draw.rect(surf, data.color, surf.get_rect(), 4)
        pygame.draw.rect(surf, settings.WHITE, surf.get_rect(), 1)
        return surf

    def update(self):
        for i, f in enumerate((self.p1, self.p2)):
            if self.lag[i] > f.health:
                self.lag[i] = max(float(f.health), self.lag[i] - 0.8)
            else:
                self.lag[i] = float(f.health)

    def draw(self, surf, timer_seconds: int, wins, round_num: int):
        self._draw_bar(surf, self.p1, self.lag[0], left=True)
        self._draw_bar(surf, self.p2, self.lag[1], left=False)
        self._draw_meter(surf, self.p1, left=True)
        self._draw_meter(surf, self.p2, left=False)
        surf.blit(self.portraits[0], (EDGE, BAR_Y))   # portreler (B9)
        surf.blit(pygame.transform.flip(self.portraits[1], True, False),
                  (settings.WIDTH - EDGE - PORTRAIT, BAR_Y))
        self._draw_timer(surf, timer_seconds)
        self._draw_wins(surf, wins)
        # ust bilgi satiri
        info = f"ROUND {round_num}"
        if self.difficulty_label:
            info += f"  •  Bot: {self.difficulty_label}"
        self._shadow_text(surf, self.font_small, info, settings.WHITE,
                          midtop=(settings.WIDTH // 2, BAR_Y + BAR_H + 34))

    @staticmethod
    def _shadow_text(surf, font, text, color, **anchor):
        """Acik gokyuzu ustunde okunurluk icin golgeli metin."""
        glyph = font.render(text, True, color)
        shadow = font.render(text, True, settings.BLACK)
        rect = glyph.get_rect(**anchor)
        surf.blit(shadow, rect.move(2, 2))
        surf.blit(glyph, rect)

    def _draw_bar(self, surf, fighter, lag_value, left: bool):
        x = BAR_X if left else settings.WIDTH - BAR_X - BAR_W
        back = pygame.Rect(x, BAR_Y, BAR_W, BAR_H)
        pygame.draw.rect(surf, settings.HP_BACK, back)

        max_hp = fighter.data.max_health
        lag_w = int(BAR_W * max(0.0, lag_value) / max_hp)
        cur_w = int(BAR_W * max(0, fighter.health) / max_hp)
        # barlar ortaya dogru erir (klasik SF): sol bar sagdan, sag bar soldan dolar
        for width, color in ((lag_w, settings.HP_LAG), (cur_w, settings.HP_MAIN)):
            if width <= 0:
                continue
            if left:
                rect = pygame.Rect(x + BAR_W - width, BAR_Y, width, BAR_H)
            else:
                rect = pygame.Rect(x, BAR_Y, width, BAR_H)
            pygame.draw.rect(surf, color, rect)
        pygame.draw.rect(surf, settings.HP_BORDER, back, 3)

        ny = BAR_Y + BAR_H + 16
        if left:
            self._shadow_text(surf, self.font_name, fighter.data.name,
                              settings.WHITE, topleft=(x + 2, ny))
        else:
            self._shadow_text(surf, self.font_name, fighter.data.name,
                              settings.WHITE, topright=(x + BAR_W - 2, ny))

    def _draw_meter(self, surf, fighter, left: bool):
        mw, mh = int(BAR_W * 0.66), 9
        x = BAR_X if left else settings.WIDTH - BAR_X - mw
        y = BAR_Y + BAR_H + 4
        back = pygame.Rect(x, y, mw, mh)
        pygame.draw.rect(surf, settings.SUPER_BACK, back)
        frac = max(0.0, min(1.0, fighter.meter / settings.SUPER_MAX))
        fw = int(mw * frac)
        if fw > 0:
            full = fighter.meter >= settings.SUPER_MAX
            color = settings.SUPER_FULL if full else settings.SUPER_FILL
            fr = pygame.Rect(x if left else x + mw - fw, y, fw, mh)
            pygame.draw.rect(surf, color, fr)
        pygame.draw.rect(surf, settings.HP_BORDER, back, 2)

    def _draw_timer(self, surf, seconds: int):
        text = self.font_timer.render(f"{max(0, seconds):02d}", True, settings.TIMER_COLOR)
        rect = text.get_rect(midtop=(settings.WIDTH // 2, 16))
        shadow = self.font_timer.render(f"{max(0, seconds):02d}", True, settings.BLACK)
        surf.blit(shadow, rect.move(3, 3))
        surf.blit(text, rect)

    def _draw_wins(self, surf, wins):
        r = 9
        cy = BAR_Y + BAR_H + 16
        for i in range(settings.ROUNDS_TO_WIN):
            # p1 isaretleri barin ic ucunda (ortada), p2'ninkiler simetrik
            x1 = BAR_X + BAR_W - 18 - i * 26
            x2 = settings.WIDTH - BAR_X - BAR_W + 18 + i * 26
            for cx, won in ((x1, wins[0] > i), (x2, wins[1] > i)):
                if won:
                    pygame.draw.circle(surf, settings.HP_MAIN, (cx, cy), r)
                pygame.draw.circle(surf, settings.WHITE, (cx, cy), r, 2)

    # ------------------------------------------------------------------
    # pankartlar
    # ------------------------------------------------------------------
    def draw_vs(self, surf, p1, p2, t: float):
        """Round basi VS acilisi: iki isim kenardan kayarak gelir + buyuk VS."""
        cx = settings.WIDTH // 2
        cy = settings.HEIGHT // 2 - 20
        ease = min(1.0, t * 1.4)
        off = int((1 - ease) ** 2 * 620)
        for f, side in ((p1, -1), (p2, 1)):
            nm = self.font_timer.render(f.data.name, True, settings.WHITE)
            sh = self.font_timer.render(f.data.name, True, settings.BLACK)
            bar = pygame.Rect(0, 0, nm.get_width() + 44, nm.get_height() + 16)
            if side < 0:
                bar.midright = (cx - 66 - off, cy)
            else:
                bar.midleft = (cx + 66 + off, cy)
            pygame.draw.rect(surf, f.data.color, bar, border_radius=10)
            pygame.draw.rect(surf, settings.WHITE, bar, 3, border_radius=10)
            surf.blit(sh, sh.get_rect(center=(bar.centerx + 2, bar.centery + 2)))
            surf.blit(nm, nm.get_rect(center=bar.center))
        scale = 0.4 + 0.6 * ease
        vs = pygame.transform.rotozoom(
            self.font_banner.render("VS", True, settings.HP_MAIN), 0, scale)
        vsh = pygame.transform.rotozoom(
            self.font_banner.render("VS", True, settings.BLACK), 0, scale)
        surf.blit(vsh, vsh.get_rect(center=(cx + 4, cy + 4)))
        surf.blit(vs, vs.get_rect(center=(cx, cy)))

    def banner(self, surf, text: str, sub: str = ""):
        big = self.font_banner.render(text, True, settings.WHITE)
        shadow = self.font_banner.render(text, True, settings.BLACK)
        rect = big.get_rect(center=(settings.WIDTH // 2, settings.HEIGHT // 2 - 40))
        surf.blit(shadow, rect.move(4, 4))
        surf.blit(big, rect)
        if sub:
            s = self.font_sub.render(sub, True, settings.TIMER_COLOR)
            surf.blit(s, s.get_rect(center=(settings.WIDTH // 2, settings.HEIGHT // 2 + 36)))
