class_name Combat
extends RefCounted
## combat.py birebir port — vurus cozumu, blok kurallari, kombo, govde itisme.
## pygame.Rect semantigi elle: kenar-degme (a.right==b.left) CARPISMA DEGIL.

const COMBO_SCALE := [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]

class HitEvent:
	var x: float
	var y: float
	var damage: int
	var blocked: bool
	var heavy: bool
	var ko: bool
	var attacker: Fighter
	var combo: int
	var knockdown: bool
	func _init(p_x: float, p_y: float, p_damage: int, p_blocked: bool,
			p_heavy: bool, p_ko: bool, p_attacker: Fighter, p_combo := 1,
			p_knockdown := false) -> void:
		x = p_x
		y = p_y
		damage = p_damage
		blocked = p_blocked
		heavy = p_heavy
		ko = p_ko
		attacker = p_attacker
		combo = p_combo
		knockdown = p_knockdown

# ---- pygame.Rect yardimcilari (kenar-degme carpisma degil) ----
static func _overlap(a: Rect2i, b: Rect2i) -> bool:
	return a.position.x < b.position.x + b.size.x \
		and b.position.x < a.position.x + a.size.x \
		and a.position.y < b.position.y + b.size.y \
		and b.position.y < a.position.y + a.size.y

static func _clip(a: Rect2i, b: Rect2i) -> Rect2i:
	var x1 := maxi(a.position.x, b.position.x)
	var y1 := maxi(a.position.y, b.position.y)
	var x2 := mini(a.position.x + a.size.x, b.position.x + b.size.x)
	var y2 := mini(a.position.y + a.size.y, b.position.y + b.size.y)
	if x2 <= x1 or y2 <= y1:
		return Rect2i(0, 0, 0, 0)
	return Rect2i(x1, y1, x2 - x1, y2 - y1)

static func _guard_ok(stance: String, guard: String) -> bool:
	if stance == "stand":
		return guard == "high" or guard == "overhead"   # ayakta: alcak GECER
	if stance == "crouch":
		return guard == "high" or guard == "low"         # comel: overhead GECER
	return false

static func resolve_hits(a: Fighter, b: Fighter) -> Array:
	## Iki dovuscunun aktif vuruslarini cozer; ayni karede iki taraf da
	## isabet ettirirse (trade) once ikisi tespit, sonra uygulanir.
	var events := []
	var hit_ab := _lands(a, b)
	var hit_ba := _lands(b, a)
	var atk_a: AttackData = a.attack
	var atk_b: AttackData = b.attack
	if hit_ab:
		a.attack_has_hit = true
		events.append(_apply(a, b, atk_a))
	if hit_ba:
		b.attack_has_hit = true
		events.append(_apply(b, a, atk_b))
	return events

static func _apply(attacker: Fighter, defender: Fighter, attack: AttackData) -> HitEvent:
	var pt := _hit_point(attacker, defender)
	var stance = defender.block_stance()
	var blocked: bool = stance != null and _guard_ok(stance, attack.guard)

	var dmg: int
	if blocked:
		attacker.combo_count = 0
		dmg = maxi(1, roundi(attack.damage * Settings.CHIP_DAMAGE_RATIO))
	else:
		if defender.state == Fighter.State.HITSTUN:   # suregelen kombo
			attacker.combo_count += 1
		else:
			attacker.combo_count = 1
		var scale: float = COMBO_SCALE[mini(COMBO_SCALE.size() - 1, attacker.combo_count - 1)]
		dmg = maxi(1, roundi(attack.damage * scale))

	defender.take_hit(attack, attacker.facing, blocked, dmg)
	var heavy: bool = attack.knockback >= 9.0 or attack.knockdown
	return HitEvent.new(pt.x, pt.y, dmg, blocked, heavy,
		defender.state == Fighter.State.KO, attacker, attacker.combo_count,
		attack.knockdown and not blocked)

static func _hit_point(attacker: Fighter, defender: Fighter) -> Vector2i:
	var hb = attacker.active_hitbox()
	var box := defender.hurtbox()
	if hb != null:
		var h: Rect2i = hb
		var clip := _clip(h, box)
		var cx: int
		var cy: int
		if clip.size.x != 0:
			cx = clip.position.x + clip.size.x / 2
		else:
			cx = ((h.position.x + h.size.x / 2) + (box.position.x + box.size.x / 2)) / 2
		if clip.size.y != 0:
			cy = clip.position.y + clip.size.y / 2
		else:
			cy = ((h.position.y + h.size.y / 2) + (box.position.y + box.size.y / 2)) / 2
		return Vector2i(cx, cy)
	return Vector2i(box.position.x + box.size.x / 2, box.position.y)

static func _lands(attacker: Fighter, defender: Fighter) -> bool:
	if attacker.attack_has_hit or defender.state == Fighter.State.KO:
		return false
	var hb = attacker.active_hitbox()
	if hb == null:
		return false
	return _overlap(hb, defender.hurtbox())

static func push_apart(a: Fighter, b: Fighter) -> void:
	## Govdelerin ust uste binmesini engeller (pushbox).
	var ra := a.hurtbox()
	var rb := b.hurtbox()
	if not _overlap(ra, rb):
		return
	var overlap: int = mini(ra.position.x + ra.size.x, rb.position.x + rb.size.x) \
		- maxi(ra.position.x, rb.position.x)
	if overlap <= 0:
		return
	var left_f: Fighter
	var right_f: Fighter
	if a.x <= b.x:
		left_f = a
		right_f = b
	else:
		left_f = b
		right_f = a
	var shift := overlap / 2.0 + 0.5
	left_f.x -= shift
	right_f.x += shift
	_clamp(left_f)
	_clamp(right_f)
	ra = a.hurtbox()
	rb = b.hurtbox()
	if _overlap(ra, rb):
		overlap = mini(ra.position.x + ra.size.x, rb.position.x + rb.size.x) \
			- maxi(ra.position.x, rb.position.x)
		if right_f.x >= Settings.WIDTH - Settings.STAGE_MARGIN - right_f.data.width / 2.0 - 1:
			left_f.x -= overlap
		else:
			right_f.x += overlap
		_clamp(left_f)
		_clamp(right_f)

static func _clamp(f: Fighter) -> void:
	var half := f.data.width / 2.0
	f.x = clampf(f.x, Settings.STAGE_MARGIN + half,
		Settings.WIDTH - Settings.STAGE_MARGIN - half)
