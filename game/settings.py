"""Oyun geneli sabitler.

Butun dengeleme/ayar degerleri burada; oyun hissini degistirmek icin
once buraya bak.
"""

WIDTH = 1280
HEIGHT = 720
FPS = 60

FLOOR_Y = 620           # zeminin ekran y koordinati (ayaklarin bastigi cizgi)
STAGE_MARGIN = 30       # dovusculerin ekran kenarina yaklasabilecegi sinir
GRAVITY = 0.9           # px/kare^2
GROUND_FRICTION = 0.82  # itilme hizinin yerde kare basina sonme carpani

# Sahne arka planlari game/stages.py'de tanimli (Kenney background pack, CC0);
# match rastgele bir stages.STAGE_NAMES sahnesi secer.

ROUND_TIME = 99         # saniye
ROUNDS_TO_WIN = 2       # macı almak icin gereken round sayisi
INTRO_FRAMES = 110      # "ROUND N" + "DOVUS!" gosterim suresi
ROUND_OVER_FRAMES = 170 # round bitis pankarti suresi

CHIP_DAMAGE_RATIO = 0.15    # blok yenen hasar orani (chip damage)
BLOCK_PUSHBACK_RATIO = 0.5  # blokta geri itilme orani

# Super metre (ozel hareket icin)
SUPER_MAX = 100
SUPER_START = 60           # round basi metre (ozel hemen denenebilsin)
SUPER_GAIN_HIT = 8          # vurus VERINCE kazanilan metre
SUPER_GAIN_TAKEN = 5        # vurus YIYINCE kazanilan metre
SUPER_BACK = (40, 40, 58)
SUPER_FILL = (86, 190, 240)
SUPER_FULL = (250, 224, 92)  # metre dolunca renk

# Renk paleti
SKY_TOP = (34, 32, 52)
SKY_BOTTOM = (92, 75, 96)
FLOOR_COLOR = (52, 46, 44)
FLOOR_LINE = (130, 118, 104)
SHADOW_COLOR = (0, 0, 0, 90)
WHITE = (240, 240, 240)
BLACK = (12, 12, 14)
SKIN = (236, 198, 166)

HP_BACK = (70, 16, 16)
HP_LAG = (214, 96, 40)     # hasar sonrasi geriden gelen bar
HP_MAIN = (238, 208, 62)   # guncel can
HP_BORDER = (240, 240, 240)
TIMER_COLOR = (250, 244, 210)
