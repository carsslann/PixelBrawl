"""Karakter tanimlari.

Her karakter bir veri paketidir: fizik degerleri + saldiri verileri +
(istege bagli) sprite referansi. Yeni karakter eklemek = buraya yeni bir
CharacterData eklemek ve anahtarini CHARACTER_ORDER'a yazmak. Kod
degisikligi gerekmez; menu ve dovus sistemi CHARACTERS'tan okur.

Gorseller: Kenney "Toon Characters" (CC0) paketi, charac/ klasorunde.
Bir karaktere sprite baglamak icin SpriteRef ver (folder + prefix).
sprites.py bu referansla pozlari yukler; yuklenemezse prosedurel cizim.
"""

import dataclasses
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
    guard: str = "high"     # "high"=her blok, "low"=sadece cömel-blok, "overhead"=sadece ayakta blok
    knockdown: bool = False  # isabet rakibi yere serer (uzun hitstun)
    chain: int = 1          # zincir kademesi; kanser sadece daha yuksek kademeye
    airborne: bool = False  # havada yapilan saldiri (hava fizigi uygulanir)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery


@dataclass(frozen=True)
class SpecialSpec:
    """Karaktere ozel ates (projectile) hareketi."""
    color: int          # atesefekt renk index'i (0..7)
    damage: int
    speed: float        # merminin yatay hizi (px/kare)
    cast: int           # kac karede mermi cikar
    recovery: int       # cikis sonrasi toparlanma
    meter_cost: int
    knockback: float
    hitstun: int
    hit_w: int = 48
    hit_h: int = 40

    @property
    def total(self) -> int:
        return self.cast + self.recovery


def _special(color, damage, speed, cast, recovery, cost, knockback, hitstun):
    return SpecialSpec(color, damage, speed, cast, recovery, cost, knockback, hitstun)


@dataclass(frozen=True)
class WeaponSpec:
    """Karaktere ozel yakin-mesafe SILAH hareketi (mermi degil, vurus kutulu)."""
    attack: "AttackData"
    meter_cost: int
    anti_air: bool = False   # yukari vurur + kullaniciyi hafif havalandirir
    lunge: float = 0.0       # ileri atilma hizi


def _weapon(name, dmg, su, act, rec, hs, kb, w, h, hf, cost,
            anti_air=False, lunge=0.0, guard="high"):
    return WeaponSpec(
        AttackData(name, dmg, su, act, rec, hs, kb, w, h, hf, guard=guard, chain=3),
        cost, anti_air, lunge)


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
    special: SpecialSpec | None = None
    weapon: WeaponSpec | None = None

    # --- turetilmis saldirilar (comelme / hava) --------------------------
    # Temel yumruk/tekmeden hesaplanir; ayri veri tutmaya gerek yok.
    @property
    def crouch_punch(self) -> AttackData:
        return dataclasses.replace(
            self.punch, name="alçak yumruk", height_frac=0.30,
            recovery=max(6, self.punch.recovery - 2), guard="high", chain=1)

    @property
    def sweep(self) -> AttackData:  # comel + tekme = supurme (yere serer)
        return dataclasses.replace(
            self.kick, name="süpürme", height_frac=0.14,
            hit_w=self.kick.hit_w + 8, knockback=self.kick.knockback * 0.6,
            recovery=self.kick.recovery + 4, guard="low", knockdown=True, chain=2)

    @property
    def jump_punch(self) -> AttackData:
        # hava saldirilari: uzun/genis vurus kutusu, inis boyunca aktif kalir
        # (jump-in); overhead -> yalnizca ayakta blok keser.
        return dataclasses.replace(
            self.punch, name="hava yumruk", height_frac=0.50,
            hit_h=self.punch.hit_h + 42, guard="overhead", airborne=True, chain=1)

    @property
    def jump_kick(self) -> AttackData:
        return dataclasses.replace(
            self.kick, name="hava tekme", height_frac=0.48,
            hit_w=self.kick.hit_w + 6, hit_h=self.kick.hit_h + 42,
            guard="overhead", airborne=True, chain=2)


# Arketip sablonlari (denge kolay tutulsun diye saldirilar paylasilir) ----
def _punch(dmg, su, act, rec, hs, kb, w, h):
    return AttackData("yumruk", dmg, su, act, rec, hs, kb, w, h, 0.74, chain=1)


def _kick(dmg, su, act, rec, hs, kb, w, h):
    return AttackData("tekme", dmg, su, act, rec, hs, kb, w, h, 0.46, chain=2)


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

# Karaktere ozel ates (kullanicinin renk/ozel tablosu):
# efe=altin(0) ada=bordo(7) zeynep=mavi(2) mira=mor(5) robo=celik(6) goron=yesil(3)
_SPECIALS = {
    "efe":    _special(0, 14, 9.0,  14, 20, 50, 7.0, 18),
    "ada":    _special(7, 14, 9.0,  14, 20, 50, 7.0, 18),
    "zeynep": _special(2, 10, 13.0, 10, 16, 40, 5.5, 14),
    "mira":   _special(5, 11, 12.0, 11, 17, 42, 6.0, 15),
    "robo":   _special(6, 19, 6.5,  18, 24, 55, 9.5, 22),
    "goron":  _special(3, 16, 7.5,  16, 22, 52, 8.5, 20),
}
# Karaktere ozel SILAH (↓ ← + K). efe/robo/goron = yukselen anti-air,
# ada/mira = ileri hilal yayi, zeynep = hizli atilma kesigi.
_WEAPONS = {
    "efe":    _weapon("alev yumruk", 16, 6, 6, 20, 20, 8.0, 72, 96, 0.70, 40, anti_air=True),
    "ada":    _weapon("hilal", 15, 8, 6, 18, 20, 8.0, 122, 46, 0.50, 40, lunge=3.0),
    "zeynep": _weapon("hızlı kesik", 12, 5, 5, 14, 16, 6.0, 106, 40, 0.50, 35, lunge=7.0),
    "mira":   _weapon("çift hilal", 13, 6, 6, 16, 17, 7.0, 112, 44, 0.50, 38, lunge=4.5),
    "robo":   _weapon("şarj vuruş", 20, 10, 6, 24, 24, 11.0, 80, 104, 0.66, 50, anti_air=True),
    "goron":  _weapon("alev sütunu", 18, 9, 7, 22, 22, 10.0, 76, 116, 0.60, 48, anti_air=True),
}
CHARACTERS = {k: dataclasses.replace(v, special=_SPECIALS[k], weapon=_WEAPONS[k])
              for k, v in CHARACTERS.items()}

CHARACTER_ORDER = ["efe", "ada", "zeynep", "mira", "robo", "goron"]

# Karaktere ozel ornek kombolar (N7) — hareket listesi ekraninda gosterilir
_COMBOS = {
    "efe":    [("Temel zincir", "J → K"), ("Jump-in", "(hava)J → J → K"),
               ("Anti-air", "↓←K yükselen")],
    "ada":    [("Hilal bitiris", "J → K → ↓←K"), ("Ateşle bitir", "J → K → ↓→J")],
    "zeynep": [("Hızlı zincir", "J → J → K"), ("Atılma", "↓J → ↓←K"),
               ("Ateş baskı", "J → ↓→J")],
    "mira":   [("Çift hilal", "J → ↓←K"), ("Jump-in", "(hava)K → J → ↓K")],
    "robo":   [("Ağır zincir", "J → K"), ("EX ateş", "(dolu)↓→J")],
    "goron":  [("Ağır bitiris", "J → ↓K süpürme"), ("Alev sütunu", "↓←K")],
}

# fx renk index -> Turkce ad (ozel ates)
COLOR_NAMES = {0: "altın", 7: "bordo", 2: "mavi", 5: "mor", 6: "çelik", 3: "yeşil"}


def character_moves(key: str):
    """(hareketler, kombolar) — move-list ekrani icin. hareket = (ad, komut)."""
    c = CHARACTERS[key]
    color = COLOR_NAMES.get(c.special.color, "") if c.special else ""
    moves = [
        ("Yürü", "A / D"),
        ("Zıpla / Çömel", "W / S"),
        ("Blok", "geri tut"),
        ("Yumruk / Tekme", "J / K"),
        ("Alçak / Süpürme", "S+J / S+K"),
        ("Hava saldırı", "(havada) J / K"),
        ("Atma (bloklanamaz)", "J + K"),
        (f"Özel ateş ({color})", "↓ → + J"),
        (f"Özel silah ({c.weapon.attack.name})" if c.weapon else "Özel silah", "↓ ← + K"),
        ("EX ateş (dolu metre)", "↓ → + J"),
    ]
    return moves, _COMBOS.get(key, [])
