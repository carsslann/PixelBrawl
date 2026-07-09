class_name AttackData
extends RefCounted
## characters.py AttackData birebir. Frozen dataclass -> RefCounted + replace().

var name: String
var damage: int
var startup: int        # vurus oncesi hazirlik (kare)
var active: int         # isabet penceresi (kare)
var recovery: int       # toparlanma (kare)
var hitstun: int        # isabet alan rakibin kilitli suresi (kare)
var knockback: float    # geri itilme hizi (px/kare)
var hit_w: int          # vurus kutusu on-uzanma / genislik
var hit_h: int          # vurus kutusu yuksekligi
var height_frac: float  # yerden yukseklik orani (0=ayak, 1=tepe)
var guard: String       # "high" | "low" | "overhead"
var knockdown: bool     # rakibi yere serer
var chain: int          # zincir kademesi (kanser sadece daha yuksege)
var airborne: bool      # havada yapilan saldiri

func _init(p_name := "", p_damage := 0, p_startup := 0, p_active := 0,
		p_recovery := 0, p_hitstun := 0, p_knockback := 0.0, p_hit_w := 0,
		p_hit_h := 0, p_height_frac := 0.0, p_guard := "high",
		p_knockdown := false, p_chain := 1, p_airborne := false) -> void:
	name = p_name
	damage = p_damage
	startup = p_startup
	active = p_active
	recovery = p_recovery
	hitstun = p_hitstun
	knockback = p_knockback
	hit_w = p_hit_w
	hit_h = p_hit_h
	height_frac = p_height_frac
	guard = p_guard
	knockdown = p_knockdown
	chain = p_chain
	airborne = p_airborne

var total: int:
	get:
		return startup + active + recovery

func replace(over := {}) -> AttackData:
	## dataclasses.replace karsiligi: kopyala, over sozlugundeki alanlari degistir.
	var a := AttackData.new(name, damage, startup, active, recovery, hitstun,
		knockback, hit_w, hit_h, height_frac, guard, knockdown, chain, airborne)
	for k in over:
		a.set(k, over[k])
	return a
