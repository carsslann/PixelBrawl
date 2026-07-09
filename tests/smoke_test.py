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

A = CHARACTER_ORDER[0]      # dengeli (efe)
B = CHARACTER_ORDER[2]      # hizli (zeynep)
HEAVY = CHARACTER_ORDER[4]  # agir (robo)


def _fresh(a_key=A, b_key=A, ax=600, bx=658):
    return (Fighter(CHARACTERS[a_key], ax, 1),
            Fighter(CHARACTERS[b_key], bx, -1))


def _step(a, b, ia=None, ib=None):
    a.update(ia or Inputs(), b)
    b.update(ib or Inputs(), a)
    ev = combat.resolve_hits(a, b)
    combat.push_apart(a, b)
    return ev


def _do_move(a, b, a_inputs, b_inputs=None, frames=50, pin=False):
    """a: ilk karede a_inputs (saldiri kenar-tetik), sonra bos.
       b: her kare b_inputs'u basili tutar. pin=True ise x'ler sabitlenir."""
    hp0 = b.health
    ax0, bx0 = a.x, b.x
    events = []
    for i in range(frames):
        ia = a_inputs if i == 0 else Inputs()
        events += _step(a, b, ia=ia, ib=(b_inputs or Inputs()))
        if pin:
            a.x, b.x = ax0, bx0
    return hp0 - b.health, events


def _chip(attack):
    return max(1, round(attack.damage * settings.CHIP_DAMAGE_RATIO))


# ---------------------------------------------------------------- temel
def test_punch_hits():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(punch=True))
    assert dmg == a.data.punch.damage, f"yumruk hasari yanlis: {dmg}"


def test_attack_hits_once():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(kick=True), frames=60)
    assert dmg == a.data.kick.damage, f"tekme bir kez vurmali, hasar={dmg}"


def test_out_of_range_misses():
    a, b = _fresh(ax=300, bx=900)
    dmg, _ = _do_move(a, b, Inputs(punch=True))
    assert dmg == 0, "menzil disindan vurus isabet etmemeli"


def test_hit_event_reported():
    a, b = _fresh()
    _, events = _do_move(a, b, Inputs(punch=True), frames=12)
    assert len(events) == 1 and not events[0].blocked
    assert events[0].attacker is a


# ---------------------------------------------------------------- blok (yuksek/alcak/overhead)
def test_standing_block_stops_high():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(punch=True), Inputs(move=1), pin=True)
    assert dmg == _chip(a.data.punch), f"ayakta blok yuksegi kesmeli (chip): {dmg}"


def test_standing_block_beaten_by_low():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(down=True, kick=True), Inputs(move=1), pin=True)
    assert dmg == a.data.sweep.damage, f"ayakta blok alcagi KESMEMELI: {dmg}"


def test_crouch_block_stops_low():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(down=True, kick=True),
                      Inputs(move=1, down=True), pin=True)
    assert dmg == _chip(a.data.sweep), f"cömel blok alcagi kesmeli (chip): {dmg}"


def test_jump_attack_is_overhead():
    """Zipla-vur overhead: ayakta blok keser, cömel blok KESMEZ."""
    def jump_attack(b_inputs, ax=600, bx=650):
        a, b = _fresh(ax=ax, bx=bx)
        hp0 = b.health
        _step(a, b, ia=Inputs(jump=True), ib=b_inputs); a.x = ax
        for _ in range(3):
            _step(a, b, ib=b_inputs); a.x = ax
        _step(a, b, ia=Inputs(punch=True), ib=b_inputs); a.x = ax
        for _ in range(40):
            _step(a, b, ib=b_inputs); a.x, b.x = ax, bx
        return hp0 - b.health, a
    clean, a = jump_attack(Inputs())
    assert clean > 0, "hava saldirisi ayakta duran rakibe isabet etmeli"
    stand, _ = jump_attack(Inputs(move=1))       # ayakta blok
    crouch, _ = jump_attack(Inputs(move=1, down=True))  # cömel blok
    assert stand < clean, "ayakta blok overhead'i kesmeli"
    assert crouch >= clean * 0.8, "cömel blok overhead'i KESMEMELI"


# ---------------------------------------------------------------- kombo
def test_chain_cancel_on_hit():
    a, b = _fresh()
    _step(a, b, ia=Inputs(punch=True))
    for _ in range(20):
        _step(a, b); a.x, b.x = 600, 658
        if a.attack_has_hit:
            break
    assert a.attack_has_hit and a.state == State.PUNCH
    _step(a, b, ia=Inputs(kick=True)); a.x, b.x = 600, 658
    assert a.state == State.KICK and a.attack.name == "tekme", \
        "isabet eden yumruk tekmeye iptal olabilmeli (zincir kombo)"


def test_no_cancel_without_hit():
    a, b = _fresh(ax=300, bx=900)  # menzil disi, whiff
    _step(a, b, ia=Inputs(punch=True))
    for _ in range(3):
        _step(a, b)
    st_before = a.state
    _step(a, b, ia=Inputs(kick=True))
    assert st_before == State.PUNCH and a.state == State.PUNCH, \
        "iskalayan saldiri iptal edilememeli"


def test_combo_counter_and_scaling():
    a, b = _fresh()
    b.state = State.HITSTUN
    b.hitstun_left = 80          # kombo penceresini acik tut
    a.combo_count = 1            # ilk vurus zaten sayildi varsay
    hp0 = b.health
    for i in range(30):
        ia = Inputs(kick=True) if i == 0 else Inputs()
        _step(a, b, ia=ia); a.x, b.x = 600, 658
        if a.combo_count >= 2:
            break
    assert a.combo_count == 2, f"hitstun sirasinda isabet komboyu artirmali: {a.combo_count}"
    dealt = hp0 - b.health
    expected = max(1, round(a.data.kick.damage * combat.COMBO_SCALE[1]))
    assert dealt == expected, f"kombo hasar olcekleme yanlis: {dealt} != {expected}"


def test_combo_resets_on_recovery():
    m = Match(A, B, AIController("orta"), AIController("orta"), "Orta")
    m.p1.combo_count = 3
    m.p2.state = State.HITSTUN
    m._prev_hitstun = [False, True]
    m.p2.state = State.IDLE  # p2 hitstun'dan cikti
    m._decay_combos()
    assert m.p1.combo_count == 0, "rakip toparlaninca kombo sifirlanmali"


# ---------------------------------------------------------------- comelme / supurme
def test_sweep_knocks_down():
    a, b = _fresh()
    dmg, _ = _do_move(a, b, Inputs(down=True, kick=True), frames=24, pin=True)
    assert dmg > 0, "supurme isabet etmeli"
    assert b.knocked_down, "supurme rakibi yere sermeli (knocked_down)"
    assert b.state == State.HITSTUN


def test_crouch_shrinks_hurtbox():
    f = Fighter(CHARACTERS[A], 600, 1)
    stand_h = f.hurtbox().height
    f.set_state(State.CROUCH)
    assert f.hurtbox().height < stand_h, "cömelince hurtbox alcalmali"


# ---------------------------------------------------------------- round akisi
def test_ko_and_round_flow():
    m = Match(A, B, AIController("orta"), AIController("orta"), "Orta")
    m.phase = Phase.FIGHT
    m.p2.health = 1
    m.p2.take_hit(m.p1.data.punch, 1, False, 5)
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
    assert m.phase == Phase.ROUND_OVER and m.wins == [0, 0]


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
    ev = combat.HitEvent(x=600, y=400, damage=8, blocked=False, heavy=False,
                         ko=False, attacker=m.p1)
    m._spawn_hit_effects([ev])
    assert m.hitstop == effects.HITSTOP_NORMAL
    x_before = m.p1.x
    m.update([], pygame.key.get_pressed())
    assert m.hitstop == effects.HITSTOP_NORMAL - 1 and m.p1.x == x_before


def test_effects_spawn_and_reset():
    fx = effects.EffectSystem()
    fx.spawn_hit(500, 300, 12, heavy=True)
    fx.spawn_combo(3, True)
    assert len(fx.numbers) == 1 and fx.particles and fx.shake > 0 and fx.combo
    for _ in range(80):
        fx.update()
    assert not fx.numbers and not fx.particles and fx.combo is None
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
        assert anim is not None, f"{key} sprite'lari yuklenemedi"
        f = Fighter(CHARACTERS[key], 600, 1)
        for state in (State.IDLE, State.WALK, State.CROUCH, State.JUMP,
                      State.PUNCH, State.KICK, State.BLOCK, State.HITSTUN, State.KO):
            f.state = state
            f.state_frame = 3
            if state in (State.PUNCH, State.KICK):
                f.attack = f.data.punch if state == State.PUNCH else f.data.kick
            assert anim.frame_for(f) is not None, f"{key}/{state} icin kare yok"


def test_preview_loads():
    for key in CHARACTER_ORDER:
        assert sprites.load_idle_preview(CHARACTERS[key], 300) is not None


def test_missing_sprite_falls_back():
    from game.characters import CharacterData, SpriteRef
    broken = CharacterData(
        key="x", name="X", color=(1, 2, 3), width=60, height=160,
        walk_speed=4, jump_vx=4, jump_vy=-18, max_health=100,
        punch=CHARACTERS[A].punch, kick=CHARACTERS[A].kick,
        sprite=SpriteRef("charac/Yok", "character_yok"))
    assert sprites.load_animator(broken) is None


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
        assert len(m.effects.particles) < 5000
    assert saw_effect, "90 saniyede hic vurus efekti olusmadi"


def test_easy_bot_is_passive():
    def count_attacks(diff, seed):
        random.seed(seed)
        bot = AIController(diff)
        me = Fighter(CHARACTERS[A], 500, 1)
        opp = Fighter(CHARACTERS[A], 640, -1)
        hits = 0
        for _ in range(60 * 20):
            inp = bot.get_inputs(me, opp, pygame.key.get_pressed(), [])
            if inp.punch or inp.kick:
                hits += 1
            me.update(inp, opp)
            opp.update(Inputs(), me)
            if me.x > opp.x - 60:
                me.x = opp.x - 60
        return hits
    assert count_attacks("kolay", 3) < count_attacks("zor", 3)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\nTUM TESTLER GECTI ({len(tests)} test)")
