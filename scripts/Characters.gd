extends Node
## characters.py birebir port — CHARACTERS veri tablosu (autoload adi: Characters).
## Karaktere ozel ates renk eslemesi: efe=altin(0) ada=bordo(7) zeynep=mavi(2)
## mira=mor(5) robo=celik(6) goron=yesil(3).

const CHARACTER_ORDER := ["efe", "ada", "zeynep", "mira", "robo", "goron"]
var CHARACTERS := {}

func _init() -> void:
	_build()

func _punch(dmg, su, act, rec, hs, kb, w, h) -> AttackData:
	return AttackData.new("yumruk", dmg, su, act, rec, hs, kb, w, h, 0.74, "high", false, 1, false)

func _kick(dmg, su, act, rec, hs, kb, w, h) -> AttackData:
	return AttackData.new("tekme", dmg, su, act, rec, hs, kb, w, h, 0.46, "high", false, 2, false)

func _spec(color, dmg, speed, cast, rec, cost, kb, hs) -> SpecialSpec:
	return SpecialSpec.new(color, dmg, speed, cast, rec, cost, kb, hs)

func _build() -> void:
	# --- dengeli ---
	CHARACTERS["efe"] = CharacterData.new(
		"efe", "EFE", Color8(210, 150, 60), 64, 172, 4.3, 4.7, -18.0, 100,
		_punch(8, 5, 4, 9, 14, 6.5, 80, 28), _kick(13, 9, 5, 14, 20, 9.0, 100, 32),
		SpriteRef.new("charac/Male adventurer", "character_maleAdventurer", 1.16),
		_spec(0, 14, 9.0, 14, 20, 50, 7.0, 18))
	CHARACTERS["ada"] = CharacterData.new(
		"ada", "ADA", Color8(196, 90, 120), 60, 168, 4.4, 4.8, -18.2, 98,
		_punch(8, 5, 4, 8, 14, 6.3, 80, 28), _kick(12, 9, 5, 13, 19, 8.6, 98, 32),
		SpriteRef.new("charac/Male person", "character_malePerson", 1.16),
		_spec(7, 14, 9.0, 14, 20, 50, 7.0, 18))
	# --- hizli ---
	CHARACTERS["zeynep"] = CharacterData.new(
		"zeynep", "ZEYNEP", Color8(58, 150, 200), 56, 164, 5.2, 5.7, -18.6, 88,
		_punch(7, 4, 4, 8, 13, 6.0, 74, 26), _kick(11, 8, 5, 12, 18, 8.0, 92, 30),
		SpriteRef.new("charac/Female adventurer", "character_femaleAdventurer", 1.14),
		_spec(2, 10, 13.0, 10, 16, 40, 5.5, 14))
	CHARACTERS["mira"] = CharacterData.new(
		"mira", "MİRA", Color8(180, 96, 200), 56, 164, 5.4, 5.9, -18.8, 85,
		_punch(7, 4, 4, 7, 12, 5.8, 74, 26), _kick(10, 7, 5, 11, 17, 7.6, 90, 30),
		SpriteRef.new("charac/Female person", "character_femalePerson", 1.14),
		_spec(5, 11, 12.0, 11, 17, 42, 6.0, 15))
	# --- agir / tank ---
	CHARACTERS["robo"] = CharacterData.new(
		"robo", "ROBO", Color8(120, 130, 150), 72, 176, 3.4, 3.7, -17.6, 118,
		_punch(10, 7, 5, 11, 16, 7.6, 86, 32), _kick(16, 12, 6, 17, 24, 11.0, 108, 36),
		SpriteRef.new("charac/Robot", "character_robot", 1.18),
		_spec(6, 19, 6.5, 18, 24, 55, 9.5, 22))
	CHARACTERS["goron"] = CharacterData.new(
		"goron", "GORON", Color8(110, 168, 90), 70, 174, 3.2, 3.5, -17.4, 124,
		_punch(10, 8, 5, 12, 17, 7.8, 86, 32), _kick(17, 13, 6, 18, 25, 11.4, 108, 36),
		SpriteRef.new("charac/Zombie", "character_zombie", 1.18),
		_spec(3, 16, 7.5, 16, 22, 52, 8.5, 20))

func get_char(key: String) -> CharacterData:
	return CHARACTERS.get(key)
