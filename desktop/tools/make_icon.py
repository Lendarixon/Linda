# -*- coding: utf-8 -*-
"""The small app icon (the one the owner keeps): dark rounded square, blue frame, letter L, three coloured dots.
Used for the exe/installer icon, the site favicon and the small installer wizard image. The wordmark logo is only for banners.
    python tools/make_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESK = Path(r"C:\Users\ninja\Desktop\Linda_desktop")
SITE = Path(r"C:\Users\ninja\Desktop\Linda_site")
S = 512
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=(14, 20, 36, 255), outline=(91, 124, 250, 255), width=10)
try:
    f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 330)
except Exception:  # noqa: BLE001
    f = ImageFont.load_default()
d.text((S // 2, S // 2 - 30), "L", font=f, fill=(110, 168, 255, 255), anchor="mm")
for i, c in enumerate([(52, 211, 153), (52, 211, 153), (255, 87, 104), (52, 211, 153)]):
    x = 150 + i * 70
    d.rounded_rectangle((x - 22, 400, x + 22, 432), radius=12, fill=c + (255,))
a = DESK / "assets"
im.save(a / "linda.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
im.save(a / "linda.png")
im.save(SITE / "assets" / "linda.png")
small = Image.new("RGB", (55, 58), (13, 15, 21))
sm = im.resize((50, 50), Image.LANCZOS)
small.paste(sm, (2, 4), sm)
small.save(a / "wizard_small.bmp")
print("small icon restored")
