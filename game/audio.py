"""Prosedurel ses motoru — hicbir harici ses dosyasi gerektirmez.

Oyunda hazir ses yok; bu modul butun efektleri KODLA SENTEZLER (procedural),
sadece Python stdlib (`wave`, `array`, `struct`, `math`, `random`) ile 16-bit
mono WAV uretir ve `pygame.mixer` ile calar. numpy KULLANILMAZ.

Uretilen WAV'lar `assets/audio/` altina yazilir (idempotent: dosya varsa yeniden
uretilmez) ve oradan yuklenir. Ayrica bellek-ici RIFF bytes uretimi de vardir.

Dayaniklilik: `pygame.mixer.init()` headless/dummy surucude basarisiz olabilir.
Tum baslatma try/except ile sarilmistir; basarisizlikta `_enabled=False` olur ve
`play`/`play_music`/`stop_music` sessizce no-op'a doner (ASLA exception firlatmaz).

Modul IMPORT'u yan etkisizdir: mixer yalnizca `audio.init()` cagrilinca baslar.

Sozlesme (match.py / menu.py bu isimleri AYNEN cagirir):
    audio.init()
    audio.play(name, vol=1.0)
    audio.set_enabled(on)
    audio.play_music() / audio.stop_music()
    audio.SOUNDS            # tanimli ses isimleri (tuple)
"""

import io
import math
import os
import random
import struct
import wave

try:
    import pygame
except Exception:  # pygame yoksa bile modul import edilebilsin
    pygame = None

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

SAMPLE_RATE = 22050          # Hz
_AMP = 32767                 # 16-bit tam olcek (signed) tepe genlik
_CHANNELS = 1                # mono
_SAMPWIDTH = 2               # bayt (16-bit)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(ROOT, "assets", "audio")

# Tanimli ses isimleri (sabit sira -> uretim/rapor sirasi belirlidir).
SOUNDS = (
    "hit_light",
    "hit_heavy",
    "block",
    "ko",
    "jump",
    "land",
    "whoosh",
    "menu_move",
    "menu_select",
)

# ---------------------------------------------------------------------------
# Modul durumu (import aninda YAN ETKISIZ)
# ---------------------------------------------------------------------------

_enabled = False             # mixer basariyla acildi mi + kullanici acik tuttu mu
_mixer_ready = False         # pygame.mixer.init() gercekten calisti mi
_initialized = False         # init() bir kez kosuldu mu
_sounds = {}                 # name -> pygame.mixer.Sound
_music_ready = False         # muzik dosyasi hazirlanabildi mi
_music_path = None


# ===========================================================================
# DSP yardimcilari — hepsi float ornek listesi ([-1.0, 1.0]) uretir/isler
# ===========================================================================

def _n_samples(dur):
    """Sureye (saniye) karsilik gelen ornek sayisi (>=1)."""
    return max(1, int(SAMPLE_RATE * dur))


def tone(freq, dur, decay=6.0, wave_type="sine", start_amp=1.0):
    """Tek frekansli ton; ustel sonum zarfiyla (decay buyudukce hizli soner).

    wave_type: "sine" | "square" | "saw" | "triangle".
    """
    n = _n_samples(dur)
    out = [0.0] * n
    two_pi_f = 2.0 * math.pi * freq
    for i in range(n):
        t = i / SAMPLE_RATE
        phase = two_pi_f * t
        if wave_type == "square":
            s = 1.0 if math.sin(phase) >= 0.0 else -1.0
        elif wave_type == "saw":
            frac = (freq * t) % 1.0
            s = 2.0 * frac - 1.0
        elif wave_type == "triangle":
            frac = (freq * t) % 1.0
            s = 4.0 * abs(frac - 0.5) - 1.0
        else:  # sine
            s = math.sin(phase)
        env = math.exp(-decay * t)
        out[i] = s * env * start_amp
    return out


def noise(dur, decay=8.0, start_amp=1.0):
    """Beyaz gurultu patlamasi; ustel sonum zarfiyla."""
    n = _n_samples(dur)
    out = [0.0] * n
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-decay * t)
        out[i] = random.uniform(-1.0, 1.0) * env * start_amp
    return out


def sweep(f_start, f_end, dur, decay=4.0, start_amp=1.0):
    """Lineer frekans kaydirmali sinus (chirp). f_start->f_end."""
    n = _n_samples(dur)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        frac = i / max(1, n - 1)
        freq = f_start + (f_end - f_start) * frac
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        env = math.exp(-decay * t)
        out[i] = math.sin(phase) * env * start_amp
    return out


def lowpass(samples, alpha=0.25):
    """Basit tek-kutuplu alcak-geciren filtre (gurultuyu 'suffle'ye yaklastirir).

    alpha kucukse daha cok yumusatir. y[i] = y[i-1] + alpha*(x[i]-y[i-1]).
    """
    out = [0.0] * len(samples)
    prev = 0.0
    for i, x in enumerate(samples):
        prev = prev + alpha * (x - prev)
        out[i] = prev
    return out


def distort(samples, drive=2.0):
    """Yumusak kirpma (tanh benzeri) distorsiyon; 'gur' vurus hissi."""
    out = [0.0] * len(samples)
    for i, x in enumerate(samples):
        out[i] = math.tanh(x * drive)
    return out


def mix(*tracks):
    """Farkli uzunluktaki ornek listelerini toplayarak karistirir.

    Cikti uzunlugu en uzun parcaya esittir (kisalar sifirla doldurulur).
    Normalize edilmez — gerekirse `normalize` cagirin.
    """
    tracks = [t for t in tracks if t]
    if not tracks:
        return []
    length = max(len(t) for t in tracks)
    out = [0.0] * length
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    return out


def normalize(samples, peak=0.89):
    """Tepe degeri `peak`'e olceklendirir (kirpma onler). Sessizse aynen doner."""
    if not samples:
        return samples
    m = max(abs(s) for s in samples)
    if m <= 1e-9:
        return samples
    g = peak / m
    return [s * g for s in samples]


def fade(samples, in_ms=3.0, out_ms=8.0):
    """Basi/sonu kisa rampalarla yumusatir; klik/pop seslerini onler."""
    n = len(samples)
    if n == 0:
        return samples
    fi = min(n, max(1, int(SAMPLE_RATE * in_ms / 1000.0)))
    fo = min(n, max(1, int(SAMPLE_RATE * out_ms / 1000.0)))
    out = list(samples)
    for i in range(fi):
        out[i] *= i / fi
    for i in range(fo):
        out[n - 1 - i] *= i / fo
    return out


# ===========================================================================
# WAV kodlama (RIFF konteyner)
# ===========================================================================

def _to_pcm16(samples):
    """float [-1,1] ornekleri -> signed 16-bit little-endian bytes."""
    frames = bytearray()
    for s in samples:
        if s > 1.0:
            s = 1.0
        elif s < -1.0:
            s = -1.0
        frames += struct.pack("<h", int(s * _AMP))
    return bytes(frames)


def _wav_bytes(samples):
    """Ornek listesinden gecerli WAV (RIFF header'li) bytes uretir."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPWIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(_to_pcm16(samples))
    return buf.getvalue()


def _write_wav(path, samples):
    """Ornekleri diske WAV olarak yazar (idempotent DEGIL — cagiran kontrol eder)."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPWIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(_to_pcm16(samples))


# ===========================================================================
# Ses tasarimlari — her biri normalize edilmis ornek listesi dondurur
# ===========================================================================

def _design_hit_light():
    # Kisa gurultu patlamasi + alcak sinus "thump", hizli sonum (~0.12s)
    thump = tone(150, 0.12, decay=28.0, wave_type="sine")
    click = noise(0.06, decay=55.0, start_amp=0.7)
    return fade(normalize(mix(thump, click), peak=0.85))


def _design_hit_heavy():
    # hit_light'in daha alcak/uzun/gur hali (~0.22s) + hafif distortion
    thump = tone(90, 0.22, decay=15.0, wave_type="sine")
    body = tone(140, 0.18, decay=18.0, wave_type="triangle", start_amp=0.6)
    crunch = noise(0.12, decay=32.0, start_amp=0.9)
    raw = mix(thump, body, crunch)
    return fade(normalize(distort(raw, drive=1.8), peak=0.95))


def _design_block():
    # Kisa metalik "tink" — iki hafif detune yuksek sinus, cok kisa (~0.08s)
    a = tone(2100, 0.08, decay=55.0, wave_type="sine")
    b = tone(2160, 0.08, decay=55.0, wave_type="sine", start_amp=0.7)
    spark = noise(0.02, decay=120.0, start_amp=0.4)
    return fade(normalize(mix(a, b, spark), peak=0.8), out_ms=6.0)


def _design_ko():
    # Alcak gong — temel + harmonikler, yavas sonum (~0.9s)
    base = tone(70, 0.9, decay=3.2, wave_type="sine")
    h2 = tone(140, 0.9, decay=3.6, wave_type="sine", start_amp=0.5)
    h3 = tone(210, 0.9, decay=4.2, wave_type="sine", start_amp=0.28)
    h5 = tone(350, 0.9, decay=5.0, wave_type="triangle", start_amp=0.14)
    strike = noise(0.05, decay=45.0, start_amp=0.5)
    return fade(normalize(mix(base, h2, h3, h5, strike), peak=0.92), out_ms=60.0)


def _design_jump():
    # Hizli yukari chirp (~0.15s)
    body = sweep(320, 760, 0.15, decay=10.0)
    return fade(normalize(body, peak=0.7))


def _design_land():
    # Kisa alcak "thud" (~0.12s)
    thud = tone(110, 0.12, decay=30.0, wave_type="sine")
    dirt = noise(0.07, decay=45.0, start_amp=0.5)
    return fade(normalize(mix(thud, dirt), peak=0.8))


def _design_whoosh():
    # Filtrelenmis gurultu suflemesi (~0.15s) — hafif zarfla yuksel-alcal
    raw = noise(0.15, decay=6.0, start_amp=1.0)
    swish = lowpass(raw, alpha=0.12)
    # ortada tepe yapan pencere ile 'savurma' hissi
    n = len(swish)
    out = [0.0] * n
    for i in range(n):
        w = math.sin(math.pi * (i / max(1, n - 1)))  # 0..1..0
        out[i] = swish[i] * w
    return fade(normalize(out, peak=0.6))


def _design_menu_move():
    # Cok kisa blip
    blip = tone(660, 0.05, decay=40.0, wave_type="square", start_amp=0.6)
    return fade(normalize(blip, peak=0.55), out_ms=5.0)


def _design_menu_select():
    # Iki-nota yukari blip
    a = tone(620, 0.06, decay=30.0, wave_type="square", start_amp=0.6)
    b = tone(940, 0.09, decay=24.0, wave_type="square", start_amp=0.6)
    silence = [0.0] * _n_samples(0.055)
    return fade(normalize(mix(a, silence + b), peak=0.6))


# name -> tasarim fonksiyonu (SOUNDS ile ayni kumeyi kapsar)
_DESIGNS = {
    "hit_light": _design_hit_light,
    "hit_heavy": _design_hit_heavy,
    "block": _design_block,
    "ko": _design_ko,
    "jump": _design_jump,
    "land": _design_land,
    "whoosh": _design_whoosh,
    "menu_move": _design_menu_move,
    "menu_select": _design_menu_select,
}


# ===========================================================================
# Muzik — basit dongulu bas/arp (opsiyonel)
# ===========================================================================

def _design_music():
    """Basit dongulu dovus muzigi: A-minor arp uzeri yuruyen bas.

    Tek bir dongu ureti; mixer.music.play(-1) ile sonsuz tekrarlanir.
    Uretilemezse cagiran no-op'a duser.
    """
    tempo = 132.0                      # BPM
    beat = 60.0 / tempo                # saniye/vurus
    eighth = beat / 2.0

    # Notalar (Hz) — A minor pentatonik civari
    A2, C3, E3, A3, C4, E4, G4 = 110.0, 130.8, 164.8, 220.0, 261.6, 329.6, 392.0
    bass_seq = [A2, A2, E3, C3, A2, A2, G4 / 4, E3]     # 8 x sekizlik bas
    arp_seq = [A3, C4, E4, C4, A3, E4, G4, E4]          # 8 x sekizlik arp

    track = []
    for i in range(len(bass_seq)):
        b = tone(bass_seq[i], eighth, decay=5.0, wave_type="triangle",
                 start_amp=0.55)
        a = tone(arp_seq[i], eighth, decay=7.0, wave_type="square",
                 start_amp=0.22)
        step = mix(b, a)
        # her adimin sonuna hafif fade -> puruzsuz zincir
        track += fade(step, in_ms=2.0, out_ms=6.0)

    # dongunun bas/son ekini yumusat
    return fade(normalize(track, peak=0.7), in_ms=8.0, out_ms=8.0)


# ===========================================================================
# Uretim + yukleme
# ===========================================================================

def _ensure_wav_files():
    """assets/audio/<name>.wav dosyalarini (yoksa) uretir. Idempotent.

    Diske yazamazsa (izin/RO fs) sessizce gecer — bellek-ici yukleme fallback'i
    _load_sounds icinde devrededir. Uretilen/dogrulanan yol listesi doner.
    """
    written = []
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
    except Exception as exc:
        print(f"[audio] klasor olusturulamadi: {exc}")
        return written

    # efektler
    items = list(_DESIGNS.items()) + [("music", _design_music)]
    for name, design in items:
        path = os.path.join(AUDIO_DIR, f"{name}.wav")
        if os.path.isfile(path):
            written.append(path)
            continue
        try:
            _write_wav(path, design())
            written.append(path)
        except Exception as exc:
            print(f"[audio] '{name}.wav' yazilamadi: {exc}")
    return written


def _make_sound(name, design):
    """Bir ses icin pygame.mixer.Sound uretir.

    Once diskteki WAV'i dener; olmazsa bellek-ici RIFF bytes'tan yukler.
    """
    path = os.path.join(AUDIO_DIR, f"{name}.wav")
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            pass  # bozuksa bellek-ici uretime dus
    try:
        data = _wav_bytes(design())
        return pygame.mixer.Sound(file=io.BytesIO(data))
    except Exception as exc:
        print(f"[audio] '{name}' ses yuklenemedi: {exc}")
        return None


def _load_sounds():
    """Tum efektleri mixer.Sound olarak yukler (_sounds sozlugune)."""
    global _sounds
    _sounds = {}
    for name, design in _DESIGNS.items():
        snd = _make_sound(name, design)
        if snd is not None:
            _sounds[name] = snd


def _prepare_music():
    """Muzik WAV'ini hazir/dogrulanmis yola isaret ettirir."""
    global _music_ready, _music_path
    _music_ready = False
    _music_path = None
    path = os.path.join(AUDIO_DIR, "music.wav")
    if not os.path.isfile(path):
        try:
            os.makedirs(AUDIO_DIR, exist_ok=True)
            _write_wav(path, _design_music())
        except Exception as exc:
            print(f"[audio] muzik uretilemedi: {exc}")
            return
    if os.path.isfile(path):
        _music_path = path
        _music_ready = True


# ===========================================================================
# Genel API (isimler AYNEN korunur)
# ===========================================================================

def init():
    """Mixer'i baslatir, sesleri (ilk sefer) uretir/yukler.

    Guvenli: pygame yoksa veya mixer.init() basarisizsa sessizce devre disi
    (`_enabled=False`) kalir; sonraki tum play/music cagrilari no-op olur.
    Birden fazla cagrilirsa yalnizca ilk sefer is yapar.
    """
    global _enabled, _mixer_ready, _initialized

    if _initialized:
        return _enabled
    _initialized = True

    if pygame is None:
        print("[audio] pygame yok -> ses devre disi")
        _enabled = False
        return False

    # WAV'lari uret (diske yazilabiliyorsa). Basarisiz olsa da bellek-ici
    # yukleme calisir; bu yuzden hatayi yutup devam ederiz.
    try:
        _ensure_wav_files()
    except Exception as exc:
        print(f"[audio] WAV uretimi atlandi: {exc}")

    # Mixer'i baslat — headless/dummy surucude patlayabilir.
    try:
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16,
                          channels=_CHANNELS, buffer=512)
        _mixer_ready = True
    except Exception as exc:
        print(f"[audio] mixer baslatilamadi ({exc}) -> ses devre disi")
        _mixer_ready = False
        _enabled = False
        return False

    try:
        _load_sounds()
        _prepare_music()
    except Exception as exc:
        print(f"[audio] sesler yuklenemedi: {exc}")

    _enabled = True
    return True


def set_enabled(on):
    """Sesi ac/kapa. Mixer hic acilamadiysa acmaya calismaz (kapali kalir).

    Kapatildiginda calan muzigi de durdurur.
    """
    global _enabled
    on = bool(on)
    if on and not _mixer_ready:
        # mixer hic acilamadi; zorla acamayiz
        _enabled = False
        return
    _enabled = on
    if not on:
        stop_music()


def is_enabled():
    """Ses su an aktif mi (mixer acik + kullanici acik tuttu)."""
    return _enabled and _mixer_ready


def play(name, vol=1.0):
    """Tek sesi calar. Bilinmeyen isim veya devre disi = no-op (crash yok)."""
    if not _enabled or not _mixer_ready:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        v = 0.0 if vol < 0.0 else (1.0 if vol > 1.0 else float(vol))
        snd.set_volume(v)
        snd.play()
    except Exception:
        pass  # calma sirasindaki hata oyunu dusurmesin


def play_music(vol=0.5, loops=-1):
    """Dovus muzigini (varsa) dongude calar. Uretilemezse/devre disi = no-op."""
    if not _enabled or not _mixer_ready or not _music_ready or not _music_path:
        return
    try:
        pygame.mixer.music.load(_music_path)
        v = 0.0 if vol < 0.0 else (1.0 if vol > 1.0 else float(vol))
        pygame.mixer.music.set_volume(v)
        pygame.mixer.music.play(loops)
    except Exception:
        pass


def stop_music():
    """Calan muzigi durdurur. Mixer yoksa/durmus ise no-op."""
    if not _mixer_ready or pygame is None:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
