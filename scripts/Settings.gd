extends Node
## settings.py birebir port — oyun geneli sabitler (autoload adi: Settings).
## Renkler Color8 (0-255) ile; Pygame RGB tuple'lariyla ayni degerler.

const WIDTH := 1280
const HEIGHT := 720
const FPS := 60

const FLOOR_Y := 620            # zeminin ekran y'si (ayaklarin bastigi cizgi)
const STAGE_MARGIN := 30
const GRAVITY := 0.9            # px/kare^2
const GROUND_FRICTION := 0.82

const ROUND_TIME := 99          # saniye
const ROUNDS_TO_WIN := 2
const INTRO_FRAMES := 110
const ROUND_OVER_FRAMES := 170

const CHIP_DAMAGE_RATIO := 0.15
const BLOCK_PUSHBACK_RATIO := 0.5

# Super metre
const SUPER_MAX := 100
const SUPER_GAIN_HIT := 7
const SUPER_GAIN_TAKEN := 4

# Dalga 1: hareket & hucum
const DASH_SPEED := 12.0
const DASH_FRAMES := 12
const BACKDASH_IFRAMES := 8
const DASH_TAP_WINDOW := 14      # cift-tus penceresi (kare)
const WAKEUP_IFRAMES := 12       # yerden kalkista dokunulmazlik
const RECOVER_DELAY := 80        # son hasardan sonra geri kazanim baslar (kare)
const RECOVER_RATE := 22         # her N karede 1 can geri
const COUNTER_DMG := 1.35        # counter-hit hasar carpani
const COUNTER_HITSTUN := 1.4     # counter-hit hitstun carpani

# Dalga 2: savunma katmani
const GUARD_MAX := 100
const GUARD_DRAIN := 10          # blok basina temel guard tuketimi (+hasar)
const GUARD_REGEN_DELAY := 55
const GUARD_REGEN := 1
const STUN_MAX := 70
const STUN_PER_HIT := 22
const STUN_DECAY_DELAY := 110
const STUN_DECAY := 1
const DIZZY_FRAMES := 120        # ~2 saniye hareket kilidi (stun)
const PARRY_WINDOW := 5          # blok baslangicindan sonra bu kadar kare = parry
const ARMOR_HITS := 1
const THROW_RANGE := 26.0
const THROW_DAMAGE := 15
const THROW_HITSTUN := 30

# Renk paleti (var: Color8 const-fold edilemedigi icin instance degiskeni)
var SUPER_BACK := Color8(40, 40, 58)
var SUPER_FILL := Color8(86, 190, 240)
var SUPER_FULL := Color8(250, 224, 92)
var GUARD_BACK := Color8(30, 44, 40)
var GUARD_FILL := Color8(120, 220, 160)
var GUARD_LOW := Color8(240, 110, 80)
var SKY_TOP := Color8(34, 32, 52)
var SKY_BOTTOM := Color8(92, 75, 96)
var FLOOR_COLOR := Color8(52, 46, 44)
var FLOOR_LINE := Color8(130, 118, 104)
var SHADOW_COLOR := Color8(0, 0, 0, 90)
var WHITE := Color8(240, 240, 240)
var BLACK := Color8(12, 12, 14)
var SKIN := Color8(236, 198, 166)
var HP_BACK := Color8(70, 16, 16)
var HP_LAG := Color8(214, 96, 40)
var HP_MAIN := Color8(238, 208, 62)
var HP_RECOVER := Color8(120, 120, 138)
var HP_BORDER := Color8(240, 240, 240)
var TIMER_COLOR := Color8(250, 244, 210)
