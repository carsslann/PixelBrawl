extends Node
## main.py port — Menu <-> Match akisi (ana sahne).

var current: Node = null

func _ready() -> void:
	if OS.get_environment("PIXELBRAWL_SHOT") == "1":
		_on_selected({"p1": "efe", "p2": "goron", "difficulty": "kolay"})
	else:
		_show_menu()

func _show_menu() -> void:
	if current != null:
		current.queue_free()
	var menu = preload("res://scenes/Menu.tscn").instantiate()
	menu.selected.connect(_on_selected)
	menu.quit_menu.connect(func(): get_tree().quit())
	add_child(menu)
	current = menu

func _on_selected(cfg: Dictionary) -> void:
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
	else:
		_show_menu()
