# -*- coding: utf-8 -*-
"""Brand assets from the ONE official logo (outreach/logo_linda_pro.png): square logo, wordmark crop, app icon, installer wizard images, base64 for the app UI.
    python tools/make_brand.py"""
import base64
import io
from pathlib import Path

from PIL import Image

SRC = Path(r"C:\Users\ninja\Desktop\Linda_commercial_release\outreach\logo_linda_pro.png")
DESK = Path(r"C:\Users\ninja\Desktop\Linda_desktop")
SITE = Path(r"C:\Users\ninja\Desktop\Linda_site")
BG = (13, 15, 21)

sq = Image.open(SRC).convert("RGB")  # 512x512, the logo as it is
word = sq.crop((36, 196, 476, 342))  # wordmark + dots, same background colour

a = DESK / "assets"
a.mkdir(exist_ok=True)
sq.save(a / "logo_square.png")
word.save(a / "logo_wordmark.png")
sq.save(a / "linda.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
sq.resize((256, 256), Image.LANCZOS).save(a / "linda.png")

# Inno Setup wizard images: large (164x314) and small (55x58)
big = Image.new("RGB", (164, 314), BG)
w = word.resize((150, int(word.height * 150 / word.width)), Image.LANCZOS)
big.paste(w, (7, 110))
big.save(a / "wizard.bmp")
small = Image.new("RGB", (55, 58), BG)
s = sq.resize((55, 55), Image.LANCZOS)
small.paste(s, (0, 1))
small.save(a / "wizard_small.bmp")

buf = io.BytesIO()
word.resize((220, int(word.height * 220 / word.width)), Image.LANCZOS).save(buf, "PNG", optimize=True)
(a / "wordmark_b64.txt").write_text(base64.b64encode(buf.getvalue()).decode(), encoding="ascii")

sa = SITE / "assets"
sa.mkdir(exist_ok=True)
sq.save(sa / "linda.png")
word.save(sa / "logo_wordmark.png")
sq.save(sa / "logo_square.png")
print("brand assets written:", [p.name for p in sorted(a.iterdir())], "| wordmark", word.size)
