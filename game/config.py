"""Kalici ayarlar: ses seviyeleri, tam ekran ve P1 tus atamalari.

JSON dosyasi `assets/config.json`'a yazilir/okunur. Dosya yoksa veya bozuksa
VARSAYILANLARLA devam edilir (asla exception firlatilmaz -> oyun cökmez).

Sozlesme (main.py / settings_screen.py bu isimleri cagirir):
    config.load()  -> dict   # JSON oku, audio + controller'a UYGULA, dict don
    config.save(cfg)         # dict'i JSON'a yaz (klasor yoksa olustur)
    config.get()   -> dict   # bellekteki mevcut cfg (load() cagrilmadiysa vars.)

Alanlar:
    sfx_vol    (float 0..1, vars. 0.8)
    music_vol  (float 0..1, vars. 0.5)
    fullscreen (bool, vars. False)
    p1_keys    (isim->pygame tus kodu; vars. controller.P1_KEYS kopyasi)

Not: `fullscreen` burada YALNIZCA saklanir; asil display moduna gecis
settings_screen / main tarafinda `pygame.display.set_mode(...)` ile yapilir.
Boylece config modulu pygame display durumundan bagimsiz kalir.
"""

import json
import os

from . import audio
from . import controller

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "assets")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# P1 eylem isimleri (kayit/okuma icin sabit kume).
P1_ACTIONS = ("left", "right", "jump", "down", "punch", "kick")


def _default_p1_keys() -> dict:
    """controller.P1_KEYS'in su anki halinden {isim: tus_kodu} kopyasi."""
    return {name: int(controller.P1_KEYS[name]) for name in P1_ACTIONS}


def defaults() -> dict:
    """Yeni bir varsayilan cfg sozlugu (her cagride taze kopya)."""
    return {
        "sfx_vol": 0.8,
        "music_vol": 0.5,
        "fullscreen": False,
        "p1_keys": _default_p1_keys(),
    }


# Bellekte tutulan tek cfg (load()/save() bunu gunceller).
_cfg = defaults()


def _clamp01(v, fallback):
    """v'yi 0..1 float'a sikistir; sayi degilse fallback don."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return fallback
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _sanitize(raw) -> dict:
    """Ham (JSON'dan gelen) veriyi guvenli/tam bir cfg'ye normalize eder.

    Eksik/bozuk alanlar varsayilanla doldurulur; fazlalik alanlar atilir.
    p1_keys icinde eksik/gecersiz tus varsa o eylem varsayilana duser.
    """
    cfg = defaults()
    if not isinstance(raw, dict):
        return cfg

    cfg["sfx_vol"] = _clamp01(raw.get("sfx_vol"), cfg["sfx_vol"])
    cfg["music_vol"] = _clamp01(raw.get("music_vol"), cfg["music_vol"])
    cfg["fullscreen"] = bool(raw.get("fullscreen", cfg["fullscreen"]))

    keys = dict(cfg["p1_keys"])  # varsayilanlarla basla
    raw_keys = raw.get("p1_keys")
    if isinstance(raw_keys, dict):
        for name in P1_ACTIONS:
            val = raw_keys.get(name)
            try:
                keys[name] = int(val)
            except (TypeError, ValueError):
                pass  # gecersizse varsayilan tus kalir
    cfg["p1_keys"] = keys
    return cfg


def _apply(cfg) -> None:
    """cfg'yi calisan sisteme uygula: ses seviyeleri + P1 tus atamalari.

    Ses: audio.set_sfx_volume / set_music_volume (0..1).
    Tuslar: controller.P1_KEYS'i YERINDE gunceller (HumanController varsayilan
    olarak bu dict'i okur; boylece yeni maclar yeni tuslarla baslar).
    Tam ekran display gecisi burada YAPILMAZ (cagiran tarafin isi).
    """
    try:
        audio.set_sfx_volume(cfg["sfx_vol"])
        audio.set_music_volume(cfg["music_vol"])
    except Exception:
        pass  # ses uygulanamasa da ayar okumasi surmeli

    try:
        for name in P1_ACTIONS:
            controller.P1_KEYS[name] = int(cfg["p1_keys"][name])
    except Exception:
        pass


def load() -> dict:
    """assets/config.json'u oku, dogrula, sisteme uygula ve cfg dict'i don.

    Dosya yoksa/bozuksa varsayilanlarla devam eder (crash yok). Sonuc bellekte
    _cfg olarak tutulur; get() ayni sozlugu doner.
    """
    global _cfg
    raw = None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        raw = None
    except (OSError, ValueError):
        # bozuk JSON / okuma hatasi -> varsayilanlar
        raw = None

    _cfg = _sanitize(raw)
    _apply(_cfg)
    return _cfg


def save(cfg=None) -> bool:
    """cfg'yi (verilmezse bellekteki _cfg) assets/config.json'a yaz.

    Klasor yoksa olusturur. Herhangi bir hatada SESSIZCE gecer (False don).
    Yazilan sozluk normalize edilerek bellekte _cfg olarak da guncellenir.
    """
    global _cfg
    _cfg = _sanitize(cfg if cfg is not None else _cfg)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(_cfg, fh, indent=2)
        return True
    except Exception:
        return False  # disk/izin hatasi oyunu dusurmesin


def get() -> dict:
    """Bellekteki mevcut cfg sozlugu (load() cagrilmadiysa varsayilanlar)."""
    return _cfg
