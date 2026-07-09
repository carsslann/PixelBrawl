"""Sahne (map) uretimi -- PixelBrawl.

Bu modul Kenney (CC0) `backgroundpack` varliklarindan cesitli dovus sahneleri
uretir. Iki tur sahne vardir:

  1. TAM-GORSEL sahneler: hazir 1024x1024 arka plan PNG'si genislige olceklenip
     zemin yuzeyi (dovusculerin bastigi cizgi) FLOOR_Y'ye hizalanir, alti toprak
     tonuyla doldurulur.
  2. KOMPOZE / PARALAKS sahneler: prosedurel gokyuzu gradyani + tint'lenmis
     siluet katmanlari (daglar / tepeler / bulutlar) + FLOOR_Y altina dolu zemin.

Disari acilan sozlesme (renderer/match bunlari cagirir):
  * STAGE_NAMES: list[str]
  * build_background(stage, size) -> pygame.Surface  (opak, tam cizilmis)

Bu modul SADECE pygame, os ve `from . import settings` import eder; boylece
renderer/fighter/match ile dongusel bagimlilik olusmaz. Bilinmeyen sahne veya
eksik dosyada cokmek yerine prosedurel bir gokyuzu+zemin (fallback) dondurur.
"""

import os
import pygame

from . import settings


# --------------------------------------------------------------------------
# Varlik konumu
# --------------------------------------------------------------------------
# settings.py "backgroundpack/..." gibi PROJE-KOKUNE gore rolatif yollar
# kullanir. Bu dosya <kok>/game/stages.py oldugundan proje koku bir ust dizin.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BG_DIR = os.path.join(_PROJECT_ROOT, "backgroundpack", "Backgrounds")
_EL_DIR = os.path.join(_BG_DIR, "Elements")

# Yuklenen varliklari yeniden yuklememek icin basit onbellek.
_IMG_CACHE: dict[str, "pygame.Surface | None"] = {}


def _load(path: str) -> "pygame.Surface | None":
    """Bir PNG'yi alfa ile yukler; yoksa/bozuksa None doner (cokme yok)."""
    if path in _IMG_CACHE:
        return _IMG_CACHE[path]
    surf = None
    try:
        if os.path.isfile(path):
            img = pygame.image.load(path)
            # Bir display ayarliysa convert_alpha hizli; degilse ham yuzey de calisir.
            try:
                surf = img.convert_alpha()
            except pygame.error:
                surf = img
    except (pygame.error, OSError):
        surf = None
    _IMG_CACHE[path] = surf
    return surf


def _bg(name: str) -> "pygame.Surface | None":
    return _load(os.path.join(_BG_DIR, name))


def _el(name: str) -> "pygame.Surface | None":
    return _load(os.path.join(_EL_DIR, name))


# --------------------------------------------------------------------------
# Kucuk cizim yardimcilari
# --------------------------------------------------------------------------
def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _vertical_gradient(surface, top_color, bottom_color, y0=0, y1=None):
    """[y0, y1) araligini dikey renk gecisiyle doldurur (dahil degil y1)."""
    w, h = surface.get_size()
    if y1 is None:
        y1 = h
    y0 = max(0, y0)
    y1 = min(h, y1)
    span = max(1, y1 - y0)
    for y in range(y0, y1):
        t = (y - y0) / span
        pygame.draw.line(surface, _lerp_color(top_color, bottom_color, t),
                         (0, y), (w, y))


def _three_stop_gradient(surface, c_top, c_mid, c_bot, y0=0, y1=None):
    """Uc-duraksiz yumusak dikey gecis (dikis olmadan). Orta renk tam ortada."""
    w, h = surface.get_size()
    if y1 is None:
        y1 = h
    y0 = max(0, y0)
    y1 = min(h, y1)
    span = max(1, y1 - y0)
    for y in range(y0, y1):
        t = (y - y0) / span
        if t < 0.5:
            col = _lerp_color(c_top, c_mid, t / 0.5)
        else:
            col = _lerp_color(c_mid, c_bot, (t - 0.5) / 0.5)
        pygame.draw.line(surface, col, (0, y), (w, y))


def _scaled_to_width(surf, width):
    """Bir yuzeyi en/boy oranini koruyarak verilen genislige olcekler."""
    sw, sh = surf.get_size()
    if sw == width:
        return surf
    scale = width / sw
    new_h = max(1, int(round(sh * scale)))
    # smoothscale yalnizca 24/32-bit yuzeylerde calisir; guvenli tarafta kal.
    try:
        return pygame.transform.smoothscale(surf, (width, new_h))
    except (ValueError, pygame.error):
        return pygame.transform.scale(surf, (width, new_h))


def _tinted(surf, color, alpha=255):
    """Duz-renkli bir siluet yuzeyini verilen renge boyar (alfa korunur).

    Kenney element seritleri tek-renk (183,231,250) siluetlerdir; carpma ile
    istedigimiz herhangi bir tona boyayabiliriz. Ek olarak toplu saydamlik.
    """
    out = surf.copy()
    # RGB'yi hedef renge cek (BLEND_RGBA_MULT gri-tonlama gerektirmez; siluet
    # zaten acik tek renk oldugu icin carpim istikrarli bir ton verir, ama
    # tam kontrol icin once beyaza yakinlastirip sonra carpalim).
    #  1) silueti beyazlat (RGB_MAX ile), boylece carpim = tam hedef renk
    out.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    #  2) hedef renge boya
    out.fill((color[0], color[1], color[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
    if alpha < 255:
        out.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def _darken_bottom(surface, height_px, max_alpha=110):
    """Ekranin en altina, karakterlerin one cikmasi icin yumusak koyulastirma."""
    w, h = surface.get_size()
    height_px = max(1, min(height_px, h))
    shade = pygame.Surface((w, height_px), pygame.SRCALPHA)
    for i in range(height_px):
        t = i / max(1, height_px - 1)
        a = int(max_alpha * t)
        pygame.draw.line(shade, (0, 0, 0, a), (0, i), (w, i))
    surface.blit(shade, (0, h - height_px))


def _fill_ground(surface, top_y, top_color, bottom_color, surface_line=True,
                 line_color=None):
    """FLOOR_Y altini (top_y'den ekran sonuna) dolu zemin ile doldurur."""
    w, h = surface.get_size()
    top_y = max(0, min(h, top_y))
    if top_y >= h:
        return
    _vertical_gradient(surface, top_color, bottom_color, top_y, h)
    if surface_line:
        lc = line_color if line_color is not None else _lerp_color(top_color, (255, 255, 255), 0.25)
        pygame.draw.line(surface, lc, (0, top_y), (w, top_y), 3)


# --------------------------------------------------------------------------
# Sahne tanimlari
# --------------------------------------------------------------------------
# TAM-GORSEL sahneler.
#   file:        backgroundpack/Backgrounds altindaki dosya adi
#   horizon:     kaynak gorselde ZEMIN YUZEYININ (dovusculerin bastigi cizgi,
#                yani gok->zemin-rengi gecisi; element/agac tabanlarinin oturdugu
#                yer) kaynak-y'si. Olculdu (merkez sutun taramasi).
#   ground:      FLOOR_Y altini kaplayacak toprak/cim rengi (gorselle uyumlu).
_FULL_STAGES = {
    "orman":    {"file": "backgroundColorForest.png", "horizon": 639,
                 "ground_top": (28, 176, 148), "ground_bot": (150, 78, 58)},
    "cayir":    {"file": "backgroundColorGrass.png",  "horizon": 639,
                 "ground_top": (39, 200, 128), "ground_bot": (24, 132, 86)},
    "sonbahar": {"file": "backgroundColorFall.png",   "horizon": 575,
                 "ground_top": (240, 140, 56), "ground_bot": (150, 78, 58)},
    "col":      {"file": "backgroundColorDesert.png", "horizon": 650,
                 "ground_top": (240, 224, 180), "ground_bot": (196, 168, 120)},
}

# KOMPOZE / PARALAKS sahneler.
# Her biri bir palet + katman listesi. Katmanlar arkadan one dogru cizilir.
_COMPOSITE_STAGES = {
    "daglar_gunduz":    {"builder": "mountains_day"},
    "tepeler_gunbatimi": {"builder": "hills_sunset"},
    "gece_dorukleri":   {"builder": "peaks_night"},
    "bulutlu_ova":      {"builder": "cloudy_plain"},
    "sisli_orman":      {"builder": "misty_forest"},
    "sato_alacakaranlik": {"builder": "castle_dusk"},
}

# Disari acilan sahne listesi (once tam-gorsel, sonra kompoze).
STAGE_NAMES: list[str] = list(_FULL_STAGES.keys()) + list(_COMPOSITE_STAGES.keys())


# --------------------------------------------------------------------------
# TAM-GORSEL insaci
# --------------------------------------------------------------------------
def _build_full(spec, size):
    w, h = size
    floor_y = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()

    src = _bg(spec["file"])
    ground_top = spec["ground_top"]
    ground_bot = spec["ground_bot"]

    if src is None:
        # Dosya yok -> prosedurel yedek.
        return _build_fallback(size, ground_top, ground_bot)

    scaled = _scaled_to_width(src, w)
    sw, sh = scaled.get_size()
    scale = w / src.get_width()
    # Kaynak zemin yuzeyi (horizon) FLOOR_Y'ye gelsin.
    offset_y = floor_y - int(round(spec["horizon"] * scale))

    # Gorselin ustunde bosluk kalirsa (offset_y > 0) gokyuzu rengiyle doldur.
    if offset_y > 0:
        sky_top = scaled.get_at((sw // 2, 0))
        bg.fill((sky_top[0], sky_top[1], sky_top[2]))
    bg.blit(scaled, (0, offset_y))

    # Gorselin alti FLOOR_Y'nin ustunde kaliyorsa (kisa dustuyse) altini
    # toprakla doldur; her halukarda FLOOR_Y altini garanti dolu tut.
    img_bottom = offset_y + sh
    fill_from = min(floor_y, img_bottom)
    if fill_from < h:
        _fill_ground(bg, fill_from, ground_top, ground_bot, surface_line=False)

    # Karakterlerin one cikmasi icin ekran altini hafif koyulastir.
    _darken_bottom(bg, height_px=h - floor_y + 40, max_alpha=95)
    return bg


# --------------------------------------------------------------------------
# Kompoze insaci -- ortak yardimci
# --------------------------------------------------------------------------
def _blit_layer_bottom(bg, layer_surf, tint, bottom_y, alpha=255):
    """Bir element seridini genislige olcekleyip ALT kenarini bottom_y'ye
    hizalayarak (tint'li) cizer."""
    if layer_surf is None:
        return
    w = bg.get_width()
    scaled = _scaled_to_width(layer_surf, w)
    tinted = _tinted(scaled, tint, alpha)
    y = bottom_y - tinted.get_height()
    bg.blit(tinted, (0, y))


def _blit_sprite(bg, sprite, tint, center_x, bottom_y, target_h, alpha=255):
    """Tekil bir siluet (dag tepesi vb.) yerlestirir: hedef yukseklige olcekle,
    merkez_x'e ve alt=bottom_y'ye hizala."""
    if sprite is None:
        return
    sw, sh = sprite.get_size()
    scale = target_h / sh
    new_w = max(1, int(sw * scale))
    try:
        sc = pygame.transform.smoothscale(sprite, (new_w, target_h))
    except (ValueError, pygame.error):
        sc = pygame.transform.scale(sprite, (new_w, target_h))
    tinted = _tinted(sc, tint, alpha)
    bg.blit(tinted, (int(center_x - new_w / 2), int(bottom_y - target_h)))


def _blit_strip_capped(bg, layer_surf, tint, bottom_y, max_h, alpha=255):
    """Element seridini (daglar/tepeler) once bos ust alanindan kirpar, sonra
    gorunur yuksekligi `max_h`'e sigacak sekilde dikey olarak sikistirir.

    Bu seritlerin ust kismi tamamen saydam, alt kismi dolu siluettir. Once
    saydam ust satirlari atariz (silueti kaybetmeden), sonra kalan dolu bandi
    genislige olcekleyip max_h'e dikey sigdiririz. Boylece tepe hattinin TAM
    sekli korunur ama alcak/uzak durur -- yesil ya da koyu "duvar" olusmaz.
    """
    if layer_surf is None:
        return
    w = bg.get_width()
    # Once bos (saydam) ust satirlari kirp: ilk >%2 kapsama satirini bul.
    sw0, sh0 = layer_surf.get_size()
    first_solid = 0
    for y in range(sh0):
        cnt = 0
        step = max(1, sw0 // 64)
        for x in range(0, sw0, step):
            if layer_surf.get_at((x, y))[3] > 30:
                cnt += 1
        if cnt >= 2:
            first_solid = y
            break
    content = layer_surf.subsurface((0, first_solid, sw0, sh0 - first_solid)).copy()
    scaled = _scaled_to_width(content, w)
    swh = scaled.get_height()
    if swh > max_h:
        try:
            scaled = pygame.transform.smoothscale(scaled, (w, max_h))
        except (ValueError, pygame.error):
            scaled = pygame.transform.scale(scaled, (w, max_h))
    tinted = _tinted(scaled, tint, alpha)
    bg.blit(tinted, (0, bottom_y - tinted.get_height()))


def _silhouette_band(src_name, src_top, src_bot, tint, alpha=255,
                     sky_is_light=True):
    """Tam-gorsel bir kaynaktan (or. ColorForest) net agac siluetini cikarir.

    Kaynak [src_top, src_bot) bandindan gokyuzu (acik/parlak) pikselleri saydam
    yapilir; geriye kalan koyu/doygun sekiller (agaclar, tepe hattı) tek renge
    (tint) boyanir. Boylece kompoze sahnede gercek "agac" silueti okunur.
    Dondurulen yuzey KAYNAK genisliginde ve band yuksekligindedir; cagiran
    tarafta genislige olcekler.
    """
    src = _bg(src_name)
    if src is None:
        return None
    sw = src.get_width()
    top = max(0, int(src_top))
    bot = min(src.get_height(), int(src_bot))
    if bot <= top:
        return None
    band = src.subsurface((0, top, sw, bot - top)).copy()
    try:
        band = band.convert_alpha()
    except pygame.error:
        pass
    out = pygame.Surface(band.get_size(), pygame.SRCALPHA)
    bw, bh = band.get_size()
    # Gokyuzu = acik VE mavi-agirlikli. Onu saydam birak; gerisini tint yap.
    for y in range(bh):
        for x in range(bw):
            c = band.get_at((x, y))
            if c[3] < 40:
                continue
            brightness = (c[0] + c[1] + c[2]) / 3
            blueish = c[2] >= c[0] and c[2] >= c[1] - 10
            is_sky = sky_is_light and brightness > 175 and blueish
            if not is_sky:
                out.set_at((x, y), (tint[0], tint[1], tint[2], alpha))
    return out


# --------------------------------------------------------------------------
# Kompoze sahneler
# --------------------------------------------------------------------------
def _build_mountains_day(size):
    """Gunduz: acik mavi gok, uzak daglar + tepeler, gunduz bulutlari, cim zemin."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _vertical_gradient(bg, (116, 192, 232), (206, 236, 246), 0, fy)

    # Gunduz bulutlari (ustte asili).
    _blit_layer_bottom(bg, _el("cloudLayer2.png"), (255, 255, 255), int(fy * 0.40), alpha=200)
    _blit_layer_bottom(bg, _el("cloudLayer1.png"), (250, 252, 255), int(fy * 0.26), alpha=160)

    # Uzak kar tepeli daglar (ayri zirveler) -- ufka oturur, alcak kalir.
    _blit_sprite(bg, _el("mountainC.png"), (176, 200, 224), w * 0.30, fy + 2, int(fy * 0.34))
    _blit_sprite(bg, _el("mountainA.png"), (158, 186, 214), w * 0.52, fy + 2, int(fy * 0.40))
    _blit_sprite(bg, _el("mountainB.png"), (168, 194, 220), w * 0.72, fy + 2, int(fy * 0.30))
    # Alcak uzak tepe siluet bandi (yalnizca crest gorunur).
    _blit_strip_capped(bg, _el("hillsLarge.png"), (120, 182, 138), fy + 4, max_h=120)
    # En on alcak cim tepeler.
    _blit_strip_capped(bg, _el("hills.png"), (86, 162, 106), fy + 10, max_h=90)

    # Zemin.
    _fill_ground(bg, fy, (74, 156, 100), (40, 96, 62))
    _darken_bottom(bg, height_px=h - fy + 40, max_alpha=95)
    return bg


def _build_hills_sunset(size):
    """Gun batimi: turuncu/pembe gok, tepeler siluet, sicak bulutlar, koyu zemin."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    # Tek parca, cok-duraksiz yumusak gecis (dikis olusmaz):
    # ust mor -> pembe -> ufukta sari-turuncu.
    _three_stop_gradient(bg, (64, 46, 96), (232, 120, 96), (255, 214, 140),
                         0, fy)

    # Alcak gunes (ufka yakin parlak disk) -- once cizilir, tepeler onunu keser.
    sun_r = int(w * 0.055)
    sun_y = int(fy * 0.72)
    glow = pygame.Surface((w, fy), pygame.SRCALPHA)
    # Yumusak hale: azalan alfa ile ic ice halkalar.
    for k in range(6, 0, -1):
        rr = int(sun_r * (1.0 + k * 0.32))
        aa = int(64 * (1.0 - k / 7.0))
        pygame.draw.circle(glow, (255, 224, 168, aa), (int(w * 0.5), sun_y), rr)
    bg.blit(glow, (0, 0))
    pygame.draw.circle(bg, (255, 240, 200), (int(w * 0.5), sun_y), sun_r)

    # Sicak bulutlar.
    _blit_layer_bottom(bg, _el("cloudLayer1.png"), (255, 190, 150), int(fy * 0.38), alpha=160)

    # Uzak daglar (soluk mor) + alcak tepe siluetleri (giderek koyulasan).
    _blit_sprite(bg, _el("mountainC.png"), (150, 96, 122), w * 0.62, fy + 2, int(fy * 0.34))
    _blit_sprite(bg, _el("mountainA.png"), (132, 82, 110), w * 0.34, fy + 2, int(fy * 0.28))
    _blit_strip_capped(bg, _el("hillsLarge.png"), (96, 56, 86), fy + 4, max_h=120)
    _blit_strip_capped(bg, _el("hills.png"), (64, 38, 62), fy + 10, max_h=90)

    _fill_ground(bg, fy, (58, 40, 58), (30, 20, 34), surface_line=False)
    _darken_bottom(bg, height_px=h - fy + 50, max_alpha=120)
    return bg


def _build_peaks_night(size):
    """Gece: derin lacivert gok, ay, sivri dag tepeleri, soluk bulut, koyu zemin."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _vertical_gradient(bg, (14, 18, 46), (54, 60, 104), 0, fy)

    # Ay.
    moon_x, moon_y, moon_r = int(w * 0.76), int(fy * 0.26), int(w * 0.035)
    pygame.draw.circle(bg, (232, 236, 248), (moon_x, moon_y), moon_r)
    pygame.draw.circle(bg, (210, 216, 236), (moon_x + moon_r // 3, moon_y - moon_r // 4),
                       int(moon_r * 0.85))
    # Yildizlar (deterministik serpme).
    star = (222, 226, 244)
    for i in range(70):
        sx = (i * 137 + 53) % w
        sy = (i * 89 + 17) % int(fy * 0.72)
        if (sx + sy) % 3 == 0:
            bg.set_at((sx, sy), star)
            if i % 5 == 0:
                bg.set_at((sx + 1, sy), star)

    # Soluk bulut bandi.
    _blit_layer_bottom(bg, _el("cloudLayer2.png"), (90, 100, 140), int(fy * 0.5), alpha=120)

    # Arka sira sivri tepeler (uc ayri dag), koyudan koyuya.
    _blit_sprite(bg, _el("mountainB.png"), (40, 46, 84), w * 0.20, fy + 2, int(fy * 0.55))
    _blit_sprite(bg, _el("mountainC.png"), (32, 38, 72), w * 0.52, fy + 4, int(fy * 0.72))
    _blit_sprite(bg, _el("mountainA.png"), (26, 30, 60), w * 0.82, fy + 2, int(fy * 0.60))
    # On siluet tepeler.
    _blit_layer_bottom(bg, _el("hills.png"), (18, 22, 44), fy + 8, alpha=255)

    _fill_ground(bg, fy, (24, 28, 48), (10, 12, 24))
    _darken_bottom(bg, height_px=h - fy + 50, max_alpha=130)
    return bg


def _build_cloudy_plain(size):
    """Bulutlu ova: acik gok, uzak alcak tepeler, ufukta puf-puf bulut banki, cim."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _vertical_gradient(bg, (128, 198, 234), (212, 238, 248), 0, fy)

    # Ust asili bulutlar.
    _blit_layer_bottom(bg, _el("cloudLayer2.png"), (255, 255, 255), int(fy * 0.34), alpha=200)
    _blit_layer_bottom(bg, _el("cloudLayer1.png"), (255, 255, 255), int(fy * 0.22), alpha=150)
    # Uzak soluk daglar (ufkun ustunde, hafif).
    _blit_sprite(bg, _el("mountainA.png"), (176, 206, 224), w * 0.24, fy - 30, int(fy * 0.30), alpha=200)
    _blit_sprite(bg, _el("mountainC.png"), (182, 210, 226), w * 0.78, fy - 30, int(fy * 0.26), alpha=200)
    # Uzak yesil tepeler (crest ufka yakin).
    _blit_strip_capped(bg, _el("hillsLarge.png"), (150, 196, 176), fy - 6, max_h=150)
    _blit_strip_capped(bg, _el("hills.png"), (116, 178, 146), fy + 8, max_h=120)
    # Ufka oturan puf-puf bulut banki (B serisi) -- gorunur puf sirasi.
    _blit_strip_capped(bg, _el("cloudLayerB1.png"), (250, 252, 255), fy + 4,
                       max_h=170, alpha=230)

    _fill_ground(bg, fy, (96, 172, 112), (54, 118, 74), surface_line=False)
    _darken_bottom(bg, height_px=h - fy + 40, max_alpha=90)
    return bg


def _build_misty_forest(size):
    """Sisli orman safagi: teal-pembe gok, katmanli agac siluetleri, sisli zemin."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _three_stop_gradient(bg, (86, 118, 130), (206, 168, 168), (248, 224, 208),
                         0, fy)

    # Sisli hafif gunes parlamasi (ufka yakin genis soluk disk).
    glow = pygame.Surface((w, fy), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 240, 220, 85), (int(w * 0.5), int(fy * 0.74)), int(w * 0.17))
    bg.blit(glow, (0, 0))

    # Uzak sisli tepeler (cok soluk, alcak).
    _blit_strip_capped(bg, _el("hillsLarge.png"), (182, 184, 192), fy - 24, max_h=90, alpha=160)

    # Orman agac siluetleri: ColorForest'in NET agac sekillerini gokyuzunu
    # keyleyerek siluet olarak al (2 kademe: uzak soluk + yakin koyu).
    far_trees = _silhouette_band("backgroundColorForest.png", 500, 660, (120, 132, 128), alpha=200)
    near_trees = _silhouette_band("backgroundColorForest.png", 500, 660, (60, 82, 74), alpha=255)
    if far_trees is not None:
        s = _scaled_to_width(far_trees, int(w * 1.06))
        bg.blit(s, (-int(w * 0.03), fy - int(s.get_height() * 0.72)))
    if near_trees is not None:
        s = _scaled_to_width(near_trees, w)
        bg.blit(s, (0, fy - s.get_height() + 6))
    if far_trees is None and near_trees is None:
        _blit_strip_capped(bg, _el("hills.png"), (60, 82, 74), fy + 8, max_h=100)

    # On sis serisi (alt bulut banki soluk, zeminde sis hissi).
    _blit_strip_capped(bg, _el("cloudLayerB2.png"), (238, 234, 232), fy + 24, max_h=90, alpha=150)

    _fill_ground(bg, fy, (74, 92, 78), (40, 52, 44), surface_line=False)
    _darken_bottom(bg, height_px=h - fy + 40, max_alpha=100)
    return bg


def _build_castle_dusk(size):
    """Dag alacakaranligi: mor/lacivert -> pembe gok, kademeli dag siluetleri,
    koyu zemin. (Kenney castle gorseli cok dusuk kontrast oldugundan sahne net
    dag/kale hatti icin element dag siluetleriyle kompoze edilir.)"""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _three_stop_gradient(bg, (48, 36, 78), (150, 96, 128), (226, 156, 132), 0, fy)

    # Soluk bulutlar.
    _blit_layer_bottom(bg, _el("cloudLayer2.png"), (196, 150, 170), int(fy * 0.40), alpha=140)

    # Buyuk merkez zirve + iki yan zirve (arka sira, soluk mor).
    _blit_sprite(bg, _el("mountainA.png"), (108, 78, 118), w * 0.50, fy + 4, int(fy * 0.62))
    _blit_sprite(bg, _el("mountainB.png"), (96, 70, 108), w * 0.24, fy + 4, int(fy * 0.42))
    _blit_sprite(bg, _el("mountainC.png"), (90, 66, 104), w * 0.78, fy + 4, int(fy * 0.50))
    # On sira jagged dag bandi (koyu mor), tepe hatti korunur ama alcak.
    _blit_strip_capped(bg, _el("mountains.png"), (58, 44, 74), fy + 8, max_h=150)

    _fill_ground(bg, fy, (52, 40, 60), (26, 20, 32), surface_line=False)
    _darken_bottom(bg, height_px=h - fy + 50, max_alpha=120)
    return bg


_COMPOSITE_BUILDERS = {
    "mountains_day": _build_mountains_day,
    "hills_sunset": _build_hills_sunset,
    "peaks_night": _build_peaks_night,
    "cloudy_plain": _build_cloudy_plain,
    "misty_forest": _build_misty_forest,
    "castle_dusk": _build_castle_dusk,
}


# --------------------------------------------------------------------------
# Prosedurel yedek
# --------------------------------------------------------------------------
def _build_fallback(size, ground_top=None, ground_bot=None):
    """Bilinmeyen sahne / eksik dosya icin makul gokyuzu + zemin."""
    w, h = size
    fy = settings.FLOOR_Y
    bg = pygame.Surface((w, h)).convert()
    _vertical_gradient(bg, settings.SKY_TOP, settings.SKY_BOTTOM, 0, fy)
    gt = ground_top if ground_top is not None else settings.FLOOR_COLOR
    gb = ground_bot if ground_bot is not None else _lerp_color(settings.FLOOR_COLOR, (0, 0, 0), 0.4)
    _fill_ground(bg, fy, gt, gb, line_color=settings.FLOOR_LINE)
    _darken_bottom(bg, height_px=h - fy + 40, max_alpha=95)
    return bg


# --------------------------------------------------------------------------
# Ana giris noktasi
# --------------------------------------------------------------------------
def build_background(stage: str, size: tuple[int, int]) -> "pygame.Surface":
    """`stage` sahnesini `size` boyutunda TAM cizilmis, opak yuzey olarak dondurur.

    Bilinmeyen sahne veya eksik dosyada cokmez; prosedurel bir yedek dondurur.
    """
    try:
        if stage in _FULL_STAGES:
            return _build_full(_FULL_STAGES[stage], size)
        if stage in _COMPOSITE_STAGES:
            builder = _COMPOSITE_BUILDERS[_COMPOSITE_STAGES[stage]["builder"]]
            return builder(size)
    except (pygame.error, ValueError, OSError):
        # Beklenmeyen bir varlik/cizim hatasinda bile oyun akmaya devam etsin.
        pass
    return _build_fallback(size)
