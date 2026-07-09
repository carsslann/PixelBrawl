"""Dovuscu durum makinesi ve fizigi.

Cizimden tamamen bagimsizdir. Saldirilar startup -> active -> recovery
kare pencereleriyle isler; vurus kutusu yalnizca active penceresinde vardir.

Hareket seti:
- Ayakta yumruk/tekme (yuksek)
- Cömel (aSagi) + yumruk = alcak yumruk; cömel + tekme = supurme (alcak, yere serer)
- Havada yumruk/tekme (overhead)
- Blok: rakibe göre GERI yönü tutmak (ya da bot icin inputs.block). Ayakta blok
  overhead+yuksegi keser, alcagi kesmez; cömel-blok yuksek+alcagi keser, overhead'i kesmez.
- Zincir kombo: bir saldiri İSABET ederse toparlanmasi daha yuksek kademeli
  bir saldiriya iptal edilebilir (yumruk -> tekme/supurme).
"""

import dataclasses
from enum import Enum, auto

import pygame

from . import settings
from .characters import AttackData, CharacterData


class State(Enum):
    IDLE = auto()
    WALK = auto()
    CROUCH = auto()
    JUMP = auto()
    PUNCH = auto()
    KICK = auto()
    WEAPON = auto()    # ozel silah (yakin vurus) hareketi
    SPECIAL = auto()   # ozel ates (mermi) hareketi
    THROW = auto()     # atma/tutma
    BLOCK = auto()
    HITSTUN = auto()
    KO = auto()


NEUTRAL_STATES = (State.IDLE, State.WALK, State.CROUCH, State.BLOCK)
ATTACK_STATES = (State.PUNCH, State.KICK, State.WEAPON)  # active_hitbox olanlar


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


class Fighter:
    def __init__(self, data: CharacterData, x: float, facing: int):
        self.data = data
        self.weapon_key = None     # kusanilmis silah (match atar); tum vuruslari olcekler
        self.reset(x, facing)

    def equip(self, weapon_key):
        self.weapon_key = weapon_key
        self._build_attacks()

    def _weapon_mult(self):
        if not self.weapon_key:
            return None
        try:
            from . import weapons
            return weapons.WEAPONS.get(self.weapon_key)
        except Exception:
            return None

    @staticmethod
    def _scale(atk, w):
        if w is None:
            return atk
        return dataclasses.replace(
            atk,
            damage=max(1, round(atk.damage * w.damage_mult)),
            hit_w=max(8, round(atk.hit_w * w.reach_mult)),
            knockback=atk.knockback * w.knockback_mult,
            startup=max(1, round(atk.startup / w.speed_mult)),
            recovery=max(1, round(atk.recovery / w.speed_mult)))

    def _build_attacks(self):
        """Kusanilmis silaha gore TUM saldirilarin olceklenmis surumleri."""
        d = self.data
        w = self._weapon_mult()
        self.mv = {
            "punch": self._scale(d.punch, w),
            "kick": self._scale(d.kick, w),
            "crouch_punch": self._scale(d.crouch_punch, w),
            "sweep": self._scale(d.sweep, w),
            "jump_punch": self._scale(d.jump_punch, w),
            "jump_kick": self._scale(d.jump_kick, w),
        }
        self.weapon_attack = self._scale(d.weapon.attack, w) if d.weapon else None

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
        self.attack_airborne = False
        self.hitstun_left = 0
        self.on_ground = True
        self.blocking = False
        self.knocked_down = False
        self.victory = False    # mac sonu kazanan sevinme pozu
        self.combo_count = 0    # bu dovuscunun SALDIRAN olarak surdurdugu kombo
        self.meter = settings.SUPER_START   # super metre (round basi dolu baslar)
        self._special = None    # su an yapilan SpecialSpec (SPECIAL durumu)
        self._special_ex = False   # metre doluyken guclendirilmis (EX) ates
        self.spawn_special = None  # mermi cikis sinyali; match okuyup temizler
        self.wants_throw = False   # bu karede atma denemesi (match cozer)
        # yalnizca gorsel katmanin kullandigi sayaclar/olaylar
        self.hit_flash = 0
        self.block_flash = 0
        self.just_jumped = False
        self.just_landed = False
        self._build_attacks()      # kusanilmis silaha gore olceklenmis saldirilar

    # ------------------------------------------------------------------
    # sorgular
    # ------------------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.health > 0

    def hurtbox(self) -> pygame.Rect:
        w, h = self.data.width, self.data.height
        if self.state == State.CROUCH:
            h = int(h * 0.64)   # cömelince alcalir (bazi yuksek vuruslar kacar)
        elif self.state == State.JUMP:
            h = int(h * 0.85)
        return pygame.Rect(int(self.x - w / 2), int(self.y - h), w, h)

    def active_hitbox(self) -> pygame.Rect | None:
        if self.state not in ATTACK_STATES or self.attack is None:
            return None
        a = self.attack
        if a.airborne:
            # hava saldirisi: startup'tan sonra inis boyunca aktif kalir
            # (jump-in); tek isabet attack_has_hit ile saglanir
            if self.state_frame < a.startup:
                return None
        elif not (a.startup <= self.state_frame < a.startup + a.active):
            return None
        cx = self.x + self.facing * (self.data.width / 2 + a.hit_w / 2)
        cy = self.y - self.data.height * a.height_frac
        return pygame.Rect(int(cx - a.hit_w / 2), int(cy - a.hit_h / 2),
                           a.hit_w, a.hit_h)

    def block_stance(self) -> str | None:
        """Blok duruSu: 'stand', 'crouch' ya da None (bloklamiyor)."""
        if not self.blocking:
            return None
        if self.state == State.CROUCH:
            return "crouch"
        if self.state == State.BLOCK:
            return "stand"
        return None

    # ------------------------------------------------------------------
    # durum degisimleri
    # ------------------------------------------------------------------
    def set_state(self, state: State):
        if state != self.state:
            self.state = state
            self.state_frame = 0

    def take_hit(self, attack: AttackData, attacker_facing: int,
                 blocked: bool, damage: int):
        """combat.resolve_hits cagirir. blocked ve damage disaridan verilir
        (yuksek/alcak blok cozumu ve kombo olcekleme combat'ta yapilir)."""
        if blocked:
            self.health = max(0, self.health - max(1, damage))
            self.vx = attacker_facing * attack.knockback * settings.BLOCK_PUSHBACK_RATIO
            self.block_flash = 8
            return
        self.health = max(0, self.health - damage)
        self.vx = attacker_facing * attack.knockback
        self.hit_flash = 6
        self.attack = None
        self.attack_airborne = False
        self._special = None       # ozel hareket kesintiye ugradi
        self.spawn_special = None
        self.wants_throw = False
        self.blocking = False
        if self.health <= 0:
            self.set_state(State.KO)
            self.vx = attacker_facing * attack.knockback * 1.4
            if self.on_ground:
                self.vy = -6.0
                self.on_ground = False
            return
        self.knocked_down = attack.knockdown
        self.hitstun_left = int(attack.hitstun * (1.7 if attack.knockdown else 1.0))
        if attack.knockdown and self.on_ground:
            self.vy = -5.5     # supurmede hafif havalanma
            self.on_ground = False
        self.set_state(State.HITSTUN)

    def _start_attack(self, state: State, attack: AttackData, airborne: bool):
        self.attack = attack
        self.attack_has_hit = False
        self.attack_airborne = airborne
        self.blocking = False
        if not airborne:
            self.vx = 0.0
        self.set_state(state)

    def _start_special(self):
        spec = self.data.special
        if self.meter >= settings.SUPER_MAX:     # metre dolu -> EX (guclu) ates
            self._special_ex = True
            self.meter = 0
        else:
            self._special_ex = False
            self.meter = max(0, self.meter - spec.meter_cost)
        self._special = spec
        self.spawn_special = None
        self.attack = None
        self.vx = 0.0
        self.set_state(State.SPECIAL)

    def _start_weapon(self):
        w = self.data.weapon
        self.meter = max(0, self.meter - w.meter_cost)
        self.attack = self.weapon_attack or w.attack   # kusanilmis silah stat'lari
        self.attack_has_hit = False
        self.blocking = False
        if w.anti_air:                # yukselen vurus (anti-air)
            self.attack_airborne = True
            self.on_ground = False
            self.vy = -12.0
            self.vx = self.facing * w.lunge * 0.4
        else:
            self.attack_airborne = False
            self.vx = self.facing * w.lunge   # ileri atilma
        self.set_state(State.WEAPON)

    def _update_special(self):
        self.vx = 0.0
        spec = self._special
        if spec is None or self.state_frame >= spec.total:
            self._special = None
            self.set_state(State.IDLE)
        elif self.state_frame == spec.cast:
            self.spawn_special = spec   # match bu sinyalle mermiyi olusturur
        self._physics()

    # ------------------------------------------------------------------
    # ana guncelleme (karede bir)
    # ------------------------------------------------------------------
    def update(self, inputs, opponent: "Fighter"):
        self.state_frame += 1
        self.just_jumped = False
        self.just_landed = False
        self.blocking = False
        if self.hit_flash:
            self.hit_flash -= 1
        if self.block_flash:
            self.block_flash -= 1

        if self.state == State.KO:
            self._physics()
            return

        if self.state in NEUTRAL_STATES and self.on_ground:
            self.facing = 1 if opponent.x >= self.x else -1

        if self.state == State.HITSTUN:
            self.hitstun_left -= 1
            if self.hitstun_left <= 0 and self.on_ground:
                self.knocked_down = False
                self.set_state(State.IDLE)
            self._physics()
            return

        if self.state in ATTACK_STATES:
            self._update_attack(inputs)
            return

        if self.state == State.SPECIAL:
            self._update_special()
            return

        if self.state == State.THROW:   # atma denemesi/animasyonu (match cozer)
            self.vx = 0.0
            if self.state_frame >= 18:
                self.set_state(State.IDLE)
            self._physics()
            return

        if self.state == State.JUMP:
            # havada tek bir saldiri hakki
            if not self.attack_airborne and (inputs.punch or inputs.kick):
                atk = self.mv["jump_kick"] if inputs.kick and not inputs.punch \
                    else self.mv["jump_punch"]
                st = State.KICK if (inputs.kick and not inputs.punch) else State.PUNCH
                self._start_attack(st, atk, airborne=True)
                self._update_attack(inputs)
                return
            self._physics()
            if self.on_ground:
                self.set_state(State.IDLE)
            return

        # ---- notr (yerde): yeni eylemler ----
        holding_back = inputs.move != 0 and _sign(inputs.move) == -self.facing
        block_req = bool(inputs.block) or holding_back

        if inputs.throw and self.on_ground:
            self.wants_throw = True         # match yakinsa atmayi cozer
            self.vx = 0.0
            self.set_state(State.THROW)
        elif (inputs.special and self.data.special is not None
                and self.meter >= self.data.special.meter_cost):
            self._start_special()
        elif (inputs.weapon and self.data.weapon is not None
                and self.meter >= self.data.weapon.meter_cost):
            self._start_weapon()          # ↓←+K: silah ozel hareketi (metre)
        elif inputs.punch or inputs.special:   # ozel niyeti + metre yok -> yumruk
            atk = self.mv["crouch_punch"] if inputs.down else self.mv["punch"]
            self._start_attack(State.PUNCH, atk, airborne=False)
        elif inputs.kick or inputs.weapon:     # silah niyeti + metre yok -> tekme
            atk = self.mv["sweep"] if inputs.down else self.mv["kick"]
            self._start_attack(State.KICK, atk, airborne=False)
        elif inputs.jump and not inputs.down:
            self.set_state(State.JUMP)
            self.on_ground = False
            self.just_jumped = True
            self.vy = self.data.jump_vy
            self.vx = inputs.move * self.data.jump_vx
        elif inputs.down:
            self.blocking = block_req      # cömel-blok (geri de tutuluyorsa)
            self.vx = 0.0
            self.set_state(State.CROUCH)
        elif block_req:
            self.blocking = True
            self.vx = inputs.move * self.data.walk_speed  # blokta geri yürüyebilir
            self.set_state(State.BLOCK)
        else:
            self.vx = inputs.move * self.data.walk_speed
            self.set_state(State.WALK if inputs.move else State.IDLE)
        self._physics()

    def _update_attack(self, inputs):
        # zincir iptali: saldiri isabet ettiyse daha yuksek kademeye gec
        if self.attack_has_hit and not self.attack_airborne:
            nxt = self._cancel_target(inputs)
            if nxt is not None:
                state, atk = nxt
                self._start_attack(state, atk, airborne=False)
                self._physics()
                return

        if self.attack_airborne:
            self._physics()
            if self.on_ground:      # yere basinca hava saldirisi biter
                self.attack = None
                self.attack_airborne = False
                self.set_state(State.IDLE)
            return

        if self.state == State.WEAPON:
            self.vx *= 0.85         # silah atilma momentumu sonumlensin
            if abs(self.vx) < 0.2:
                self.vx = 0.0
        else:
            self.vx = 0.0
        if self.attack is None or self.state_frame >= self.attack.total:
            self.attack = None
            self.set_state(State.IDLE)
        self._physics()

    def _cancel_target(self, inputs):
        """İsabet sonrasi izin verilen zincir hedefi (daha yuksek kademe)."""
        cur = self.attack.chain if self.attack else 0
        if inputs.kick:
            atk = self.mv["sweep"] if inputs.down else self.mv["kick"]
            if atk.chain > cur:
                return State.KICK, atk
        if inputs.punch:
            atk = self.mv["crouch_punch"] if inputs.down else self.mv["punch"]
            if atk.chain > cur:
                return State.PUNCH, atk
        return None

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
            if self.state in (State.HITSTUN, State.KO, State.BLOCK):
                self.vx *= settings.GROUND_FRICTION
                if abs(self.vx) < 0.1:
                    self.vx = 0.0
        half = self.data.width / 2
        self.x = max(settings.STAGE_MARGIN + half,
                     min(settings.WIDTH - settings.STAGE_MARGIN - half, self.x))
