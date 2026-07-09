extends Node2D
## Baslik ekrani — bir tusa basinca menuye.

signal start()
var _t := 0

func _ready() -> void:
	Audio.play_music(0.28)

func _process(_d: float) -> void:
	_t += 1
	queue_redraw()

func _input(event: InputEvent) -> void:
	if (event is InputEventKey and event.pressed and not event.echo) \
			or (event is InputEventJoypadButton and event.pressed):
		Audio.play("menu_select")
		start.emit()

func _ct(font: Font, s: String, cx: float, y: float, size: int, col: Color) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	draw_string(font, Vector2(cx - w / 2.0 + 4, y + 4), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Settings.BLACK)
	draw_string(font, Vector2(cx - w / 2.0, y), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func _draw() -> void:
	var font := ThemeDB.fallback_font
	var cx := Settings.WIDTH / 2.0
	draw_rect(Rect2(0, 0, Settings.WIDTH, Settings.HEIGHT), Settings.SKY_TOP)
	draw_rect(Rect2(0, Settings.HEIGHT * 0.62, Settings.WIDTH, Settings.HEIGHT * 0.38), Settings.FLOOR_COLOR)
	_ct(font, "PIXELBRAWL", cx, Settings.HEIGHT * 0.36, 120, Settings.HP_MAIN)
	_ct(font, "SOKAK KAVGACISI", cx, Settings.HEIGHT * 0.36 + 78, 36, Settings.WHITE)
	if (_t / 30) % 2 == 0:
		_ct(font, "Başlamak için bir tuşa bas", cx, Settings.HEIGHT * 0.74, 28, Settings.TIMER_COLOR)
	var rec := "Galibiyet: %d   Mağlubiyet: %d" % [int(Config.data["wins"]), int(Config.data["losses"])]
	_ct(font, rec, cx, Settings.HEIGHT - 40.0, 18, Settings.FLOOR_LINE)
