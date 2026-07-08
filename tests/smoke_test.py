"""Pencere acmadan calisan duman testleri.

Calistirma: py tests/smoke_test.py
SDL dummy surucusuyle kosar; ekranda hicbir sey gorunmez.
"""

import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))

from game import combat, effects, settings, sprites  # noqa: E402
from game.characters import CHARACTERS, CHARACTER_ORDER  # noqa: E402
from game.controller import AIController, Inputs  # noqa: E402
from game.fighter import Fighter, State  # noqa: E402
from game.match import Match, Phase  # noqa: E402

A = CHARACTER_ORDER[0]  # dengeli karakter (efe)
B = CHARACTER_ORDER[2]  # hizli karakter (zeynep)
HEAVY = CHARACTER_ORDER[4]  # agir karakter (robo)


def _step(a, b, ia=None, ib=None):
    a.update(ia or Inputs(), b)
    b.update(ib or Inputs(), a)
    ev = combat.resolve_hits(a, b)
    combat.push_apart(a, b)
    return ev


# ---------------------------------------------------------------- mantik
def test_punch_hits():
    a = Fighter(CHARACTERS[A], 600, 1)
    b = Fighter(CHARACTERS[A], 660, -1)
    hp0 = b.health
    _step(a, b, ia=Inputs(punch=True))
    for _ in range(30):
        _step(a, b)
    assert b.health == hp0 - a.data.punch.damage, \
        f"yumruk hasari yanlis: {hp0 - b.health}"
    assert b.state in (State.HITSTUN, State.IDLE)


def test_attack_hits_once():
    a = Fighter(CHARACTERS[A], 600, 1)
    b = Fighter(CHARACTERS[A], 660, -1)
    hp0 = b.health
    _step(a, b, ia=Inputs(kick=True))
    for _ in range(60):
        _step(a, b)
    dealt = hp0 - b.health
    assert dealt == a.data.kick.damage, f"tekme bir kez vurmali, hasar={dealt}"


def test_block_chips():
    a = Fighter(CHARACTERS[A], 600, 1)
    b = Fighter(CHARACTERS[A], 660, -1)
    hp0 = b.health
    _step(a, b, ia=Inputs(punch=True), ib=Inputs(block=True))
    for _ in range(30):
        _step(a, b, ib=Inputs(block=True))
    dealt = hp0 - b.health
    expected = max(1, round(a.data.punch.damage * settings.CHIP_DAMAGE_RATIO))
    assert dealt == expected, f"blok chip hasari yanlis: {dealt} != {expected}"
    assert b.state == State.BLOCK


def test_out_of_range_misses():
    a = Fighter(CHARACTERS[A], 300, 1)
    b = Fighter(CHARACTERS[A], 900, -1)
    hp0 = b.health
    _step(a, b, ia=Inputs(punch=True))
    for _ in range(30):
        _step(a, b)
    assert b.health == hp0, "menzil disindan vurus isabet etmemeli"


def test_hit_event_reported():
    a = Fighter(CHARACTERS[A], 600, 1)
    b = Fighter(CHARACTERS[A], 660, -1)
    events = []
    events += _step(a, b, ia=Inputs(punch=True))
    for _ in range(10):
        events += _step(a, b)
    assert len(events) == 1, f"tam bir isabet olayi beklenir, {len(events)} geldi"
    ev = events[0]
    assert ev.damage == a.data.punch.damage and not ev.blocked


def test_ko_and_round_flow():
    m = Match(A, B, AIController("orta"), AIController("orta"), "Orta")
    m.phase = Phase.FIGHT
    m.p2.health = 1
    m.p2.take_hit(m.p1.data.punch, 1)
    assert m.p2.state == State.KO
    m._check_round_end()
    assert m.phase == Phase.ROUND_OVER and m.wins == [1, 0]
    for _ in range(settings.ROUND_OVER_FRAMES + 5):
        m.update([], pygame.key.get_pressed())
    assert m.round_num == 2 and m.phase in (Phase.INTRO, Phase.FIGHT)


def test_timeout_draw():
    m = Match(A, A, AIController("orta"), AIController("orta"), "Orta")
    m.phase = Phase.FIGHT
    m.timer_frames = 1
    m.p1.x, m.p2.x = 300, 900
    m.update([], pygame.key.get_pressed())
    assert m.phase == Phase.ROUND_OVER
    assert m.wins == [0, 0], "esit canla sure bitince round kimseye yazilmamali"


def test_wall_pushback():
    a = Fighter(CHARACTERS[HEAVY], settings.STAGE_MARGIN + 40, -1)
    b = Fighter(CHARACTERS[HEAVY], settings.STAGE_MARGIN + 50, 1)
    for _ in range(5):
        combat.push_apart(a, b)
    assert not a.hurtbox().colliderect(b.hurtbox()), "duvarda govdeler ayrilamadi"


# ---------------------------------------------------------------- efekt
def test_hitstop_freezes_fighters():
    m = Match(A, B, AIController("orta"), AIController("orta"), "Orta")
    m.phase = Phase.FIGHT
    ev = combat.HitEvent(x=600, y=400, damage=8, blocked=False, heavy=False, ko=False)
    m._spawn_hit_effects([ev])
    assert m.hitstop == effects.HITSTOP_NORMAL
    x_before = m.p1.x
    m.update([], pygame.key.get_pressed())
    assert m.hitstop == effects.HITSTOP_NORMAL - 1
    assert m.p1.x == x_before, "hitstop sirasinda dovuscu ilerlememeli"


def test_effects_spawn_and_reset():
    fx = effects.EffectSystem()
    fx.spawn_hit(500, 300, 12, heavy=True)
    assert len(fx.numbers) == 1 and len(fx.particles) > 0
    assert fx.shake > 0
    for _ in range(80):
        fx.update()
    assert not fx.numbers and not fx.particles, "efektler zamanla temizlenmeli"
    fx.spawn_hit(1, 1, 5)
    fx.reset()
    assert not fx.numbers and not fx.particles and fx.shake == 0


def test_block_event_effect():
    fx = effects.EffectSystem()
    fx.spawn_hit(400, 300, 8, blocked=True)
    assert fx.numbers[0].text == "BLOK"


# ---------------------------------------------------------------- sprite
def test_all_sprites_load():
    for key in CHARACTER_ORDER:
        anim = sprites.load_animator(CHARACTERS[key])
        assert anim is not None, f"{key} sprite'lari yuklenemedi (charac/ eksik?)"
        f = Fighter(CHARACTERS[key], 600, 1)
        for state in (State.IDLE, State.WALK, State.JUMP, State.PUNCH,
                      State.KICK, State.BLOCK, State.HITSTUN, State.KO):
            f.state = state
            f.state_frame = 3
            if state in (State.PUNCH, State.KICK):
                f.attack = f.data.punch if state == State.PUNCH else f.data.kick
            frame = anim.frame_for(f)
            assert frame is not None, f"{key}/{state} icin kare yok"


def test_preview_loads():
    for key in CHARACTER_ORDER:
        img = sprites.load_idle_preview(CHARACTERS[key], 300)
        assert img is not None, f"{key} onizlemesi yuklenemedi"


def test_missing_sprite_falls_back():
    from game.characters import CharacterData, SpriteRef
    broken = CharacterData(
        key="x", name="X", color=(1, 2, 3), width=60, height=160,
        walk_speed=4, jump_vx=4, jump_vy=-18, max_health=100,
        punch=CHARACTERS[A].punch, kick=CHARACTERS[A].kick,
        sprite=SpriteRef("charac/Yok", "character_yok"))
    assert sprites.load_animator(broken) is None, "eksik klasor None dondurmeli"


# ---------------------------------------------------------------- entegrasyon
def test_full_match_with_draw_and_effects():
    random.seed(11)
    m = Match(A, HEAVY, AIController("zor"), AIController("zor"), "Zor")
    surf = pygame.display.get_surface()
    saw_effect = False
    for _ in range(60 * 90):
        if m.result is not None or m.phase == Phase.MATCH_OVER:
            break
        m.update([], pygame.key.get_pressed())
        m.draw(surf)
        if m.effects.numbers or m.effects.particles:
            saw_effect = True
        assert len(m.effects.particles) < 5000, "parcacik birikimi (sizinti)"
    assert saw_effect, "90 saniyede hic vurus efekti olusmadi"


def test_easy_bot_is_passive():
    """Kolay bot, zor bota gore belirgin sekilde daha az saldirmali."""
    def count_attacks(diff, seed):
        random.seed(seed)
        bot = AIController(diff)
        me = Fighter(CHARACTERS[A], 500, 1)
        opp = Fighter(CHARACTERS[A], 640, -1)  # menzil icinde tut
        hits = 0
        for _ in range(60 * 20):
            inp = bot.get_inputs(me, opp, pygame.key.get_pressed(), [])
            if inp.punch or inp.kick:
                hits += 1
            me.update(inp, opp)
            opp.update(Inputs(), me)
            if me.x > opp.x - 60:
                me.x = opp.x - 60  # sabit mesafede tut
        return hits
    easy = count_attacks("kolay", 3)
    hard = count_attacks("zor", 3)
    assert easy < hard, f"kolay({easy}) zordan({hard}) daha saldirgan olmamali"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\nTUM TESTLER GECTI ({len(tests)} test)")
