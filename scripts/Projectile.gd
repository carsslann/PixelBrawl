class_name Projectile
extends RefCounted
## projectile.py port — yatay ucan animasyonlu ates topu.
## Carpisma cozumu cagiranda (Match): hitbox() ile hedef hurtbox kesisirse
## take_hit + register_hit. owner opak (kendi mermisine vurmamak icin).

var x: float
var y: float
var vx: float
var facing: int
var frames: Array
var atk: AttackData          # hasar/knockback/hitstun tasiyan sentetik saldiri
var owner                    # Fighter (opak)
var hit_w: int
var hit_h: int
var lifetime: int
var fps: int
var hits_once: bool
var age := 0
var _anim := 0.0
var frame_index := 0
var alive := true
var has_hit := false

func _init(px: float, py: float, pvx: float, pfacing: int, pframes: Array,
		patk: AttackData, powner, phit_w := 44, phit_h := 34,
		plifetime := 150, pfps := 14, phits_once := true) -> void:
	x = px
	y = py
	vx = pvx
	facing = 1 if pfacing >= 0 else -1
	frames = pframes if pframes != null else []
	atk = patk
	owner = powner
	hit_w = phit_w
	hit_h = phit_h
	lifetime = plifetime
	fps = maxi(1, pfps)
	hits_once = phits_once

func update() -> void:
	if not alive:
		return
	x += vx
	age += 1
	if not frames.is_empty():
		_anim += fps / float(Settings.FPS)
		frame_index = int(_anim) % frames.size()
	if age >= lifetime:
		alive = false
		return
	if hits_once and has_hit:
		alive = false
		return
	var half := hit_w / 2.0
	if x + half < -80.0 or x - half > Settings.WIDTH + 80.0:
		alive = false

func hitbox() -> Rect2i:
	return Rect2i(int(x - hit_w / 2.0), int(y - hit_h / 2.0), hit_w, hit_h)

func register_hit() -> void:
	has_hit = true
	if hits_once:
		alive = false

func current_frame():
	if frames.is_empty():
		return null
	return frames[clampi(frame_index, 0, frames.size() - 1)]

func draw(ci: CanvasItem, off: Vector2) -> void:
	var tex = current_frame()
	var cx := x + off.x
	var cy := y + off.y
	if tex == null:
		ci.draw_circle(Vector2(cx, cy), maxf(3.0, hit_h / 3.0), Color8(255, 210, 90))
		return
	var sz := Vector2(tex.get_width(), tex.get_height())
	if facing < 0:
		ci.draw_set_transform(Vector2(cx, cy), 0.0, Vector2(-1, 1))
		ci.draw_texture_rect(tex, Rect2(-sz.x / 2.0, -sz.y / 2.0, sz.x, sz.y), false)
		ci.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	else:
		ci.draw_texture_rect(tex, Rect2(cx - sz.x / 2.0, cy - sz.y / 2.0, sz.x, sz.y), false)
