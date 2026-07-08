"""Gorsel katman: sahne ve dovuscu cizimi.

Dovuscu cizimi tek kapidan gecer: draw_fighter(). Karakterin sprite'i
yuklenebiliyorsa Kenney poz karesi, aksi halde prosedurel (dikdortgen)
poz cizilir. Oyun mantigi cizimden habersizdir.
"""

import math
import os

import pygame

from . import settings, sprites
from .fighter import State

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Renderer:
    def __init__(self, stage: str = "orman"):
        self._bg: pygame.Surface | None = None
        self._stage = stage
        self._animators: dict = {}

    # ------------------------------------------------------------------
    # sahne
    # ------------------------------------------------------------------
    def draw_stage(self, surf: pygame.Surface):
        if self._bg is None or self._bg.get_size() != surf.get_size():
            self._bg = self._build_background(surf.get_size())
        surf.blit(self._bg, (0, 0))

    def _build_background(self, size) -> pygame.Surface:
        img = self._load_stage_image(size)
        if img is not None:
            return img
        return self._build_procedural_bg(size)

    def _load_stage_image(self, size) -> pygame.Surface | None:
        path = settings.STAGES.get(self._stage)
        if not path:
            return None
        full = os.path.join(ROOT, *path.split("/"))
        if not os.path.isfile(full):
            return None
        try:
            w, h = size
            src = pygame.image.load(full).convert()
            scale = w / src.get_width()
            scaled = pygame.transform.smoothscale(
                src, (w, int(src.get_height() * scale)))
            # cim/toprak ufkunu FLOOR_Y'ye hizala
            offset_y = settings.FLOOR_Y - int(settings.STAGE_HORIZON * scale)
            bg = pygame.Surface(size)
            bg.fill((120, 66, 48))  # olasi alt bosluk icin toprak tonu
            bg.blit(scaled, (0, offset_y))
            # zemin cizgisi + zemine hafif koyulasma (dovuscular one ciksin)
            shade = pygame.Surface((w, h - settings.FLOOR_Y), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 40))
            bg.blit(shade, (0, settings.FLOOR_Y))
            pygame.draw.line(bg, (60, 44, 34), (0, settings.FLOOR_Y),
                             (w, settings.FLOOR_Y), 3)
            return bg
        except Exception as exc:
            print(f"[stage] '{self._stage}' yuklenemedi: {exc}")
            return None

    def _build_procedural_bg(self, size) -> pygame.Surface:
        w, h = size
        bg = pygame.Surface(size)
        # gokyuzu gradyani (aksam: mor -> turuncu)
        top = (44, 34, 66)
        bottom = (196, 118, 92)
        for y in range(settings.FLOOR_Y):
            t = y / settings.FLOOR_Y
            color = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
            pygame.draw.line(bg, color, (0, y), (w, y))
        pygame.draw.circle(bg, (255, 214, 150), (int(w * 0.5), int(settings.FLOOR_Y * 0.72)), 90)
        pygame.draw.circle(bg, (255, 236, 190), (int(w * 0.5), int(settings.FLOOR_Y * 0.72)), 60)
        far = (78, 62, 90)
        near = (54, 44, 72)
        self._silhouette(bg, far, base_y=settings.FLOOR_Y, peaks=7, height=180, seed=1, w=w)
        self._silhouette(bg, near, base_y=settings.FLOOR_Y, peaks=11, height=120, seed=2, w=w)
        floor = pygame.Rect(0, settings.FLOOR_Y, w, h - settings.FLOOR_Y)
        pygame.draw.rect(bg, (46, 40, 40), floor)
        for i in range(1, 7):
            y = settings.FLOOR_Y + i * i * 3
            if y < h:
                shade = max(30, 70 - i * 6)
                pygame.draw.line(bg, (shade, shade - 4, shade - 6), (0, y), (w, y), 2)
        pygame.draw.line(bg, (150, 130, 110), (0, settings.FLOOR_Y),
                         (w, settings.FLOOR_Y), 4)
        return bg

    @staticmethod
    def _silhouette(surf, color, base_y, peaks, height, seed, w):
        # deterministik zikzak silue (rastgelesiz, tekrarlanabilir)
        pts = [(0, base_y)]
        for i in range(peaks + 1):
            x = int(w * i / peaks)
            wob = ((i * 928371 + seed * 15731) % 100) / 100.0
            y = base_y - int(height * (0.45 + 0.55 * wob))
            pts.append((x, y))
        pts.append((w, base_y))
        pygame.draw.polygon(surf, color, pts)

    # ------------------------------------------------------------------
    # dovuscu
    # ------------------------------------------------------------------
    def draw_fighter(self, surf: pygame.Surface, f, ox=0, oy=0):
        self._draw_shadow(surf, f, ox, oy)
        animator = self._animator_for(f)
        if animator is not None:
            frame = animator.frame_for(f)
            if frame is not None:
                bob = int(math.sin(f.state_frame * 0.12) * 2) if f.state == State.IDLE else 0
                rect = frame.get_rect(midbottom=(int(f.x + ox), int(f.y + oy + bob)))
                surf.blit(frame, rect)
                if f.hit_flash:
                    self._flash_sprite(surf, frame, rect)
                return
        self._draw_procedural(surf, f, ox, oy)

    def _animator_for(self, f):
        key = f.data.key
        if key not in self._animators:
            self._animators[key] = sprites.load_animator(f.data)
        return self._animators[key]

    @staticmethod
    def _flash_sprite(surf, frame, rect):
        tint = frame.copy()
        tint.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
        white = frame.copy()
        white.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_ADD)
        white.set_alpha(150)
        surf.blit(white, rect)

    def _draw_shadow(self, surf, f, ox=0, oy=0):
        height_above = settings.FLOOR_Y - f.y
        spread = max(0.45, 1.0 - height_above / 400.0)
        w = int(f.data.width * 1.7 * spread)
        rect = pygame.Rect(0, 0, w, 16)
        rect.center = (int(f.x + ox), settings.FLOOR_Y + 8 + int(oy))
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, settings.SHADOW_COLOR, shadow.get_rect())
        surf.blit(shadow, rect)

    def _draw_procedural(self, surf, f, ox=0, oy=0):
        w, h = f.data.width, f.data.height
        color = f.data.color
        dark = tuple(max(0, c - 55) for c in color)
        x, y = f.x + ox, f.y + oy
        fc = f.facing

        if f.state == State.KO:
            body = pygame.Rect(0, 0, int(h * 0.72), int(w * 0.62))
            body.midbottom = (int(x), int(y))
            pygame.draw.rect(surf, dark, body, border_radius=10)
            head_x = body.centerx - fc * body.width // 2
            pygame.draw.circle(surf, settings.SKIN, (head_x, body.centery), int(w * 0.30))
            return

        bob = math.sin(f.state_frame * 0.28) * 3 if f.state == State.WALK else 0
        crouch = h * 0.07 if f.state == State.BLOCK else 0
        tuck = h * 0.16 if f.state == State.JUMP else 0
        lean = -fc * 7 if f.state == State.HITSTUN else 0
        eff_h = h - crouch - tuck

        legs = pygame.Rect(0, 0, int(w * 0.52), int(eff_h * 0.42))
        legs.midbottom = (int(x), int(y))
        torso = pygame.Rect(0, 0, int(w * 0.78), int(eff_h * 0.40))
        torso.midbottom = (int(x + lean + bob * 0.3), legs.top + 4)
        head_c = (int(x + lean * 1.4), int(torso.top - w * 0.24 + bob))

        pygame.draw.rect(surf, dark, legs, border_radius=6)
        pygame.draw.rect(surf, color, torso, border_radius=8)
        pygame.draw.circle(surf, settings.SKIN, head_c, int(w * 0.27))
        eye = (head_c[0] + fc * int(w * 0.12), head_c[1] - 3)
        pygame.draw.circle(surf, settings.BLACK, eye, 3)

        if f.state in (State.PUNCH, State.KICK) and f.attack is not None:
            a = f.attack
            progress = f.state_frame
            arm_y = int(y - h * a.height_frac)
            front = x + fc * (w / 2)
            if progress < a.startup:
                ext = int(a.hit_w * 0.25)
            elif progress < a.startup + a.active:
                ext = a.hit_w
            else:
                ext = int(a.hit_w * 0.45)
            thick = a.hit_h - 6 if f.state == State.PUNCH else a.hit_h
            limb = pygame.Rect(0, 0, ext, max(10, thick))
            if fc > 0:
                limb.midleft = (int(front - 4), arm_y)
            else:
                limb.midright = (int(front + 4), arm_y)
            limb_color = settings.SKIN if f.state == State.PUNCH else dark
            pygame.draw.rect(surf, limb_color, limb, border_radius=6)
        elif f.state == State.BLOCK:
            guard = pygame.Rect(0, 0, 14, int(eff_h * 0.42))
            gx = x + fc * (w / 2 + 8)
            guard.center = (int(gx), int(y - eff_h * 0.55))
            pygame.draw.rect(surf, settings.SKIN, guard, border_radius=5)
            if f.block_flash:
                pygame.draw.rect(surf, settings.WHITE, guard.inflate(8, 8), 2,
                                 border_radius=7)
        else:
            for side in (-1, 1):
                arm = pygame.Rect(0, 0, 12, int(eff_h * 0.30))
                arm.midtop = (torso.centerx + side * (torso.width // 2 - 2), torso.top + 6)
                pygame.draw.rect(surf, settings.SKIN, arm, border_radius=5)

        if f.hit_flash:
            box = f.hurtbox().move(ox, oy)
            flash = pygame.Surface(box.size, pygame.SRCALPHA)
            flash.fill((255, 255, 255, 120))
            surf.blit(flash, box)
