class_name SpriteAnimator
extends RefCounted
## sprites.py port — Kenney poz PNG'lerini yukler, duruma gore kare secer.
## Basarisizsa ok=false -> renderer prosedurel cizime duser.

const CONTENT_HEIGHT_RATIO := 95.0 / 128.0

var poses := {}                # int(state) -> {frames:Array, fps:int, loop:bool}
var victory_frames: Array = []
var scale := 1.0
var ok := false

func _init(char_data: CharacterData) -> void:
	var ref: SpriteRef = char_data.sprite
	if ref == null:
		return
	var base := "res://%s/PNG/Poses" % ref.folder
	var target_h: float = char_data.height * ref.scale
	# durum -> [poz adlari, fps, dongu] (WEAPON/THROW su an Fighter'da yok, atlandi)
	var pose_def := {
		Fighter.State.IDLE:    [["idle"], 1, false],
		Fighter.State.WALK:    [["walk0", "walk1", "walk2", "walk3",
								"walk4", "walk5", "walk6", "walk7"], 14, true],
		Fighter.State.CROUCH:  [["duck"], 1, false],
		Fighter.State.BLOCK:   [["hold"], 1, false],
		Fighter.State.JUMP:    [["jump"], 1, false],
		Fighter.State.HITSTUN: [["hit"], 1, false],
		Fighter.State.KO:      [["hurt", "fallDown", "down"], 9, false],
		Fighter.State.PUNCH:   [["attack0", "attack1", "attack2"], 0, false],
		Fighter.State.KICK:    [["attack1", "kick", "kick"], 0, false],
		Fighter.State.SPECIAL: [["attack1", "attack2"], 6, false],
	}
	var scale_set := false
	for state in pose_def:
		var names: Array = pose_def[state][0]
		var frames: Array = []
		for nm in names:
			var path := "%s/%s_%s.png" % [base, ref.prefix, nm]
			if ResourceLoader.exists(path):
				var tex := load(path) as Texture2D
				if tex != null:
					if not scale_set:
						scale = target_h / (tex.get_height() * CONTENT_HEIGHT_RATIO)
						scale_set = true
					frames.append(tex)
		if not frames.is_empty():
			poses[state] = {"frames": frames, "fps": int(pose_def[state][1]),
				"loop": bool(pose_def[state][2])}
	# kazanma pozu (cheer0/cheer1) — durum degil, victory bayragiyla secilir
	if scale_set:
		for nm in ["cheer0", "cheer1"]:
			var path := "%s/%s_%s.png" % [base, ref.prefix, nm]
			if ResourceLoader.exists(path):
				var tex := load(path) as Texture2D
				if tex != null:
					victory_frames.append(tex)
	ok = poses.has(Fighter.State.IDLE)

func frame_for(f: Fighter):  # -> Texture2D veya null
	if f.victory and not victory_frames.is_empty():
		var vi := int(f.state_frame * 3 / Settings.FPS) % victory_frames.size()
		return victory_frames[vi]
	var st: int = f.state
	if st == Fighter.State.HITSTUN and f.knocked_down:
		st = Fighter.State.KO
	var entry = poses.get(st)
	if entry == null:
		entry = poses.get(Fighter.State.IDLE)
	if entry == null:
		return null
	var frames: Array = entry["frames"]
	var n := frames.size()
	if n == 0:
		return null
	var idx: int
	if (f.state == Fighter.State.PUNCH or f.state == Fighter.State.KICK) and f.attack != null:
		var progress := minf(0.999, f.state_frame / float(maxi(1, f.attack.total)))
		idx = int(progress * n)
	elif int(entry["fps"]) <= 0 or n == 1:
		idx = 0
	else:
		idx = int(f.state_frame * int(entry["fps"]) / Settings.FPS)
		idx = (idx % n) if bool(entry["loop"]) else mini(idx, n - 1)
	return frames[clampi(idx, 0, n - 1)]
