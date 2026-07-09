class_name HumanController
extends RefCounted
## Klavye + gamepad. Blok = rakibe gore GERI tutmak. jump/punch/kick/special
## kenar-tetikli. Dash = ileri/geri cift-tus (klavye veya kol dpad/stick).

var key_left := KEY_A
var key_right := KEY_D
var key_jump := KEY_W
var key_down := KEY_S
var key_punch := KEY_J
var key_kick := KEY_K
var key_special := KEY_L
var key_throw := KEY_I
var pad := 0            # gamepad cihaz index'i

var _frame := 0
var _pl := false
var _pr := false
var _pj := false
var _pp := false
var _pk := false
var _ps := false
var _pt := false
var _tap_dir := 0
var _tap_frame := -999

func _held_left() -> bool:
	return Input.is_key_pressed(key_left) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_LEFT) \
		or Input.get_joy_axis(pad, JOY_AXIS_LEFT_X) < -0.5

func _held_right() -> bool:
	return Input.is_key_pressed(key_right) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_RIGHT) \
		or Input.get_joy_axis(pad, JOY_AXIS_LEFT_X) > 0.5

func get_inputs(_me: Fighter, _opponent: Fighter) -> Inputs:
	_frame += 1
	var inp := Inputs.new()
	var left := _held_left()
	var right := _held_right()
	var down := Input.is_key_pressed(key_down) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_DOWN) \
		or Input.get_joy_axis(pad, JOY_AXIS_LEFT_Y) > 0.5
	var jump := Input.is_key_pressed(key_jump) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_Y) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_UP) \
		or Input.get_joy_axis(pad, JOY_AXIS_LEFT_Y) < -0.5
	var punch := Input.is_key_pressed(key_punch) or Input.is_joy_button_pressed(pad, JOY_BUTTON_A)
	var kick := Input.is_key_pressed(key_kick) or Input.is_joy_button_pressed(pad, JOY_BUTTON_B)
	var special := Input.is_key_pressed(key_special) or Input.is_joy_button_pressed(pad, JOY_BUTTON_X)
	var throw := Input.is_key_pressed(key_throw) \
		or Input.is_joy_button_pressed(pad, JOY_BUTTON_RIGHT_SHOULDER) \
		or (punch and kick)

	inp.move = (1 if right else 0) - (1 if left else 0)
	inp.down = down
	inp.jump = jump and not _pj
	inp.punch = punch and not _pp
	inp.kick = kick and not _pk
	inp.special = special and not _ps
	inp.throw = throw and not _pt

	# dash: ayni yone kisa surede iki kez basma
	var l_edge := left and not _pl
	var r_edge := right and not _pr
	if l_edge or r_edge:
		var dir := 1 if r_edge else -1
		if dir == _tap_dir and _frame - _tap_frame <= Settings.DASH_TAP_WINDOW:
			inp.dash = dir
			_tap_dir = 0
		else:
			_tap_dir = dir
			_tap_frame = _frame

	_pl = left
	_pr = right
	_pj = jump
	_pp = punch
	_pk = kick
	_ps = special
	_pt = throw
	return inp
