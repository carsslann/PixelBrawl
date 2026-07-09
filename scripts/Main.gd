extends Node2D
## PixelBrawl — Godot port. Su an Faz 1 (veri katmani) dogrulama harness'i.

func _ready() -> void:
	print("== PixelBrawl port — Faz 1 (veri katmani) testi ==")
	print("Settings: %dx%d @%d fps, FLOOR_Y=%d, SUPER_MAX=%d"
		% [Settings.WIDTH, Settings.HEIGHT, Settings.FPS, Settings.FLOOR_Y, Settings.SUPER_MAX])
	print("Toplam karakter: %d -> %s"
		% [Characters.CHARACTER_ORDER.size(), str(Characters.CHARACTER_ORDER)])

	for key in Characters.CHARACTER_ORDER:
		var c: CharacterData = Characters.get_char(key)
		print("  %-7s can:%3d  yumruk(d%d,t%d)  tekme(d%d,t%d)  ozel(renk%d,d%d,hiz%.1f)"
			% [c.name, c.max_health, c.punch.damage, c.punch.total,
			   c.kick.damage, c.kick.total, c.special.color, c.special.damage, c.special.speed])

	# turetilmis saldirilari dogrula (EFE)
	var efe: CharacterData = Characters.get_char("efe")
	print("EFE turetilmis:")
	print("  alcak yumruk: h_frac=%.2f guard=%s" % [efe.crouch_punch.height_frac, efe.crouch_punch.guard])
	print("  supurme: guard=%s knockdown=%s chain=%d hit_w=%d"
		% [efe.sweep.guard, str(efe.sweep.knockdown), efe.sweep.chain, efe.sweep.hit_w])
	print("  hava yumruk: guard=%s airborne=%s hit_h=%d"
		% [efe.jump_punch.guard, str(efe.jump_punch.airborne), efe.jump_punch.hit_h])
	print("Faz 1: veri katmani OK.")

	if DisplayServer.get_name() == "headless":
		get_tree().quit()
