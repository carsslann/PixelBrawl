class_name FxSprites
extends RefCounted
## fx_sprites.py port — atesefekt/ 16x16 sheet'lerinden ates topu kareleri.
## Fireball: satir 15, sutun 16/18/20 (her kare 32x16), 8 renk. Kareler saga bakar.

const FX := "res://atesefekt/All_Fire_Bullet_Pixel_16x16_%02d.png"
const CELL := 16
const FIREBALL_ROW := 15
const FIREBALL_COL0 := 16
const FIREBALL_COUNT := 3
const FIREBALL_CELLS_W := 2

static var _sheets := {}       # ci -> Image
static var _frames := {}       # key -> Array[Texture2D]

const _CORES := [
	Color8(255, 210, 70), Color8(255, 170, 60), Color8(120, 210, 255), Color8(120, 210, 255),
	Color8(255, 230, 120), Color8(200, 150, 255), Color8(200, 150, 255), Color8(255, 180, 200),
]

static func _sheet(ci: int) -> Image:
	ci = ci % 8
	if _sheets.has(ci):
		return _sheets[ci]
	var im: Image = null
	var path := FX % ci
	if ResourceLoader.exists(path):
		var t = load(path)
		if t != null:
			im = t.get_image()
			if im != null:
				im = im.duplicate()
				if im.get_format() != Image.FORMAT_RGBA8:
					im.convert(Image.FORMAT_RGBA8)
	_sheets[ci] = im
	return im

static func fireball_frames(color: int, scale := 3.0) -> Array:
	var key := "%d_%d" % [color % 8, int(scale * 10)]
	if _frames.has(key):
		return _frames[key]
	var out: Array = []
	var sheet := _sheet(color)
	if sheet != null:
		var bw := CELL * FIREBALL_CELLS_W
		for i in range(FIREBALL_COUNT):
			var col0 := FIREBALL_COL0 + i * FIREBALL_CELLS_W
			var reg := Rect2i(col0 * CELL, FIREBALL_ROW * CELL, bw, CELL)
			if reg.position.x + reg.size.x <= sheet.get_width() and reg.position.y + reg.size.y <= sheet.get_height():
				var sub := sheet.get_region(reg)
				sub.resize(int(bw * scale), int(CELL * scale), Image.INTERPOLATE_NEAREST)
				out.append(ImageTexture.create_from_image(sub))
	if out.is_empty():
		out = _fallback(color, scale)
	_frames[key] = out
	return out

static func _fallback(color: int, scale: float) -> Array:
	var core: Color = _CORES[color % 8]
	var size := int(32 * scale)
	var im := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var c := size / 2.0
	for y in size:
		for x in size:
			var d := Vector2(x - c, y - c).length() / (size / 2.0)
			if d <= 1.0:
				im.set_pixel(x, y, Color(core.r, core.g, core.b, 1.0 - d * d))
	var tex := ImageTexture.create_from_image(im)
	return [tex, tex, tex]
