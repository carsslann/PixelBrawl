class_name SpecialSpec
extends RefCounted
## characters.py SpecialSpec birebir — karaktere ozel ates (projectile) hareketi.

var color: int          # atesefekt renk index'i (0..7)
var damage: int
var speed: float        # merminin yatay hizi (px/kare)
var cast: int           # kac karede mermi cikar
var recovery: int       # cikis sonrasi toparlanma
var meter_cost: int
var knockback: float
var hitstun: int
var hit_w: int
var hit_h: int

func _init(p_color := 0, p_damage := 0, p_speed := 0.0, p_cast := 0,
		p_recovery := 0, p_meter_cost := 0, p_knockback := 0.0, p_hitstun := 0,
		p_hit_w := 48, p_hit_h := 40) -> void:
	color = p_color
	damage = p_damage
	speed = p_speed
	cast = p_cast
	recovery = p_recovery
	meter_cost = p_meter_cost
	knockback = p_knockback
	hitstun = p_hitstun
	hit_w = p_hit_w
	hit_h = p_hit_h

var total: int:
	get:
		return cast + recovery
