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

# Renk paleti (var: Color8 const-fold edilemedigi icin instance degiskeni)
var SUPER_BACK := Color8(40, 40, 58)
var SUPER_FILL := Color8(86, 190, 240)
var SUPER_FULL := Color8(250, 224, 92)
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
var HP_BORDER := Color8(240, 240, 240)
var TIMER_COLOR := Color8(250, 244, 210)
