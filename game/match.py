"""Mac akisi: round'lar, sure, KO ve kazanan tespiti.

Match sinifi cizimden bagimsiz test edilebilsin diye update() ve draw()
ayridir; run() ana dongu sarmalayicisidir.
"""

import random
from enum import Enum, auto

import pygame

from . import (audio, combat, effects, fx_sprites, hud, projectile, renderer,
               settings, stages)
from .characters import CHARACTERS, AttackData
from .controller import AIController, HumanController, Inputs, DIFFICULTY_LABELS
from .fighter import Fighter, State

P1_START_X = settings.WIDTH * 0.32
P2_START_X = settings.WIDTH * 0.68

# sahneye gore ortam partikulu (atmosfer)
AMBIENT_BY_STAGE = {
    "orman": "leaves", "cayir": "leaves", "sonbahar": "leaves",
    "sisli_orman": "leaves", "bulutlu_ova": "leaves", "daglar_gunduz": "leaves",
    "col": "dust", "tepeler_gunbatimi": "embers",
    "gece_dorukleri": "none", "sato_alacakaranlik": "none",
}


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
        self.slowmo = 0                      # KO slow-mo sayaci
        self._prev_hitstun = [False, False]  # kombo düSme tespiti icin
        self._prev_attacking = [False, False]  # whoosh sesi icin
        self.cam_x = 0.0                     # parallax kamera salinimi
        self.result: str | None = None  # 'menu' | 'quit' | 'rematch'
        self.hud = hud.HUD(self.p1, self.p2, difficulty_label)
        self.stage = random.choice(stages.STAGE_NAMES)
        self.renderer = renderer.Renderer(self.stage)
        self.effects = effects.EffectSystem()
        self.effects.set_ambient(AMBIENT_BY_STAGE.get(self.stage, "leaves"))
        self.projectiles = []                # ucan ozel ates mermileri

    # ------------------------------------------------------------------
    def start_round(self):
        self.p1.reset(P1_START_X, 1)
        self.p2.reset(P2_START_X, -1)
        self.hud.lag = [float(self.p1.health), float(self.p2.health)]
        self.timer_frames = settings.ROUND_TIME * settings.FPS
        self.hitstop = 0
        self.slowmo = 0
        self.projectiles.clear()
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
                self._whoosh_check()
                self._handle_specials()
                self._resolve_throws()
                hit_events = combat.resolve_hits(self.p1, self.p2)
                combat.push_apart(self.p1, self.p2)
                self._spawn_hit_effects(hit_events)
                self._update_projectiles()
                self._spawn_movement_dust()
                self._decay_combos()
                self.timer_frames -= 1
                self._check_round_end()
        elif self.phase == Phase.ROUND_OVER:
            # kazanan/kaybeden fizigi islemeye devam etsin (KO dususu vs.);
            # KO'dan hemen sonra slow-mo (her 3 karede 1 ilerle)
            if self.slowmo > 0:
                self.slowmo -= 1
                if self.slowmo % 3 == 0:
                    self.p1.update(Inputs(), self.p2)
                    self.p2.update(Inputs(), self.p1)
                    self._spawn_movement_dust()
                if self.slowmo == 0:
                    self.effects.set_slowmo_vignette(False)
            else:
                self.p1.update(Inputs(), self.p2)
                self.p2.update(Inputs(), self.p1)
                self._spawn_movement_dust()
            if self.phase_frame >= settings.ROUND_OVER_FRAMES:
                if max(self.wins) >= settings.ROUNDS_TO_WIN:
                    self.phase = Phase.MATCH_OVER
                    self.phase_frame = 0
                    winner = self.p1 if self.wins[0] > self.wins[1] else self.p2
                    winner.victory = True
                else:
                    self.round_num += 1
                    self.start_round()
        elif self.phase == Phase.MATCH_OVER:
            # kazanan sevinme pozunda, kaybeden yerde — animasyonlar ilerlesin
            self.p1.update(Inputs(), self.p2)
            self.p2.update(Inputs(), self.p1)
        self.hud.update()
        self.effects.update()

    def _spawn_hit_effects(self, hit_events):
        for ev in hit_events:
            self.effects.spawn_hit(ev.x, ev.y, ev.damage, blocked=ev.blocked,
                                   heavy=ev.heavy, ko=ev.ko)
            if ev.combo >= 2 and not ev.blocked:
                self.effects.spawn_combo(ev.combo, ev.attacker is self.p1)
            col = ev.attacker.data.color   # tema-renkli halka (D18)
            if ev.blocked:
                audio.play("block")
                self.hitstop = max(self.hitstop, effects.HITSTOP_BLOCK)
            elif ev.heavy or ev.ko:
                self.effects.spawn_impact_ring(ev.x, ev.y, color=col, big=True)
                audio.play("hit_heavy")
                self.hitstop = max(self.hitstop, effects.HITSTOP_HEAVY)
            else:
                self.effects.spawn_impact_ring(ev.x, ev.y, color=col)
                audio.play("hit_light")
                self.hitstop = max(self.hitstop, effects.HITSTOP_NORMAL)

    def _whoosh_check(self):
        for i, f in enumerate((self.p1, self.p2)):
            atk = f.state in (State.PUNCH, State.KICK)
            if atk and not self._prev_attacking[i]:
                audio.play("whoosh", 0.6)
            self._prev_attacking[i] = atk

    def _handle_specials(self):
        """Dovuscunun ozel ates sinyalini okuyup mermi olusturur (EX dahil)."""
        for f in (self.p1, self.p2):
            if f.spawn_special is None:
                continue
            spec = f.spawn_special
            f.spawn_special = None
            ex = getattr(f, "_special_ex", False)   # metre dolu = EX (guclu)
            px = f.x + f.facing * (f.data.width * 0.6)
            py = f.y - f.data.height * 0.55
            scale = 4.6 if ex else 3.0
            dmg = round(spec.damage * 1.7) if ex else spec.damage
            speed = spec.speed * (1.12 if ex else 1.0)
            hw = spec.hit_w + (20 if ex else 0)
            hh = spec.hit_h + (16 if ex else 0)
            kb = spec.knockback + (3.0 if ex else 0.0)
            proj = projectile.make_fireball(px, py, f.facing, spec.color, dmg, f,
                                            speed=speed, scale=scale, hit_w=hw, hit_h=hh)
            proj.attack = AttackData("özel ateş", dmg, 0, 1, 0, spec.hitstun, kb,
                                     hw, hh, 0.55, guard="high")
            self.projectiles.append(proj)
            # namlu flasi (muzzle)
            self.effects.spawn_anim(fx_sprites.explosion_frames(spec.color, scale=2.4),
                                    px, py, fps=30)
            audio.play("whoosh", 0.9)

    def _update_projectiles(self):
        if not self.projectiles:
            return
        for proj in self.projectiles:
            proj.update()
        events = combat.resolve_projectiles(self.projectiles, self.p1, self.p2)
        for ev in events:   # isabet noktasinda patlama animasyonu
            color = ev.attacker.data.special.color if ev.attacker.data.special else 0
            self.effects.spawn_anim(fx_sprites.explosion_frames(color, scale=3.0),
                                    ev.x, ev.y, fps=26)
        self._spawn_hit_effects(events)
        self.projectiles = [p for p in self.projectiles if p.alive]

    def _resolve_throws(self):
        """Yakin mesafede atma (bloklanamaz); match iki dovuscuyu birden gorur."""
        for f, other in ((self.p1, self.p2), (self.p2, self.p1)):
            if not f.wants_throw:
                continue
            f.wants_throw = False
            gap = abs(other.x - f.x) - (f.data.width + other.data.width) / 2
            if not (gap < 46 and other.on_ground and other.state not in (
                    State.KO, State.HITSTUN, State.SPECIAL, State.WEAPON, State.THROW)):
                continue
            dmg = 12
            other.health = max(0, other.health - dmg)
            other.attack = None
            other.blocking = False
            other.knocked_down = True
            other.hitstun_left = 30
            other.set_state(State.HITSTUN)
            other.vx = f.facing * 12.0
            other.vy = -8.0
            other.on_ground = False
            f.meter = min(settings.SUPER_MAX, f.meter + settings.SUPER_GAIN_HIT)
            other.meter = min(settings.SUPER_MAX, other.meter + settings.SUPER_GAIN_TAKEN)
            self.effects.spawn_hit(other.x, other.y - other.data.height * 0.5,
                                   dmg, heavy=True)
            self.effects.add_shake(10)
            audio.play("hit_heavy")
            if other.health <= 0:
                other.set_state(State.KO)
                other.vy = -7.0

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
                audio.play("jump", 0.7)
            if f.just_landed:
                self.effects.spawn_dust(f.x, settings.FLOOR_Y)
                audio.play("land", 0.6)

    def _start_ko_slowmo(self, loser=None):
        self.slowmo = 48
        key = loser.data.key if loser is not None else None
        audio.play(f"ko_{key}" if key else "ko")   # karaktere özel KO sesi
        self.effects.set_slowmo_vignette(True)

    def _check_round_end(self):
        ko1 = self.p1.state == State.KO
        ko2 = self.p2.state == State.KO
        if ko1 or ko2:
            self._start_ko_slowmo(self.p1 if ko1 else self.p2)
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
        # parallax kamera salinimi: dovusculerin ortalamasi merkezden kayinca
        # arka katmanlar derinliklerine gore kayar (yumusatilmis takip)
        target = max(-80.0, min(80.0,
                     ((self.p1.x + self.p2.x) / 2 - settings.WIDTH / 2) * 0.25))
        self.cam_x += (target - self.cam_x) * 0.12
        self.renderer.draw_stage(surf, self.cam_x)
        ox, oy = self.effects.shake_offset()  # ekran sarsintisi (dunya katmani)
        # KO olan altta kalsin diye once onu ciz
        order = sorted((self.p1, self.p2), key=lambda f: f.state == State.KO, reverse=True)
        for f in order:
            self.renderer.draw_fighter(surf, f, ox, oy)
        for f in (self.p1, self.p2):           # silah hilali dovusculerin ustunde
            if f.state == State.WEAPON:
                self.renderer.draw_weapon_arc(surf, f, ox, oy)
        self.effects.draw_world(surf, ox, oy)  # kivilcim/toz (sarsintiya dahil)
        for proj in self.projectiles:          # ucan mermiler
            proj.draw(surf, ox, oy)
        self.renderer.draw_foreground(surf, self.cam_x)  # on plan (dovusculerin ONUNDE)
        seconds = -(-self.timer_frames // settings.FPS)  # ceil
        self.hud.draw(surf, seconds, self.wins, self.round_num)
        self.effects.draw_overlay(surf)  # hasar sayilari + KO flash (sarsintisiz)

        if self.phase == Phase.INTRO:
            if self.phase_frame < settings.INTRO_FRAMES * 0.62:
                t = self.phase_frame / (settings.INTRO_FRAMES * 0.62)
                self.hud.draw_vs(surf, self.p1, self.p2, t)
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
