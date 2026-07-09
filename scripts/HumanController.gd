class_name HumanController
extends RefCounted
## controller.py HumanController port — klavye. Blok = rakibe gore GERI tutmak
## (fighter cozer). jump/punch/kick kenar-tetikli (bir kez), edge takibi ile.
## Ozel ates simdilik L tusu (Pygame'de insan special'i yoktu; Godot'ta ekliyoruz).

var key_left := KEY_A
var key_right := KEY_D
var key_jump := KEY_W
var key_down := KEY_S
var key_punch := KEY_J
var key_kick := KEY_K
var key_special := KEY_L

var _prev_jump := false
var _prev_punch := false
var _prev_kick := false
var _prev_special := false

func get_inputs(_me: Fighter, _opponent: Fighter) -> Inputs:
	var inp := Inputs.new()
	inp.move = (1 if Input.is_key_pressed(key_right) else 0) \
		- (1 if Input.is_key_pressed(key_left) else 0)
	inp.down = Input.is_key_pressed(key_down)

	var jn := Input.is_key_pressed(key_jump)
	var pn := Input.is_key_pressed(key_punch)
	var kn := Input.is_key_pressed(key_kick)
	var sn := Input.is_key_pressed(key_special)
	inp.jump = jn and not _prev_jump
	inp.punch = pn and not _prev_punch
	inp.kick = kn and not _prev_kick
	inp.special = sn and not _prev_special
	_prev_jump = jn
	_prev_punch = pn
	_prev_kick = kn
	_prev_special = sn
	return inp
