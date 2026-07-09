class_name CharacterData
extends RefCounted
## characters.py CharacterData birebir. Turetilmis saldirilar (comel/hava)
## Python'da @property; burada _init sonunda bir kez hesaplanip saklanir
## (temel punch/kick degismez oldugu icin degerler aynidir).

var key: String
var name: String
var color: Color      # HUD/menu vurgusu ve prosedurel yedek cizim rengi
var width: int
var height: int
var walk_speed: float
var jump_vx: float
var jump_vy: float
var max_health: int
var punch: AttackData
var kick: AttackData
var sprite: SpriteRef
var special: SpecialSpec

# turetilmis saldirilar
var crouch_punch: AttackData
var sweep: AttackData
var jump_punch: AttackData
var jump_kick: AttackData

func _init(p_key := "", p_name := "", p_color := Color.WHITE, p_width := 64,
		p_height := 172, p_walk_speed := 4.0, p_jump_vx := 4.5, p_jump_vy := -18.0,
		p_max_health := 100, p_punch: AttackData = null, p_kick: AttackData = null,
		p_sprite: SpriteRef = null, p_special: SpecialSpec = null) -> void:
	key = p_key
	name = p_name
	color = p_color
	width = p_width
	height = p_height
	walk_speed = p_walk_speed
	jump_vx = p_jump_vx
	jump_vy = p_jump_vy
	max_health = p_max_health
	punch = p_punch
	kick = p_kick
	sprite = p_sprite
	special = p_special
	_build_derived()

func _build_derived() -> void:
	if punch == null or kick == null:
		return
	crouch_punch = punch.replace({
		"name": "alçak yumruk", "height_frac": 0.30,
		"recovery": max(6, punch.recovery - 2), "guard": "high", "chain": 1})
	sweep = kick.replace({
		"name": "süpürme", "height_frac": 0.14, "hit_w": kick.hit_w + 8,
		"knockback": kick.knockback * 0.6, "recovery": kick.recovery + 4,
		"guard": "low", "knockdown": true, "chain": 2})
	jump_punch = punch.replace({
		"name": "hava yumruk", "height_frac": 0.50, "hit_h": punch.hit_h + 42,
		"guard": "overhead", "airborne": true, "chain": 1})
	jump_kick = kick.replace({
		"name": "hava tekme", "height_frac": 0.48, "hit_w": kick.hit_w + 6,
		"hit_h": kick.hit_h + 42, "guard": "overhead", "airborne": true, "chain": 2})
