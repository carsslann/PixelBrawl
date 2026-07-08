# Sokak Kavgacısı — çakma street fighter

Pygame ile yazılmış 2D dövüş oyunu. Sen (klavye) bota karşı oynarsın:
3 zorluk, 6 karakter (Kenney "Toon Characters" sprite'ları), klasik
round / can barı / süre akışı, ve vuruş efektleri (kıvılcım, hasar
sayısı, ekran sarsıntısı, isabet donması, KO flaşı).

## Başlatma

`run.bat` çift tıkla (pygame yoksa kendisi kurar), ya da:

```
py main.py
```

> Not: Python 3.14'te klasik `pygame` derlenmediği için birebir uyumlu
> `pygame-ce` kullanılıyor (`import pygame` aynı kalır).

## Kontroller

| Tuş | İşlev |
|-----|-------|
| A / D | Yürü (geri / ileri) |
| W | Zıpla |
| S | Blok (basılı tut) |
| J | Yumruk (hızlı, az hasar) |
| K | Tekme (yavaş, çok hasar, uzun menzil) |
| ESC | Duraklat / devam (duraklatmada Q: ana menü) |

Menüde ok tuşları / WASD ile karakterini, rakibini ve bot zorluğunu
seç, ENTER ile başla. Maç sonu ENTER = tekrar, ESC = menü.

Blok hasarın ~%85'ini keser (kalan "chip" hasarıdır). Yumruk/tekmenin
startup → active → recovery kare pencereleri vardır: vuruş yalnızca
active penceresinde isabet eder, recovery sırasında savunmasızsın.

## Karakterler

| Karakter | Arketip | Sprite |
|----------|---------|--------|
| EFE | dengeli | Male adventurer |
| ADA | dengeli | Male person |
| ZEYNEP | hızlı | Female adventurer |
| MİRA | hızlı | Female person |
| ROBO | ağır / tank | Robot |
| GORON | ağır / tank | Zombie |

## Mimari

```
main.py            giriş, sahne döngüsü (menü <-> maç)
game/
  settings.py      tüm sabitler ve denge değerleri
  characters.py    KARAKTERLER = saf veri (fizik + saldırılar + sprite referansı)
  fighter.py       durum makinesi + fizik (çizimden tamamen bağımsız)
  controller.py    Inputs; HumanController (klavye) + AIController (bot, 3 zorluk)
  combat.py        vuruş çözümü (hitbox/hurtbox), gövde itişme, isabet olayları
  match.py         round/maç akışı, süre, KO, efekt + hitstop + sarsıntı tetikleme
  effects.py       kıvılcım / hasar sayısı / toz / ekran sarsıntısı / KO flaşı
  hud.py           can barları, süre, pankartlar
  renderer.py      TEK çizim kapısı: sprite varsa Kenney pozu, yoksa prosedürel
  sprites.py       Kenney poz-başına PNG yükleyici + animasyon seçimi
  menu.py          karakter / rakip / zorluk seçim ekranı (sprite önizlemeli)
charac/            Kenney "Toon Characters" sprite paketi (CC0) — bkz. Krediler
tests/smoke_test.py  pencere açmadan çalışan testler (py tests/smoke_test.py)
```

Bot ile insan aynı `Inputs` yapısını üretir; **PvP** eklemek ikinci bir
`HumanController`'a farklı tuş seti vermekten ibarettir. Oyun mantığı
çizimden tamamen ayrık: `sprites.py`/`renderer.py` dışında hiçbir yer
görsel bilmez.

## Yeni karakter ekleme

`game/characters.py` içindeki `CHARACTERS`'a yeni bir `CharacterData`
ekle, anahtarını `CHARACTER_ORDER`'a yaz. Sprite bağlamak için
`SpriteRef(folder, prefix, scale)` ver — `folder` proje köküne göre
klasör (or. `"charac/Robot"`), `prefix` dosya ön eki
(or. `"character_robot"`). Menüde kendiliğinden görünür; sprite
yüklenemezse oyun prosedürel (dikdörtgen) çizime düşer, çökmez.

## Sprite eşleme (Kenney pozları → oyun durumları)

`game/sprites.py` içindeki `STATE_POSES`, dövüşçü durumlarını Kenney
poz adlarına eşler (idle, walk0..7, jump, attack0..2, kick, duck, hit,
hurt/fallDown/down). Farklı bir sprite paketi kullanmak istersen bu
eşlemeyi ve `_CONTENT_HEIGHT_RATIO`'yu paketin canvas düzenine göre
güncellemen yeterli.

## Krediler

Karakter görselleri: **Kenney — Toon Characters** (https://kenney.nl),
**CC0** (kamu malı) lisansı. Tam lisans: `charac/License.txt`.
Oyun kodu bu proje kapsamında yazılmıştır.

## Sonrası için fikirler

- Özel hareketler (hadouken benzeri mermi) ve kombo girişi (`events` akışıyla input buffer)
- Havada tekme/yumruk, eğilme (crouch)
- PvP modu (ikinci `HumanController` + menüde mod seçimi)
- Ses efektleri (`pygame.mixer`)
