"""AYARLAR ekrani: ses, tam ekran ve P1 tus atamalari.

Menu benzeri kendi kendine yeten bir dongu:
    settings_screen(screen, clock) -> str   # "back" ya da "quit"

Kontroller:
    Yukari/Asagi  : satir sec
    Sol/Sag       : secili satirin degerini degistir (ses %, tam ekran)
    ENTER         : tus atama satirinda -> "sonraki tusa bas" modu
    ESC           : geri (tus atama modundaysa atamayi iptal eder)

Her degisiklik aninda uygulanir (audio setter'lari / display modu / P1_KEYS)
ve config.save() ile assets/config.json'a yazilir.

Baglanti (main): donuste ekran degismis olabilir (tam ekran toggle), bu yuzden
cagiran taraf `screen = pygame.display.get_surface()` ile guncel yuzeyi almali.
"""

import pygame

from . import audio
from . import config
from . import controller
from . import settings
from .hud import load_font

# Satir kimlikleri (ekranda yukaridan asagiya sira).
ROW_SFX = "sfx"
ROW_MUSIC = "music"
ROW_FULLSCREEN = "fullscreen"
# tus atama satirlari: (kimlik, P1 eylem anahtari, Turkce etiket)
KEY_ROWS = [
    ("key_left", "left", "Sol"),
    ("key_right", "right", "Sağ"),
    ("key_jump", "jump", "Zıpla"),
    ("key_down", "down", "Çömel"),
    ("key_punch", "punch", "Yumruk"),
    ("key_kick", "kick", "Tekme"),
]
ROW_BACK = "back"

VOL_STEP = 0.10  # ses %10'ar degisir


def _rows():
    """Ekrandaki tum satirlarin (kimlik) sirali listesi."""
    ids = [ROW_SFX, ROW_MUSIC, ROW_FULLSCREEN]
    ids += [rid for (rid, _act, _lbl) in KEY_ROWS]
    ids.append(ROW_BACK)
    return ids


def _key_label(code) -> str:
    """pygame tus kodu -> okunur ad (buyuk harf). Bilinmezse '???'."""
    try:
        name = pygame.key.name(int(code))
    except Exception:
        name = ""
    return name.upper() if name else "???"


def _apply_fullscreen(want_full: bool):
    """Display modunu tam ekran/pencere olarak ayarlar ve yeni yuzeyi don.

    Basarisiz olursa mevcut yuzeyi (veya guvenli pencere modunu) don.
    """
    size = (settings.WIDTH, settings.HEIGHT)
    try:
        if want_full:
            return pygame.display.set_mode(size, pygame.FULLSCREEN)
        return pygame.display.set_mode(size)
    except Exception:
        surf = pygame.display.get_surface()
        return surf if surf is not None else pygame.display.set_mode(size)


def settings_screen(screen, clock) -> str:
    """Ayarlar dongusu. "back" (geri) ya da "quit" (pencere kapat) doner."""
    cfg = config.get()
    rows = _rows()
    selected = 0
    rebinding_action = None  # None degilse: bu P1 eyleme yeni tus bekleniyor
    fonts = {
        "title": load_font(70),
        "row": load_font(32),
        "help": load_font(20),
    }

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type != pygame.KEYDOWN:
                continue

            # --- tus atama modu: bir sonraki KEYDOWN yeni tus olur ----------
            if rebinding_action is not None:
                if e.key == pygame.K_ESCAPE:
                    rebinding_action = None          # iptal
                    audio.play("menu_move")
                else:
                    controller.P1_KEYS[rebinding_action] = e.key
                    cfg["p1_keys"][rebinding_action] = int(e.key)
                    config.save(cfg)
                    rebinding_action = None
                    audio.play("menu_select")
                continue

            # --- normal gezinme --------------------------------------------
            if e.key == pygame.K_ESCAPE:
                return "back"

            if e.key in (pygame.K_UP, pygame.K_w):
                selected = (selected - 1) % len(rows)
                audio.play("menu_move")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                selected = (selected + 1) % len(rows)
                audio.play("menu_move")
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                screen = _adjust(rows[selected], -1, cfg, screen)
                audio.play("menu_move")
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                screen = _adjust(rows[selected], +1, cfg, screen)
                audio.play("menu_move")
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                row = rows[selected]
                if row == ROW_BACK:
                    return "back"
                if row == ROW_FULLSCREEN:
                    screen = _adjust(row, +1, cfg, screen)  # ENTER = toggle
                    audio.play("menu_select")
                else:
                    act = _row_action(row)
                    if act is not None:               # tus atama baslat
                        rebinding_action = act
                        audio.play("menu_select")

        _draw(screen, fonts, rows, selected, cfg, rebinding_action)
        pygame.display.flip()
        clock.tick(settings.FPS)

    return "back"


def _row_action(row_id):
    """Tus atama satiri kimliginden P1 eylem anahtarini don (yoksa None)."""
    for rid, act, _lbl in KEY_ROWS:
        if rid == row_id:
            return act
    return None


def _adjust(row_id, step, cfg, screen):
    """Sol/Sag ile secili satirin degerini degistir + uygula + kaydet.

    Yeni display yuzeyini don (yalnizca tam ekran degisince degisir; digerlerinde
    gelen 'screen' aynen doner).
    """
    if row_id == ROW_SFX:
        v = _stepped(cfg["sfx_vol"], step)
        cfg["sfx_vol"] = v
        audio.set_sfx_volume(v)
        config.save(cfg)
    elif row_id == ROW_MUSIC:
        v = _stepped(cfg["music_vol"], step)
        cfg["music_vol"] = v
        audio.set_music_volume(v)
        config.save(cfg)
    elif row_id == ROW_FULLSCREEN:
        want = not bool(cfg["fullscreen"])   # sol/sag ikisi de toggle eder
        cfg["fullscreen"] = want
        screen = _apply_fullscreen(want)
        config.save(cfg)
    # tus satirlari ve "back" sol/sag'a tepki vermez
    return screen


def _stepped(value, step):
    """0..1 sesi VOL_STEP kadar degistirir; %10'luk izgaraya yuvarlar."""
    v = value + step * VOL_STEP
    if v < 0.0:
        v = 0.0
    elif v > 1.0:
        v = 1.0
    return round(v / VOL_STEP) * VOL_STEP


def _value_text(row_id, cfg, rebinding_action):
    """Satirin sag tarafinda gosterilecek deger metni."""
    if row_id == ROW_SFX:
        return f"%{int(round(cfg['sfx_vol'] * 100))}"
    if row_id == ROW_MUSIC:
        return f"%{int(round(cfg['music_vol'] * 100))}"
    if row_id == ROW_FULLSCREEN:
        return "Açık" if cfg["fullscreen"] else "Kapalı"
    act = _row_action(row_id)
    if act is not None:
        if rebinding_action == act:
            return "[ bir tuşa bas... ]"
        return _key_label(controller.P1_KEYS.get(act))
    return ""


def _label_text(row_id):
    """Satirin sol tarafindaki Turkce etiket."""
    if row_id == ROW_SFX:
        return "Efekt Sesi"
    if row_id == ROW_MUSIC:
        return "Müzik Sesi"
    if row_id == ROW_FULLSCREEN:
        return "Tam Ekran"
    if row_id == ROW_BACK:
        return "Geri"
    for rid, _act, lbl in KEY_ROWS:
        if rid == row_id:
            return f"Tuş: {lbl}"
    return row_id


def _draw(surf, fonts, rows, selected, cfg, rebinding_action):
    surf.fill(settings.SKY_TOP)
    cx = settings.WIDTH // 2

    title = fonts["title"].render("AYARLAR", True, settings.HP_MAIN)
    shadow = fonts["title"].render("AYARLAR", True, settings.BLACK)
    rect = title.get_rect(center=(cx, 90))
    surf.blit(shadow, rect.move(4, 4))
    surf.blit(title, rect)

    top = 190
    gap = 62
    for i, row_id in enumerate(rows):
        y = top + i * gap
        is_sel = i == selected
        color = settings.HP_MAIN if is_sel else settings.WHITE

        if row_id == ROW_BACK:
            # tek ortalanmis satir
            label = fonts["row"].render(_label_text(row_id), True, color)
            surf.blit(label, label.get_rect(center=(cx, y)))
            continue

        label = fonts["row"].render(_label_text(row_id), True, color)
        surf.blit(label, label.get_rect(midright=(cx - 30, y)))

        value = _value_text(row_id, cfg, rebinding_action)
        # ayarlanabilir satirlarda secince oklarla cerceve
        act = _row_action(row_id)
        arrowable = row_id in (ROW_SFX, ROW_MUSIC, ROW_FULLSCREEN)
        if is_sel and arrowable and rebinding_action is None:
            value = f"◄  {value}  ►"
        val = fonts["row"].render(value, True, color)
        surf.blit(val, val.get_rect(midleft=(cx + 30, y)))

    helps = [
        "↑/↓ Seç    ←/→ Değiştir    ENTER Tuş ata / Onayla    ESC Geri",
        "Tuş atama: ENTER'a bas, sonra atamak istediğin tuşa bas (iptal: ESC)",
    ]
    for i, h in enumerate(helps):
        t = fonts["help"].render(h, True, settings.FLOOR_LINE)
        surf.blit(t, t.get_rect(center=(cx, settings.HEIGHT - 70 + i * 28)))
