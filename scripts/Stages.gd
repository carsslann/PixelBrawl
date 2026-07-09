class_name Stages
extends RefCounted
## stages.py port (pragmatik) — 4 tam-gorsel sahne (gercek foto arka plan) +
## 6 kompoze parallax sahne (gradient gok + tint'li silueti dag/tepe + on plan).
## StageScene dondurur; Match parallax cam_x ile cizer.

const NAMES := ["orman", "cayir", "sonbahar", "col",
	"daglar_gunduz", "tepeler_gunbatimi", "gece_dorukleri",
	"bulutlu_ova", "sisli_orman", "sato_alacakaranlik"]

const BG := "res://backgroundpack/Backgrounds/"
const EL := "res://backgroundpack/Backgrounds/Elements/"
const PP := "res://backgroundpack/PNG/Default/"
const PAD := 140.0

const D_FAR := 0.15
const D_CLOUD := 0.25
const D_MID := 0.35
const D_NEAR := 0.70
const D_FRONT := 1.15

static var _cache := {}

static func build(name: String, _size: Vector2i) -> StageScene:
	if _cache.has(name):
		return _cache[name]
	var sc := StageScene.new()
	match name:
		"orman": _full(sc, "backgroundColorForest.png", 639, "forest")
		"cayir": _full(sc, "backgroundColorGrass.png", 639, "grass")
		"sonbahar": _full(sc, "backgroundColorFall.png", 575, "fall")
		"col": _full(sc, "backgroundColorDesert.png", 650, "desert")
		"daglar_gunduz": _mountains_day(sc)
		"tepeler_gunbatimi": _hills_sunset(sc)
		"gece_dorukleri": _peaks_night(sc)
		"bulutlu_ova": _cloudy_plain(sc)
		"sisli_orman": _misty_forest(sc)
		"sato_alacakaranlik": _castle_dusk(sc)
		_: _full(sc, "backgroundColorForest.png", 639, "forest")
	_cache[name] = sc
	return sc

# ---------------------------------------------------------------- yardimcilar
static func _img(path: String) -> Image:
	if not ResourceLoader.exists(path):
		return null
	var t = load(path)
	if t == null:
		return null
	var im: Image = t.get_image()
	if im == null:
		return null
	im = im.duplicate()
	if im.get_format() != Image.FORMAT_RGBA8:
		im.convert(Image.FORMAT_RGBA8)
	return im

static func _tex(path: String) -> Texture2D:
	if not ResourceLoader.exists(path):
		return null
	return load(path) as Texture2D

static func _tint(path: String, tint: Color, alpha := 1.0) -> Texture2D:
	var im := _img(path)
	if im == null:
		return null
	for y in im.get_height():
		for x in im.get_width():
			var a := im.get_pixel(x, y).a
			if a > 0.04:
				im.set_pixel(x, y, Color(tint.r, tint.g, tint.b, a * alpha))
	return ImageTexture.create_from_image(im)

static func _grad2(top: Color, bot: Color) -> GradientTexture2D:
	return _grad(PackedFloat32Array([0.0, 1.0]), PackedColorArray([top, bot]))

static func _grad3(a: Color, b: Color, c: Color) -> GradientTexture2D:
	return _grad(PackedFloat32Array([0.0, 0.5, 1.0]), PackedColorArray([a, b, c]))

static func _grad(offs: PackedFloat32Array, cols: PackedColorArray) -> GradientTexture2D:
	var g := Gradient.new()
	g.offsets = offs
	g.colors = cols
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	gt.width = 4
	gt.height = 256
	return gt

static func _sprite(sc: StageScene, phase: String, tex: Texture2D, cx: float,
		bottom_y: float, target_h: float, depth: float) -> void:
	if tex == null:
		return
	var tw := float(tex.get_width())
	var th := float(tex.get_height())
	var s := Vector2(tw * (target_h / th), target_h)
	var item := {"tex": tex, "depth": depth,
		"pos": Vector2(cx - s.x / 2.0, bottom_y - s.y), "size": s, "mod": Color.WHITE}
	if phase == "front":
		sc.front.append(item)
	else:
		sc.back.append(item)

static func _strip(sc: StageScene, tex: Texture2D, bottom_y: float, max_h: float, depth: float) -> void:
	if tex == null:
		return
	var w := Settings.WIDTH + 2.0 * PAD
	var th := float(tex.get_height()) * (w / float(tex.get_width()))
	if th > max_h:
		th = max_h
	sc.back.append({"tex": tex, "depth": depth,
		"pos": Vector2(-PAD, bottom_y - th), "size": Vector2(w, th), "mod": Color.WHITE})

# ---------------------------------------------------------------- tam-gorsel
static func _photo(file: String, horizon: float) -> Texture2D:
	var w := Settings.WIDTH
	var h := Settings.HEIGHT
	var fy := Settings.FLOOR_Y
	var src := _img(BG + file)
	if src == null:
		return null
	var scale := w / float(src.get_width())
	var new_h := int(src.get_height() * scale)
	src.resize(w, new_h)
	var canvas := Image.create(w, h, false, Image.FORMAT_RGBA8)
	canvas.fill(src.get_pixel(int(w / 2.0), 0))
	var dst_y := fy - int(horizon * scale)
	var src_y := 0
	if dst_y < 0:
		src_y = -dst_y
		dst_y = 0
	var bh := mini(new_h - src_y, h - dst_y)
	if bh > 0:
		canvas.blit_rect(src, Rect2i(0, src_y, w, bh), Vector2i(0, dst_y))
	return ImageTexture.create_from_image(canvas)

static func _full(sc: StageScene, file: String, horizon: float, kind: String) -> void:
	var fy := Settings.FLOOR_Y
	sc.sky = _photo(file, horizon)
	sc.has_ground = false
	var W := float(Settings.WIDTH)
	var props := {
		"forest": [["treeSmall_green1.png", 0.05, 128], ["bush1.png", 0.13, 72],
			["bush3.png", 0.89, 76], ["treeSmall_green3.png", 0.96, 134]],
		"grass": [["bushAlt1.png", 0.06, 74], ["treeSmall_green2.png", 0.14, 122],
			["bushAlt3.png", 0.88, 78], ["treeSmall_greenAlt2.png", 0.96, 126]],
		"fall": [["treeSmall_orange1.png", 0.05, 128], ["bushOrange1.png", 0.13, 72],
			["bushOrange3.png", 0.89, 76], ["treeSmall_orange3.png", 0.96, 132]],
		"desert": [["cactus1.png", 0.06, 150], ["cactus3.png", 0.14, 110],
			["cactus2.png", 0.90, 130], ["cactus1.png", 0.96, 156]],
	}
	for pr in props.get(kind, []):
		_sprite(sc, "front", _tex(PP + pr[0]), W * pr[1], fy + 24, pr[2], D_FRONT)

# ---------------------------------------------------------------- kompoze
static func _mountains_day(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad2(Color8(116, 192, 232), Color8(206, 236, 246))
	sc.has_ground = true
	sc.ground_top = Color8(74, 156, 100)
	sc.ground_bot = Color8(40, 96, 62)
	_strip(sc, _tint(EL + "cloudLayer2.png", Color8(255, 255, 255), 0.78), fy * 0.40, 130, D_CLOUD)
	_sprite(sc, "back", _tint(EL + "mountainC.png", Color8(176, 200, 224)), W * 0.30, fy + 2, fy * 0.34, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainA.png", Color8(158, 186, 214)), W * 0.52, fy + 2, fy * 0.40, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainB.png", Color8(168, 194, 220)), W * 0.72, fy + 2, fy * 0.30, D_FAR)
	_strip(sc, _tint(EL + "hills.png", Color8(86, 162, 106)), fy + 10, 90, D_NEAR)
	_sprite(sc, "front", _tex(PP + "treeSmall_green1.png"), W * 0.05, fy + 22, 120, D_FRONT)
	_sprite(sc, "front", _tex(PP + "treeSmall_green3.png"), W * 0.97, fy + 24, 130, D_FRONT)

static func _hills_sunset(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad3(Color8(64, 46, 96), Color8(232, 120, 96), Color8(255, 214, 140))
	sc.has_ground = true
	sc.ground_top = Color8(58, 40, 58)
	sc.ground_bot = Color8(30, 20, 34)
	sc.celestial.append({"type": "disc", "pos": Vector2(W * 0.5, fy * 0.72),
		"r": W * 0.055, "col": Color8(255, 240, 200), "halo": true})
	_sprite(sc, "back", _tint(EL + "mountainA.png", Color8(132, 82, 110)), W * 0.34, fy + 2, fy * 0.28, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainC.png", Color8(150, 96, 122)), W * 0.62, fy + 2, fy * 0.34, D_FAR)
	_strip(sc, _tint(EL + "hills.png", Color8(64, 38, 62)), fy + 10, 90, D_NEAR)
	_sprite(sc, "front", _tint(PP + "treeDead.png", Color8(34, 22, 34)), W * 0.06, fy + 24, 150, D_FRONT)
	_sprite(sc, "front", _tint(PP + "treeSmall_green2.png", Color8(28, 18, 30)), W * 0.96, fy + 24, 130, D_FRONT)

static func _peaks_night(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad2(Color8(14, 18, 46), Color8(54, 60, 104))
	sc.has_ground = true
	sc.ground_top = Color8(24, 28, 48)
	sc.ground_bot = Color8(10, 12, 24)
	sc.celestial.append({"type": "disc", "pos": Vector2(W * 0.76, fy * 0.26),
		"r": W * 0.035, "col": Color8(232, 236, 248)})
	var stars: Array = []
	for i in range(70):
		var sx := float((i * 137 + 53) % int(W))
		var sy := float((i * 89 + 17) % int(fy * 0.72))
		if int(sx + sy) % 3 == 0:
			stars.append(Vector2(sx, sy))
	sc.celestial.append({"type": "stars", "pts": stars, "col": Color8(222, 226, 244)})
	_sprite(sc, "back", _tint(EL + "mountainB.png", Color8(40, 46, 84)), W * 0.20, fy + 2, fy * 0.55, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainC.png", Color8(32, 38, 72)), W * 0.52, fy + 4, fy * 0.72, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainA.png", Color8(26, 30, 60)), W * 0.82, fy + 2, fy * 0.60, D_FAR)
	_strip(sc, _tint(EL + "hills.png", Color8(18, 22, 44)), fy + 8, 100, D_NEAR)
	_sprite(sc, "front", _tint(PP + "treePine.png", Color8(10, 14, 30)), W * 0.05, fy + 24, 170, D_FRONT)
	_sprite(sc, "front", _tint(PP + "treePine.png", Color8(8, 12, 26)), W * 0.96, fy + 24, 180, D_FRONT)

static func _cloudy_plain(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad2(Color8(128, 198, 234), Color8(212, 238, 248))
	sc.has_ground = true
	sc.ground_top = Color8(96, 172, 112)
	sc.ground_bot = Color8(54, 118, 74)
	_strip(sc, _tint(EL + "cloudLayer2.png", Color8(255, 255, 255), 0.80), fy * 0.34, 150, D_CLOUD)
	_sprite(sc, "back", _tint(EL + "mountainA.png", Color8(176, 206, 224), 0.8), W * 0.24, fy - 30, fy * 0.30, D_FAR)
	_strip(sc, _tint(EL + "hills.png", Color8(116, 178, 146)), fy + 8, 120, D_NEAR)
	_strip(sc, _tint(EL + "cloudLayerB1.png", Color8(250, 252, 255), 0.90), fy + 4, 170, D_NEAR)
	_sprite(sc, "front", _tex(PP + "treeSmall_green2.png"), W * 0.15, fy + 22, 120, D_FRONT)
	_sprite(sc, "front", _tex(PP + "bushAlt3.png"), W * 0.88, fy + 24, 78, D_FRONT)

static func _misty_forest(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad3(Color8(86, 118, 130), Color8(206, 168, 168), Color8(248, 224, 208))
	sc.has_ground = true
	sc.ground_top = Color8(74, 92, 78)
	sc.ground_bot = Color8(40, 52, 44)
	sc.celestial.append({"type": "disc", "pos": Vector2(W * 0.5, fy * 0.74),
		"r": W * 0.10, "col": Color(1, 0.94, 0.86, 0.30)})
	_strip(sc, _tint(EL + "hillsLarge.png", Color8(182, 184, 192), 0.63), fy - 24, 90, D_FAR)
	_strip(sc, _tint(EL + "hills.png", Color8(60, 82, 74)), fy + 8, 110, D_NEAR)
	_sprite(sc, "front", _tint(PP + "tree.png", Color8(40, 54, 48)), W * 0.06, fy + 22, 150, D_FRONT)
	_sprite(sc, "front", _tint(PP + "treePine.png", Color8(38, 52, 46)), W * 0.95, fy + 22, 160, D_FRONT)

static func _castle_dusk(sc: StageScene) -> void:
	var fy := float(Settings.FLOOR_Y)
	var W := float(Settings.WIDTH)
	sc.sky_grad = _grad3(Color8(48, 36, 78), Color8(150, 96, 128), Color8(226, 156, 132))
	sc.has_ground = true
	sc.ground_top = Color8(52, 40, 60)
	sc.ground_bot = Color8(26, 20, 32)
	_sprite(sc, "back", _tint(EL + "mountainA.png", Color8(108, 78, 118)), W * 0.30, fy + 4, fy * 0.62, D_FAR)
	_sprite(sc, "back", _tint(EL + "mountainC.png", Color8(90, 66, 104)), W * 0.86, fy + 4, fy * 0.44, D_FAR)
	_sprite(sc, "back", _tint(PP + "castleSmall.png", Color8(58, 42, 72)), W * 0.64, fy - 195, fy * 0.15, D_MID)
	_sprite(sc, "back", _tint(PP + "tower.png", Color8(48, 34, 62)), W * 0.70, fy - 195, fy * 0.26, D_MID)
	_strip(sc, _tint(EL + "mountains.png", Color8(58, 44, 74)), fy + 8, 150, D_NEAR)
	_sprite(sc, "front", _tint(PP + "treeDead.png", Color8(30, 22, 38)), W * 0.07, fy + 24, 235, D_FRONT)
	_sprite(sc, "front", _tint(PP + "treeDead.png", Color8(26, 18, 34)), W * 0.93, fy + 24, 250, D_FRONT)
