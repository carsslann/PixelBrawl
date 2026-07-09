class_name EffectSystem
extends RefCounted
## effects.py port — kivilcim / hasar sayisi / impact halkasi / ambient /
## ekran sarsintisi / KO flasi / kombo pankarti. Cizim _draw'dan cagrilir.

const HITSTOP_NORMAL := 4
const HITSTOP_HEAVY := 7
const HITSTOP_BLOCK := 3

# ---------------------------------------------------------------- parcaciklar
class Particle:
	var x: float
	var y: float
	var vx: float
	var vy: float
	var life: int
	var max_life: int
	var size: float
	var color: Color
	var grav: float
	func _init(px, py, pvx, pvy, plife, psize, pcolor, pgrav := 0.0) -> void:
		x = px; y = py; vx = pvx; vy = pvy
		life = plife; max_life = plife; size = psize; color = pcolor; grav = pgrav
	func update() -> void:
		x += vx; y += vy; vy += grav; life -= 1
	func draw(ci: CanvasItem, off: Vector2) -> void:
		if life <= 0: return
		var t := life / float(max_life)
		ci.draw_circle(Vector2(x + off.x, y + off.y), maxf(1.0, size * t), color)

class ImpactRing:
	var x: float
	var y: float
	var life: int
	var max_life: int
	var r0: float
	var r1: float
	var color: Color
	var w0: float
	func _init(px, py, pcolor, pr0, pr1, plife, pw0) -> void:
		x = px; y = py; color = pcolor; r0 = pr0; r1 = pr1
		life = plife; max_life = plife; w0 = pw0
	func update() -> void:
		life -= 1
	func draw(ci: CanvasItem, off: Vector2) -> void:
		if life <= 0: return
		var p := 1.0 - (life / float(max_life))
		var ease := 1.0 - (1.0 - p) * (1.0 - p)
		var r := r0 + (r1 - r0) * ease
		if r < 1: return
		var t := life / float(max_life)
		var alpha := 0.86 * t
		var width := maxf(1.0, w0 * t)
		var c := Vector2(x + off.x, y + off.y)
		ci.draw_arc(c, r, 0.0, TAU, 40, Color(color.r, color.g, color.b, alpha), width)
		var r2 := r * 0.62
		if r2 > 1:
			ci.draw_arc(c, r2, 0.0, TAU, 32, Color(color.r, color.g, color.b, alpha * 0.55), maxf(1.0, width * 0.5))
		if p < 0.35:
			var fa := 0.8 * (1.0 - p / 0.35)
			ci.draw_circle(c, maxf(2.0, r0 * (1.0 - p / 0.35) + 2.0), Color(1, 1, 1, fa))

class AmbientParticle:
	var x: float
	var y: float
	var vx: float
	var vy: float
	var life: int
	var max_life: int
	var size: float
	var color: Color
	var sway: float
	var phase: float
	func _init(px, py, pvx, pvy, plife, psize, pcolor, psway, pphase) -> void:
		x = px; y = py; vx = pvx; vy = pvy
		life = plife; max_life = plife; size = psize; color = pcolor
		sway = psway; phase = pphase
	func update() -> void:
		phase += 0.06
		x += vx + sin(phase) * sway
		y += vy
		life -= 1
	func draw(ci: CanvasItem, off: Vector2) -> void:
		if life <= 0: return
		var t := life / float(max_life)
		var fade := minf(1.0, minf(t * 4.0, (1.0 - t) * 8.0 + 0.15))
		var alpha := 0.78 * clampf(fade, 0.0, 1.0)
		if alpha <= 0: return
		ci.draw_circle(Vector2(x + off.x, y + off.y), maxf(1.0, size),
			Color(color.r, color.g, color.b, alpha))

class DamageNumber:
	var x: float
	var y: float
	var vy: float
	var life: int
	var max_life: int
	var text: String
	var color: Color
	var size: int
	func _init(px, py, ptext, pcolor, psize) -> void:
		x = px; y = py; vy = -1.6; life = 46; max_life = 46
		text = ptext; color = pcolor; size = psize
	func update() -> void:
		y += vy; vy += 0.045; life -= 1
	func draw(ci: CanvasItem, off: Vector2) -> void:
		if life <= 0: return
		var alpha := clampf((life / float(max_life)) * 2.2, 0.0, 1.0)
		var fs := size
		if life > max_life - 6:
			fs = int(size * (0.6 + 0.4 * (max_life - life) / 6.0))
		var font := ThemeDB.fallback_font
		var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		var p := Vector2(x + off.x - w / 2.0, y + off.y)
		ci.draw_string(font, p + Vector2(2, 2), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0, 0, 0, alpha))
		ci.draw_string(font, p, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(color.r, color.g, color.b, alpha))

# ---------------------------------------------------------------- sistem
var particles: Array = []
var numbers: Array = []
var rings: Array = []
var ambient: Array = []
var ambient_kind := "none"
var _ambient_timer := 0
var vignette := false
var shake := 0.0
var flash := 0
var combo = null      # [count, life, left_side]

func reset() -> void:
	particles.clear(); numbers.clear(); rings.clear(); ambient.clear()
	_ambient_timer = 0; vignette = false; shake = 0.0; flash = 0; combo = null

func add_shake(amount: float) -> void:
	shake = maxf(shake, amount)

func set_ambient(kind: String) -> void:
	if kind not in ["none", "leaves", "dust", "snow", "embers"]:
		kind = "none"
	ambient_kind = kind

func set_slowmo_vignette(on: bool) -> void:
	vignette = on

func spawn_hit(x: float, y: float, damage: int, blocked := false, heavy := false, ko := false) -> void:
	if blocked:
		_spark(x, y, Color8(150, 200, 255), 8, 4.0)
		numbers.append(DamageNumber.new(x, y - 30, "BLOK", Color8(150, 200, 255), 34))
		add_shake(4.0)
		return
	var color := Color8(255, 90, 70) if (heavy or ko) else Color8(255, 210, 70)
	_spark(x, y, color, 14 if heavy else 10, 7.0 if heavy else 5.0)
	_spark(x, y, Settings.WHITE, 6, 9.0, 4.0, 10)
	numbers.append(DamageNumber.new(x, y - 40, str(damage), color, 46 if heavy else 34))
	add_shake(9.0 if heavy else 5.0)
	if ko:
		flash = 8
		add_shake(16.0)

func spawn_combo(count: int, left_side: bool) -> void:
	combo = [count, 46, left_side]

func spawn_counter(x: float, y: float) -> void:
	numbers.append(DamageNumber.new(x, y - 62, "COUNTER!", Color8(255, 90, 90), 32))

func spawn_parry(x: float, y: float) -> void:
	numbers.append(DamageNumber.new(x, y - 60, "PARRY!", Color8(150, 220, 255), 32))
	_spark(x, y, Color8(180, 230, 255), 10, 6.0)

func spawn_guardcrush(x: float, y: float) -> void:
	numbers.append(DamageNumber.new(x, y - 66, "GUARD CRUSH!", Color8(255, 200, 90), 30))

func spawn_throw(x: float, y: float) -> void:
	numbers.append(DamageNumber.new(x, y - 60, "THROW!", Color8(255, 160, 200), 30))

func spawn_dizzy(x: float, y: float) -> void:
	_spark(x, y, Color8(255, 220, 120), 14, 5.5)

func spawn_dust(x: float, y: float, direction := 0) -> void:
	for i in range(7):
		var ang := randf_range(PI * 0.9, PI * 2.1)
		var spd := randf_range(1.0, 3.2)
		particles.append(Particle.new(
			x + randf_range(-8, 8), y,
			cos(ang) * spd + direction * 1.2,
			-absf(sin(ang) * spd) * 0.5,
			randi_range(14, 24), randi_range(3, 6), Color8(180, 170, 155), 0.06))

func _spark(x: float, y: float, color: Color, count := 10, speed := 5.0, size := 5.0, life := 18) -> void:
	for i in range(count):
		var ang := randf_range(0.0, TAU)
		var spd := randf_range(speed * 0.4, speed)
		particles.append(Particle.new(x, y, cos(ang) * spd, sin(ang) * spd,
			randi_range(int(life * 0.6), life), size, color, 0.12))

func spawn_impact_ring(x: float, y: float, color := Color8(255, 220, 120), big := false) -> void:
	if big:
		rings.append(ImpactRing.new(x, y, color, 10.0, 110.0, 20, 8.0))
	else:
		rings.append(ImpactRing.new(x, y, color, 6.0, 64.0, 15, 5.0))

func _spawn_ambient() -> void:
	var w := Settings.WIDTH
	var h := Settings.HEIGHT
	match ambient_kind:
		"leaves":
			var cols := [Color8(196, 142, 58), Color8(168, 108, 46), Color8(142, 158, 62), Color8(120, 90, 40)]
			ambient.append(AmbientParticle.new(randf_range(0, w), randf_range(-20, -4),
				randf_range(-0.4, 0.6), randf_range(0.7, 1.4), randi_range(240, 380),
				randi_range(4, 7), cols[randi() % cols.size()], randf_range(0.8, 1.8), randf_range(0, TAU)))
		"dust":
			var drift := (1 if randf() < 0.5 else -1) * randf_range(0.8, 1.8)
			ambient.append(AmbientParticle.new((-10 if drift > 0 else w + 10),
				randf_range(0, h * 0.85), drift, randf_range(-0.1, 0.25), randi_range(180, 300),
				randi_range(2, 4), Color8(200, 188, 160), randf_range(0.1, 0.4), randf_range(0, TAU)))
		"embers":
			var cols := [Color8(255, 170, 60), Color8(255, 120, 40), Color8(255, 210, 120)]
			ambient.append(AmbientParticle.new(randf_range(0, w), randf_range(h - 4, h + 16),
				randf_range(-0.5, 0.5), randf_range(-1.6, -0.8), randi_range(150, 260),
				randi_range(2, 4), cols[randi() % cols.size()], randf_range(0.3, 0.9), randf_range(0, TAU)))

func update() -> void:
	for p in particles: p.update()
	for d in numbers: d.update()
	for r in rings: r.update()
	if ambient_kind != "none":
		_ambient_timer += 1
		if _ambient_timer >= 6 and ambient.size() < 60:
			_ambient_timer = 0
			_spawn_ambient()
		for a in ambient: a.update()
	particles = particles.filter(func(p): return p.life > 0)
	numbers = numbers.filter(func(d): return d.life > 0)
	rings = rings.filter(func(r): return r.life > 0)
	ambient = ambient.filter(func(a): return a.life > 0 \
		and a.y >= -40 and a.y <= Settings.HEIGHT + 40 \
		and a.x >= -40 and a.x <= Settings.WIDTH + 40)
	shake *= 0.82
	if shake < 0.4: shake = 0.0
	if flash > 0: flash -= 1
	if combo != null:
		combo[1] -= 1
		if combo[1] <= 0: combo = null

func shake_offset() -> Vector2:
	if shake <= 0: return Vector2.ZERO
	return Vector2(randf_range(-shake, shake), randf_range(-shake, shake))

func draw_world(ci: CanvasItem, off: Vector2) -> void:
	for a in ambient: a.draw(ci, off)
	for p in particles: p.draw(ci, off)
	for r in rings: r.draw(ci, off)

func draw_overlay(ci: CanvasItem) -> void:
	for d in numbers: d.draw(ci, Vector2.ZERO)
	if combo != null: _draw_combo(ci)
	if vignette:
		ci.draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.HEIGHT), Color(0, 0, 0, 0.34))
	if flash > 0:
		ci.draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.HEIGHT), Color(1, 1, 1, 0.59 * flash / 8.0))

func _draw_combo(ci: CanvasItem) -> void:
	var count: int = combo[0]
	var life: int = combo[1]
	var left: bool = combo[2]
	var x := 330.0 if left else Settings.WIDTH - 330.0
	var text := "%d VURUŞ!" % count
	var fs := 44
	if life > 40:
		fs = int(44 * (0.6 + 0.4 * (46 - life) / 6.0))
	var alpha := clampf(life / 12.0, 0.0, 1.0)
	var font := ThemeDB.fallback_font
	var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var p := Vector2(x - w / 2.0, 210.0)
	ci.draw_string(font, p + Vector2(3, 3), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0, 0, 0, alpha))
	ci.draw_string(font, p, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1.0, 0.886, 0.33, alpha))
