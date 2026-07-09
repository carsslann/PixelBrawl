extends Node2D
## OYNANABILIR DILIM (Faz 4 + minimal render).
## Dovus dongusu _physics_process'te (60Hz, integer kareler), cizim _draw'da
## (prosedurel dikdortgen dovuscular + can barlari). Tam round/faz/sprite/efekt
## akisi Faz 6-11'de zenginlesecek. Su an: P1 (klavye) vs bot, surekli dovus.

var p1: Fighter
var p2: Fighter
var c1                       # HumanController veya AIController
var c2: AIController
var timer_frames: int
var hitstop: int = 0
var ko_wait: int = 0
var _headless := false
var _hl := 0

func _ready() -> void:
	_headless = DisplayServer.get_name() == "headless"
	_new_round()
	if _headless:
		c1 = AIController.new("zor")     # self-play testi
	else:
		c1 = HumanController.new()
		print("== PixelBrawl oynanabilir dilim ==")
		print("A/D yuru  W zipla  S comel  J yumruk  K tekme  L ozel  (geri tut=blok)")

func _new_round() -> void:
	var efe: CharacterData = Characters.get_char("efe")
	var goron: CharacterData = Characters.get_char("goron")
	p1 = Fighter.new(efe, Settings.WIDTH * 0.32, 1)
	p2 = Fighter.new(goron, Settings.WIDTH * 0.68, -1)
	c2 = AIController.new("orta")
	timer_frames = Settings.ROUND_TIME * Settings.FPS
	hitstop = 0
	ko_wait = 0

func _physics_process(_dt: float) -> void:
	if ko_wait > 0:
		ko_wait -= 1
		p1.update(Inputs.new(), p2)
		p2.update(Inputs.new(), p1)
		if ko_wait == 0:
			var keep_c1 = c1
			_new_round()
			c1 = keep_c1
		queue_redraw()
		return

	if hitstop > 0:
		hitstop -= 1
	else:
		var i1: Inputs = c1.get_inputs(p1, p2)
		var i2: Inputs = c2.get_inputs(p2, p1)
		p1.update(i1, p2)
		p2.update(i2, p1)
		var evs := Combat.resolve_hits(p1, p2)
		Combat.push_apart(p1, p2)
		for e in evs:
			hitstop = maxi(hitstop, 7 if e.heavy else 4)
		if timer_frames > 0:
			timer_frames -= 1
		if p1.state == Fighter.State.KO or p2.state == Fighter.State.KO:
			ko_wait = 120

	queue_redraw()
	_headless_tick()

func _headless_tick() -> void:
	if not _headless:
		return
	_hl += 1
	if _hl % 150 == 0:
		print("frame %d | p1 st%d can%d | p2 st%d can%d"
			% [_hl, p1.state, p1.health, p2.state, p2.health])
	if _hl >= 700:
		print("Dilim self-test OK: p1 can %d, p2 can %d" % [p1.health, p2.health])
		get_tree().quit()

# ============================================================ CIZIM
func _draw() -> void:
	draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.FLOOR_Y), Settings.SKY_TOP)
	draw_rect(Rect2(0, Settings.FLOOR_Y, Settings.WIDTH, Settings.HEIGHT - Settings.FLOOR_Y),
		Settings.FLOOR_COLOR)
	draw_line(Vector2(0, Settings.FLOOR_Y), Vector2(Settings.WIDTH, Settings.FLOOR_Y),
		Settings.FLOOR_LINE, 3.0)
	# KO olan altta kalsin
	if p2.state == Fighter.State.KO:
		_draw_fighter(p2); _draw_fighter(p1)
	else:
		_draw_fighter(p1); _draw_fighter(p2)
	_draw_hud()

func _draw_fighter(f: Fighter) -> void:
	var w := float(f.data.width)
	var h := float(f.data.height)
	var col := f.data.color
	var dark := Color(maxf(0.0, col.r - 0.22), maxf(0.0, col.g - 0.22), maxf(0.0, col.b - 0.22))
	var x := f.x
	var y := f.y
	var fc := f.facing
	# golge
	draw_rect(Rect2(x - w * 0.75, Settings.FLOOR_Y + 2.0, w * 1.5, 10.0), Color(0, 0, 0, 0.35))

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
	elif f.state == Fighter.State.BLOCK or (f.state == Fighter.State.CROUCH and f.blocking):
		var gx := x + fc * (w / 2.0 + 8.0)
		draw_rect(Rect2(gx - 7.0, y - eff_h * 0.76, 14.0, eff_h * 0.42), Settings.SKIN)
	else:
		for side in [-1.0, 1.0]:
			var ax := torso.get_center().x + side * (torso.size.x / 2.0 - 2.0)
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

func _bar(bx: float, by: float, bw: float, bh: float, frac: float, left: bool) -> void:
	draw_rect(Rect2(bx, by, bw, bh), Settings.HP_BACK)
	var cw := bw * clampf(frac, 0.0, 1.0)
	if left:
		draw_rect(Rect2(bx + bw - cw, by, cw, bh), Settings.HP_MAIN)
	else:
		draw_rect(Rect2(bx, by, cw, bh), Settings.HP_MAIN)
	draw_rect(Rect2(bx, by, bw, bh), Settings.HP_BORDER, false, 3.0)
