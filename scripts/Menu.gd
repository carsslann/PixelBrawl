extends Node2D
## Karakter / rakip / zorluk / mod / sahne secimi (sprite onizleme + stat bari).

signal selected(cfg: Dictionary)
signal quit_menu()

const MODES := ["versus", "arcade", "training"]
const MODE_LABELS := {"versus": "Versus (vs Bot)", "arcade": "Arcade", "training": "Antrenman"}

var rows := ["mode", "p1", "p2", "difficulty", "stage"]
var row_labels := {"mode": "MOD", "p1": "KARAKTERİN", "p2": "RAKİP",
	"difficulty": "ZORLUK", "stage": "SAHNE"}
var selected_row := 0
var mode_idx := 0
var p1_idx := 0
var p2_idx := 1
var diff_idx := 0
var stage_idx := 0      # 0 = rastgele
var _preview := {}
var _shot := OS.get_environment("PIXELBRAWL_SHOT") == "menu"
var _shot_f := 0

func _ready() -> void:
	Audio.play_music(0.28)
	queue_redraw()

func _process(_d: float) -> void:
	if not _shot:
		return
	_shot_f += 1
	if _shot_f == 30:
		get_viewport().get_texture().get_image().save_png("user://pixelbrawl_menu.png")
		print("MENU SHOT: " + ProjectSettings.globalize_path("user://pixelbrawl_menu.png"))
		get_tree().quit()

func _stages() -> Array:
	return ["rastgele"] + Stages.NAMES

func _preview_tex(key: String) -> Texture2D:
	if not _preview.has(key):
		var c: CharacterData = Characters.get_char(key)
		var t: Texture2D = null
		if c.sprite != null:
			var path := "res://%s/PNG/Poses/%s_idle.png" % [c.sprite.folder, c.sprite.prefix]
			if ResourceLoader.exists(path):
				t = load(path)
		_preview[key] = t
	return _preview[key]

func _input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var kc := (event as InputEventKey).keycode
	if kc == KEY_ESCAPE:
		quit_menu.emit()
	elif kc == KEY_ENTER or kc == KEY_KP_ENTER:
		Audio.play("menu_select")
		var st: String = _stages()[stage_idx]
		if st == "rastgele":
			st = Stages.NAMES[randi() % Stages.NAMES.size()]
		selected.emit({
			"p1": Characters.CHARACTER_ORDER[p1_idx],
			"p2": Characters.CHARACTER_ORDER[p2_idx],
			"difficulty": AIController.DIFFICULTY_ORDER[diff_idx],
			"mode": MODES[mode_idx],
			"stage": st})
	elif kc == KEY_UP or kc == KEY_W:
		selected_row = (selected_row - 1 + rows.size()) % rows.size()
		Audio.play("menu_move"); queue_redraw()
	elif kc == KEY_DOWN or kc == KEY_S:
		selected_row = (selected_row + 1) % rows.size()
		Audio.play("menu_move"); queue_redraw()
	elif kc == KEY_LEFT or kc == KEY_A:
		_change(-1); Audio.play("menu_move"); queue_redraw()
	elif kc == KEY_RIGHT or kc == KEY_D:
		_change(1); Audio.play("menu_move"); queue_redraw()

func _change(step: int) -> void:
	var n := Characters.CHARACTER_ORDER.size()
	var row: String = rows[selected_row]
	match row:
		"mode": mode_idx = (mode_idx + step + MODES.size()) % MODES.size()
		"p1": p1_idx = (p1_idx + step + n) % n
		"p2": p2_idx = (p2_idx + step + n) % n
		"difficulty":
			var d := AIController.DIFFICULTY_ORDER.size()
			diff_idx = (diff_idx + step + d) % d
		"stage":
			var s := _stages().size()
			stage_idx = (stage_idx + step + s) % s

func _row_value(row: String) -> String:
	match row:
		"mode": return MODE_LABELS[MODES[mode_idx]]
		"p1": return Characters.get_char(Characters.CHARACTER_ORDER[p1_idx]).name
		"p2": return Characters.get_char(Characters.CHARACTER_ORDER[p2_idx]).name
		"difficulty": return AIController.DIFFICULTY_LABELS[AIController.DIFFICULTY_ORDER[diff_idx]]
		"stage": return _stages()[stage_idx].capitalize()
	return ""

func _ct(font: Font, s: String, cx: float, y: float, size: int, col: Color) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	draw_string(font, Vector2(cx - w / 2.0 + 3, y + 3), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Settings.BLACK)
	draw_string(font, Vector2(cx - w / 2.0, y), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func _statbar(x: float, y: float, label: String, frac: float) -> void:
	var font := ThemeDB.fallback_font
	draw_string(font, Vector2(x, y + 9), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Settings.WHITE)
	var bx := x + 52.0
	draw_rect(Rect2(bx, y, 90, 8), Settings.SUPER_BACK)
	draw_rect(Rect2(bx, y, 90 * clampf(frac, 0.05, 1.0), 8), Settings.HP_MAIN)

func _stats(key: String, x: float, y: float) -> void:
	var c: CharacterData = Characters.get_char(key)
	_statbar(x, y, "Güç", (c.kick.damage - 9) / 9.0)
	_statbar(x, y + 14, "Hız", (c.walk_speed - 3.0) / 2.6)
	_statbar(x, y + 28, "Menzil", (c.kick.hit_w - 88) / 22.0)
	_statbar(x, y + 42, "Can", (c.max_health - 84) / 42.0)

func _draw() -> void:
	var font := ThemeDB.fallback_font
	var cx := Settings.WIDTH / 2.0
	draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.FLOOR_Y), Settings.SKY_TOP)
	draw_rect(Rect2(0, Settings.FLOOR_Y, Settings.WIDTH, Settings.HEIGHT - Settings.FLOOR_Y), Settings.FLOOR_COLOR)
	_ct(font, "SOKAK KAVGACISI", cx, 96, 62, Settings.HP_MAIN)

	for i in rows.size():
		var row: String = rows[i]
		var y := 200.0 + i * 58.0
		var sel := i == selected_row
		var col := Settings.HP_MAIN if sel else Settings.WHITE
		var lbl: String = row_labels[row]
		var lw := font.get_string_size(lbl, HORIZONTAL_ALIGNMENT_LEFT, -1, 30).x
		draw_string(font, Vector2(cx - 40.0 - lw, y), lbl, HORIZONTAL_ALIGNMENT_LEFT, -1, 30, col)
		var val := _row_value(row)
		if sel:
			val = "◄  %s  ►" % val
		draw_string(font, Vector2(cx + 40.0, y), val, HORIZONTAL_ALIGNMENT_LEFT, -1, 30, col)

	var base_y := 600.0
	for pair in [[p1_idx, -1.0], [p2_idx, 1.0]]:
		var idx: int = pair[0]
		var side: float = pair[1]
		var key: String = Characters.CHARACTER_ORDER[idx]
		var x := cx + side * 440.0
		draw_set_transform(Vector2(x, base_y + 4.0), 0.0, Vector2(1, 0.28))
		draw_circle(Vector2.ZERO, 76.0, Color(0, 0, 0, 0.35))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var tex := _preview_tex(key)
		if tex != null:
			var th := 280.0
			var sz := Vector2(tex.get_width(), tex.get_height()) * (th / tex.get_height())
			if side > 0:
				draw_set_transform(Vector2(x, base_y), 0.0, Vector2(-1, 1))
				draw_texture_rect(tex, Rect2(-sz.x / 2.0, -sz.y, sz.x, sz.y), false)
				draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
			else:
				draw_texture_rect(tex, Rect2(x - sz.x / 2.0, base_y - sz.y, sz.x, sz.y), false)
		_stats(key, x - 71.0, base_y - 290.0)

	var helps := ["ENTER: Başla     ESC: Geri     Ok / WASD: Seçim",
		"A/D yürü  W zıpla  S çömel  J yumruk  K tekme  L özel  I atma  A/D çift-tuş: dash"]
	for i in helps.size():
		_ct(font, helps[i], cx, Settings.HEIGHT - 66.0 + i * 24.0, 19, Settings.FLOOR_LINE)
