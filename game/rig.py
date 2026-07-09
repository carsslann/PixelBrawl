"""Parca-tabanli karakter rig'i (kagit-bebek / cutout).

Kenney "Parts" (kafa/govde/kol/el/bacak) parcalarindan karakteri kurar ve
uzuvlari DONDURENEK poz verir; boylece silah elin (bilek) cocugu gibi kolla
beraber kavranip savrulur — hazir tam-govde pozlara yapistirilan "havada"
silah sorunu ortadan kalkar.

Cizimden bagimsiz oyun mantigini (fighter.py) etkilemez; renderer bu modulu
silah kusanmis dovuscuyu cizmek icin kullanir. Godot portu icin ayni iskelet
(omuz/kalca eklemleri, kol acilari) node hiyerarsisine tasinacak.
"""

import math

import pygame

from . import settings, weapons
from .fighter import State

V = pygame.math.Vector2

# parca yerel bagla noktalari (orijinal piksel, olceksiz)
_ARM_SHOULDER = V(10, 3)    # kol: ust-orta (omuz)
_ARM_WRIST = V(10, 28)      # kol: alt-orta (bilek)
_HAND_C = V(9, 8)
_LEG_HIP = V(9, 3)
_BODY_HIP = V(18, 38)       # govde alt-orta (kalca)
_HEAD_BOT = V(28, 54)       # kafa alt-orta (biraz yukarida = govdeyle binisme)

_PART_NAMES = ["head", "body", "arm", "hand", "leg", "legBend"]
_cache: dict = {}            # (folder) -> {part: Surface}


def _load_parts(char_data):
    folder = char_data.sprite.folder if char_data.sprite else None
    if not folder:
        return None
    if folder in _cache:
        return _cache[folder]
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = os.path.join(root, *folder.split("/"), "PNG", "Parts")
    parts = {}
    try:
        for nm in _PART_NAMES:
            p = os.path.join(base, f"{nm}.png")
            if os.path.isfile(p):
                parts[nm] = pygame.image.load(p).convert_alpha()
    except Exception:
        parts = {}
    if "body" not in parts or "arm" not in parts:
        parts = None
    _cache[folder] = parts
    return parts


def available(char_data) -> bool:
    return _load_parts(char_data) is not None


def _scale_for(f) -> float:
    # rig'in gorunur boyu eski sprite'inkine yakin olsun (~data.height)
    return f.data.height / 96.0


def _attach(surf, img, joint, attach_local, angle, S, flip=False):
    """img'in attach_local noktasi joint'e otursun, o nokta etrafinda don."""
    src = pygame.transform.flip(img, True, False) if flip else img
    al = V(src.get_width() - attach_local.x, attach_local.y) if flip else V(attach_local)
    rot = pygame.transform.rotozoom(src, angle, S)
    c = V(src.get_width() / 2, src.get_height() / 2)
    off = (c - al).rotate(-angle) * S
    surf.blit(rot, rot.get_rect(center=(joint[0] + off.x, joint[1] + off.y)))


def _wrist_world(shoulder, angle, S, flip):
    d = (_ARM_WRIST - _ARM_SHOULDER)
    if flip:
        d = V(-d.x, d.y)
    v = d.rotate(-angle) * S
    return (shoulder[0] + v.x, shoulder[1] + v.y)


def _arm_angles(f):
    """(on_kol_acisi, arka_kol_acisi) — duruma gore. 0 = asagi sarkik."""
    st = f.state
    if st in (State.PUNCH, State.KICK, State.WEAPON) and f.attack is not None:
        # yukaridan ONE savurma: kol +150 (geri-yukari) -> +35 (one-asagi)
        # (+ aci = pygame'de CCW = facing yonune savurur)
        prog = max(0.0, min(1.0, f.state_frame / max(1, f.attack.total)))
        front = 150 - 115 * (prog ** 0.7)
        return front, 20
    if st == State.BLOCK:
        return -70, -60         # iki kol one (guard)
    if st == State.JUMP:
        return -35, 30
    if st == State.HITSTUN or st == State.KO:
        return 40, 55           # savrulmus
    # idle / walk / crouch: silah elde, ucu one-asagi
    bob = math.sin(f.state_frame * 0.25) * 6 if st == State.WALK else 0
    return -18 + bob, 14


def draw(surf, f, ox=0, oy=0):
    """Dovuscuyu parcalardan cizer. Basarisizsa False (renderer sprite'a duser)."""
    parts = _load_parts(f.data)
    if parts is None or f.state == State.KO or getattr(f, "victory", False):
        return False               # KO/kazanma: Kenney pozu (fallDown/cheer) daha iyi
    S = _scale_for(f)
    fc = f.facing
    flip = fc < 0
    x = f.x + ox
    feet = f.y + oy
    # KO: yatay dus
    crouch = 0.0
    if f.state == State.CROUCH:
        crouch = 22 * S
    hipy = feet - 29 * S + crouch
    sh_y = hipy - 30 * S + crouch * 0.4
    # eklemler (facing'e gore x aynala)
    def jx(dx):
        return x + fc * dx * S
    HJ = (x, hipy)
    LS = (jx(-12), sh_y)          # arka omuz (govde arkasi)
    RS = (jx(12), sh_y)           # on omuz
    front_ang, back_ang = _arm_angles(f)
    if flip:
        front_ang = -front_ang
        back_ang = -back_ang

    leg = parts.get("legBend" if f.state == State.WALK else "leg", parts["leg"])
    head, body, arm, hand = parts["head"], parts["body"], parts["arm"], parts.get("hand")

    # arka kol (govdeden once)
    _attach(surf, arm, LS, _ARM_SHOULDER, back_ang, S, flip)
    # bacaklar
    lstep = math.sin(f.state_frame * 0.3) * 10 if f.state == State.WALK else 0
    _attach(surf, leg, (jx(-7), hipy), _LEG_HIP, 4 + lstep, S, flip)
    _attach(surf, leg, (jx(7), hipy), _LEG_HIP, -4 - lstep, S, flip)
    # govde + kafa
    _attach(surf, body, (x, hipy + 2), _BODY_HIP, 0, S, flip)
    _attach(surf, head, (x, sh_y - 2 * S), _HEAD_BOT, 0, S, flip)
    # on kol + el + silah
    _attach(surf, arm, RS, _ARM_SHOULDER, front_ang, S, flip)
    wp = _wrist_world(RS, front_ang, S, flip)
    if hand is not None:
        _attach(surf, hand, wp, _HAND_C, front_ang, S, flip)
    _draw_weapon(surf, f, wp, front_ang, flip)
    return True


def _draw_weapon(surf, f, wrist, arm_angle, flip):
    key = getattr(f, "weapon_key", None)
    if not key:
        return
    try:
        bl = weapons.blade(key, 2.7)
    except Exception:
        return
    # silah kabzasi bilekte; kol asagi(0) iken silah asagi/one dogru.
    # arm_angle draw()'da facing icin zaten aynalandi -> burada TEKRAR aynalamiyoruz.
    if flip:
        bl = pygame.transform.flip(bl, True, False)   # ucu sola
        ang = 90 - arm_angle
    else:
        ang = arm_angle - 90
    hx = 0 if not flip else bl.get_width()
    hilt = V(hx, bl.get_height() / 2)
    c = V(bl.get_width() / 2, bl.get_height() / 2)
    off = (c - hilt).rotate(-ang)
    rot = pygame.transform.rotate(bl, ang)
    surf.blit(rot, rot.get_rect(center=(wrist[0] + off.x, wrist[1] + off.y)))
