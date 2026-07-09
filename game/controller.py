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
    down: bool = False   # comelme (insan: S)
    block: bool = False  # dogrudan blok (bot kullanir; insan GERI tutarak bloklar)
    special: bool = False  # ozel ates (insan: ↓ → + yumruk; bot: ara sira)
    weapon: bool = False   # ozel silah (insan: ↓ ← + tekme)
    throw: bool = False    # atma/tutma (insan: yumruk + tekme ayni anda)


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
    "down": pygame.K_s,
    "punch": pygame.K_j,
    "kick": pygame.K_k,
}


class HumanController(Controller):
    # ozel ates komutu: ↓ sonra ILERI (rakibe dogru), ardindan yumruk —
    # basitleStirilmis quarter-circle-forward. Girdi tamponu son kareleri tutar.
    QCF_DOWN_WINDOW = 18   # ↓ tuSundan yumruga izin verilen azami kare
    QCF_FWD_WINDOW = 12    # ILERI'den yumruga izin verilen azami kare

    def __init__(self, keys=None):
        self.keys = keys or P1_KEYS
        self.frame = 0
        self.t_down = -999   # son ↓ karesi
        self.t_fwd = -999    # son ILERI karesi
        self.t_back = -999   # son GERI karesi

    def get_inputs(self, me, opponent, pressed, events) -> Inputs:
        inp = Inputs()
        self.frame += 1
        inp.move = ((1 if pressed[self.keys["right"]] else 0)
                    - (1 if pressed[self.keys["left"]] else 0))
        inp.down = bool(pressed[self.keys["down"]])
        # yon tamponu: ↓, ILERI ve GERI basimlarini zaman damgala
        fwd = 1 if opponent.x >= me.x else -1
        if inp.down:
            self.t_down = self.frame
        if inp.move == fwd:
            self.t_fwd = self.frame
        elif inp.move == -fwd:
            self.t_back = self.frame
        # bu karedeki yumruk/tekme basimlari
        punch_down = kick_down = False
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == self.keys["jump"]:
                    inp.jump = True
                elif e.key == self.keys["punch"]:
                    punch_down = True
                elif e.key == self.keys["kick"]:
                    kick_down = True
        if punch_down and kick_down:        # ayni kare J+K = atma
            inp.throw = True
        else:
            if punch_down:
                if self._qcf():             # ↓→+J = ozel ates
                    inp.special = True
                    self.t_down = self.t_fwd = -999
                else:
                    inp.punch = True
            if kick_down:
                if self._qcb():             # ↓←+K = ozel silah
                    inp.weapon = True
                    self.t_down = self.t_back = -999
                else:
                    inp.kick = True
        return inp

    def _qcf(self) -> bool:
        return (self.t_down < self.t_fwd
                and self.frame - self.t_down <= self.QCF_DOWN_WINDOW
                and self.frame - self.t_fwd <= self.QCF_FWD_WINDOW)

    def _qcb(self) -> bool:
        return (self.t_down < self.t_back
                and self.frame - self.t_down <= self.QCF_DOWN_WINDOW
                and self.frame - self.t_back <= self.QCF_FWD_WINDOW)


# ----------------------------------------------------------------------
# Bot
# ----------------------------------------------------------------------
DIFFICULTIES = {
    # idle_prob: menzil disindayken bazen yaklasmayip bekleme ihtimali
    # (yuksek = daha pasif, oyuncuya nefes payi = daha kolay).
    # reaction: bloga gecme gecikmesi (kare). Saldiri startup'indan BUYUK
    # olmali; kucukse blok vurus kutusu aktiflesmeden kalkar ve garanti
    # (insanustu) negatiflenir. Denge olcumle dogrulandi: oyuncu kazanma
    # kolay ~99% > orta ~44% > zor ~27% (monotonik, adil).
    "kolay": dict(decision_interval=32, reaction=26, aggression=0.16,
                  block_prob=0.05, jump_prob=0.03, retreat_prob=0.30, idle_prob=0.45),
    "orta": dict(decision_interval=16, reaction=18, aggression=0.42,
                 block_prob=0.28, jump_prob=0.07, retreat_prob=0.16, idle_prob=0.05),
    "zor": dict(decision_interval=14, reaction=12, aggression=0.55,
                block_prob=0.48, jump_prob=0.10, retreat_prob=0.10, idle_prob=0.0),
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

        # metre doluysa ara sira ozel ates (uzak-orta mesafe, bloklanabilir)
        if (me.data.special is not None and me.meter >= me.data.special.meter_cost
                and me.state in (State.IDLE, State.WALK)
                and 120 < gap < 520 and random.random() < 0.03):
            inp.special = True
            return inp
        # metre doluysa yakinken ara sira ozel silah
        if (me.data.weapon is not None and me.meter >= me.data.weapon.meter_cost
                and me.state in (State.IDLE, State.WALK)
                and gap < 95 and random.random() < 0.025):
            inp.weapon = True
            return inp
        # cok yakinsa ara sira atma (blogu kirar)
        if (me.state in (State.IDLE, State.WALK)
                and gap < 42 and random.random() < 0.02):
            inp.throw = True
            return inp

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
