"""Secilebilir silahlar (equipments/ sheet'leri).

Her silah bir veri paketidir: stat carpanlari (tum saldirilari olcekler) +
sheet uzerindeki 32x32 hucre + efekt turu. Fighter._scale bu carpanlari
uygular; menu icon() ile gosterir; renderer blade() ile elde cizer.
"""

import os
from dataclasses import dataclass

import pygame

from . import settings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 32   # her silah sprite'i 32x32


@dataclass(frozen=True)
class WeaponData:
    key: str
    name: str
    sheet: str          # equipments/<sheet>.png
    row: int
    col: int
    damage_mult: float
    reach_mult: float
    speed_mult: float   # >1 = daha hizli (startup/recovery azalir)
    knockback_mult: float
    effect_kind: str    # "slash"|"pierce"|"heavy"|"magic"|"chop"
    blade_rot: float    # blade()'i ileri (saga) dondurmek icin aci


# Denge: kilic referans; balta/topuz agir-yavas, hancer hizli-kisa,
# mizrak uzun, asa hizli-buyu.
WEAPONS = {
    "kilic":  WeaponData("kilic",  "Kılıç",  "SWORDS1", 0, 0, 1.00, 1.00, 1.00, 1.00, "slash", -45),
    "balta":  WeaponData("balta",  "Balta",  "AXES",    0, 0, 1.35, 1.00, 0.80, 1.35, "chop",  -70),
    "hancer": WeaponData("hancer", "Hançer", "DAGGERS", 0, 0, 0.80, 0.82, 1.30, 0.90, "slash", -45),
    "mizrak": WeaponData("mizrak", "Mızrak", "SPEARS",  0, 0, 1.00, 1.40, 0.95, 1.00, "pierce", -50),
    "topuz":  WeaponData("topuz",  "Topuz",  "MACES",   0, 0, 1.20, 0.95, 0.85, 1.55, "heavy", -70),
    "asa":    WeaponData("asa",    "Asa",    "STAFFS",  0, 0, 0.90, 1.18, 1.15, 0.95, "magic", -80),
}
WEAPON_ORDER = ["kilic", "balta", "hancer", "mizrak", "topuz", "asa"]

_sheet_cache: dict = {}
_raw_cache: dict = {}
_icon_cache: dict = {}
_blade_cache: dict = {}


def _sheet(name: str):
    if name not in _sheet_cache:
        path = os.path.join(ROOT, "equipments", f"{name}.png")
        try:
            _sheet_cache[name] = pygame.image.load(path).convert_alpha()
        except Exception:
            _sheet_cache[name] = None
    return _sheet_cache[name]


def _raw(key: str):
    """Silahin ham 32x32 sprite'i (kirpilmis sinir kutusuyla)."""
    if key in _raw_cache:
        return _raw_cache[key]
    w = WEAPONS[key]
    sheet = _sheet(w.sheet)
    surf = None
    if sheet is not None:
        rect = pygame.Rect(w.col * CELL, w.row * CELL, CELL, CELL)
        if sheet.get_rect().contains(rect):
            cell = sheet.subsurface(rect).copy()
            bb = pygame.mask.from_surface(cell).get_bounding_rects()
            if bb:
                surf = cell.subsurface(bb[0].unionall(bb)).copy()
    if surf is None:   # fallback: renkli bicak
        surf = pygame.Surface((10, 26), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (200, 200, 220), [(5, 0), (9, 20), (1, 20)])
        pygame.draw.rect(surf, (120, 80, 40), (3, 20, 4, 6))
    _raw_cache[key] = surf
    return surf


def icon(key: str, size: int) -> pygame.Surface:
    """Menu ikonu: silah sprite'i size x size kutuya sigacak sekilde olceklenmis."""
    ck = (key, size)
    if ck not in _icon_cache:
        raw = _raw(key)
        w, h = raw.get_size()
        scale = min(size / w, size / h) * 0.92
        _icon_cache[ck] = pygame.transform.rotozoom(raw, 0, scale)
    return _icon_cache[ck]


def blade(key: str, scale: float = 2.5) -> pygame.Surface:
    """Elde cizim: silahi ILERI (saga) bakacak sekilde dondurup olcekler."""
    ck = (key, scale)
    if ck not in _blade_cache:
        w = WEAPONS[key]
        _blade_cache[ck] = pygame.transform.rotozoom(_raw(key), w.blade_rot, scale)
    return _blade_cache[ck]
