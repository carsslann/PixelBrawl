"""Vurus cozumu, blok kurallari, kombo sayaci ve govde itisme."""

from dataclasses import dataclass

from . import settings
from .fighter import Fighter, State

# kombo icinde sonraki vuruslar daha az hasar (sonsuz kombo olmasin)
COMBO_SCALE = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]


@dataclass
class HitEvent:
    x: float
    y: float
    damage: int
    blocked: bool
    heavy: bool
    ko: bool
    attacker: Fighter
    combo: int = 1        # saldiranin bu andaki kombo sayisi
    knockdown: bool = False


def _guard_ok(stance: str, guard: str) -> bool:
    """Blok duruSu saldirinin yuksekligini kesebiliyor mu?"""
    if stance == "stand":
        return guard in ("high", "overhead")   # ayakta: overhead+yuksek, alcak GECER
    if stance == "crouch":
        return guard in ("high", "low")         # cömel: yuksek+alcak, overhead GECER
    return False


def resolve_hits(a: Fighter, b: Fighter) -> list[HitEvent]:
    """Iki dovuscunun aktif vuruslarini cozer, isabet olaylarini dondurur.

    Ayni karede iki taraf da isabet ettirirse (trade) ikisi de yer;
    once iki isabet tespit edilir, sonra uygulanir.
    """
    events: list[HitEvent] = []
    hit_ab = _lands(a, b)
    hit_ba = _lands(b, a)
    atk_a, atk_b = a.attack, b.attack
    if hit_ab:
        a.attack_has_hit = True
        events.append(_apply(a, b, atk_a))
    if hit_ba:
        b.attack_has_hit = True
        events.append(_apply(b, a, atk_b))
    return events


def _apply(attacker: Fighter, defender: Fighter, attack) -> HitEvent:
    cx, cy = _hit_point(attacker, defender)
    stance = defender.block_stance()
    blocked = stance is not None and _guard_ok(stance, attack.guard)

    if blocked:
        attacker.combo_count = 0
        dmg = max(1, round(attack.damage * settings.CHIP_DAMAGE_RATIO))
    else:
        if defender.state == State.HITSTUN:   # süregelen kombo
            attacker.combo_count += 1
        else:
            attacker.combo_count = 1
        scale = COMBO_SCALE[min(len(COMBO_SCALE) - 1, attacker.combo_count - 1)]
        dmg = max(1, round(attack.damage * scale))

    defender.take_hit(attack, attacker.facing, blocked, dmg)
    heavy = attack.knockback >= 9.0 or attack.knockdown
    return HitEvent(cx, cy, dmg, blocked, heavy,
                    ko=(defender.state == State.KO), attacker=attacker,
                    combo=attacker.combo_count,
                    knockdown=attack.knockdown and not blocked)


def _hit_point(attacker: Fighter, defender: Fighter):
    hb = attacker.active_hitbox()
    box = defender.hurtbox()
    if hb is not None:
        clip = hb.clip(box)
        cx = clip.centerx if clip.width else (hb.centerx + box.centerx) // 2
        cy = clip.centery if clip.height else (hb.centery + box.centery) // 2
        return cx, cy
    return box.centerx, box.top


def _lands(attacker: Fighter, defender: Fighter) -> bool:
    if attacker.attack_has_hit or defender.state == State.KO:
        return False
    hb = attacker.active_hitbox()
    return hb is not None and hb.colliderect(defender.hurtbox())


def push_apart(a: Fighter, b: Fighter):
    """Govdelerin ust uste binmesini engeller (pushbox)."""
    ra, rb = a.hurtbox(), b.hurtbox()
    if not ra.colliderect(rb):
        return
    overlap = min(ra.right, rb.right) - max(ra.left, rb.left)
    if overlap <= 0:
        return
    left_f, right_f = (a, b) if a.x <= b.x else (b, a)
    shift = overlap / 2 + 0.5
    left_f.x -= shift
    right_f.x += shift
    _clamp(left_f)
    _clamp(right_f)
    ra, rb = a.hurtbox(), b.hurtbox()
    if ra.colliderect(rb):
        overlap = min(ra.right, rb.right) - max(ra.left, rb.left)
        if right_f.x >= settings.WIDTH - settings.STAGE_MARGIN - right_f.data.width / 2 - 1:
            left_f.x -= overlap
        else:
            right_f.x += overlap
        _clamp(left_f)
        _clamp(right_f)


def _clamp(f: Fighter):
    half = f.data.width / 2
    f.x = max(settings.STAGE_MARGIN + half,
              min(settings.WIDTH - settings.STAGE_MARGIN - half, f.x))
