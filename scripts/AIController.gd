class_name AIController
extends RefCounted
## controller.py AIController birebir — kural tabanli bot, 3 zorluk.

const DIFFICULTIES := {
	"kolay": {"decision_interval": 38, "reaction": 30, "aggression": 0.10,
		"block_prob": 0.03, "jump_prob": 0.02, "retreat_prob": 0.34, "idle_prob": 0.60},
	"orta": {"decision_interval": 16, "reaction": 18, "aggression": 0.42,
		"block_prob": 0.28, "jump_prob": 0.07, "retreat_prob": 0.16, "idle_prob": 0.05},
	"zor": {"decision_interval": 14, "reaction": 12, "aggression": 0.55,
		"block_prob": 0.48, "jump_prob": 0.10, "retreat_prob": 0.10, "idle_prob": 0.0},
}
const DIFFICULTY_ORDER := ["kolay", "orta", "zor"]
const DIFFICULTY_LABELS := {"kolay": "Kolay", "orta": "Orta", "zor": "Zor"}

var p: Dictionary
var frame: int = 0
var move: int = 0
var want_attack: String = ""      # "" | "punch" | "kick"
var block_from: int = -1
var block_until: int = -1
var prev_opp_attacking: bool = false

func _init(difficulty := "orta") -> void:
	p = DIFFICULTIES[difficulty]

func get_inputs(me: Fighter, opp: Fighter) -> Inputs:
	frame += 1
	var inp := Inputs.new()
	if me.state == Fighter.State.KO or opp.state == Fighter.State.KO:
		return inp

	var gap := absf(opp.x - me.x) - (me.data.width + opp.data.width) / 2.0
	var toward := 1 if opp.x >= me.x else -1

	# rakip saldiriya yeni mi gecti -> blok karari
	var opp_attacking := opp.state == Fighter.State.PUNCH or opp.state == Fighter.State.KICK
	if opp_attacking and not prev_opp_attacking:
		if gap < 150 and opp.attack != null and randf() < float(p["block_prob"]):
			block_from = frame + int(p["reaction"])
			block_until = block_from + opp.attack.total + 6
	prev_opp_attacking = opp_attacking

	if block_from <= frame and frame <= block_until:
		inp.block = true
		return inp

	# periyodik karar
	if frame % int(p["decision_interval"]) == 0:
		var r := randf()
		var in_punch := gap < me.data.punch.hit_w * 0.9
		var in_kick := gap < me.data.kick.hit_w * 0.95
		if in_punch or in_kick:
			if r < float(p["aggression"]):
				var use_punch := in_punch and (not in_kick or randf() < 0.55)
				want_attack = "punch" if use_punch else "kick"
				move = 0
			elif r < float(p["aggression"]) + float(p["retreat_prob"]):
				move = -toward
			else:
				move = 0
		else:
			want_attack = ""
			if r < float(p["jump_prob"]) and me.state != Fighter.State.JUMP:
				inp.jump = true
			if randf() < float(p.get("idle_prob", 0.0)):
				move = 0
			else:
				move = toward

	# planlanan saldiriyi ilk uygun anda uygula
	if want_attack != "" and gap > 220:
		want_attack = ""
	if want_attack != "" and (me.state == Fighter.State.IDLE or me.state == Fighter.State.WALK):
		if want_attack == "punch":
			inp.punch = true
		else:
			inp.kick = true
		want_attack = ""
		move = 0

	# ozel ates: metre dolu + orta mesafe -> ara sira firlat (zorlukla olcekli)
	if me.data.special != null and me.meter >= me.data.special.meter_cost \
			and (me.state == Fighter.State.IDLE or me.state == Fighter.State.WALK) \
			and gap > 120 and randf() < float(p["aggression"]) * 0.05:
		inp.special = true
		inp.move = 0
		return inp

	inp.move = move
	return inp
