extends Node
## Ayar + rekor kaliciligi (user://config.json) — autoload: Config.

var data := {"music_vol": 0.28, "sfx_vol": 1.0, "wins": 0, "losses": 0, "fastest_ko": 0}

func _ready() -> void:
	load_cfg()

func load_cfg() -> void:
	if not FileAccess.file_exists("user://config.json"):
		return
	var f := FileAccess.open("user://config.json", FileAccess.READ)
	if f == null:
		return
	var j = JSON.parse_string(f.get_as_text())
	if j is Dictionary:
		for k in j:
			data[k] = j[k]

func save_cfg() -> void:
	var f := FileAccess.open("user://config.json", FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(data))

func record_result(won: bool, ko_frames: int) -> void:
	if won:
		data["wins"] = int(data["wins"]) + 1
	else:
		data["losses"] = int(data["losses"]) + 1
	if won and ko_frames > 0 and (int(data["fastest_ko"]) == 0 or ko_frames < int(data["fastest_ko"])):
		data["fastest_ko"] = ko_frames
	save_cfg()
