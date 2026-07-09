class_name SpriteRef
extends RefCounted
## characters.py SpriteRef birebir — bir karakterin Kenney poz paketi referansi.

var folder: String   # proje kokune gore, or. "charac/Male adventurer"
var prefix: String   # dosya on eki, or. "character_maleAdventurer"
var scale: float     # gorunur boyu data.height'in bu kati kadar yap

func _init(p_folder := "", p_prefix := "", p_scale := 1.0) -> void:
	folder = p_folder
	prefix = p_prefix
	scale = p_scale
