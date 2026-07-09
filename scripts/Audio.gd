extends Node
## audio.py yerine — assets/audio/ WAV'larini AudioStreamPlayer ile calar (autoload: Audio).
## SFX havuzu (ust uste sesler icin) + donguleyen muzik.

const NAMES := ["hit_light", "hit_heavy", "block", "ko", "jump", "land",
	"whoosh", "menu_move", "menu_select"]

var _sounds := {}
var _sfx: Array = []
var _sfx_i := 0
var _music: AudioStreamPlayer
var _muted := false
var _base_vol := 0.28

func _ready() -> void:
	for n in NAMES:
		var path := "res://assets/audio/%s.wav" % n
		if ResourceLoader.exists(path):
			_sounds[n] = load(path)
	for i in range(8):
		var pl := AudioStreamPlayer.new()
		add_child(pl)
		_sfx.append(pl)
	_music = AudioStreamPlayer.new()
	add_child(_music)
	var mpath := "res://assets/audio/music.wav"
	if ResourceLoader.exists(mpath):
		_music.stream = load(mpath)
	# muzigi guvenilir sekilde dongule (WAV loop ayarina guvenme)
	_music.finished.connect(func(): if _music.stream != null: _music.play())

func play(sound: String, vol := 1.0) -> void:
	if _muted:
		return
	var s = _sounds.get(sound)
	if s == null:
		return
	var pl: AudioStreamPlayer = _sfx[_sfx_i]
	_sfx_i = (_sfx_i + 1) % _sfx.size()
	pl.stream = s
	pl.volume_db = linear_to_db(clampf(vol, 0.02, 1.0))
	pl.play()

func play_music(vol := 0.3) -> void:
	if _music.stream == null:
		return
	_music.volume_db = linear_to_db(vol)
	if not _music.playing:
		_music.play()

func set_music_vol(v: float) -> void:
	_base_vol = v
	if _music != null and _music.playing and not _muted:
		_music.volume_db = linear_to_db(clampf(v, 0.02, 1.0))

func toggle_mute() -> void:
	_muted = not _muted
	if _music != null:
		_music.volume_db = -80.0 if _muted else linear_to_db(clampf(_base_vol, 0.02, 1.0))

func stop_music() -> void:
	_music.stop()
