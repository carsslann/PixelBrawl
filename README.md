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
| S | Çömel |
| J | Yumruk |
| K | Tekme |
| **geri tut** | Blok (rakibin tersine bas) |
| ↓ → + J | Özel ateş (mermi) · dolu metre = EX |
| ↓ ← + K | Özel silah (hilal / anti-air) |
| J + K | Atma (bloklanamaz, yakın) |
| ESC | Duraklat / devam (duraklatmada Q: ana menü) |

Menüde ok tuşları / WASD ile **mod**, karakter, rakip ve zorluğu seç,
ENTER ile başla. **H** hareket listesi, **O** ayarlar (ses / tam ekran /
tuş atama). Maç sonu ENTER = tekrar, ESC = menü.

Ayrıca: kamera yakın dövüşte hafif **zoom** yapar, sahneye göre **ışık
tonu** değişir, HUD'da karakter **portreleri** görünür.

## Modlar

- **Tek Kişi (Bot):** sen vs bot (3 zorluk).
- **2 Kişi (PvP):** aynı klavyede iki oyuncu. **1. oyuncu:** WASD + J/K.
  **2. oyuncu:** ok tuşları + `,` (yumruk) / `.` (tekme), yön komutları aynı.
- **Arcade:** seçtiğin karakterle 6 rakibi sırayla yen; kaybedince biter,
  hepsini geçersen ŞAMPİYON.

## Hareketler ve kombolar

Saldırıların **startup → active → recovery** kare pencereleri vardır:
vuruş yalnızca active penceresinde isabet eder, recovery sırasında
savunmasızsın.

- **Ayakta:** J yumruk, K tekme (yüksek — ayakta veya çömelerek bloklanır)
- **Çömelerek (S + vuruş):** alçak yumruk; **S + K = süpürme** (alçak, rakibi
  yere serer). Alçak saldırılar yalnızca **çömel-blok** ile kesilir.
- **Havada (zıpla + vuruş):** overhead hava yumruğu/tekmesi. Overhead yalnızca
  **ayakta blok** ile kesilir → yüksek/alçak ikilemi (mixup).
- **Zincir kombo (magic series):** bir vuruş **isabet ederse** toparlanması
  daha ağır bir vuruşa iptal edilebilir (yumruk → tekme/süpürme). Zıpla-vur
  ile başlayıp yere inince yer vuruşuyla devam = jump-in kombo. Kombodaki
  sonraki vuruşlar kademeli olarak daha az hasar verir (sonsuz kombo yok).
- **Özel ateş (mermi):** komut **↓ → + J** (aşağı, sonra rakibe doğru, sonra
  yumruk — quarter-circle-forward). Süper metre yeterliyse karakterin renkli
  ateş topunu fırlatır; blokla kesilebilir (chip). Her karakterin rengi/hızı/
  hasarı farklı (ROBO yavaş-güçlü, ZEYNEP hızlı-zayıf).
- **Özel silah:** komut **↓ ← + K**. Yakın mesafe hilal/vuruş; efe/robo/goron
  yükselen anti-air (havadaki rakibi düşürür), ada/mira ileri hilal, zeynep
  hızlı atılma. Karaktere göre renkli yay çizilir.
- **Atma (throw):** **J + K aynı anda**, yakın mesafede. **Bloklanamaz** — bloğu
  kıran tek seçenek; rakibi yere serer.
- **EX ateş:** süper metre **doluyken** özel ateş yaparsan tüm barı harcayıp
  daha büyük/hızlı/güçlü ateş fırlatır.

**Süper metre:** can barının altındaki bar; vuruş verince/yiyince dolar (dolunca
sarı). Özel ateş/silah harcar, dolu bar = EX. Bot da metresi dolunca kullanır.

**Blok:** rakibin tersine bastığın sürece bloklarsın; hasarın ~%85'ini keser
(kalan "chip"). Doğru yükseklikte bloklamak şart: alçağı çömelerek, overhead'i
ayakta.

## His & görsel (efektler, ses, kamera)

- **Parallax sahneler:** her sahne derinlikli katmanlardan oluşur (uzak dağ →
  tepe → zemin → ön plan çalı/ağaç); dövüşçüler kenara yüklendikçe kamera hafif
  salınır, katmanlar farklı hızda kayar → derinlik. Ön plan öğeleri dövüşçüleri
  önden çerçeveler.
- **Ses** (`audio.py`): tüm sesler kodla sentezlenir (harici dosya yok) —
  yumruk/tekme, blok "tınk", KO gong, zıpla/in, whoosh, menü, düşük sesli müzik.
- **Vuruş efektleri:** kıvılcım, yükselen hasar sayısı, **impact ring** (ağır
  vuruşta radyal halka), ekran sarsıntısı, **isabet donması** (hitstop), kombo
  sayacı ("N VURUŞ!"), KO'da tam ekran flaş + **slow-mo + vinyet**.
- **Atmosfer:** sahneye göre süzülen ortam partikülleri (yaprak/toz/kor).
- **Hareket izi** (afterimage) hızlı hareket ve saldırılarda; **kazanma pozu**
  (maç sonu kazanan sevinir); round başı **VS açılışı**.

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
  match.py         round/maç akışı, süre, KO, efekt/ses/kamera tetikleme
  effects.py       kıvılcım/hasar sayısı/toz/sarsıntı/KO flaşı/impact ring/ambient/vinyet
  audio.py         prosedürel ses sentezi (pygame.mixer, harici dosya yok)
  hud.py           can barları, süre, pankartlar, VS açılışı
  renderer.py      TEK çizim kapısı: sprite + hareket izi; sahne parallax'ı stages'e devreder
  sprites.py       Kenney poz-başına PNG yükleyici + animasyon (kazanma cheer dahil)
  stages.py        10 sahne + PARALLAX (Scene: derinlikli katmanlar, kamera salınımı)
  projectile.py    uçan mermi (özel ateş) sınıfı + make_fireball fabrikası
  fx_sprites.py    atesefekt sheet yükleyici (renk başına ateş topu / patlama)
  screens.py       hareket listesi + arcade pankart ekranları
  settings_screen.py  ayarlar ekranı (ses / tam ekran / tuş atama)
  config.py        ayar kalıcılığı (assets/config.json)
  menu.py          karakter / rakip / zorluk seçim ekranı (sprite önizlemeli)
charac/            Kenney "Toon Characters" sprite paketi (CC0) — bkz. Krediler
backgroundpack/    Kenney "Background elements" paketi (CC0) — sahne görselleri
tests/smoke_test.py  pencere açmadan çalışan testler (py tests/smoke_test.py, 25 test)
```

Her maçta 10 sahneden biri rastgele gelir (orman/çayır/sonbahar/çöl + gündüz
dağlar, gün batımı, gece, bulutlu ova, sisli orman, şato). Yeni sahne eklemek
için `game/stages.py`'ye bir giriş yaz.

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

Görseller: **Kenney** (https://kenney.nl), **CC0** (kamu malı) lisansı.
- Karakterler: *Toon Characters* — `charac/License.txt`
- Sahneler: *Background elements* — `backgroundpack/License.txt`

Oyun kodu bu proje kapsamında yazılmıştır.

## Sonrası için fikirler

- Özel hareketler (hadouken benzeri mermi) ve kombo girişi (`events` akışıyla input buffer)
- Havada tekme/yumruk, eğilme (crouch)
- PvP modu (ikinci `HumanController` + menüde mod seçimi)
- Ses efektleri (`pygame.mixer`)
