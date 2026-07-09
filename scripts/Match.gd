extends Node2D
## match.py + hud.py port — tam mac akisi: INTRO(VS) -> FIGHT -> ROUND_OVER -> MATCH_OVER.
## best-of-3, timer, KO slow-mo, eriyens can bari, round pip, super metre, banner.
## finished sinyali Main'e sonucu doner ("menu" | "quit").

signal finished(result: String)

enum Phase { INTRO, FIGHT, ROUND_OVER, MATCH_OVER }

var cfg := {"p1": "efe", "p2": "goron", "difficulty": "kolay"}

var p1: Fighter
var p2: Fighter
var c1
var c2: AIController
var wins := [0, 0]
var round_num := 1
var phase := Phase.INTRO
var phase_frame := 0
var timer_frames := 0
var banner_text := ""
var banner_sub := ""
var paused := false
var hitstop := 0
var slowmo := 0
var cam_x := 0.0
var hud_lag := [0.0, 0.0]
var effects: EffectSystem
var projectiles: Array = []
var stage_scene: StageScene
var stage_name := ""
var _diff_label := ""
var _prev_hitstun := [false, false]
var _prev_attacking := [false, false]
var _anim := {}
var _shot_mode := false
var _shot_f := 0

func _ready() -> void:
	_shot_mode = OS.get_environment("PIXELBRAWL_SHOT") == "1"
	effects = EffectSystem.new()
	c1 = HumanController.new()
	c2 = AIController.new(cfg["difficulty"])
	_diff_label = AIController.DIFFICULTY_LABELS.get(cfg["difficulty"], "")
	stage_name = Stages.NAMES[randi() % Stages.NAMES.size()]
	stage_scene = Stages.build(stage_name, Vector2i(Settings.WIDTH, Settings.HEIGHT))
	_reset_match()
	Audio.play_music(0.28)
	if _shot_mode:
		phase = Phase.FIGHT
		phase_frame = 0

func _reset_match() -> void:
	wins = [0, 0]
	round_num = 1
	_start_round()

func _start_round() -> void:
	p1 = Fighter.new(Characters.get_char(cfg["p1"]), Settings.WIDTH * 0.32, 1)
	p2 = Fighter.new(Characters.get_char(cfg["p2"]), Settings.WIDTH * 0.68, -1)
	hud_lag = [float(p1.health), float(p2.health)]
	timer_frames = Settings.ROUND_TIME * Settings.FPS
	hitstop = 0
	slowmo = 0
	projectiles.clear()
	effects.reset()
	effects.set_ambient(_ambient_for(stage_name))
	phase = Phase.INTRO
	phase_frame = 0
	_prev_hitstun = [false, false]
	_prev_attacking = [false, false]

func _ambient_for(s: String) -> String:
	if s == "col":
		return "dust"
	if s == "tepeler_gunbatimi":
		return "embers"
	if s == "gece_dorukleri" or s == "sato_alacakaranlik":
		return "none"
	return "leaves"

func _animator(f: Fighter) -> SpriteAnimator:
	if not _anim.has(f.data.key):
		_anim[f.data.key] = SpriteAnimator.new(f.data)
	return _anim[f.data.key]

# ============================================================ GIRDI
func _input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var kc := (event as InputEventKey).keycode
	if kc == KEY_ESCAPE:
		if phase == Phase.MATCH_OVER:
			finished.emit("menu")
		else:
			paused = not paused
	elif paused and kc == KEY_Q:
		finished.emit("menu")
	elif phase == Phase.MATCH_OVER and kc == KEY_ENTER:
		_reset_match()

# ============================================================ DONGU
func _physics_process(_dt: float) -> void:
	if paused:
		queue_redraw()
		return
	phase_frame += 1
	match phase:
		Phase.INTRO:
			if phase_frame >= Settings.INTRO_FRAMES:
				phase = Phase.FIGHT
				phase_frame = 0
		Phase.FIGHT:
			_fight_step()
		Phase.ROUND_OVER:
			_round_over_step()
		Phase.MATCH_OVER:
			p1.update(Inputs.new(), p2)
			p2.update(Inputs.new(), p1)
	_hud_lag_update()
	effects.update()
	_update_cam()
	queue_redraw()
	_shot_tick()

func _fight_step() -> void:
	if hitstop > 0:
		hitstop -= 1
		return
	var i1: Inputs = c1.get_inputs(p1, p2)
	var i2: Inputs = c2.get_inputs(p2, p1)
	p1.update(i1, p2)
	p2.update(i2, p1)
	_check_special(p1)
	_check_special(p2)
	_whoosh_check()
	var evs := Combat.resolve_hits(p1, p2)
	Combat.push_apart(p1, p2)
	_spawn_hit_fx(evs)
	_spawn_move_fx()
	_update_projectiles()
	_decay_combos()
	if timer_frames > 0:
		timer_frames -= 1
	_check_round_end()

func _round_over_step() -> void:
	if slowmo > 0:
		slowmo -= 1
		if slowmo % 3 == 0:
			p1.update(Inputs.new(), p2)
			p2.update(Inputs.new(), p1)
			_spawn_move_fx()
		if slowmo == 0:
			effects.set_slowmo_vignette(false)
	else:
		p1.update(Inputs.new(), p2)
		p2.update(Inputs.new(), p1)
		_spawn_move_fx()
	if phase_frame >= Settings.ROUND_OVER_FRAMES:
		if wins.max() >= Settings.ROUNDS_TO_WIN:
			phase = Phase.MATCH_OVER
			phase_frame = 0
			var w: Fighter = p1 if wins[0] > wins[1] else p2
			w.victory = true
		else:
			round_num += 1
			_start_round()

func _check_round_end() -> void:
	var ko1 := p1.state == Fighter.State.KO
	var ko2 := p2.state == Fighter.State.KO
	if ko1 or ko2:
		_start_ko_slowmo()
	if ko1 and ko2:
		_end_round(-1, "ÇİFT NAKAVT!")
	elif ko1:
		_end_round(1, "K.O.!")
	elif ko2:
		_end_round(0, "K.O.!")
	elif timer_frames <= 0:
		if p1.health > p2.health:
			_end_round(0, "SÜRE BİTTİ!")
		elif p2.health > p1.health:
			_end_round(1, "SÜRE BİTTİ!")
		else:
			_end_round(-1, "BERABERE!")

func _start_ko_slowmo() -> void:
	slowmo = 48
	Audio.play("ko")
	effects.set_slowmo_vignette(true)

func _end_round(widx: int, text: String) -> void:
	if widx >= 0:
		wins[widx] += 1
		banner_text = text
		banner_sub = "%s round'u aldı" % [p1, p2][widx].data.name
	else:
		banner_text = text
		banner_sub = "Round tekrar oynanacak"
	phase = Phase.ROUND_OVER
	phase_frame = 0

# ---------------------------------------------------------------- efekt/ses
func _spawn_hit_fx(evs: Array) -> void:
	for e in evs:
		e.attacker.meter = mini(Settings.SUPER_MAX, e.attacker.meter + Settings.SUPER_GAIN_HIT)
		var defender: Fighter = p2 if e.attacker == p1 else p1
		defender.meter = mini(Settings.SUPER_MAX, defender.meter + Settings.SUPER_GAIN_TAKEN)
		effects.spawn_hit(e.x, e.y, e.damage, e.blocked, e.heavy, e.ko)
		if e.combo >= 2 and not e.blocked:
			effects.spawn_combo(e.combo, e.attacker == p1)
		if e.blocked:
			Audio.play("block")
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_BLOCK)
		elif e.heavy or e.ko:
			effects.spawn_impact_ring(e.x, e.y, Color8(255, 220, 120), true)
			Audio.play("hit_heavy")
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_HEAVY)
		else:
			effects.spawn_impact_ring(e.x, e.y)
			Audio.play("hit_light")
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_NORMAL)

func _whoosh_check() -> void:
	for i in range(2):
		var f: Fighter = p1 if i == 0 else p2
		var atk := f.state == Fighter.State.PUNCH or f.state == Fighter.State.KICK
		if atk and not _prev_attacking[i]:
			Audio.play("whoosh", 0.6)
		_prev_attacking[i] = atk

func _decay_combos() -> void:
	for i in range(2):
		var f: Fighter = p1 if i == 0 else p2
		var other: Fighter = p2 if i == 0 else p1
		var now := f.state == Fighter.State.HITSTUN
		if _prev_hitstun[i] and not now:
			other.combo_count = 0
		_prev_hitstun[i] = now

func _spawn_move_fx() -> void:
	for f in [p1, p2]:
		if f.just_jumped:
			var d := 1 if f.vx > 0.5 else (-1 if f.vx < -0.5 else 0)
			effects.spawn_dust(f.x, Settings.FLOOR_Y, d)
			Audio.play("jump", 0.7)
		if f.just_landed:
			effects.spawn_dust(f.x, Settings.FLOOR_Y)
			Audio.play("land", 0.6)

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
	Audio.play("whoosh", 0.7)

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
			Audio.play("hit_heavy")
			proj.owner.meter = mini(Settings.SUPER_MAX, proj.owner.meter + Settings.SUPER_GAIN_HIT)
			target.meter = mini(Settings.SUPER_MAX, target.meter + Settings.SUPER_GAIN_TAKEN)
			hitstop = maxi(hitstop, EffectSystem.HITSTOP_HEAVY)
			proj.register_hit()
	projectiles = projectiles.filter(func(pr): return pr.alive)

func _update_cam() -> void:
	var target := clampf(((p1.x + p2.x) / 2.0 - Settings.WIDTH / 2.0) * 0.25, -80.0, 80.0)
	cam_x += (target - cam_x) * 0.12

func _hud_lag_update() -> void:
	for i in range(2):
		var f: Fighter = p1 if i == 0 else p2
		if hud_lag[i] > f.health:
			hud_lag[i] = maxf(float(f.health), hud_lag[i] - 0.8)
		else:
			hud_lag[i] = float(f.health)

func _shot_tick() -> void:
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

# ============================================================ CIZIM
func _draw() -> void:
	var off := effects.shake_offset()
	stage_scene.draw_back(self, cam_x)
	if p2.state == Fighter.State.KO:
		_draw_fighter(p2, off); _draw_fighter(p1, off)
	else:
		_draw_fighter(p1, off); _draw_fighter(p2, off)
	for proj in projectiles:
		proj.draw(self, off)
	effects.draw_world(self, off)
	stage_scene.draw_front(self, cam_x)
	_draw_hud()
	effects.draw_overlay(self)
	_draw_banners()

func _draw_banners() -> void:
	if phase == Phase.INTRO:
		if phase_frame < Settings.INTRO_FRAMES * 0.62:
			_draw_vs(phase_frame / (Settings.INTRO_FRAMES * 0.62))
		else:
			_banner("DÖVÜŞ!")
	elif phase == Phase.ROUND_OVER:
		_banner(banner_text, banner_sub)
	elif phase == Phase.MATCH_OVER:
		var w: Fighter = p1 if wins[0] > wins[1] else p2
		_banner("KAZANAN: %s" % w.data.name, "ENTER: Tekrar    ESC: Ana menü")
	if paused:
		draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.HEIGHT), Color(0, 0, 0, 0.59))
		_banner("DURAKLATILDI", "ESC: Devam    Q: Ana menü")

func _text(font: Font, s: String, cx: float, y: float, size: int, col: Color, shadow := true) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	if shadow:
		draw_string(font, Vector2(cx - w / 2.0 + 3, y + 3), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Settings.BLACK)
	draw_string(font, Vector2(cx - w / 2.0, y), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func _banner(text: String, sub := "") -> void:
	var font := ThemeDB.fallback_font
	var cy := Settings.HEIGHT / 2.0 - 20.0
	_text(font, text, Settings.WIDTH / 2.0, cy, 84, Settings.WHITE)
	if sub != "":
		_text(font, sub, Settings.WIDTH / 2.0, Settings.HEIGHT / 2.0 + 56.0, 30, Settings.TIMER_COLOR)

func _draw_vs(t: float) -> void:
	var font := ThemeDB.fallback_font
	var cx := Settings.WIDTH / 2.0
	var cy := Settings.HEIGHT / 2.0
	var ease := minf(1.0, t * 1.4)
	var off := (1.0 - ease) * (1.0 - ease) * 620.0
	for pair in [[p1, -1.0], [p2, 1.0]]:
		var f: Fighter = pair[0]
		var side: float = pair[1]
		var nm: String = f.data.name
		var tw := font.get_string_size(nm, HORIZONTAL_ALIGNMENT_LEFT, -1, 48).x
		var bx: float = (cx - 70.0 - off - tw - 22.0) if side < 0 else (cx + 70.0 + off)
		draw_rect(Rect2(bx - 22, cy - 40, tw + 44, 72), f.data.color)
		draw_rect(Rect2(bx - 22, cy - 40, tw + 44, 72), Settings.WHITE, false, 3.0)
		draw_string(font, Vector2(bx, cy + 16), nm, HORIZONTAL_ALIGNMENT_LEFT, -1, 48, Settings.WHITE)
	var vs_fs := int((0.4 + 0.6 * ease) * 84)
	_text(font, "VS", cx, cy + vs_fs * 0.35, vs_fs, Settings.HP_MAIN)

func _draw_hud() -> void:
	var bw := 460.0
	var bh := 30.0
	var yy := 34.0
	_hp_bar(p1, hud_lag[0], 40.0, yy, bw, bh, true)
	_hp_bar(p2, hud_lag[1], Settings.WIDTH - 40.0 - bw, yy, bw, bh, false)
	var mw := bw * 0.6
	_meter(40.0, yy + bh + 6.0, mw, 8.0, float(p1.meter) / Settings.SUPER_MAX, true)
	_meter(Settings.WIDTH - 40.0 - mw, yy + bh + 6.0, mw, 8.0, float(p2.meter) / Settings.SUPER_MAX, false)
	_wins(bw)
	var font := ThemeDB.fallback_font
	var secs := int(ceil(timer_frames / float(Settings.FPS)))
	_text(font, "%02d" % maxi(0, secs), Settings.WIDTH / 2.0, 58.0, 46, Settings.TIMER_COLOR)
	var info := "ROUND %d" % round_num
	if _diff_label != "":
		info += "   •   Bot: " + _diff_label
	_text(font, info, Settings.WIDTH / 2.0, yy + bh + 34.0, 18, Settings.WHITE)

func _hp_bar(f: Fighter, lag: float, x: float, y: float, bw: float, bh: float, left: bool) -> void:
	draw_rect(Rect2(x, y, bw, bh), Settings.HP_BACK)
	var mx := float(f.data.max_health)
	var lag_w := bw * maxf(0.0, lag) / mx
	var cur_w := bw * maxf(0.0, f.health) / mx
	for pair in [[lag_w, Settings.HP_LAG], [cur_w, Settings.HP_MAIN]]:
		var wdt: float = pair[0]
		if wdt <= 0:
			continue
		if left:
			draw_rect(Rect2(x + bw - wdt, y, wdt, bh), pair[1])
		else:
			draw_rect(Rect2(x, y, wdt, bh), pair[1])
	draw_rect(Rect2(x, y, bw, bh), Settings.HP_BORDER, false, 3.0)
	var font := ThemeDB.fallback_font
	var ny := y + bh + 24.0
	if left:
		draw_string(font, Vector2(x + 2, ny), f.data.name, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Settings.WHITE)
	else:
		var w := font.get_string_size(f.data.name, HORIZONTAL_ALIGNMENT_LEFT, -1, 22).x
		draw_string(font, Vector2(x + bw - 2 - w, ny), f.data.name, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Settings.WHITE)

func _wins(bw: float) -> void:
	var r := 9.0
	var cy := 34.0 + 30.0 + 18.0
	for i in range(Settings.ROUNDS_TO_WIN):
		var x1 := 40.0 + bw - 18.0 - i * 26.0
		var x2 := Settings.WIDTH - 40.0 - bw + 18.0 + i * 26.0
		for pair in [[x1, wins[0] > i], [x2, wins[1] > i]]:
			var cx: float = pair[0]
			if pair[1]:
				draw_circle(Vector2(cx, cy), r, Settings.HP_MAIN)
			draw_arc(Vector2(cx, cy), r, 0, TAU, 20, Settings.WHITE, 2.0)

func _meter(bx: float, by: float, w: float, h: float, frac: float, left: bool) -> void:
	draw_rect(Rect2(bx, by, w, h), Settings.SUPER_BACK)
	var cw := w * clampf(frac, 0.0, 1.0)
	var col := Settings.SUPER_FULL if frac >= 1.0 else Settings.SUPER_FILL
	if left:
		draw_rect(Rect2(bx + w - cw, by, cw, h), col)
	else:
		draw_rect(Rect2(bx, by, cw, h), col)

# ---------------------------------------------------------------- dovuscu
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

func _blit_sprite(tex: Texture2D, cx: float, bottom_y: float, sz: Vector2, flip: bool, mod: Color, off: Vector2) -> void:
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
	var legs := Rect2(x - w * 0.26, y - eff_h * 0.42, w * 0.52, eff_h * 0.42)
	var torso := Rect2(x + lean - w * 0.39, legs.position.y - eff_h * 0.40 + 4.0, w * 0.78, eff_h * 0.40)
	var head_c := Vector2(x + lean * 1.4, torso.position.y - w * 0.24 + bob)
	draw_rect(legs, dark)
	draw_rect(torso, col)
	draw_circle(head_c, w * 0.27, Settings.SKIN)
	draw_circle(Vector2(head_c.x + fc * w * 0.12, head_c.y - 3.0), 3.0, Settings.BLACK)
	if (f.state == Fighter.State.PUNCH or f.state == Fighter.State.KICK) and f.attack != null:
		var a := f.attack
		var arm_y := y - h * a.height_frac
		var front := x + fc * (w / 2.0)
		var ext: float
		if f.state_frame < a.startup:
			ext = a.hit_w * 0.25
		elif f.state_frame < a.startup + a.active:
			ext = float(a.hit_w)
		else:
			ext = a.hit_w * 0.45
		var thick: float = float(a.hit_h - 6) if f.state == Fighter.State.PUNCH else float(a.hit_h)
		var limb_col := Settings.SKIN if f.state == Fighter.State.PUNCH else dark
		var lx := front if fc > 0 else front - ext
		draw_rect(Rect2(lx, arm_y - thick / 2.0, ext, maxf(10.0, thick)), limb_col)
	elif f.blocking:
		draw_rect(Rect2(x + fc * (w / 2.0 + 8.0) - 7.0, y - eff_h * 0.76, 14.0, eff_h * 0.42), Settings.SKIN)
	else:
		for side in [-1.0, 1.0]:
			var ax: float = torso.get_center().x + side * (torso.size.x / 2.0 - 2.0)
			draw_rect(Rect2(ax - 6.0, torso.position.y + 6.0, 12.0, eff_h * 0.30), Settings.SKIN)
