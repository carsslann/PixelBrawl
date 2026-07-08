"""Kontrolculer: klavye (insan) ve bot (PvE).

Iki kontrolcu de ayni Inputs yapisini uretir; Fighter icin insan ile
bot arasinda fark yoktur. PvP eklemek = ikinci HumanController'a farkli
tus seti vermek.
"""

import random
from dataclasses import dataclass

import pygame

from .fighter import State


@dataclass
class Inputs:
    move: int = 0        # -1 sol, 0 dur, +1 sag (ekran yonu)
    jump: bool = False
    punch: bool = False
    kick: bool = False
    block: bool = False


class Controller:
    def get_inputs(self, me, opponent, pressed, events) -> Inputs:
        raise NotImplementedError


# ----------------------------------------------------------------------
# Insan
# ----------------------------------------------------------------------
P1_KEYS = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "block": pygame.K_s,
    "punch": pygame.K_j,
    "kick": pygame.K_k,
}


class HumanController(Controller):
    def __init__(self, keys=None):
        self.keys = keys or P1_KEYS

    def get_inputs(self, me, opponent, pressed, events) -> Inputs:
        inp = Inputs()
        inp.move = ((1 if pressed[self.keys["right"]] else 0)
                    - (1 if pressed[self.keys["left"]] else 0))
        inp.block = bool(pressed[self.keys["block"]])
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == self.keys["jump"]:
                    inp.jump = True
                elif e.key == self.keys["punch"]:
                    inp.punch = True
                elif e.key == self.keys["kick"]:
                    inp.kick = True
        return inp


# ----------------------------------------------------------------------
# Bot
# ----------------------------------------------------------------------
DIFFICULTIES = {
    # idle_prob: menzil disindayken bazen yaklasmayip bekleme ihtimali
    # (yuksek = daha pasif, oyuncuya nefes payi = daha kolay)
    "kolay": dict(decision_interval=32, reaction=26, aggression=0.16,
                  block_prob=0.05, jump_prob=0.03, retreat_prob=0.30, idle_prob=0.45),
    "orta": dict(decision_interval=12, reaction=9, aggression=0.55,
                 block_prob=0.40, jump_prob=0.08, retreat_prob=0.15, idle_prob=0.0),
    "zor": dict(decision_interval=7, reaction=4, aggression=0.78,
                block_prob=0.70, jump_prob=0.10, retreat_prob=0.08, idle_prob=0.0),
}
DIFFICULTY_ORDER = ["kolay", "orta", "zor"]
DIFFICULTY_LABELS = {"kolay": "Kolay", "orta": "Orta", "zor": "Zor"}


class AIController(Controller):
    """Kural tabanli bot: mesafeye gore yaklas/saldir/blokla.

    Rakip saldiriya gectiginde block_prob ihtimaliyle, reaction karesi
    gecikmeyle bloga gecer. Kararlar decision_interval karede bir alinir
    ki davranis okunabilir (ve zorluk ayarlanabilir) olsun.
    """

    def __init__(self, difficulty: str = "orta"):
        self.p = DIFFICULTIES[difficulty]
        self.frame = 0
        self.move = 0
        self.want_attack: str | None = None
        self.block_from = -1
        self.block_until = -1
        self.prev_opp_attacking = False

    def get_inputs(self, me, opp, pressed, events) -> Inputs:
        self.frame += 1
        inp = Inputs()
        if me.state == State.KO or opp.state == State.KO:
            return inp

        gap = abs(opp.x - me.x) - (me.data.width + opp.data.width) / 2
        toward = 1 if opp.x >= me.x else -1

        # rakip saldiriya yeni mi gecti? -> blok karari
        opp_attacking = opp.state in (State.PUNCH, State.KICK)
        if opp_attacking and not self.prev_opp_attacking:
            if gap < 150 and opp.attack is not None \
                    and random.random() < self.p["block_prob"]:
                self.block_from = self.frame + self.p["reaction"]
                self.block_until = self.block_from + opp.attack.total + 6
        self.prev_opp_attacking = opp_attacking

        if self.block_from <= self.frame <= self.block_until:
            inp.block = True
            return inp

        # periyodik karar
        if self.frame % self.p["decision_interval"] == 0:
            r = random.random()
            in_punch = gap < me.data.punch.hit_w * 0.9
            in_kick = gap < me.data.kick.hit_w * 0.95
            if in_punch or in_kick:
                if r < self.p["aggression"]:
                    use_punch = in_punch and (not in_kick or random.random() < 0.55)
                    self.want_attack = "punch" if use_punch else "kick"
                    self.move = 0
                elif r < self.p["aggression"] + self.p["retreat_prob"]:
                    self.move = -toward
                else:
                    self.move = 0
            else:
                self.want_attack = None
                if r < self.p["jump_prob"] and me.state != State.JUMP:
                    inp.jump = True
                # bazen yaklasmayip bekle (kolay bot icin nefes payi)
                if random.random() < self.p.get("idle_prob", 0.0):
                    self.move = 0
                else:
                    self.move = toward

        # planlanan saldiriyi ilk uygun anda uygula
        if self.want_attack and gap > 220:
            self.want_attack = None  # rakip kacti, plani birak
        if self.want_attack and me.state in (State.IDLE, State.WALK):
            if self.want_attack == "punch":
                inp.punch = True
            else:
                inp.kick = True
            self.want_attack = None
            self.move = 0

        inp.move = self.move
        return inp
