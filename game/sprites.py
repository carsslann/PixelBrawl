"""Sprite yukleme ve animasyon secimi.

Kenney "Toon Characters" paketi poz basina AYRI PNG kullanir
(idle.png, walk0..walk7.png, attack0..2.png, kick.png, duck.png,
hit.png, hurt.png, fallDown.png ...). Bu modul Fighter durumlarini bu
pozlara eslestirir, hepsini tek bir olcekle yukler ve durum/kareye gore
do"gru pozu dondurur.

Cizim katmani (renderer) yalnizca frame_for() cagirir; sprite yuklenemezse
None doner ve renderer prosedurel cizime duser. Oyun mantigi sprite'tan
tamamen habersizdir.
"""

import os

import pygame

from . import settings
from .fighter import State

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fighter durumu -> (Kenney poz adlari, saniyedeki kare, dongu?)
# Birden fazla poz = animasyon; tek poz = sabit duruş.
STATE_POSES = {
    State.IDLE:    (["idle"], 1, False),
    State.WALK:    (["walk0", "walk1", "walk2", "walk3",
                    "walk4", "walk5", "walk6", "walk7"], 14, True),
    State.CROUCH:  (["duck"], 1, False),
    State.BLOCK:   (["hold"], 1, False),   # ayakta guard (kollar önde)
    State.JUMP:    (["jump"], 1, False),
    State.HITSTUN: (["hit"], 1, False),
    State.KO:      (["hurt", "fallDown", "down"], 9, False),
    # PUNCH/KICK ozel: kareler saldirinin startup->recovery suresine yayilir
    State.PUNCH:   (["attack0", "attack1", "attack2"], 0, False),
    State.KICK:    (["attack1", "kick", "kick"], 0, False),
}
# yere serilince (supurme) gosterilecek pozlar
KNOCKDOWN_POSES = ["hurt", "fallDown"]

# Kenney pozlarinin gorunur govde yuksekligi ~ canvas'in bu orani kadar
# (idle icerigi 96x128 canvasta y=33..128). Olcegi buna gore normalize
# ederiz ki farkli karakterler ayni ekran boyunda gorunsun.
_CONTENT_HEIGHT_RATIO = 95 / 128


class Animator:
    def __init__(self, poses: dict):
        self.poses = poses  # State -> (frames_right, frames_left, fps, loop)

    def frame_for(self, fighter) -> pygame.Surface | None:
        if getattr(fighter, "victory", False) and "victory" in self.poses:
            right, left, fps, _ = self.poses["victory"]
            idx = int(fighter.state_frame * fps / settings.FPS) % len(right)
            return right[idx] if fighter.facing >= 0 else left[idx]
        state = fighter.state
        if state == State.HITSTUN and getattr(fighter, "knocked_down", False):
            state = State.KO   # yere serilme: KO (hurt/fallDown) pozlarini kullan
        entry = self.poses.get(state) or self.poses.get(State.IDLE)
        if entry is None:
            return None
        right, left, fps, loop = entry
        n = len(right)
        if n == 0:
            return None

        if fighter.state in (State.PUNCH, State.KICK) and fighter.attack is not None:
            # kareleri saldirinin toplam suresine yay (startup..recovery)
            progress = min(0.999, fighter.state_frame / max(1, fighter.attack.total))
            idx = int(progress * n)
        elif fps <= 0 or n == 1:
            idx = 0
        else:
            idx = int(fighter.state_frame * fps / settings.FPS)
            idx = idx % n if loop else min(idx, n - 1)

        idx = max(0, min(n - 1, idx))
        return right[idx] if fighter.facing >= 0 else left[idx]


def load_animator(char_data) -> Animator | None:
    """characters.py'deki sprite referansina gore animator kurar.

    Basarisizlikta None doner (renderer prosedurel cizime duser).
    """
    ref = getattr(char_data, "sprite", None)
    if not ref:
        return None
    folder = os.path.join(ROOT, *ref.folder.split("/"))
    poses_dir = os.path.join(folder, "PNG", "Poses")
    if not os.path.isdir(poses_dir):
        print(f"[sprite] klasor yok: {poses_dir} -> prosedurel cizim")
        return None

    try:
        target_h = char_data.height * ref.scale
        scale = None  # ilk yuklenen kareden hesaplanir, hepsine ayni uygulanir
        built: dict = {}
        for state, (names, fps, loop) in STATE_POSES.items():
            frames = []
            for name in names:
                path = os.path.join(poses_dir, f"{ref.prefix}_{name}.png")
                if not os.path.isfile(path):
                    continue
                img = pygame.image.load(path).convert_alpha()
                if scale is None:
                    scale = target_h / (img.get_height() * _CONTENT_HEIGHT_RATIO)
                img = pygame.transform.rotozoom(img, 0, scale)
                frames.append(img)
            if not frames:
                continue
            flipped = [pygame.transform.flip(f, True, False) for f in frames]
            built[state] = (frames, flipped, fps, loop)
        if State.IDLE not in built:
            print(f"[sprite] '{ref.prefix}' idle pozu yok -> prosedurel cizim")
            return None
        # kazanma pozu (cheer0/cheer1) — durum degil, victory bayragiyla secilir
        if scale is not None:
            vf = []
            for name in ("cheer0", "cheer1"):
                path = os.path.join(poses_dir, f"{ref.prefix}_{name}.png")
                if os.path.isfile(path):
                    img = pygame.image.load(path).convert_alpha()
                    vf.append(pygame.transform.rotozoom(img, 0, scale))
            if vf:
                built["victory"] = (vf, [pygame.transform.flip(f, True, False)
                                         for f in vf], 3, True)
        return Animator(built)
    except Exception as exc:  # bozuk/eksik dosya oyunu dusurmesin
        print(f"[sprite] '{getattr(ref, 'prefix', '?')}' yuklenemedi: {exc}")
        return None


def load_idle_preview(char_data, target_h: int) -> pygame.Surface | None:
    """Menu onizlemesi icin tek idle karesini verilen boyda yukler."""
    ref = getattr(char_data, "sprite", None)
    if not ref:
        return None
    path = os.path.join(ROOT, *ref.folder.split("/"),
                        "PNG", "Poses", f"{ref.prefix}_idle.png")
    if not os.path.isfile(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        scale = target_h / (img.get_height() * _CONTENT_HEIGHT_RATIO)
        return pygame.transform.rotozoom(img, 0, scale)
    except Exception:
        return None
