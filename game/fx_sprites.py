"""Ates efekt sheet'lerinden mermi/patlama kareleri uretir.

Varlik: atesefekt/All_Fire_Bullet_Pixel_16x16_00.png ... _07.png
8 renk varyanti. Her sheet 640x400 = 40 sutun x 25 satir, 16x16 piksel hucre.

Grid gorsel olarak incelendi:
  * ATES TOPU (fireball): satir 15, sutun ciftleri 16-17 / 18-19 / 20-21.
    Her kare 2 hucre genisliginde (32x16): sagda parlak yuvarlak bas,
    solda savrulan alev kuyrugu -> saga giden kuyruklu ates topu (3 kare).
  * PATLAMA (explosion): satir 1, sutun 0..4 (5 kare, 16x16 tek hucre).
    Dolu ates topundan baslayip halka olup genisleyerek sonen fiery burst.

Kareler SAGA bakar (cagiran oyun sola cevirmek icin flip eder). Alfa korunur
(convert_alpha). Sonuclar (renk+olcek) cache'lenir. Dosya/eksiklik durumunda
oyun cokmez: makul prosedurel bir daire yuzeyi fallback dondurulur.

Bu modul yalnizca cizim varligi uretir; oyun mantigindan tamamen bagimsizdir.
"""

import os

import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX_DIR = os.path.join(ROOT, "atesefekt")

COLOR_COUNT = 8
CELL = 16                       # sheet hucre boyutu (piksel)
SHEET_COLS = 40
SHEET_ROWS = 25

# --- gorsel incelemeyle secilen kare konumlari ---
# Ates topu: satir 15, her kare 2 hucre genis (32x16), sol-ust sutunlari:
FIREBALL_ROW = 15
FIREBALL_COL0 = 16              # ilk karenin sol hucresi
FIREBALL_COUNT = 3             # kare sayisi (16,18,20 -> 3 kare)
FIREBALL_CELLS_W = 2           # kare genisligi (hucre)

# Patlama: satir 1, sutun 0..4 (tek hucre 16x16)
EXPLOSION_ROW = 1
EXPLOSION_COL0 = 0
EXPLOSION_COUNT = 5

# renk_index -> yuklenmis sheet Surface (convert_alpha), yoksa None
_sheet_cache: dict[int, "pygame.Surface | None"] = {}
# (fonksiyon, color_index, scale) -> kare listesi
_frames_cache: dict[tuple, list] = {}


def _sheet_path(color_index: int) -> str:
    ci = int(color_index) % COLOR_COUNT
    return os.path.join(FX_DIR, f"All_Fire_Bullet_Pixel_16x16_{ci:02d}.png")


def _load_sheet(color_index: int) -> "pygame.Surface | None":
    """Renk sheet'ini bir kez yukleyip cache'ler; hata durumunda None."""
    ci = int(color_index) % COLOR_COUNT
    if ci in _sheet_cache:
        return _sheet_cache[ci]
    sheet = None
    path = _sheet_path(ci)
    try:
        img = pygame.image.load(path)
        # convert_alpha display gerektirir; yoksa ham surface ile devam et
        try:
            img = img.convert_alpha()
        except pygame.error:
            pass
        sheet = img
    except Exception as exc:  # dosya yok / bozuk -> fallback kullanilacak
        print(f"[fx] sheet yuklenemedi: {path} ({exc})")
        sheet = None
    _sheet_cache[ci] = sheet
    return sheet


# ates topu renk cekirdegi (fallback dairesi icin) — sheet paletiyle kabaca uyumlu
_FALLBACK_CORES = [
    (255, 210, 70),   # 0 kirmizi/turuncu
    (255, 170, 60),   # 1
    (255, 120, 60),   # 2 (mavi sheet olsa da sicak cekirdek)
    (120, 210, 255),  # 3 mavi
    (255, 230, 120),  # 4 altin/sari
    (200, 255, 140),  # 5 yesil
    (200, 150, 255),  # 6 mor
    (255, 180, 200),  # 7 pembe
]


def _fallback_surface(color_index: int, scale: float, base_px: int = 16) -> pygame.Surface:
    """Sheet yoksa cizilecek basit isikli daire (oyun cokmesin diye)."""
    ci = int(color_index) % COLOR_COUNT
    core = _FALLBACK_CORES[ci]
    size = max(4, int(round(base_px * scale)))
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2.0
    r = size / 2.0
    # disdan ice birkac halka: dis sicak/yari saydam -> ic parlak
    layers = [
        (r,          (*core, 90)),
        (r * 0.72,   (*core, 170)),
        (r * 0.45,   (min(255, core[0] + 20), min(255, core[1] + 30),
                      min(255, core[2] + 40), 255)),
        (r * 0.22,   (255, 255, 245, 255)),
    ]
    for rad, col in layers:
        pygame.draw.circle(surf, col, (int(cx), int(cy)), max(1, int(rad)))
    return surf


def _scaled(surf: pygame.Surface, scale: float) -> pygame.Surface:
    if abs(scale - 1.0) < 1e-6:
        return surf.copy()
    w = max(1, int(round(surf.get_width() * scale)))
    h = max(1, int(round(surf.get_height() * scale)))
    # pixel-art: NEAREST (smoothscale bulaniklastirir)
    return pygame.transform.scale(surf, (w, h))


def cell(color_index: int, row: int, col: int) -> pygame.Surface:
    """Sheet'ten tek 16x16 hucreyi (olceksiz) dondurur (yardimci).

    Sheet yoksa/sinir disi ise saydam bos hucre dondurur.
    """
    sheet = _load_sheet(color_index)
    empty = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    if sheet is None:
        return empty
    x, y = col * CELL, row * CELL
    if x < 0 or y < 0 or x + CELL > sheet.get_width() or y + CELL > sheet.get_height():
        return empty
    try:
        sub = sheet.subsurface(pygame.Rect(x, y, CELL, CELL))
        return sub.copy()
    except Exception:
        return empty


def _block(color_index: int, row: int, col0: int, cells_w: int) -> "pygame.Surface | None":
    """Sheet'ten (cells_w * 16) x 16 boyutunda bir blok keser."""
    sheet = _load_sheet(color_index)
    if sheet is None:
        return None
    w = CELL * cells_w
    x, y = col0 * CELL, row * CELL
    if x < 0 or y < 0 or x + w > sheet.get_width() or y + CELL > sheet.get_height():
        return None
    try:
        return sheet.subsurface(pygame.Rect(x, y, w, CELL)).copy()
    except Exception:
        return None


def fireball_frames(color_index: int, scale: float = 3.0) -> list:
    """Saga giden kuyruklu ates topu animasyon kareleri (color_index 0..7).

    Kareler saga bakar ve verilen olcekle olceklenir. Sonuc cache'lenir.
    Sheet yoksa tek renk isikli daire karesi(leri) fallback olarak doner
    (bos liste DEGIL) ki oyun cizim yaparken cokmesin.
    """
    key = ("fire", int(color_index) % COLOR_COUNT, float(scale))
    cached = _frames_cache.get(key)
    if cached is not None:
        return cached

    frames: list = []
    for i in range(FIREBALL_COUNT):
        col0 = FIREBALL_COL0 + i * FIREBALL_CELLS_W
        blk = _block(color_index, FIREBALL_ROW, col0, FIREBALL_CELLS_W)
        if blk is None:
            frames = []
            break
        frames.append(_scaled(blk, scale))

    if not frames:
        # fallback: birkac kare buyuyup/parlayan daire (animasyon hissi olsun)
        base = _fallback_surface(color_index, scale, base_px=CELL * FIREBALL_CELLS_W)
        frames = [base,
                  _fallback_surface(color_index, scale * 1.06, base_px=CELL * FIREBALL_CELLS_W),
                  _fallback_surface(color_index, scale, base_px=CELL * FIREBALL_CELLS_W)]

    _frames_cache[key] = frames
    return frames


def explosion_frames(color_index: int, scale: float = 3.0) -> list:
    """Isabet patlamasi kareleri (color_index 0..7), olceklenmis, cache'li.

    Satir 1 / sutun 0..4: dolu ates topundan halkaya genisleyen fiery burst.
    Uygun satir okunamazsa fireball'un buyuyen+solan bir varyantini uretir.
    """
    key = ("boom", int(color_index) % COLOR_COUNT, float(scale))
    cached = _frames_cache.get(key)
    if cached is not None:
        return cached

    frames: list = []
    for i in range(EXPLOSION_COUNT):
        c = cell(color_index, EXPLOSION_ROW, EXPLOSION_COL0 + i)
        # bos (tamamen saydam) hucre geldiyse sheet yok demektir -> fallback
        if c.get_bounding_rect().width == 0:
            frames = []
            break
        frames.append(_scaled(c, scale))

    if not frames:
        # fallback: fireball ilk karesini buyuyerek+solarak patlama gibi goster
        fb = fireball_frames(color_index, scale)
        src = fb[0] if fb else _fallback_surface(color_index, scale)
        steps = 5
        for i in range(steps):
            grow = 1.0 + 0.5 * (i / (steps - 1))
            surf = _scaled(src, grow)
            alpha = int(255 * (1.0 - i / steps))
            surf.set_alpha(max(0, alpha))
            frames.append(surf)

    _frames_cache[key] = frames
    return frames


def clear_cache() -> None:
    """Yuklu sheet ve kare cache'lerini bosaltir ( or. video reinit sonrasi)."""
    _sheet_cache.clear()
    _frames_cache.clear()
