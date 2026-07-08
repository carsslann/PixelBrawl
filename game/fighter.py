"""Dovuscu durum makinesi ve fizigi.

Cizimden tamamen bagimsizdir: Fighter yalnizca konum/durum/kare sayaci
tutar, gorsel katman (renderer/sprites) bu durumu okuyarak cizer.
Saldirilar startup -> active -> recovery kare pencereleriyle isler;
vurus kutusu yalnizca active penceresinde vardir.
"""

from enum import Enum, auto

import pygame

from . import settings
from .characters import AttackData, CharacterData


class State(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    PUNCH = auto()
    KICK = auto()
    BLOCK = auto()
    HITSTUN = auto()
    KO = auto()


# Yeni eylem baslatilabilen durumlar
NEUTRAL_STATES = (State.IDLE, State.WALK)
ATTACK_STATES = (State.PUNCH, State.KICK)


class Fighter:
    def __init__(self, data: CharacterData, x: float, facing: int):
        self.data = data
        self.reset(x, facing)

    def reset(self, x: float, facing: int):
        self.x = float(x)
        self.y = float(settings.FLOOR_Y)  # y = ayaklarin bastigi nokta
        self.vx = 0.0
        self.vy = 0.0
        self.facing = facing              # 1 = saga bakiyor, -1 = sola
        self.health = self.data.max_health
        self.state = State.IDLE
        self.state_frame = 0
        self.attack: AttackData | None = None
        self.attack_has_hit = False
        self.hitstun_left = 0
        self.on_ground = True
        # yalnizca gorsel katmanin kullandigi sayaclar/olaylar
        self.hit_flash = 0
        self.block_flash = 0
        self.just_jumped = False   # bu karede yerden ayrildi (toz efekti)
        self.just_landed = False   # bu karede yere basti (toz efekti)

    # ------------------------------------------------------------------
    # sorgular
    # ------------------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.health > 0

    def hurtbox(self) -> pygame.Rect:
        w, h = self.data.width, self.data.height
        if self.state == State.JUMP:
            h = int(h * 0.85)  # havada toplanmis govde
        return pygame.Rect(int(self.x - w / 2), int(self.y - h), w, h)

    def active_hitbox(self) -> pygame.Rect | None:
        """Su an isabet edebilen vurus kutusu (yoksa None)."""
        if self.state not in ATTACK_STATES or self.attack is None:
            return None
        a = self.attack
        if not (a.startup <= self.state_frame < a.startup + a.active):
            return None
        cx = self.x + self.facing * (self.data.width / 2 + a.hit_w / 2)
        cy = self.y - self.data.height * a.height_frac
        return pygame.Rect(int(cx - a.hit_w / 2), int(cy - a.hit_h / 2),
                           a.hit_w, a.hit_h)

    # ------------------------------------------------------------------
    # durum degisimleri
    # ------------------------------------------------------------------
    def set_state(self, state: State):
        self.state = state
        self.state_frame = 0

    def take_hit(self, attack: AttackData, attacker_facing: int):
        """Rakibin saldirisi isabet etti (combat.resolve_hits cagirir)."""
        if self.state == State.BLOCK:
            chip = max(1, round(attack.damage * settings.CHIP_DAMAGE_RATIO))
            self.health = max(0, self.health - chip)
            self.vx = attacker_facing * attack.knockback * settings.BLOCK_PUSHBACK_RATIO
            self.block_flash = 8
        else:
            self.health = max(0, self.health - attack.damage)
            self.vx = attacker_facing * attack.knockback
            self.hitstun_left = attack.hitstun
            self.hit_flash = 6
            self.attack = None
            self.set_state(State.HITSTUN)
        if self.health <= 0:
            self.attack = None
            self.set_state(State.KO)
            self.vx = attacker_facing * attack.knockback * 1.4
            if self.on_ground:
                self.vy = -6.0   # nakavtta hafif savrulma
                self.on_ground = False

    def _start_attack(self, state: State, attack: AttackData):
        self.attack = attack
        self.attack_has_hit = False
        self.vx = 0.0
        self.set_state(state)

    # ------------------------------------------------------------------
    # ana guncelleme (karede bir)
    # ------------------------------------------------------------------
    def update(self, inputs, opponent: "Fighter"):
        self.state_frame += 1
        self.just_jumped = False
        self.just_landed = False
        if self.hit_flash:
            self.hit_flash -= 1
        if self.block_flash:
            self.block_flash -= 1

        if self.state == State.KO:
            self._physics()
            return

        # yon: yalnizca notr durumda rakibe donulur (SF kurali)
        if self.state in NEUTRAL_STATES and self.on_ground:
            self.facing = 1 if opponent.x >= self.x else -1

        if self.state == State.HITSTUN:
            self.hitstun_left -= 1
            if self.hitstun_left <= 0 and self.on_ground:
                self.set_state(State.IDLE)
            self._physics()
            return

        if self.state in ATTACK_STATES:
            self.vx = 0.0
            if self.attack is None or self.state_frame >= self.attack.total:
                self.attack = None
                self.set_state(State.IDLE)
            self._physics()
            return

        if self.state == State.JUMP:
            # havada yon/eylem degistirilemez
            self._physics()
            if self.on_ground:
                self.set_state(State.IDLE)
            return

        if self.state == State.BLOCK:
            self.vx = 0.0
            if not inputs.block:
                self.set_state(State.IDLE)
            self._physics()
            return

        # ---- notr (IDLE / WALK): yeni eylemler ----
        if inputs.punch:
            self._start_attack(State.PUNCH, self.data.punch)
        elif inputs.kick:
            self._start_attack(State.KICK, self.data.kick)
        elif inputs.block:
            self.vx = 0.0
            self.set_state(State.BLOCK)
        elif inputs.jump:
            self.set_state(State.JUMP)
            self.on_ground = False
            self.just_jumped = True
            self.vy = self.data.jump_vy
            self.vx = inputs.move * self.data.jump_vx
        else:
            self.vx = inputs.move * self.data.walk_speed
            wanted = State.WALK if inputs.move else State.IDLE
            if wanted != self.state:
                self.set_state(wanted)
        self._physics()

    def _physics(self):
        self.x += self.vx
        if not self.on_ground:
            self.vy += settings.GRAVITY
            self.y += self.vy
            if self.y >= settings.FLOOR_Y:
                self.y = float(settings.FLOOR_Y)
                self.vy = 0.0
                self.on_ground = True
                self.just_landed = True
        else:
            # yerde: itilme (knockback) hizlari surtunmeyle soner
            if self.state in (State.HITSTUN, State.KO, State.BLOCK):
                self.vx *= settings.GROUND_FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0
        half = self.data.width / 2
        self.x = max(settings.STAGE_MARGIN + half,
                     min(settings.WIDTH - settings.STAGE_MARGIN - half, self.x))
