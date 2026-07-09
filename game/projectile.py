"""Mermi (projectile) altyapisi: ucan ates topu vb.

Projectile cizim + basit hareket/omur mantigini tasir; carpisma cozumu
(hasar uygulama, isabet olayi) cagiran tarafta (or. match.py) yapilir:
her kare update(), sonra hitbox() ile hedef hitbox'lari kesistir, isabet
olursa on_hit()/register_hit() cagirilir.

Tasarim notlari:
  * `owner` OPAK tutulur (Fighter import EDILMEZ) — mermi bagimsiz kalir.
    Cagiran, kendi mermisinin sahibine vurmamasi icin `proj.owner is fighter`
    karsilastirmasi yapar.
  * Ekran sinirlari icin settings.WIDTH kullanilir.
  * `frames` disaridan verilir (fx_sprites'a zorunlu bagimlilik yok). Kolaylik
    icin bu modul fx_sprites'i (opsiyonel) import edip make_fireball() fabrika
    yardimcisi sunar; fx_sprites yoksa yine calisir (frames bos olur).
"""

import pygame

from . import settings

try:  # opsiyonel: sadece make_fireball fabrika yardimcisi icin
    from . import fx_sprites
except Exception:  # fx_sprites yoksa/bozuksa mermi yine calisir
    fx_sprites = None


# ekrandan bu kadar disari cikinca mermi olur (kuyruk tamamen ciksin diye)
_OFFSCREEN_MARGIN = 80


class Projectile:
    """Yatay ucan animasyonlu mermi.

    Kareler SAGA bakacak sekilde verilir; facing<0 ise cizerken flip edilir.
    """

    def __init__(self, x, y, vx, facing, frames, damage, owner,
                 hit_w=44, hit_h=34, lifetime=150, fps=14, hits_once=True):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        # yon: +1 saga, -1 sola. Verilmezse vx isaretinden turet.
        self.facing = 1 if facing >= 0 else -1
        self.frames = list(frames) if frames else []
        self.damage = damage
        self.owner = owner                 # opak sahip kimligi

        self.hit_w = hit_w
        self.hit_h = hit_h
        self.lifetime = int(lifetime)
        self.fps = max(1, int(fps))
        self.hits_once = bool(hits_once)

        self.age = 0                       # gecen kare sayisi
        self._anim = 0.0                   # animasyon ilerlemesi (kare cinsinden)
        self.frame_index = 0
        self.alive = True
        self.has_hit = False

        # sola giden ama facing verilmemis durum icin vx'e gore hizala
        if facing == 0 and self.vx < 0:
            self.facing = -1

    # ------------------------------------------------------------------ update
    def update(self):
        """Bir kare ilerlet: konum, animasyon, omur ve olum kosullari."""
        if not self.alive:
            return
        self.x += self.vx
        self.age += 1

        # animasyon karesini ilerlet (fps, oyunun FPS'ine gore)
        if self.frames:
            self._anim += self.fps / float(settings.FPS)
            self.frame_index = int(self._anim) % len(self.frames)

        # omur bitti mi?
        if self.age >= self.lifetime:
            self.alive = False
            return

        # tek-vurus ve isabet olduysa artik yasamaz
        if self.hits_once and self.has_hit:
            self.alive = False
            return

        # ekran disina cikti mi? (WIDTH sinirlari + pay)
        half = self.hit_w / 2.0
        if (self.x + half < -_OFFSCREEN_MARGIN or
                self.x - half > settings.WIDTH + _OFFSCREEN_MARGIN):
            self.alive = False

    # ---------------------------------------------------------------- collision
    def hitbox(self) -> pygame.Rect:
        """Merkezi (x, y) olan hit_w x hit_h dikdortgen."""
        return pygame.Rect(int(self.x - self.hit_w / 2),
                           int(self.y - self.hit_h / 2),
                           int(self.hit_w), int(self.hit_h))

    def register_hit(self) -> None:
        """Cagiran, isabeti onayladiginda cagirir (hits_once ise mermi biter)."""
        self.has_hit = True
        if self.hits_once:
            self.alive = False

    # ---------------------------------------------------------------- rendering
    def current_frame(self) -> "pygame.Surface | None":
        if not self.frames:
            return None
        idx = max(0, min(len(self.frames) - 1, self.frame_index))
        return self.frames[idx]

    def draw(self, surf, ox=0, oy=0):
        """Anlik kareyi (x, y) merkezine cizer; facing<0 ise yatay flipli.

        ox/oy dunya->ekran kaydirmasi (kamera) icin eklenir.
        """
        img = self.current_frame()
        cx = int(self.x + ox)
        cy = int(self.y + oy)
        if img is None:
            # kare yok (fallback bile uretilemedi): kucuk daire ciz, gorunur kalsin
            r = max(3, int(self.hit_h / 3))
            pygame.draw.circle(surf, (255, 210, 90), (cx, cy), r)
            pygame.draw.circle(surf, (255, 255, 240), (cx, cy), max(1, r // 2))
            return
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        rect = img.get_rect(center=(cx, cy))
        surf.blit(img, rect)


# --------------------------------------------------------------------- fabrika
def make_fireball(x, y, facing, color, damage, owner,
                  speed=12.0, scale=3.0, **kwargs) -> Projectile:
    """Kolaylik fabrikasi: fx_sprites'tan ates topu kareleriyle Projectile kurar.

    facing: +1 saga, -1 sola (hiz ve karelerin yonu buna gore ayarlanir).
    color : renk indexi 0..7 (fx_sprites.COLOR_COUNT).
    fx_sprites yoksa frames bos gelir; Projectile yine calisir (daire fallback).
    kwargs Projectile'e gecirilir (hit_w, hit_h, lifetime, fps, hits_once...).
    """
    facing = 1 if facing >= 0 else -1
    frames = []
    if fx_sprites is not None:
        try:
            frames = fx_sprites.fireball_frames(color, scale)
        except Exception:
            frames = []
    vx = abs(speed) * facing
    return Projectile(x, y, vx, facing, frames, damage, owner, **kwargs)
