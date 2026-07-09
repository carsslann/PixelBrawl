extends Node2D
## PixelBrawl port — Faz 2+3 (Fighter + Combat mantik) dogrulama harness'i.

var _pass := 0
var _fail := 0

func _check(label: String, got, want) -> void:
	var ok: bool = str(got) == str(want)
	if ok: _pass += 1
	else: _fail += 1
	print("  [%s] %s: %s (beklenen %s)" % ["OK " if ok else "HATA", label, str(got), str(want)])

func _ready() -> void:
	print("== Faz 2+3: Fighter + Combat mantik testi ==")
	var efe: CharacterData = Characters.get_char("efe")

	# --- Test 1: yumruk isabet + hasar + kombo ---
	print("Test 1: yumruk isabeti")
	var p1 := Fighter.new(efe, 600.0, 1)
	var p2 := Fighter.new(efe, 700.0, -1)
	var punch := Inputs.new(); punch.punch = true
	var idle := Inputs.new()
	p1.update(punch, p2)           # yumruk basla
	var hit_dmg := 0
	var hit_combo := 0
	for i in range(16):
		p1.update(idle, p2)
		p2.update(idle, p1)
		for e in Combat.resolve_hits(p1, p2):
			hit_dmg = e.damage
			hit_combo = e.combo
		Combat.push_apart(p1, p2)
	_check("hasar", hit_dmg, 8)                     # 8 * scale1.0
	_check("kombo", hit_combo, 1)
	_check("p2 can", p2.health, 92)
	_check("p2 hitstun'a girdi", p2.state == Fighter.State.HITSTUN, true)

	# --- Test 2: blok -> chip hasari ---
	print("Test 2: blok (chip hasari)")
	var b1 := Fighter.new(efe, 600.0, 1)
	var b2 := Fighter.new(efe, 700.0, -1)
	var block := Inputs.new(); block.block = true
	b1.update(punch, b2)
	b2.update(block, b1)
	var blk_dmg := -1
	var was_blocked := false
	for i in range(16):
		b1.update(idle, b2)
		b2.update(block, b1)
		for e in Combat.resolve_hits(b1, b2):
			blk_dmg = e.damage
			was_blocked = e.blocked
		Combat.push_apart(b1, b2)
	_check("bloklandi", was_blocked, true)
	_check("chip hasar", blk_dmg, 1)                # round(8*0.15)=1
	_check("b2 can", b2.health, 99)
	_check("b2 hala blokta", b2.state == Fighter.State.BLOCK, true)

	# --- Test 3: comel hurtbox alcalir, supurme knockdown ---
	print("Test 3: comelme + supurme")
	var c1 := Fighter.new(efe, 600.0, 1)
	var down := Inputs.new(); down.down = true
	c1.update(down, Fighter.new(efe, 700.0, -1))
	_check("comel state", c1.state == Fighter.State.CROUCH, true)
	var full_h := efe.height
	var crouch_h := c1.hurtbox().size.y
	_check("comel hurtbox alcaldi", crouch_h < full_h, true)
	_check("supurme knockdown", efe.sweep.knockdown, true)

	# --- Test 4: sinir clamp (sahne kenari) ---
	print("Test 4: sahne siniri")
	var e1 := Fighter.new(efe, 5000.0, 1)   # cok saga
	e1.update(idle, Fighter.new(efe, 100.0, -1))
	var max_x: float = Settings.WIDTH - Settings.STAGE_MARGIN - efe.width / 2.0
	_check("sag sinir", e1.x <= max_x, true)

	print("== SONUC: %d gecti, %d kaldi ==" % [_pass, _fail])
	if DisplayServer.get_name() == "headless":
		get_tree().quit()
