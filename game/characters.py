"""Karakter tanimlari.

Her karakter bir veri paketidir: fizik degerleri + saldiri verileri +
(istege bagli) sprite referansi. Yeni karakter eklemek = buraya yeni bir
CharacterData eklemek ve anahtarini CHARACTER_ORDER'a yazmak. Kod
degisikligi gerekmez; menu ve dovus sistemi CHARACTERS'tan okur.

Gorseller: Kenney "Toon Characters" (CC0) paketi, charac/ klasorunde.
Bir karaktere sprite baglamak icin SpriteRef ver (folder + prefix).
sprites.py bu referansla pozlari yukler; yuklenemezse prosedurel cizim.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpriteRef:
    folder: str    # proje kokune gore, or. "charac/Male adventurer"
    prefix: str    # dosya on eki, or. "character_maleAdventurer"
    scale: float = 1.0  # gorunur boyu data.height'in bu kati kadar yap


@dataclass(frozen=True)
class AttackData:
    name: str
    damage: int
    startup: int      # vurus oncesi hazirlik (kare)
    active: int       # vurusun isabet edebildigi pencere (kare)
    recovery: int     # vurus sonrasi toparlanma (kare)
    hitstun: int      # isabet alan rakibin kilitli kaldigi sure (kare)
    knockback: float  # isabet alan rakibin geri itilme hizi (px/kare)
    hit_w: int        # vurus kutusunun govde onunden uzanma mesafesi/genisligi
    hit_h: int        # vurus kutusu yuksekligi
    height_frac: float  # vurusun yerden yuksekligi (boy orani, 0=ayak 1=tepe)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery


@dataclass(frozen=True)
class CharacterData:
    key: str
    name: str
    color: tuple      # HUD/menu vurgusu ve prosedurel yedek cizim rengi
    width: int
    height: int
    walk_speed: float
    jump_vx: float    # ziplarken yatay hiz
    jump_vy: float    # ziplama baslangic dikey hizi (negatif = yukari)
    max_health: int
    punch: AttackData
    kick: AttackData
    sprite: SpriteRef | None = None


# Arketip sablonlari (denge kolay tutulsun diye saldirilar paylasilir) ----
def _punch(dmg, su, act, rec, hs, kb, w, h):
    return AttackData("yumruk", dmg, su, act, rec, hs, kb, w, h, 0.74)


def _kick(dmg, su, act, rec, hs, kb, w, h):
    return AttackData("tekme", dmg, su, act, rec, hs, kb, w, h, 0.46)


CHARACTERS = {
    # --- dengeli ---
    "efe": CharacterData(
        key="efe", name="EFE", color=(210, 150, 60),
        width=64, height=172, walk_speed=4.3, jump_vx=4.7, jump_vy=-18.0,
        max_health=100,
        punch=_punch(8, 5, 4, 9, 14, 6.5, 80, 28),
        kick=_kick(13, 9, 5, 14, 20, 9.0, 100, 32),
        sprite=SpriteRef("charac/Male adventurer", "character_maleAdventurer", 1.16),
    ),
    "ada": CharacterData(
        key="ada", name="ADA", color=(196, 90, 120),
        width=60, height=168, walk_speed=4.4, jump_vx=4.8, jump_vy=-18.2,
        max_health=98,
        punch=_punch(8, 5, 4, 8, 14, 6.3, 80, 28),
        kick=_kick(12, 9, 5, 13, 19, 8.6, 98, 32),
        sprite=SpriteRef("charac/Male person", "character_malePerson", 1.16),
    ),
    # --- hizli ---
    "zeynep": CharacterData(
        key="zeynep", name="ZEYNEP", color=(58, 150, 200),
        width=56, height=164, walk_speed=5.2, jump_vx=5.7, jump_vy=-18.6,
        max_health=88,
        punch=_punch(7, 4, 4, 8, 13, 6.0, 74, 26),
        kick=_kick(11, 8, 5, 12, 18, 8.0, 92, 30),
        sprite=SpriteRef("charac/Female adventurer", "character_femaleAdventurer", 1.14),
    ),
    "mira": CharacterData(
        key="mira", name="MİRA", color=(180, 96, 200),
        width=56, height=164, walk_speed=5.4, jump_vx=5.9, jump_vy=-18.8,
        max_health=85,
        punch=_punch(7, 4, 4, 7, 12, 5.8, 74, 26),
        kick=_kick(10, 7, 5, 11, 17, 7.6, 90, 30),
        sprite=SpriteRef("charac/Female person", "character_femalePerson", 1.14),
    ),
    # --- agir / tank ---
    "robo": CharacterData(
        key="robo", name="ROBO", color=(120, 130, 150),
        width=72, height=176, walk_speed=3.4, jump_vx=3.7, jump_vy=-17.6,
        max_health=118,
        punch=_punch(10, 7, 5, 11, 16, 7.6, 86, 32),
        kick=_kick(16, 12, 6, 17, 24, 11.0, 108, 36),
        sprite=SpriteRef("charac/Robot", "character_robot", 1.18),
    ),
    "goron": CharacterData(
        key="goron", name="GORON", color=(110, 168, 90),
        width=70, height=174, walk_speed=3.2, jump_vx=3.5, jump_vy=-17.4,
        max_health=124,
        punch=_punch(10, 8, 5, 12, 17, 7.8, 86, 32),
        kick=_kick(17, 13, 6, 18, 25, 11.4, 108, 36),
        sprite=SpriteRef("charac/Zombie", "character_zombie", 1.18),
    ),
}

CHARACTER_ORDER = ["efe", "ada", "zeynep", "mira", "robo", "goron"]
