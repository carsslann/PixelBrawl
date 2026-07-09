"""Mac akisi: round'lar, sure, KO ve kazanan tespiti.

Match sinifi cizimden bagimsiz test edilebilsin diye update() ve draw()
ayridir; run() ana dongu sarmalayicisidir.
"""

import random
from enum import Enum, auto

import pygame

from . import combat, effects, hud, renderer, settings, stages
from .characters import CHARACTERS
from .controller import AIController, HumanController, Inputs, DIFFICULTY_LABELS
from .fighter import Fighter, State

P1_START_X = settings.WIDTH * 0.32
P2_START_X = settings.WIDTH * 0.68


class Phase(Enum):
    INTRO = auto()
    FIGHT = auto()
    ROUND_OVER = auto()
    MATCH_OVER = auto()


class Match:
    def __init__(self, p1_char: str, p2_char: str, c1, c2, difficulty_label: str = ""):
        self.p1 = Fighter(CHARACTERS[p1_char], P1_START_X, 1)
        self.p2 = Fighter(CHARACTERS[p2_char], P2_START_X, -1)
        self.c1, self.c2 = c1, c2
        self.wins = [0, 0]
        self.round_num = 1
        self.phase = Phase.INTRO
        self.phase_frame = 0
        self.timer_frames = settings.ROUND_TIME * settings.FPS
        self.banner_text = ""
        self.banner_sub = ""
        self.paused = False
        self.hitstop = 0
        self._prev_hitstun = [False, False]  # kombo düSme tespiti icin
        self.result: str | None = None  # 'menu' | 'quit' | 'rematch'
        self.hud = hud.HUD(self.p1, self.p2, difficulty_label)
        self.renderer = renderer.Renderer(random.choice(stages.STAGE_NAMES))
        self.effects = effects.EffectSystem()

    # ------------------------------------------------------------------
    def start_round(self):
        self.p1.reset(P1_START_X, 1)
        self.p2.reset(P2_START_X, -1)
        self.hud.lag = [float(self.p1.health), float(self.p2.health)]
        self.timer_frames = settings.ROUND_TIME * settings.FPS
        self.hitstop = 0
        self.effects.reset()
        self.phase = Phase.INTRO
        self.phase_frame = 0

    def update(self, events, pressed):
        for e in events:
            if e.type == pygame.QUIT:
                self.result = "quit"
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.phase == Phase.MATCH_OVER:
                        self.result = "menu"
                        return
                    self.paused = not self.paused
                elif self.paused and e.key == pygame.K_q:
                    self.result = "menu"
                    return
                elif self.phase == Phase.MATCH_OVER and e.key == pygame.K_RETURN:
                    self.result = "rematch"
                    return
        if self.paused:
            return

        self.phase_frame += 1
        if self.phase == Phase.INTRO:
            if self.phase_frame >= settings.INTRO_FRAMES:
                self.phase = Phase.FIGHT
                self.phase_frame = 0
        elif self.phase == Phase.FIGHT:
            if self.hitstop > 0:
                self.hitstop -= 1  # isabet donmasi: dovusculer bu kare bekler
            else:
                i1 = self.c1.get_inputs(self.p1, self.p2, pressed, events)
                i2 = self.c2.get_inputs(self.p2, self.p1, pressed, events)
                self.p1.update(i1, self.p2)
                self.p2.update(i2, self.p1)
                hit_events = combat.resolve_hits(self.p1, self.p2)
                combat.push_apart(self.p1, self.p2)
                self._spawn_hit_effects(hit_events)
                self._spawn_movement_dust()
                self._decay_combos()
                self.timer_frames -= 1
                self._check_round_end()
        elif self.phase == Phase.ROUND_OVER:
            # kazanan/kaybeden fizigi islemeye devam etsin (KO dususu vs.)
            self.p1.update(Inputs(), self.p2)
            self.p2.update(Inputs(), self.p1)
            self._spawn_movement_dust()
            if self.phase_frame >= settings.ROUND_OVER_FRAMES:
                if max(self.wins) >= settings.ROUNDS_TO_WIN:
                    self.phase = Phase.MATCH_OVER
                    self.phase_frame = 0
                else:
                    self.round_num += 1
                    self.start_round()
        # MATCH_OVER: yalnizca tus bekler
        self.hud.update()
        self.effects.update()

    def _spawn_hit_effects(self, hit_events):
        for ev in hit_events:
            self.effects.spawn_hit(ev.x, ev.y, ev.damage, blocked=ev.blocked,
                                   heavy=ev.heavy, ko=ev.ko)
            if ev.combo >= 2 and not ev.blocked:
                self.effects.spawn_combo(ev.combo, ev.attacker is self.p1)
            if ev.blocked:
                self.hitstop = max(self.hitstop, effects.HITSTOP_BLOCK)
            elif ev.heavy or ev.ko:
                self.hitstop = max(self.hitstop, effects.HITSTOP_HEAVY)
            else:
                self.hitstop = max(self.hitstop, effects.HITSTOP_NORMAL)

    def _decay_combos(self):
        """Bir dovuscu hitstun'dan cikinca rakibinin kombosunu sifirla."""
        for i, (f, other) in enumerate(((self.p1, self.p2), (self.p2, self.p1))):
            now = f.state == State.HITSTUN
            if self._prev_hitstun[i] and not now:
                other.combo_count = 0
            self._prev_hitstun[i] = now

    def _spawn_movement_dust(self):
        for f in (self.p1, self.p2):
            if f.just_jumped:
                d = 1 if f.vx > 0.5 else -1 if f.vx < -0.5 else 0
                self.effects.spawn_dust(f.x, settings.FLOOR_Y, direction=d)
            if f.just_landed:
                self.effects.spawn_dust(f.x, settings.FLOOR_Y)

    def _check_round_end(self):
        ko1 = self.p1.state == State.KO
        ko2 = self.p2.state == State.KO
        if ko1 and ko2:
            self._end_round(None, "ÇİFT NAKAVT!")
        elif ko1:
            self._end_round(1, "K.O.!")
        elif ko2:
            self._end_round(0, "K.O.!")
        elif self.timer_frames <= 0:
            if self.p1.health > self.p2.health:
                self._end_round(0, "SÜRE BİTTİ!")
            elif self.p2.health > self.p1.health:
                self._end_round(1, "SÜRE BİTTİ!")
            else:
                self._end_round(None, "BERABERE!")

    def _end_round(self, winner_idx, text: str):
        if winner_idx is not None:
            self.wins[winner_idx] += 1
            winner = (self.p1, self.p2)[winner_idx]
            self.banner_text = text
            self.banner_sub = f"{winner.data.name} round'u aldı"
        else:
            self.banner_text = text
            self.banner_sub = "Round tekrar oynanacak"
        self.phase = Phase.ROUND_OVER
        self.phase_frame = 0

    # ------------------------------------------------------------------
    def draw(self, surf):
        self.renderer.draw_stage(surf)
        ox, oy = self.effects.shake_offset()  # ekran sarsintisi (dunya katmani)
        # KO olan altta kalsin diye once onu ciz
        order = sorted((self.p1, self.p2), key=lambda f: f.state == State.KO, reverse=True)
        for f in order:
            self.renderer.draw_fighter(surf, f, ox, oy)
        self.effects.draw_world(surf, ox, oy)  # kivilcim/toz (sarsintiya dahil)
        seconds = -(-self.timer_frames // settings.FPS)  # ceil
        self.hud.draw(surf, seconds, self.wins, self.round_num)
        self.effects.draw_overlay(surf)  # hasar sayilari + KO flash (sarsintisiz)

        if self.phase == Phase.INTRO:
            if self.phase_frame < settings.INTRO_FRAMES * 0.6:
                self.hud.banner(surf, f"ROUND {self.round_num}")
            else:
                self.hud.banner(surf, "DÖVÜŞ!")
        elif self.phase == Phase.ROUND_OVER:
            self.hud.banner(surf, self.banner_text, self.banner_sub)
        elif self.phase == Phase.MATCH_OVER:
            winner = self.p1 if self.wins[0] > self.wins[1] else self.p2
            self.hud.banner(surf, f"KAZANAN: {winner.data.name}",
                            "ENTER: Tekrar oyna    ESC: Ana menü")
        if self.paused:
            overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surf.blit(overlay, (0, 0))
            self.hud.banner(surf, "DURAKLATILDI", "ESC: Devam    Q: Ana menü")


def run(screen, clock, config) -> str:
    """Menu'den gelen secimle mac(lar)i kosar; 'menu' ya da 'quit' dondurur."""
    while True:
        m = Match(
            config["p1"], config["p2"],
            HumanController(),
            AIController(config["difficulty"]),
            DIFFICULTY_LABELS[config["difficulty"]],
        )
        while m.result is None:
            events = pygame.event.get()
            pressed = pygame.key.get_pressed()
            m.update(events, pressed)
            m.draw(screen)
            pygame.display.flip()
            clock.tick(settings.FPS)
        if m.result != "rematch":
            return m.result
