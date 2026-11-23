"""Google Play store graphics -> store/play/.

1. raw shots (1920x1080, clean game state):
   write a temporary override.cfg with a 1920x1080 window, then
   godot --path . scenes/game.tscn -- --storeshots          -> renders/play/raw/sN_*.png  (scripts/store_shots.gd)
2. python tools/play_store.py
   {en,ru}_N.png              landscape screenshots 1920x1080 with a caption band
   feature_{en,ru}_1024x500.png
   icon_512.png
English captions use the game's Gothic font; Russian ones Georgia Bold (the Gothic font has no Cyrillic).
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "renders", "play", "raw")
OUT = os.path.join(ROOT, "store", "play")
GOTHIC = os.path.join(ROOT, "assets", "fonts", "UnifrakturMaguntia-Book.ttf")
BODY = os.path.join(ROOT, "assets", "fonts", "IMFellEnglish-Roman.ttf")
CYR = "C:/Windows/Fonts/georgiab.ttf"
CYR_BODY = "C:/Windows/Fonts/georgia.ttf"
GOLD = (222, 178, 92)
PARCH = (240, 224, 190)

ORDER = ["s1_square", "s2_dialogue", "s7_bridge_golem", "s6_night_fight", "s3_weapons", "s4_journal", "s8_bridge_dusk", "s5_map"]
CAPTIONS = {
    "en": {"s1_square": "Medieval Prague, 1357", "s2_dialogue": "Talk to its people — Gothic style",
           "s7_bridge_golem": "Break the clay giants", "s6_night_fight": "The dead walk at night",
           "s3_weapons": "Swords, axes and greatswords", "s4_journal": "20 quests, always know where to go",
           "s8_bridge_dusk": "Four districts, one open city", "s5_map": "A painted map of Prague"},
    "ru": {"s1_square": "Средневековая Прага, 1357 год", "s2_dialogue": "Диалоги в духе «Готики»",
           "s7_bridge_golem": "Разбей глиняных великанов", "s6_night_fight": "Ночью мёртвые встают",
           "s3_weapons": "Мечи, топоры и двуручники", "s4_journal": "20 квестов — всегда ясно, куда идти",
           "s8_bridge_dusk": "Четыре района, один открытый город", "s5_map": "Рисованная карта Праги"},
}
TOP = {"s2_dialogue"}
TITLE = {"en": ("Alchemists of Prague", "A dark-fantasy action RPG in medieval Prague"),
         "ru": ("Alchemists of Prague", "Мрачное фэнтези-RPG в средневековой Праге")}


def font(lang, size, body=False):
    if lang == "ru":
        return ImageFont.truetype(CYR_BODY if body else CYR, size)
    return ImageFont.truetype(BODY if body else GOTHIC, size)


def fit(text, lang, size, max_w, body=False):
    while size > 24:
        f = font(lang, size, body)
        if f.getlength(text) <= max_w:
            return f
        size -= 4
    return font(lang, size, body)


def shadow_text(im, xy, text, f, fill, anchor="mm", blur=6):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(xy, text, font=f, fill=(0, 0, 0, 230), anchor=anchor, stroke_width=4, stroke_fill=(0, 0, 0, 230))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.alpha_composite(sh)
    ImageDraw.Draw(im).text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=2, stroke_fill=(30, 18, 8))


def screenshot(lang, name, n):
    im = Image.open(os.path.join(RAW, name + ".png")).convert("RGBA")
    w, h = im.size
    band = 230
    grad = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(grad)
    if name not in TOP:
        for y in range(band):
            d.line([(0, h - 1 - y), (w, h - 1 - y)], fill=int(225 * (1 - y / band) ** 1.2))
    dark = Image.new("RGBA", (w, h), (12, 8, 4, 255))
    im = Image.composite(dark, im, grad)
    text = CAPTIONS[lang][name]
    if name in TOP:      # the dialogue window fills the bottom: caption under the compass instead
        shadow_text(im, (w // 2, 175), text, fit(text, lang, 84, w - 200), GOLD)
    else:
        shadow_text(im, (w // 2, h - 92), text, fit(text, lang, 84, w - 200), GOLD)
    im.convert("RGB").save(os.path.join(OUT, f"{lang}_{n}.png"))


def feature(lang):
    bg = Image.open(os.path.join(ROOT, "assets", "ui", "title.png")).convert("RGBA")
    W, H = 1024, 500
    # the left 3/4 of the title art: painted logo, knight, Prague and the golem; the painted menu on the right is cut off
    cw = 1220
    ch = int(cw * H / W)
    y0 = 18
    bg = bg.crop((0, y0, cw, y0 + ch)).resize((W, H), Image.LANCZOS)
    # the title art already carries the painted logo top-left; add the tagline in a dark band at the bottom
    band = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(band)
    for y in range(120):
        d.line([(0, H - 1 - y), (W, H - 1 - y)], fill=int(220 * (1 - y / 120)))
    bg = Image.composite(Image.new("RGBA", (W, H), (10, 6, 3, 255)), bg, band)
    sub = TITLE[lang][1]
    shadow_text(bg, (W // 2, H - 44), sub, fit(sub, lang, 40, W - 80, body=True), PARCH, blur=4)
    bg.convert("RGB").save(os.path.join(OUT, f"feature_{lang}_1024x500.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    for lang in ("en", "ru"):
        for i, name in enumerate(ORDER):
            screenshot(lang, name, i + 1)
        feature(lang)
    Image.open(os.path.join(ROOT, "assets", "ui", "app_icon", "icon_512.png")).convert("RGB").resize((512, 512)).save(
        os.path.join(OUT, "icon_512.png"))
    print("store graphics ->", OUT)


if __name__ == "__main__":
    main()
