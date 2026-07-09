class_name Fighter
extends RefCounted
## fighter.py birebir port — dovuscu durum makinesi + fizik (cizimden bagimsiz).
## Saldirilar startup -> active -> recovery kare pencereleriyle isler.
## Frame-determinizmi: integer state_frame, _physics_process'ten kare basi update().

enum State { IDLE, WALK, CROUCH, JUMP, PUNCH, KICK, SPECIAL, BLOCK, HITSTUN, KO, DASH, DIZZY, THROW }

const NEUTRAL_STATES := [State.IDLE, State.WALK, State.CROUCH, State.BLOCK]
const ATTACK_STATES := [State.PUNCH, State.KICK]

var data: CharacterData
var x: float
var y: float
var vx: float
var vy: float
var facing: int            # 1 = saga, -1 = sola
var health: int
var state: State = State.IDLE
var state_frame: int
var attack: AttackData = null
var attack_has_hit: bool
var attack_airborne: bool
var hitstun_left: int
var on_ground: bool
var blocking: bool
var knocked_down: bool
var victory: bool          # mac sonu kazanan sevinme pozu
var combo_count: int       # SALDIRAN olarak surdurulen kombo
var meter: int             # super metre
var _special: SpecialSpec = null   # su an yapilan ozel hareket
var spawn_special: SpecialSpec = null  # mermi cikis sinyali (match okur, temizler)
# yalnizca gorsel katmanin kullandigi sayaclar
var hit_flash: int
var block_flash: int
var just_jumped: bool
var just_landed: bool
var just_dashed: bool
# Dalga 1
var invuln: int          # dokunulmazlik kareleri (backdash / wake-up)
var recoverable: int     # geri kazanilabilir (gri) can
var hurt_cd: int         # son hasardan sonra geri-kazanim gecikmesi
var recover_tick: int
var dash_dir: int
# Dalga 2
var guard_meter: int
var guard_cd: int
var stun: int
var stun_cd: int
var stunned_left: int    # aktif sersem (stun) sayaci — kilit + gorsel bu sure boyunca
var armor: int
var block_frames: int

var alive: bool:
	get: return health > 0

func _init(p_data: CharacterData, p_x: float, p_facing: int) -> void:
	data = p_data
	reset(p_x, p_facing)

func reset(p_x: float, p_facing: int) -> void:
	x = float(p_x)
	y = float(Settings.FLOOR_Y)
	vx = 0.0
	vy = 0.0
	facing = p_facing
	health = data.max_health
	state = State.IDLE
	state_frame = 0
	attack = null
	attack_has_hit = false
	attack_airborne = false
	hitstun_left = 0
	on_ground = true
	blocking = false
	knocked_down = false
	victory = false
	combo_count = 0
	meter = 0
	_special = null
	spawn_special = null
	hit_flash = 0
	block_flash = 0
	just_jumped = false
	just_landed = false
	just_dashed = false
	invuln = 0
	recoverable = 0
	hurt_cd = 0
	recover_tick = 0
	dash_dir = 0
	guard_meter = Settings.GUARD_MAX
	guard_cd = 0
	stun = 0
	stun_cd = 0
	stunned_left = 0
	armor = 0
	block_frames = 0

# ------------------------------------------------------------------ sorgular
func hurtbox() -> Rect2i:
	var w := data.width
	var h := data.height
	if state == State.CROUCH:
		h = int(h * 0.64)
	elif state == State.JUMP:
		h = int(h * 0.85)
	return Rect2i(int(x - w / 2.0), int(y - h), w, h)

func active_hitbox():  # -> Rect2i, yoksa null
	if not (state in ATTACK_STATES) or attack == null:
		return null
	var a := attack
	if a.airborne:
		if state_frame < a.startup:
			return null
	elif not (a.startup <= state_frame and state_frame < a.startup + a.active):
		return null
	var cx := x + facing * (data.width / 2.0 + a.hit_w / 2.0)
	var cy := y - data.height * a.height_frac
	return Rect2i(int(cx - a.hit_w / 2.0), int(cy - a.hit_h / 2.0), a.hit_w, a.hit_h)

func block_stance():  # -> "stand" | "crouch" | null
	if not blocking:
		return null
	if state == State.CROUCH:
		return "crouch"
	if state == State.BLOCK:
		return "stand"
	return null

# ------------------------------------------------------------ durum degisimi
func set_state(new_state: State) -> void:
	if new_state != state:
		state = new_state
		state_frame = 0

func take_hit(atk: AttackData, attacker_facing: int, blocked: bool, damage: int,
		hitstun_mult := 1.0, parry := false) -> void:
	hurt_cd = Settings.RECOVER_DELAY
	# super armor: ozel hareket sirasinda 1 vurus emer (yarim hasar, sersem yok)
	if armor > 0 and not blocked and health > 0:
		armor -= 1
		var ad := maxi(1, int(damage * 0.5))
		health = max(0, health - ad)
		recoverable = maxi(0, recoverable - ad)
		hit_flash = 6
		if health <= 0:
			set_state(State.KO)
			vx = attacker_facing * atk.knockback * 1.4
			if on_ground:
				vy = -6.0
				on_ground = false
		return
	if blocked:
		if parry:                    # just-defend: hasar yok, guard geri gelir
			guard_meter = mini(Settings.GUARD_MAX, guard_meter + 20)
			block_flash = 12
			return
		health = max(0, health - max(1, damage))
		recoverable = mini(data.max_health, recoverable + maxi(1, damage))
		vx = attacker_facing * atk.knockback * Settings.BLOCK_PUSHBACK_RATIO
		block_flash = 8
		guard_meter -= Settings.GUARD_DRAIN + damage
		if guard_meter <= 0:         # guard crush -> baygin
			guard_meter = Settings.GUARD_MAX
			stunned_left = Settings.DIZZY_FRAMES
			blocking = false
			set_state(State.DIZZY)
		return
	health = max(0, health - damage)
	recoverable = maxi(0, recoverable - damage)
	stun = mini(Settings.STUN_MAX, stun + Settings.STUN_PER_HIT)
	stun_cd = Settings.STUN_DECAY_DELAY
	vx = attacker_facing * atk.knockback
	hit_flash = 6
	attack = null
	attack_airborne = false
	_special = null
	spawn_special = null
	blocking = false
	if health <= 0:
		set_state(State.KO)
		vx = attacker_facing * atk.knockback * 1.4
		if on_ground:
			vy = -6.0
			on_ground = false
		return
	knocked_down = atk.knockdown
	hitstun_left = int(atk.hitstun * (1.7 if atk.knockdown else 1.0) * hitstun_mult)
	if atk.knockdown and on_ground:
		vy = -5.5
		on_ground = false
	set_state(State.HITSTUN)

func _start_attack(new_state: State, atk: AttackData, airborne: bool) -> void:
	attack = atk
	attack_has_hit = false
	attack_airborne = airborne
	blocking = false
	if not airborne:
		vx = 0.0
	set_state(new_state)

func _start_special() -> void:
	var spec := data.special
	meter = max(0, meter - spec.meter_cost)
	_special = spec
	spawn_special = null
	attack = null
	armor = Settings.ARMOR_HITS   # ozel harekette super armor
	vx = 0.0
	set_state(State.SPECIAL)

func _update_special() -> void:
	vx = 0.0
	var spec := _special
	if spec == null or state_frame >= spec.total:
		_special = null
		armor = 0
		set_state(State.IDLE)
	elif state_frame == spec.cast:
		spawn_special = spec
	_physics()

func _start_dash(dir: int) -> void:
	dash_dir = dir
	just_dashed = true
	var forward := dir == facing
	set_state(State.DASH)
	vx = dir * Settings.DASH_SPEED
	if not forward:
		invuln = Settings.BACKDASH_IFRAMES   # backdash = kacinma penceresi

func _recover_regen() -> void:
	if hurt_cd > 0 or recoverable <= 0:
		return
	if state == State.KO or state == State.HITSTUN:
		return
	recover_tick += 1
	if recover_tick >= Settings.RECOVER_RATE:
		recover_tick = 0
		if health < data.max_health:
			health += 1
		recoverable -= 1

# ------------------------------------------------------ ana guncelleme (kare)
func update(inputs: Inputs, opponent: Fighter) -> void:
	state_frame += 1
	# guard/stun bakimi (onceki karenin blocking durumuna gore)
	if blocking:
		block_frames += 1
		guard_cd = Settings.GUARD_REGEN_DELAY
	else:
		block_frames = 0
		if guard_cd > 0:
			guard_cd -= 1
		elif guard_meter < Settings.GUARD_MAX:
			guard_meter = mini(Settings.GUARD_MAX, guard_meter + Settings.GUARD_REGEN)
	if stun_cd > 0:
		stun_cd -= 1
	elif stun > 0:
		stun = maxi(0, stun - Settings.STUN_DECAY)
	just_jumped = false
	just_landed = false
	just_dashed = false
	blocking = false
	if hit_flash > 0:
		hit_flash -= 1
	if block_flash > 0:
		block_flash -= 1
	if invuln > 0:
		invuln -= 1
	if hurt_cd > 0:
		hurt_cd -= 1
	if stunned_left > 0:
		stunned_left -= 1     # sersem sayaci her zaman iSler (vurulsa bile)
	_recover_regen()

	if state == State.KO:
		_physics()
		return

	if state == State.DIZZY:
		vx = 0.0                 # sersem: yerinde donar, hareket edemez (stun)
		if stunned_left <= 0:
			set_state(State.IDLE)
		_physics()
		return

	if state == State.THROW:
		vx = 0.0
		if state_frame >= 14:
			set_state(State.IDLE)
		_physics()
		return

	if (state in NEUTRAL_STATES) and on_ground:
		facing = 1 if opponent.x >= x else -1

	if state == State.HITSTUN:
		hitstun_left -= 1
		if hitstun_left <= 0 and on_ground:
			if knocked_down:
				invuln = Settings.WAKEUP_IFRAMES   # kalkista dokunulmazlik
			knocked_down = false
			if stunned_left > 0:
				set_state(State.DIZZY)       # hala sersem -> tekrar kilitlen
			elif stun >= Settings.STUN_MAX:
				stun = 0
				stunned_left = Settings.DIZZY_FRAMES
				set_state(State.DIZZY)
			else:
				set_state(State.IDLE)
		_physics()
		return

	if state in ATTACK_STATES:
		_update_attack(inputs)
		return

	if state == State.SPECIAL:
		_update_special()
		return

	if state == State.DASH:
		if state_frame >= Settings.DASH_FRAMES:
			set_state(State.IDLE)
		else:
			vx *= 0.90
		_physics()
		return

	if state == State.JUMP:
		# havada tek saldiri hakki
		if not attack_airborne and (inputs.punch or inputs.kick):
			var use_kick := inputs.kick and not inputs.punch
			var atk: AttackData = data.jump_kick if use_kick else data.jump_punch
			var st: State = State.KICK if use_kick else State.PUNCH
			_start_attack(st, atk, true)
			_update_attack(inputs)
			return
		_physics()
		if on_ground:
			set_state(State.IDLE)
		return

	# ---- notr (yerde): yeni eylemler ----
	var holding_back := inputs.move != 0 and signi(inputs.move) == -facing
	var block_req := inputs.block or holding_back

	if inputs.special and data.special != null and meter >= data.special.meter_cost:
		_start_special()
	elif inputs.punch:
		var atk: AttackData = data.crouch_punch if inputs.down else data.punch
		_start_attack(State.PUNCH, atk, false)
	elif inputs.kick:
		var atk: AttackData = data.sweep if inputs.down else data.kick
		_start_attack(State.KICK, atk, false)
	elif inputs.jump and not inputs.down:
		set_state(State.JUMP)
		on_ground = false
		just_jumped = true
		vy = data.jump_vy
		vx = inputs.move * data.jump_vx
	elif inputs.dash != 0:
		_start_dash(inputs.dash)
	elif inputs.down:
		blocking = block_req            # comel-blok (geri de tutuluyorsa)
		vx = 0.0
		set_state(State.CROUCH)
	elif block_req:
		blocking = true
		vx = inputs.move * data.walk_speed   # blokta geri yuruyebilir
		set_state(State.BLOCK)
	else:
		vx = inputs.move * data.walk_speed
		set_state(State.WALK if inputs.move != 0 else State.IDLE)
	_physics()

func _update_attack(inputs: Inputs) -> void:
	# iptal: saldiri isabet ettiyse ozel harekete ya da daha yuksek kademeye gec
	if attack_has_hit and not attack_airborne:
		if inputs.special and data.special != null and meter >= data.special.meter_cost:
			_start_special()
			_physics()
			return
		var nxt = _cancel_target(inputs)
		if nxt != null:
			_start_attack(nxt[0], nxt[1], false)
			_physics()
			return

	if attack_airborne:
		_physics()
		if on_ground:
			attack = null
			attack_airborne = false
			set_state(State.IDLE)
		return

	vx = 0.0
	if attack == null or state_frame >= attack.total:
		attack = null
		set_state(State.IDLE)
	_physics()

func _cancel_target(inputs: Inputs):  # -> [State, AttackData] | null
	var cur := attack.chain if attack != null else 0
	if inputs.kick:
		var atk: AttackData = data.sweep if inputs.down else data.kick
		if atk.chain > cur:
			return [State.KICK, atk]
	if inputs.punch:
		var atk: AttackData = data.crouch_punch if inputs.down else data.punch
		if atk.chain > cur:
			return [State.PUNCH, atk]
	return null

func _physics() -> void:
	x += vx
	if not on_ground:
		vy += Settings.GRAVITY
		y += vy
		if y >= Settings.FLOOR_Y:
			y = float(Settings.FLOOR_Y)
			vy = 0.0
			on_ground = true
			just_landed = true
	else:
		if state == State.HITSTUN or state == State.KO or state == State.BLOCK:
			vx *= Settings.GROUND_FRICTION
			if abs(vx) < 0.1:
				vx = 0.0
	var half := data.width / 2.0
	x = clampf(x, Settings.STAGE_MARGIN + half,
		Settings.WIDTH - Settings.STAGE_MARGIN - half)
