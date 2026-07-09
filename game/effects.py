"""Gorsel efektler: vurus kivilcimi, hasar sayilari, toz, ekran sarsintisi.

EffectSystem cizim dunyasina aittir; oyun mantigini etkilemez. match.py
her vurus olayinda spawn_hit() cagirir, her kare update()/draw() isler.
"""

import math
import random

import pygame

from . import settings
from .hud import load_font

# hitstop: isabet aninda birkac kare dondurma (vurus "otursun" diye)
HITSTOP_NORMAL = 4
HITSTOP_HEAVY = 7
HITSTOP_BLOCK = 3


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "grav")

    def __init__(self, x, y, vx, vy, life, size, color, grav=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color
        self.grav = grav

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.grav
        self.life -= 1

    def draw(self, surf, ox, oy):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        r = max(1, int(self.size * t))
        pygame.draw.circle(surf, self.color, (int(self.x + ox), int(self.y + oy)), r)


class _DamageNumber:
    __slots__ = ("x", "y", "vy", "life", "max_life", "text", "color", "size", "font")

    def __init__(self, x, y, text, color, size, font):
        self.x, self.y = x, y
        self.vy = -1.6
        self.life = self.max_life = 46
        self.text = text
        self.color = color
        self.size = size
        self.font = font

    def update(self):
        self.y += self.vy
        self.vy += 0.045  # yavaslayarak yuksel
        self.life -= 1

    def draw(self, surf, ox, oy):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        alpha = int(255 * min(1.0, t * 2.2))  # sonda solar
        glyph = self.font.render(self.text, True, self.color)
        shadow = self.font.render(self.text, True, settings.BLACK)
        glyph.set_alpha(alpha)
        shadow.set_alpha(alpha)
        pop = 1.0 + 0.35 * max(0.0, (self.max_life - self.life) / 8 - 0)  # kucuk zipla
        if self.life > self.max_life - 6:
            scale = 0.6 + 0.4 * (self.max_life - self.life) / 6
            glyph = pygame.transform.rotozoom(glyph, 0, scale)
            shadow = pygame.transform.rotozoom(shadow, 0, scale)
        rect = glyph.get_rect(center=(int(self.x + ox), int(self.y + oy)))
        surf.blit(shadow, rect.move(2, 2))
        surf.blit(glyph, rect)


class EffectSystem:
    def __init__(self):
        self.particles: list[_Particle] = []
        self.numbers: list[_DamageNumber] = []
        self.shake = 0.0
        self.flash = 0          # tam ekran beyaz parlama (KO)
        self.combo = None       # [count, life, left_side] kombo pankarti
        self._font_big = load_font(46)
        self._font_med = load_font(34)
        self._font_combo = load_font(44)

    # ------------------------------------------------------------------
    def reset(self):
        self.particles.clear()
        self.numbers.clear()
        self.shake = 0.0
        self.flash = 0
        self.combo = None

    def add_shake(self, amount: float):
        self.shake = max(self.shake, amount)

    def spawn_hit(self, x, y, damage, blocked=False, heavy=False, ko=False):
        """Bir isabet noktasinda kivilcim + hasar sayisi uretir."""
        if blocked:
            self._spark(x, y, (150, 200, 255), count=8, speed=4)
            self.numbers.append(_DamageNumber(x, y - 30, "BLOK",
                                              (150, 200, 255), 34, self._font_med))
            self.add_shake(4)
            return

        color = (255, 90, 70) if (heavy or ko) else (255, 210, 70)
        self._spark(x, y, color, count=14 if heavy else 10, speed=7 if heavy else 5)
        # beyaz cekirdek patlama
        self._spark(x, y, settings.WHITE, count=6, speed=9, size=4, life=10)
        font = self._font_big if (heavy or ko) else self._font_med
        self.numbers.append(_DamageNumber(x, y - 40, str(int(damage)), color,
                                          46 if heavy else 34, font))
        self.add_shake(9 if heavy else 5)
        if ko:
            self.flash = 8
            self.add_shake(16)

    def spawn_combo(self, count, left_side):
        self.combo = [count, 46, bool(left_side)]

    def spawn_dust(self, x, y, direction=0):
        """Zipla/in isinde ayak dumani."""
        for _ in range(7):
            ang = random.uniform(math.pi * 0.9, math.pi * 2.1)
            spd = random.uniform(1.0, 3.2)
            self.particles.append(_Particle(
                x + random.uniform(-8, 8), y,
                math.cos(ang) * spd + direction * 1.2,
                -abs(math.sin(ang) * spd) * 0.5,
                life=random.randint(14, 24), size=random.randint(3, 6),
                color=(180, 170, 155), grav=0.06))

    def _spark(self, x, y, color, count=10, speed=5, size=5, life=18):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.4, speed)
            self.particles.append(_Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                life=random.randint(int(life * 0.6), life),
                size=size, color=color, grav=0.12))

    # ------------------------------------------------------------------
    def update(self):
        for p in self.particles:
            p.update()
        for d in self.numbers:
            d.update()
        self.particles = [p for p in self.particles if p.life > 0]
        self.numbers = [d for d in self.numbers if d.life > 0]
        self.shake *= 0.82
        if self.shake < 0.4:
            self.shake = 0.0
        if self.flash > 0:
            self.flash -= 1
        if self.combo is not None:
            self.combo[1] -= 1
            if self.combo[1] <= 0:
                self.combo = None

    def shake_offset(self):
        if self.shake <= 0:
            return 0, 0
        return (random.uniform(-self.shake, self.shake),
                random.uniform(-self.shake, self.shake))

    def draw_world(self, surf, ox, oy):
        """Dunya katmaninda (sarsintiya dahil) cizilen efektler: kivilcim/toz."""
        for p in self.particles:
            p.draw(surf, ox, oy)

    def draw_overlay(self, surf):
        """HUD ustunde, sarsintisiz cizilen efektler: hasar sayilari + flash."""
        for d in self.numbers:
            d.draw(surf, 0, 0)
        if self.combo is not None:
            self._draw_combo(surf)
        if self.flash > 0:
            layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            layer.fill((255, 255, 255, int(150 * self.flash / 8)))
            surf.blit(layer, (0, 0))

    def _draw_combo(self, surf):
        count, life, left = self.combo
        x = 330 if left else settings.WIDTH - 330
        y = 210
        text = f"{count} VURUŞ!"
        glyph = self._font_combo.render(text, True, (255, 226, 84))
        shadow = self._font_combo.render(text, True, settings.BLACK)
        if life > 40:  # giriSte küçükten büyüe zipla
            s = 0.6 + 0.4 * (46 - life) / 6
            glyph = pygame.transform.rotozoom(glyph, 0, s)
            shadow = pygame.transform.rotozoom(shadow, 0, s)
        alpha = int(255 * min(1.0, life / 12))
        glyph.set_alpha(alpha)
        shadow.set_alpha(alpha)
        rect = glyph.get_rect(center=(int(x), y))
        surf.blit(shadow, rect.move(3, 3))
        surf.blit(glyph, rect)
