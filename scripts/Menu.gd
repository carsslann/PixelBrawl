extends Node2D
## menu.py port — karakter / rakip / zorluk secimi (sprite onizlemeli).
## ENTER -> selected(cfg); ESC -> quit_menu.

signal selected(cfg: Dictionary)
signal quit_menu()

var rows := ["p1", "p2", "difficulty"]
var row_labels := {"p1": "KARAKTERİN", "p2": "RAKİP", "difficulty": "ZORLUK"}
var selected_row := 0
var p1_idx := 0
var p2_idx := 1
var diff_idx := 0        # kolay (bot varsayilan kolay)
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
		var img := get_viewport().get_texture().get_image()
		img.save_png("user://pixelbrawl_menu.png")
		print("MENU SHOT: " + ProjectSettings.globalize_path("user://pixelbrawl_menu.png"))
		get_tree().quit()

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
		selected.emit({
			"p1": Characters.CHARACTER_ORDER[p1_idx],
			"p2": Characters.CHARACTER_ORDER[p2_idx],
			"difficulty": AIController.DIFFICULTY_ORDER[diff_idx]})
	elif kc == KEY_UP or kc == KEY_W:
		selected_row = (selected_row - 1 + rows.size()) % rows.size()
		Audio.play("menu_move")
		queue_redraw()
	elif kc == KEY_DOWN or kc == KEY_S:
		selected_row = (selected_row + 1) % rows.size()
		Audio.play("menu_move")
		queue_redraw()
	elif kc == KEY_LEFT or kc == KEY_A:
		_change(-1)
		Audio.play("menu_move")
		queue_redraw()
	elif kc == KEY_RIGHT or kc == KEY_D:
		_change(1)
		Audio.play("menu_move")
		queue_redraw()

func _change(step: int) -> void:
	var n := Characters.CHARACTER_ORDER.size()
	var row: String = rows[selected_row]
	if row == "p1":
		p1_idx = (p1_idx + step + n) % n
	elif row == "p2":
		p2_idx = (p2_idx + step + n) % n
	else:
		var d := AIController.DIFFICULTY_ORDER.size()
		diff_idx = (diff_idx + step + d) % d

func _row_value(row: String) -> String:
	if row == "p1":
		return Characters.get_char(Characters.CHARACTER_ORDER[p1_idx]).name
	if row == "p2":
		return Characters.get_char(Characters.CHARACTER_ORDER[p2_idx]).name
	return AIController.DIFFICULTY_LABELS[AIController.DIFFICULTY_ORDER[diff_idx]]

func _ctext(font: Font, s: String, cx: float, y: float, size: int, col: Color) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	draw_string(font, Vector2(cx - w / 2.0 + 3, y + 3), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Settings.BLACK)
	draw_string(font, Vector2(cx - w / 2.0, y), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func _draw() -> void:
	var font := ThemeDB.fallback_font
	var cx := Settings.WIDTH / 2.0
	draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.FLOOR_Y), Settings.SKY_TOP)
	draw_rect(Rect2(0, Settings.FLOOR_Y, Settings.WIDTH, Settings.HEIGHT - Settings.FLOOR_Y), Settings.FLOOR_COLOR)

	_ctext(font, "SOKAK KAVGACISI", cx, 150, 80, Settings.HP_MAIN)
	_ctext(font, "çakma street fighter", cx, 208, 24, Settings.WHITE)

	for i in rows.size():
		var row: String = rows[i]
		var y := 330.0 + i * 70.0
		var sel := i == selected_row
		var col := Settings.HP_MAIN if sel else Settings.WHITE
		var lbl: String = row_labels[row]
		var lw := font.get_string_size(lbl, HORIZONTAL_ALIGNMENT_LEFT, -1, 34).x
		draw_string(font, Vector2(cx - 40.0 - lw, y), lbl, HORIZONTAL_ALIGNMENT_LEFT, -1, 34, col)
		var val := _row_value(row)
		if sel:
			val = "◄  %s  ►" % val
		draw_string(font, Vector2(cx + 40.0, y), val, HORIZONTAL_ALIGNMENT_LEFT, -1, 34, col)

	var base_y := 590.0
	for pair in [[p1_idx, -1.0], [p2_idx, 1.0]]:
		var idx: int = pair[0]
		var side: float = pair[1]
		var key: String = Characters.CHARACTER_ORDER[idx]
		var x := cx + side * 430.0
		draw_set_transform(Vector2(x, base_y + 4.0), 0.0, Vector2(1, 0.28))
		draw_circle(Vector2.ZERO, 78.0, Color(0, 0, 0, 0.35))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var tex := _preview_tex(key)
		if tex != null:
			var th := 300.0
			var sz := Vector2(tex.get_width(), tex.get_height()) * (th / tex.get_height())
			if side > 0:
				draw_set_transform(Vector2(x, base_y), 0.0, Vector2(-1, 1))
				draw_texture_rect(tex, Rect2(-sz.x / 2.0, -sz.y, sz.x, sz.y), false)
				draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
			else:
				draw_texture_rect(tex, Rect2(x - sz.x / 2.0, base_y - sz.y, sz.x, sz.y), false)
		else:
			var c: CharacterData = Characters.get_char(key)
			draw_rect(Rect2(x - c.width / 2.0, base_y - c.height, c.width, c.height), c.color)

	var helps := ["ENTER: Başla       ESC: Çıkış       Ok tuşları / WASD: Seçim",
		"A/D yürü   W zıpla   S çömel   J yumruk   K tekme   L özel   (geri tut = blok)"]
	for i in helps.size():
		_ctext(font, helps[i], cx, Settings.HEIGHT - 74.0 + i * 26.0, 20, Settings.FLOOR_LINE)
