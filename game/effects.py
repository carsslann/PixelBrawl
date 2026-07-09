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


class _ImpactRing:
    """Isabet noktasinda hizla genisleyip inceleyip solan radyal halka."""
    __slots__ = ("x", "y", "life", "max_life", "r0", "r1", "color", "w0")

    def __init__(self, x, y, color, r0, r1, life, w0):
        self.x, self.y = x, y
        self.life = self.max_life = life
        self.r0 = r0            # baslangic yaricapi
        self.r1 = r1            # bitis yaricapi
        self.color = color
        self.w0 = w0            # baslangic kenar kalinligi

    def update(self):
        self.life -= 1

    def draw(self, surf, ox, oy):
        if self.life <= 0:
            return
        # ilerleme 0->1 (ease-out ile hizli acilip yavaslar)
        p = 1.0 - (self.life / self.max_life)
        ease = 1.0 - (1.0 - p) * (1.0 - p)
        r = self.r0 + (self.r1 - self.r0) * ease
        if r < 1:
            return
        t = self.life / self.max_life          # 1->0 solma
        alpha = int(220 * t)
        if alpha <= 0:
            return
        width = max(1, int(self.w0 * t))
        width = min(width, int(r))             # width, yaricapi asamaz
        cx, cy = int(self.x + ox), int(self.y + oy)
        # alfa icin ayri katman (halka + ikinci esmerkezli hat)
        pad = int(r) + width + 4
        size = pad * 2
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        col = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(layer, col, (pad, pad), int(r), width)
        # ince ikinci halka (biraz iceride, daha soluk)
        r2 = int(r * 0.62)
        if r2 > 1:
            col2 = (self.color[0], self.color[1], self.color[2], int(alpha * 0.55))
            pygame.draw.circle(layer, col2, (pad, pad), r2, max(1, width // 2))
        # erken karelerde kisa merkez flasi
        if p < 0.35:
            fa = int(200 * (1.0 - p / 0.35))
            fr = max(2, int(self.r0 * (1.0 - p / 0.35) + 2))
            pygame.draw.circle(
                layer, (255, 255, 255, fa), (pad, pad), fr)
        surf.blit(layer, (cx - pad, cy - pad))


class _AnimEffect:
    """Kare-dizisi (sprite) animasyon efekti: patlama, muzzle flas vb.

    Kareler disaridan verilir (fx_sprites'tan gelir, burada import edilmez).
    (x, y) MERKEZdir. loop=False ise bir kez oynayip biter (life yok olur);
    loop=True ise sonsuza kadar donerek oynar.
    """
    __slots__ = ("frames", "x", "y", "spf", "loop", "n", "_t", "idx", "life")

    def __init__(self, frames, x, y, fps=24, scale=1.0, loop=False):
        # olcekleme gerekiyorsa kareleri bir kez olcekleyip sakla
        if scale != 1.0:
            scaled = []
            for f in frames:
                w = max(1, int(f.get_width() * scale))
                h = max(1, int(f.get_height() * scale))
                scaled.append(pygame.transform.smoothscale(f, (w, h)))
            self.frames = scaled
        else:
            self.frames = list(frames)
        self.x, self.y = x, y
        self.n = len(self.frames)
        # kare basina gecen "kare" sayisi (60fps oyun dongusune gore)
        self.spf = max(1.0, settings.FPS / max(1, fps))
        self.loop = bool(loop)
        self._t = 0.0          # gecen zaman (kare cinsinden)
        self.idx = 0           # anlik kare index'i
        self.life = 1          # >0 iken canli; loop=False'da son karede 0'lanir

    def update(self):
        if self.life <= 0:
            return
        self._t += 1.0
        if self._t >= self.spf:
            self._t -= self.spf
            self.idx += 1
            if self.idx >= self.n:
                if self.loop:
                    self.idx = 0
                else:
                    # son kareyi gecti -> efekt biter
                    self.idx = self.n - 1
                    self.life = 0

    def draw(self, surf, ox, oy):
        if self.life <= 0 or self.n == 0:
            return
        frame = self.frames[self.idx]
        rect = frame.get_rect(center=(int(self.x + ox), int(self.y + oy)))
        surf.blit(frame, rect)


class _AmbientParticle:
    """Sahne atmosferi: yavasca suzulen yaprak/toz/kar/kor."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color",
                 "sway", "phase", "shape")

    def __init__(self, x, y, vx, vy, life, size, color, sway, phase, shape):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color
        self.sway = sway        # yatay salinim genligi
        self.phase = phase      # salinim fazi
        self.shape = shape      # "dot" | "leaf" | "flake"

    def update(self):
        self.phase += 0.06
        self.x += self.vx + math.sin(self.phase) * self.sway
        self.y += self.vy
        self.life -= 1

    def draw(self, surf, ox, oy):
        if self.life <= 0:
            return
        # basta ve sonda hafif solma (girip-cikma yumusak olsun)
        t = self.life / self.max_life
        fade = min(1.0, t * 4.0, (1.0 - t) * 8.0 + 0.15)
        alpha = int(200 * max(0.0, min(1.0, fade)))
        if alpha <= 0:
            return
        x, y = int(self.x + ox), int(self.y + oy)
        s = max(1, int(self.size))
        col = (self.color[0], self.color[1], self.color[2], alpha)
        if self.shape == "leaf":
            layer = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(layer, col, (1, 1, s * 2, s + 1))
            layer = pygame.transform.rotate(layer, math.degrees(self.phase) % 360)
            rect = layer.get_rect(center=(x, y))
            surf.blit(layer, rect)
        else:
            layer = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(layer, col, (s + 1, s + 1), s)
            surf.blit(layer, (x - s - 1, y - s - 1))


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
        self.rings: list[_ImpactRing] = []          # impact halkalari
        self.anims: list[_AnimEffect] = []          # kare-dizisi anim efektleri
        self.ambient: list[_AmbientParticle] = []   # ortam partikulleri
        self.ambient_kind = "none"                  # sahne atmosferi turu
        self._ambient_timer = 0                     # uretim sayaci
        self.vignette = False                       # slow-mo vinyet acik mi
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
        self.rings.clear()
        self.anims.clear()          # kare-dizisi anim efektlerini temizle
        self.ambient.clear()        # birikmis ambient partikulleri temizle
        self._ambient_timer = 0
        # NOT: ambient_kind sahne ayaridir, reset'te korunur
        self.vignette = False
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
    def spawn_impact_ring(self, x, y, color=(255, 220, 120), big=False):
        """Isabet noktasinda hizla genisleyip solan radyal halka (impact ring).

        Agir vurus / KO icin big=True daha buyuk halka uretir. draw_world
        icinde (sarsintiya dahil) cizilir.
        """
        if big:
            self.rings.append(_ImpactRing(
                x, y, color, r0=10, r1=110, life=20, w0=8))
        else:
            self.rings.append(_ImpactRing(
                x, y, color, r0=6, r1=64, life=15, w0=5))

    def spawn_anim(self, frames, x, y, fps=24, scale=1.0, loop=False):
        """Kare-dizisi (sprite) animasyon efekti baslat.

        frames: list[pygame.Surface] (fx_sprites'tan gelir; burada import
        edilmez). (x, y) MERKEZdir. loop=False iken bir kez oynayip kaybolur.
        scale != 1.0 ise kareler olceklenir. Bos/None frames -> no-op (crash
        yok). draw_world icinde (sarsintiya dahil) cizilir.
        """
        if not frames:
            return
        self.anims.append(_AnimEffect(frames, x, y, fps=fps, scale=scale, loop=loop))

    def set_ambient(self, kind):
        """Sahne ortam partikullerini ayarla.

        kind ∈ {"none","leaves","dust","snow","embers"}. Ayarlanmasi mevcut
        birikmis partikulleri silmez; gecersiz tur "none" gibi davranir.
        """
        if kind not in ("none", "leaves", "dust", "snow", "embers"):
            kind = "none"
        self.ambient_kind = kind

    def set_slowmo_vignette(self, on: bool):
        """KO slow-mo ani icin ekran kenarlarini koyultan vinyeti ac/kapat."""
        self.vignette = bool(on)

    def _spawn_ambient_particle(self):
        """ambient_kind'a gore ekranin ustunden bir atmosfer partikulu uret."""
        k = self.ambient_kind
        w = settings.WIDTH
        h = settings.HEIGHT
        if k == "leaves":
            self.ambient.append(_AmbientParticle(
                x=random.uniform(0, w), y=random.uniform(-20, -4),
                vx=random.uniform(-0.4, 0.6), vy=random.uniform(0.7, 1.4),
                life=random.randint(240, 380),
                size=random.randint(4, 7),
                color=random.choice([(196, 142, 58), (168, 108, 46),
                                     (142, 158, 62), (120, 90, 40)]),
                sway=random.uniform(0.8, 1.8),
                phase=random.uniform(0, math.tau), shape="leaf"))
        elif k == "dust":
            drift = random.choice((-1, 1)) * random.uniform(0.8, 1.8)
            self.ambient.append(_AmbientParticle(
                x=(-10 if drift > 0 else w + 10),
                y=random.uniform(0, h * 0.85),
                vx=drift, vy=random.uniform(-0.1, 0.25),
                life=random.randint(180, 300),
                size=random.randint(2, 4),
                color=(200, 188, 160),
                sway=random.uniform(0.1, 0.4),
                phase=random.uniform(0, math.tau), shape="dot"))
        elif k == "snow":
            self.ambient.append(_AmbientParticle(
                x=random.uniform(0, w), y=random.uniform(-20, -4),
                vx=random.uniform(-0.3, 0.3), vy=random.uniform(0.9, 1.8),
                life=random.randint(240, 400),
                size=random.randint(2, 4),
                color=(238, 244, 255),
                sway=random.uniform(0.4, 1.0),
                phase=random.uniform(0, math.tau), shape="flake"))
        elif k == "embers":
            self.ambient.append(_AmbientParticle(
                x=random.uniform(0, w), y=random.uniform(h - 4, h + 16),
                vx=random.uniform(-0.5, 0.5), vy=random.uniform(-1.6, -0.8),
                life=random.randint(150, 260),
                size=random.randint(2, 4),
                color=random.choice([(255, 170, 60), (255, 120, 40),
                                     (255, 210, 120)]),
                sway=random.uniform(0.3, 0.9),
                phase=random.uniform(0, math.tau), shape="dot"))

    # ------------------------------------------------------------------
    def update(self):
        for p in self.particles:
            p.update()
        for d in self.numbers:
            d.update()
        for r in self.rings:
            r.update()
        for an in self.anims:
            an.update()
        # ortam partikulleri: birkac karede bir hafifce uret (dusuk yogunluk)
        if self.ambient_kind != "none":
            self._ambient_timer += 1
            # ~her 6 karede bir yeni partikul; ekranda toplam sinirli
            if self._ambient_timer >= 6 and len(self.ambient) < 60:
                self._ambient_timer = 0
                self._spawn_ambient_particle()
            for a in self.ambient:
                a.update()
        self.particles = [p for p in self.particles if p.life > 0]
        self.numbers = [d for d in self.numbers if d.life > 0]
        self.rings = [r for r in self.rings if r.life > 0]
        # biten (loop=False, son kareyi gecmis) anim efektlerini ele
        self.anims = [an for an in self.anims if an.life > 0]
        # ekran disina cikan veya omru biten ambient'leri ele
        self.ambient = [
            a for a in self.ambient
            if a.life > 0
            and -40 <= a.y <= settings.HEIGHT + 40
            and -40 <= a.x <= settings.WIDTH + 40
        ]
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
        """Dunya katmaninda (sarsintiya dahil) cizilen efektler.

        Ortam partikulleri (arka atmosfer) -> kivilcim/toz -> impact halkalari
        -> kare-dizisi anim efektleri (patlama/muzzle) sirasiyla cizilir.
        """
        for a in self.ambient:
            a.draw(surf, ox, oy)
        for p in self.particles:
            p.draw(surf, ox, oy)
        for r in self.rings:
            r.draw(surf, ox, oy)
        for an in self.anims:
            an.draw(surf, ox, oy)

    def draw_overlay(self, surf):
        """HUD ustunde, sarsintisiz cizilen efektler: hasar sayilari + flash."""
        for d in self.numbers:
            d.draw(surf, 0, 0)
        if self.combo is not None:
            self._draw_combo(surf)
        if self.vignette:
            self._draw_vignette(surf)
        if self.flash > 0:
            layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            layer.fill((255, 255, 255, int(150 * self.flash / 8)))
            surf.blit(layer, (0, 0))

    _vignette_cache = None      # (boyut, yuzey) onbellek

    def _draw_vignette(self, surf):
        """Ekran kenarlarina dogru koyulasan yumusak radyal karanlik."""
        size = surf.get_size()
        cache = EffectSystem._vignette_cache
        if cache is None or cache[0] != size:
            w, h = size
            layer = pygame.Surface(size, pygame.SRCALPHA)
            # dusuk cozunurlukte radyal gradyan uret, sonra olcekle (hizli)
            small_w = max(2, w // 8)
            small_h = max(2, h // 8)
            small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
            cx, cy = small_w / 2.0, small_h / 2.0
            max_d = math.hypot(cx, cy)
            for yy in range(small_h):
                for xx in range(small_w):
                    d = math.hypot(xx - cx, yy - cy) / max_d
                    # merkez temiz, kenarlara dogru koyu (ease ile yumusak)
                    a = int(190 * max(0.0, (d - 0.35) / 0.65) ** 1.6)
                    small.set_at((xx, yy), (0, 0, 0, min(190, a)))
            layer = pygame.transform.smoothscale(small, size)
            EffectSystem._vignette_cache = (size, layer)
            cache = EffectSystem._vignette_cache
        surf.blit(cache[1], (0, 0))

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
