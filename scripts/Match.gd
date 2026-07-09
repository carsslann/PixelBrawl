extends Node2D
## OYNANABILIR DILIM (Faz 4 + 7 sprite + 6 efekt).
## Dovus dongusu _physics_process (60Hz); cizim _draw: sahne + Kenney sprite +
## efektler (kivilcim/hasar sayisi/impact/kombo/sarsinti) + can barlari.
## Tam round/faz/stage/menu Faz 8-12'de zenginlesecek.

var p1: Fighter
var p2: Fighter
var c1
var c2: AIController
var timer_frames: int
var hitstop: int = 0
var ko_wait: int = 0
var effects: EffectSystem
var projectiles: Array = []
var stage_scene: StageScene
var stage_name := ""
var cam_x := 0.0
var _shot_mode := false
var _shot_f := 0
var _anim := {}
var _headless := false
var _hl := 0

func _ready() -> void:
	_headless = DisplayServer.get_name() == "headless"
	_shot_mode = OS.get_environment("PIXELBRAWL_SHOT") == "1"
	effects = EffectSystem.new()
	stage_name = Stages.NAMES[randi() % Stages.NAMES.size()]
	stage_scene = Stages.build(stage_name, Vector2i(Settings.WIDTH, Settings.HEIGHT))
	_new_round()
	if _headless:
		c1 = AIController.new("zor")
	else:
		c1 = HumanController.new()
		print("== PixelBrawl ==  A/D yuru  W zipla  S comel  J yumruk  K tekme  L ozel  (geri=blok)")

func _new_round() -> void:
	p1 = Fighter.new(Characters.get_char("efe"), Settings.WIDTH * 0.32, 1)
	p2 = Fighter.new(Characters.get_char("goron"), Settings.WIDTH * 0.68, -1)
	c2 = AIController.new("orta")
	timer_frames = Settings.ROUND_TIME * Settings.FPS
	hitstop = 0
	ko_wait = 0
	effects.reset()
	effects.set_ambient(_ambient_for(stage_name))
	projectiles.clear()

func _ambient_for(s: String) -> String:
	if s == "col":
		return "dust"
	if s == "tepeler_gunbatimi":
		return "embers"
	if s == "gece_dorukleri" or s == "sato_alacakaranlik":
		return "none"
	return "leaves"

func _update_cam() -> void:
	var target := clampf(((p1.x + p2.x) / 2.0 - Settings.WIDTH / 2.0) * 0.25, -80.0, 80.0)
	cam_x += (target - cam_x) * 0.12

func _animator(f: Fighter) -> SpriteAnimator:
	if not _anim.has(f.data.key):
		_anim[f.data.key] = SpriteAnimator.new(f.data)
	return _anim[f.data.key]

# ============================================================ DONGU
func _physics_process(_dt: float) -> void:
	if ko_wait > 0:
		ko_wait -= 1
		p1.update(Inputs.new(), p2)
		p2.update(Inputs.new(), p1)
		_spawn_move_fx()
		effects.update()
		if ko_wait == 0:
			var keep = c1
			_new_round()
			c1 = keep
		_update_cam()
		queue_redraw()
		return

	if hitstop > 0:
		hitstop -= 1
	else:
		var i1: Inputs = c1.get_inputs(p1, p2)
		var i2: Inputs = c2.get_inputs(p2, p1)
		p1.update(i1, p2)
		p2.update(i2, p1)
		_check_special(p1)
		_check_special(p2)
		var evs := Combat.resolve_hits(p1, p2)
		Combat.push_apart(p1, p2)
		_spawn_hit_fx(evs)
		_spawn_move_fx()
		_update_projectiles()
		if timer_frames > 0:
			timer_frames -= 1
		if p1.state == Fighter.State.KO or p2.state == Fighter.State.KO:
			ko_wait = 120
			effects.set_slowmo_vignette(true)

	effects.update()
	_update_cam()
	queue_redraw()
	_headless_tick()

func _spawn_hit_fx(evs: Array) -> void:
	for e in evs:
		e.attacker.meter = mini(Settings.SUPER_MAX, e.attacker.meter + Settings.SUPER_GAIN_HIT)
		var defender: Fighter = p2 if e.attacker == p1 else p1
		defender.meter = mini(Settings.SUPER_MAX, defender.meter + Settings.SUPER_GAIN_TAKEN)
		effects.spawn_hit(e.x, e.y, e.damage, e.blocked, e.heavy, e.ko)
		if e.combo >= 2 and not e.blocked:
			effects.spawn_combo(e.combo, e.attacker == p1)
		if e.blocked:
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_BLOCK)
		elif e.heavy or e.ko:
			effects.spawn_impact_ring(e.x, e.y, Color8(255, 220, 120), true)
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_HEAVY)
		else:
			effects.spawn_impact_ring(e.x, e.y)
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_NORMAL)

func _spawn_move_fx() -> void:
	for f in [p1, p2]:
		if f.just_jumped:
			var d := 1 if f.vx > 0.5 else (-1 if f.vx < -0.5 else 0)
			effects.spawn_dust(f.x, Settings.FLOOR_Y, d)
		if f.just_landed:
			effects.spawn_dust(f.x, Settings.FLOOR_Y)

func _check_special(f: Fighter) -> void:
	if f.spawn_special == null:
		return
	var spec: SpecialSpec = f.spawn_special
	f.spawn_special = null
	var frames := FxSprites.fireball_frames(spec.color, 3.0)
	var atk := AttackData.new("özel ateş", spec.damage, 0, 999, 0, spec.hitstun,
		spec.knockback, spec.hit_w, spec.hit_h, 0.60, "high")
	var px := f.x + f.facing * (f.data.width * 0.5 + 12.0)
	var py := f.y - f.data.height * 0.58
	projectiles.append(Projectile.new(px, py, spec.speed * f.facing, f.facing,
		frames, atk, f, spec.hit_w, spec.hit_h))
	effects.spawn_impact_ring(px, py, Color8(255, 180, 90))

func _update_projectiles() -> void:
	for proj in projectiles:
		proj.update()
		if not proj.alive:
			continue
		var target: Fighter = p2 if proj.owner == p1 else p1
		if target.state == Fighter.State.KO:
			continue
		if Combat._overlap(proj.hitbox(), target.hurtbox()):
			var stance = target.block_stance()
			var blocked: bool = stance != null and Combat._guard_ok(stance, proj.atk.guard)
			var dmg := maxi(1, roundi(proj.atk.damage * (Settings.CHIP_DAMAGE_RATIO if blocked else 1.0)))
			var hb: Rect2i = proj.hitbox()
			var cx := hb.position.x + hb.size.x / 2
			var cy := hb.position.y + hb.size.y / 2
			target.take_hit(proj.atk, proj.facing, blocked, dmg)
			effects.spawn_hit(cx, cy, dmg, blocked, true, target.state == Fighter.State.KO)
			effects.spawn_impact_ring(cx, cy, Color8(255, 170, 80), true)
			proj.owner.meter = mini(Settings.SUPER_MAX, proj.owner.meter + Settings.SUPER_GAIN_HIT)
			target.meter = mini(Settings.SUPER_MAX, target.meter + Settings.SUPER_GAIN_TAKEN)
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_HEAVY)
			proj.register_hit()
	projectiles = projectiles.filter(func(pr): return pr.alive)

func _process(_d: float) -> void:
	if not _shot_mode:
		return
	_shot_f += 1
	if _shot_f == 40:
		p1.meter = Settings.SUPER_MAX
		p1.spawn_special = p1.data.special
	if _shot_f == 62:
		var img := get_viewport().get_texture().get_image()
		img.save_png("user://pixelbrawl_shot.png")
		print("SHOT: " + ProjectSettings.globalize_path("user://pixelbrawl_shot.png"))
		get_tree().quit()

func _headless_tick() -> void:
	if not _headless:
		return
	_hl += 1
	if _hl >= 400:
		print("Efekt dilim self-test OK: p1 can %d, p2 can %d | parcacik=%d"
			% [p1.health, p2.health, effects.particles.size()])
		get_tree().quit()

# ============================================================ CIZIM
func _draw() -> void:
	var off := effects.shake_offset()
	stage_scene.draw_back(self, cam_x)     # gokyuzu..zemin (parallax)
	if p2.state == Fighter.State.KO:
		_draw_fighter(p2, off); _draw_fighter(p1, off)
	else:
		_draw_fighter(p1, off); _draw_fighter(p2, off)
	for proj in projectiles:
		proj.draw(self, off)
	effects.draw_world(self, off)
	stage_scene.draw_front(self, cam_x)    # on plan cerceve (parallax)
	_draw_hud()
	effects.draw_overlay(self)

func _draw_fighter(f: Fighter, off: Vector2) -> void:
	_draw_shadow(f, off)
	var anim := _animator(f)
	if anim.ok:
		var tex = anim.frame_for(f)
		if tex != null:
			var sz := Vector2(tex.get_width(), tex.get_height()) * anim.scale
			var dy := 0.0
			if f.state == Fighter.State.IDLE:
				dy = sin(f.state_frame * 0.12) * 2.0
			elif (f.state == Fighter.State.PUNCH or f.state == Fighter.State.KICK) \
					and f.attack != null and not f.attack_airborne and f.attack.height_frac < 0.4:
				dy = f.data.height * 0.16
			var mod := Color(2.4, 2.4, 2.4) if f.hit_flash > 0 else Color.WHITE
			_blit_sprite(tex, f.x, f.y + dy, sz, f.facing < 0, mod, off)
			if f.blocking:
				_draw_guard(f, off)
			return
	_draw_procedural_body(f, off)

func _blit_sprite(tex: Texture2D, cx: float, bottom_y: float, sz: Vector2,
		flip: bool, mod: Color, off: Vector2) -> void:
	if flip:
		draw_set_transform(Vector2(cx + off.x, bottom_y + off.y), 0.0, Vector2(-1, 1))
		draw_texture_rect(tex, Rect2(-sz.x / 2.0, -sz.y, sz.x, sz.y), false, mod)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	else:
		draw_texture_rect(tex, Rect2(cx - sz.x / 2.0 + off.x, bottom_y - sz.y + off.y, sz.x, sz.y), false, mod)

func _draw_shadow(f: Fighter, off: Vector2) -> void:
	var spread := maxf(0.45, 1.0 - (Settings.FLOOR_Y - f.y) / 400.0)
	var rw := f.data.width * 1.7 * spread * 0.5
	draw_set_transform(Vector2(f.x + off.x, Settings.FLOOR_Y + 8.0 + off.y), 0.0, Vector2(1, 0.28))
	draw_circle(Vector2.ZERO, rw, Color(0, 0, 0, 0.35))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func _draw_guard(f: Fighter, off: Vector2) -> void:
	var gx := f.x + off.x + f.facing * (f.data.width * 0.5 + 8.0)
	var low := f.state == Fighter.State.CROUCH
	var gy := f.y + off.y - f.data.height * (0.34 if low else 0.52)
	var a := 0.78 if f.block_flash > 0 else 0.43
	draw_set_transform(Vector2(gx, gy), 0.0, Vector2(0.6, 2.0))
	draw_circle(Vector2.ZERO, 15.0, Color(0.59, 0.78, 1.0, a))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

func _draw_procedural_body(f: Fighter, off: Vector2) -> void:
	var w := float(f.data.width)
	var h := float(f.data.height)
	var col := f.data.color
	var dark := Color(maxf(0.0, col.r - 0.22), maxf(0.0, col.g - 0.22), maxf(0.0, col.b - 0.22))
	var x := f.x + off.x
	var y := f.y + off.y
	var fc := f.facing

	if f.state == Fighter.State.KO:
		var bw := h * 0.72
		var bh := w * 0.62
		draw_rect(Rect2(x - bw / 2.0, y - bh, bw, bh), dark)
		draw_circle(Vector2(x - fc * bw * 0.5, y - bh * 0.5), w * 0.30, Settings.SKIN)
		return

	var bob := (sin(f.state_frame * 0.28) * 3.0) if f.state == Fighter.State.WALK else 0.0
	var crouch := (h * 0.30) if f.state == Fighter.State.CROUCH else 0.0
	var tuck := (h * 0.16) if f.state == Fighter.State.JUMP else 0.0
	var lean := (-fc * 7.0) if f.state == Fighter.State.HITSTUN else 0.0
	var eff_h := h - crouch - tuck

	var legs_w := w * 0.52
	var legs_h := eff_h * 0.42
	var legs := Rect2(x - legs_w / 2.0, y - legs_h, legs_w, legs_h)
	var torso_w := w * 0.78
	var torso_h := eff_h * 0.40
	var torso := Rect2(x + lean - torso_w / 2.0, legs.position.y - torso_h + 4.0, torso_w, torso_h)
	var head_c := Vector2(x + lean * 1.4, torso.position.y - w * 0.24 + bob)

	draw_rect(legs, dark)
	draw_rect(torso, col)
	draw_circle(head_c, w * 0.27, Settings.SKIN)
	draw_circle(Vector2(head_c.x + fc * w * 0.12, head_c.y - 3.0), 3.0, Settings.BLACK)

	if (f.state == Fighter.State.PUNCH or f.state == Fighter.State.KICK) and f.attack != null:
		var a := f.attack
		var prog := f.state_frame
		var arm_y := y - h * a.height_frac
		var front := x + fc * (w / 2.0)
		var ext: float
		if prog < a.startup:
			ext = a.hit_w * 0.25
		elif prog < a.startup + a.active:
			ext = float(a.hit_w)
		else:
			ext = a.hit_w * 0.45
		var thick: float = float(a.hit_h - 6) if f.state == Fighter.State.PUNCH else float(a.hit_h)
		var limb_col := Settings.SKIN if f.state == Fighter.State.PUNCH else dark
		var lx := front if fc > 0 else front - ext
		draw_rect(Rect2(lx, arm_y - thick / 2.0, ext, maxf(10.0, thick)), limb_col)
	elif f.blocking:
		var gx := x + fc * (w / 2.0 + 8.0)
		draw_rect(Rect2(gx - 7.0, y - eff_h * 0.76, 14.0, eff_h * 0.42), Settings.SKIN)
	else:
		for side in [-1.0, 1.0]:
			var ax: float = torso.get_center().x + side * (torso.size.x / 2.0 - 2.0)
			draw_rect(Rect2(ax - 6.0, torso.position.y + 6.0, 12.0, eff_h * 0.30), Settings.SKIN)

func _draw_hud() -> void:
	var bw := 460.0
	var bh := 30.0
	var yy := 34.0
	_bar(40.0, yy, bw, bh, float(p1.health) / p1.data.max_health, true)
	_bar(Settings.WIDTH - 40.0 - bw, yy, bw, bh, float(p2.health) / p2.data.max_health, false)
	var font := ThemeDB.fallback_font
	var secs := int(ceil(timer_frames / float(Settings.FPS)))
	draw_string(font, Vector2(Settings.WIDTH / 2.0 - 24.0, 62.0), "%02d" % maxi(0, secs),
		HORIZONTAL_ALIGNMENT_LEFT, -1, 44, Settings.TIMER_COLOR)
	draw_string(font, Vector2(44.0, yy + bh + 24.0), p1.data.name,
		HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Settings.WHITE)
	draw_string(font, Vector2(Settings.WIDTH - 40.0 - bw, yy + bh + 24.0), p2.data.name,
		HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Settings.WHITE)
	var mw := bw * 0.6
	_meter(40.0, yy + bh + 6.0, mw, 8.0, float(p1.meter) / Settings.SUPER_MAX, true)
	_meter(Settings.WIDTH - 40.0 - mw, yy + bh + 6.0, mw, 8.0, float(p2.meter) / Settings.SUPER_MAX, false)

func _meter(bx: float, by: float, w: float, h: float, frac: float, left: bool) -> void:
	draw_rect(Rect2(bx, by, w, h), Settings.SUPER_BACK)
	var cw := w * clampf(frac, 0.0, 1.0)
	var col := Settings.SUPER_FULL if frac >= 1.0 else Settings.SUPER_FILL
	if left:
		draw_rect(Rect2(bx + w - cw, by, cw, h), col)
	else:
		draw_rect(Rect2(bx, by, cw, h), col)

func _bar(bx: float, by: float, bw: float, bh: float, frac: float, left: bool) -> void:
	draw_rect(Rect2(bx, by, bw, bh), Settings.HP_BACK)
	var cw := bw * clampf(frac, 0.0, 1.0)
	if left:
		draw_rect(Rect2(bx + bw - cw, by, cw, bh), Settings.HP_MAIN)
	else:
		draw_rect(Rect2(bx, by, cw, bh), Settings.HP_MAIN)
	draw_rect(Rect2(bx, by, bw, bh), Settings.HP_BORDER, false, 3.0)
