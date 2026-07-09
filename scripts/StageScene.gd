class_name StageScene
extends RefCounted
## Bir sahnenin parallax katmanlari. draw_back (dovusculerDEN once) +
## draw_front (sonra). cam_x ile uzak katman az, yakin cok kayar.

var sky: Texture2D = null          # tam-ekran foto (tam-gorsel sahneler)
var sky_grad: Texture2D = null     # gradient gok (kompoze), 0..FLOOR_Y
var has_ground := false
var ground_top := Color.BLACK
var ground_bot := Color.BLACK
var celestial: Array = []          # {type:"disc"/"stars", ...}
var back: Array = []               # {tex, depth, pos:Vector2, size:Vector2, mod:Color}
var front: Array = []
var darken_h := 150.0

static var _darken: GradientTexture2D = null

static func _darken_tex() -> GradientTexture2D:
	if _darken == null:
		var g := Gradient.new()
		g.offsets = PackedFloat32Array([0.0, 1.0])
		g.colors = PackedColorArray([Color(0, 0, 0, 0.0), Color(0, 0, 0, 0.5)])
		_darken = GradientTexture2D.new()
		_darken.gradient = g
		_darken.fill_from = Vector2(0, 0)
		_darken.fill_to = Vector2(0, 1)
		_darken.width = 4
		_darken.height = 128
	return _darken

func draw_back(ci: CanvasItem, cam_x: float) -> void:
	if sky != null:
		ci.draw_texture_rect(sky, Rect2(0, 0, Settings.WIDTH, Settings.HEIGHT), false)
	if sky_grad != null:
		ci.draw_texture_rect(sky_grad, Rect2(0, 0, Settings.WIDTH, Settings.FLOOR_Y), false)
	for c in celestial:
		if c["type"] == "disc":
			ci.draw_circle(c["pos"], c["r"], c["col"])
			if c.has("halo"):
				ci.draw_circle(c["pos"], c["r"] * 1.9, Color(c["col"].r, c["col"].g, c["col"].b, 0.12))
		elif c["type"] == "stars":
			for s in c["pts"]:
				ci.draw_circle(s, 1.3, c["col"])
	for l in back:
		var x: float = l["pos"].x - cam_x * l["depth"]
		ci.draw_texture_rect(l["tex"], Rect2(x, l["pos"].y, l["size"].x, l["size"].y), false, l["mod"])
	if has_ground:
		ci.draw_rect(Rect2(0, Settings.FLOOR_Y, Settings.WIDTH, Settings.HEIGHT - Settings.FLOOR_Y), ground_top)
		ci.draw_rect(Rect2(0, Settings.HEIGHT - 60, Settings.WIDTH, 60), ground_bot)
	ci.draw_texture_rect(_darken_tex(), Rect2(0, Settings.HEIGHT - darken_h, Settings.WIDTH, darken_h), false)

func draw_front(ci: CanvasItem, cam_x: float) -> void:
	for l in front:
		var x: float = l["pos"].x - cam_x * l["depth"]
		ci.draw_texture_rect(l["tex"], Rect2(x, l["pos"].y, l["size"].x, l["size"].y), false, l["mod"])
