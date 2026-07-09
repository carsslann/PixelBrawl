class_name Inputs
extends RefCounted
## controller.py Inputs birebir — bir karede bir kontrolcunun urettigi girdi.

var move: int = 0        # -1 sol, 0 dur, +1 sag (ekran yonu)
var jump: bool = false
var punch: bool = false
var kick: bool = false
var down: bool = false    # comelme
var block: bool = false   # dogrudan blok (bot); insan GERI tutarak bloklar
var special: bool = false # ozel ates
