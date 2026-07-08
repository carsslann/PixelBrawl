"""Vurus cozumu ve govde itisme kurallari."""

from dataclasses import dataclass

from . import settings
from .fighter import Fighter, State


@dataclass
class HitEvent:
    x: float          # isabet noktasi (efektler icin)
    y: float
    damage: int
    blocked: bool
    heavy: bool       # agir vurus (tekme) -> daha buyuk efekt/sarsinti
    ko: bool          # bu vurus rakibi nakavt etti


def resolve_hits(a: Fighter, b: Fighter) -> list[HitEvent]:
    """Iki dovuscunun aktif vuruslarini cozer, isabet olaylarini dondurur.

    Iki taraf ayni karede isabet ettirirse (trade) ikisi de hasar alir;
    bu yuzden once iki isabet de tespit edilir, sonra uygulanir.
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
    hb = attacker.active_hitbox()
    box = defender.hurtbox()
    # isabet noktasi: vurus kutusu ile govdenin ortak alaninin ortasi
    if hb is not None:
        clip = hb.clip(box)
        cx = clip.centerx if clip.width else (hb.centerx + box.centerx) // 2
        cy = clip.centery if clip.height else (hb.centery + box.centery) // 2
    else:
        cx, cy = box.centerx, box.top
    blocked = defender.state == State.BLOCK
    defender.take_hit(attack, attacker.facing)
    return HitEvent(cx, cy, attack.damage, blocked,
                    heavy=attack.knockback >= 9.0, ko=(defender.state == State.KO))


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
    # duvara sikisma: taraflardan biri duvarda kaldiysa digerini ittir
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
