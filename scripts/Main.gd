extends Node
## Baslik -> Menu -> Match akisi (+ arcade zinciri). Ana sahne.

var current: Node = null
var arcade := false
var arcade_cfg := {}
var arcade_queue: Array = []

func _ready() -> void:
	var shot := OS.get_environment("PIXELBRAWL_SHOT")
	if shot == "1":
		_start_match({"p1": "efe", "p2": "goron", "difficulty": "kolay", "mode": "versus", "stage": "rastgele"})
	elif shot == "train":
		_start_match({"p1": "efe", "p2": "goron", "difficulty": "kolay", "mode": "training", "stage": "cayir"})
	elif shot == "menu":
		_show_menu()
	else:
		_show_title()

func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	match (event as InputEventKey).keycode:
		KEY_F11:
			var w := get_window()
			w.mode = Window.MODE_WINDOWED if w.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
		KEY_M:
			Audio.toggle_mute()
		KEY_MINUS:
			Engine.time_scale = clampf(Engine.time_scale - 0.1, 0.4, 1.0)
		KEY_EQUAL:
			Engine.time_scale = clampf(Engine.time_scale + 0.1, 0.4, 1.0)

func _swap(node: Node) -> void:
	if current != null:
		current.queue_free()
	add_child(node)
	current = node

func _show_title() -> void:
	_swap(preload("res://scenes/TitleScreen.tscn").instantiate())
	current.start.connect(_show_menu)

func _show_menu() -> void:
	arcade = false
	_swap(preload("res://scenes/Menu.tscn").instantiate())
	current.selected.connect(_on_selected)
	current.quit_menu.connect(_show_title)

func _on_selected(cfg: Dictionary) -> void:
	if cfg.get("mode", "versus") == "arcade":
		arcade = true
		arcade_cfg = cfg.duplicate()
		arcade_queue = []
		for k in Characters.CHARACTER_ORDER:
			if k != cfg["p1"]:
				arcade_queue.append(k)
		_next_arcade()
	else:
		_start_match(cfg)

func _next_arcade() -> void:
	if arcade_queue.is_empty():
		arcade = false
		_show_menu()          # tum rakipler yenildi (basitlestirilmis ending)
		return
	var opp = arcade_queue.pop_front()
	var beaten := 5 - arcade_queue.size()
	var diff := "kolay" if beaten <= 1 else ("orta" if beaten <= 3 else "zor")
	var cfg := arcade_cfg.duplicate()
	cfg["p2"] = opp
	cfg["difficulty"] = diff
	_start_match(cfg)

func _start_match(cfg: Dictionary) -> void:
	# cfg, _ready'den ONCE atanmali (add_child _ready'yi tetikler)
	if current != null:
		current.queue_free()
	var m = preload("res://scenes/Match.tscn").instantiate()
	m.cfg = cfg
	m.finished.connect(_on_match_finished)
	add_child(m)
	current = m

func _on_match_finished(result: String) -> void:
	if result == "quit":
		get_tree().quit()
	elif result == "arcade_win" and arcade:
		_next_arcade()
	else:
		arcade = false
		_show_menu()
