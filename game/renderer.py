"""Gorsel katman: sahne ve dovuscu cizimi.

Dovuscu cizimi tek kapidan gecer: draw_fighter(). Karakterin sprite'i
yuklenebiliyorsa Kenney poz karesi, aksi halde prosedurel (dikdortgen)
poz cizilir. Oyun mantigi cizimden habersizdir.
"""

import math

import pygame

from . import settings, sprites, stages
from .fighter import State


class Renderer:
    def __init__(self, stage: str = "orman"):
        self._bg: pygame.Surface | None = None
        self._stage = stage
        self._animators: dict = {}

    # ------------------------------------------------------------------
    # sahne
    # ------------------------------------------------------------------
    def draw_stage(self, surf: pygame.Surface):
        # sahne cizimi game/stages.py'ye devredilir (Kenney arka planlari)
        if self._bg is None or self._bg.get_size() != surf.get_size():
            self._bg = stages.build_background(self._stage, surf.get_size())
        surf.blit(self._bg, (0, 0))

    # ------------------------------------------------------------------
    # dovuscu
    # ------------------------------------------------------------------
    def draw_fighter(self, surf: pygame.Surface, f, ox=0, oy=0):
        self._draw_shadow(surf, f, ox, oy)
        animator = self._animator_for(f)
        if animator is not None:
            frame = animator.frame_for(f)
            if frame is not None:
                dy = 0
                if f.state == State.IDLE:
                    dy = int(math.sin(f.state_frame * 0.12) * 2)
                elif (f.state in (State.PUNCH, State.KICK) and f.attack is not None
                      and not f.attack_airborne and f.attack.height_frac < 0.4):
                    dy = int(f.data.height * 0.16)   # alcak/cömel saldiri: sprite'i indir
                rect = frame.get_rect(midbottom=(int(f.x + ox), int(f.y + oy + dy)))
                surf.blit(frame, rect)
                if f.hit_flash:
                    self._flash_sprite(surf, frame, rect)
                if f.blocking:
                    self._draw_guard(surf, f, ox, oy)
                return
        self._draw_procedural(surf, f, ox, oy)

    def _draw_guard(self, surf, f, ox=0, oy=0):
        gx = f.x + ox + f.facing * (f.data.width * 0.5 + 8)
        low = f.state == State.CROUCH
        gy = f.y + oy - f.data.height * (0.34 if low else 0.52)
        rect = pygame.Rect(0, 0, 18, 60)
        rect.center = (int(gx), int(gy))
        shield = pygame.Surface(rect.size, pygame.SRCALPHA)
        a = 200 if f.block_flash else 110
        pygame.draw.ellipse(shield, (150, 200, 255, a), shield.get_rect())
        pygame.draw.ellipse(shield, (210, 235, 255, min(255, a + 90)),
                            shield.get_rect(), 3)
        surf.blit(shield, rect)

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
        crouch = h * 0.30 if f.state == State.CROUCH else 0
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
        elif f.blocking:
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
