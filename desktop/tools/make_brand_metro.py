# -*- coding: utf-8 -*-
"""Фирменный стиль Metro (10.10.2026, вариант C «подсветка»): голубая плитка с тремя строками текста, кусок средней
подсвечен красным - как пословная подсветка ИИ в приложении. Рисует все растровые файлы бренда из одного описания знака и раскладывает их по местам.
    python tools/make_brand_metro.py            # только папка Desktop\\Linda_brand_metro
    python tools/make_brand_metro.py --install  # + assets приложения, публичного репо и сайта"""
import base64
import io
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DESK = Path(r"C:\Users\ninja\Desktop")
OUT = DESK / "Linda_brand_metro"
BG, CYAN, RED, WHITE, MUTED = (13, 15, 21), (27, 161, 226), (229, 20, 0), (255, 255, 255), (168, 173, 184)
COBALT, TEAL = (0, 80, 239), (0, 171, 169)
LIGHT, SEMI, REG = "C:/Windows/Fonts/segoeuil.ttf", "C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/segoeui.ttf"

# знак - плитка с тремя строками текста, кусок средней подсвечен красным (как пословная подсветка в приложении).
# Сетка 2x2 из квадратов (вариант A) отвергнута: слишком похожа на логотип Windows.
SVG_MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#1ba1e2"/>'
            '<rect x="14" y="24" width="72" height="12" fill="#fff"/><rect x="14" y="44" width="32" height="12" fill="#fff"/>'
            '<rect x="52" y="44" width="34" height="12" fill="#e51400"/><rect x="14" y="64" width="52" height="12" fill="#fff"/></svg>\n')
SVG_ICON = SVG_MARK
# (x0, y0, x1, y1, цвет) в долях 0..100; для 24 px и меньше - две строки, чтобы не слиплось
BARS = [(14, 24, 86, 36, WHITE), (14, 44, 46, 56, WHITE), (52, 44, 86, 56, RED), (14, 64, 66, 76, WHITE)]
BARS_SMALL = [(14, 22, 86, 42, WHITE), (14, 58, 42, 78, WHITE), (50, 58, 86, 78, RED)]

def font(path, size):
    return ImageFont.truetype(path, size)


def mark(d, x, y, s, main=CYAN, red=RED):
    """Знак-плитка размером s в точке (x, y)."""
    d.rectangle((x, y, x + s - 1, y + s - 1), fill=main)
    for x0, y0, x1, y1, c in (BARS_SMALL if s <= 24 else BARS):
        d.rectangle((x + round(x0 * s / 100), y + round(y0 * s / 100), x + round(x1 * s / 100) - 1, y + round(y1 * s / 100) - 1),
                    fill=red if c == RED else c)


def icon(s):
    """Иконка приложения = знак-плитка во весь размер."""
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    mark(ImageDraw.Draw(im), 0, 0, s)
    return im

def wordmark(h, bg=None, text=WHITE, sub=None, accent=CYAN):
    """Знак + «linda» (бренд), высота h; sub - имя продукта полужирным акцентом («assay», «loupe»). bg=None - прозрачный фон."""
    fl, fs = font(LIGHT, round(h * 0.9)), font(SEMI, round(h * 0.9))
    w1 = fl.getlength("linda" + (" " if sub else ""))
    w2 = fs.getlength(sub) if sub else 0
    gap = round(h * 0.32)
    W = h + gap + int(w1 + w2) + round(h * 0.08)
    im = Image.new("RGBA", (W, h), (bg + (255,)) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    mark(d, 0, 0, h)
    base = round(h * 0.82)
    d.text((h + gap, base), "linda" + (" " if sub else ""), font=fl, fill=text, anchor="ls")
    if sub:
        d.text((h + gap + w1, base), sub, font=fs, fill=accent, anchor="ls")
    return im


def square(s=512):
    im = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(im)
    m = round(s * 0.36)
    mark(d, (s - m) // 2, round(s * 0.17), m)
    d.text((s / 2, round(s * 0.80)), "linda", font=font(LIGHT, round(s * 0.18)), fill=WHITE, anchor="ms")
    return im


def avatar(s=512):
    im = Image.new("RGB", (s, s), BG)
    m = round(s * 0.5)
    mark(ImageDraw.Draw(im), (s - m) // 2, (s - m) // 2, m)
    return im


def og():
    im = Image.new("RGB", (1200, 630), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1199, 9), fill=CYAN)
    mark(d, 80, 110, 192)
    d.text((320, 232), "linda", font=font(LIGHT, 130), fill=WHITE, anchor="ls")
    d.text((82, 400), "Was this text written by AI?", font=font(LIGHT, 46), fill=WHITE, anchor="ls")
    d.text((82, 456), "Local detector for English, Russian and Polish. Your texts stay on your PC.", font=font(REG, 27), fill=MUTED, anchor="ls")
    x = 80
    for tag, name, col in (("As", "Linda Assay", COBALT), ("Lp", "Linda Loupe", TEAL)):
        d.rectangle((x, 518, x + 55, 573), fill=col)
        d.text((x + 28, 556), tag, font=font(SEMI, 26), fill=WHITE, anchor="ms")
        d.text((x + 70, 556), name, font=font(REG, 26), fill=WHITE, anchor="ls")
        x += 290
    d.text((1120, 556), "lendarixon.github.io/Linda", font=font(REG, 24), fill=MUTED, anchor="rs")
    return im


def banner():
    im = Image.new("RGB", (1280, 320), (23, 26, 34))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1279, 7), fill=CYAN)
    mark(d, 72, 92, 144)
    d.text((260, 178), "linda", font=font(LIGHT, 104), fill=WHITE, anchor="ls")
    d.text((264, 228), "Local AI-text detector  ·  Linda Assay  ·  Linda Loupe  ·  EN / RU / PL", font=font(REG, 28), fill=MUTED, anchor="ls")
    return im


def wizard_big():
    im = Image.new("RGB", (164, 314), BG)
    d = ImageDraw.Draw(im)
    mark(d, 42, 100, 80)
    d.text((82, 226), "linda", font=font(LIGHT, 44), fill=WHITE, anchor="ms")
    return im


def wizard_small():
    im = Image.new("RGB", (55, 58), BG)
    ic = icon(48)
    im.paste(ic, (3, 5), ic)
    return im

def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "mark.svg").write_text(SVG_MARK, encoding="utf-8")
    (OUT / "icon.svg").write_text(SVG_ICON, encoding="utf-8")
    sizes = [256, 128, 64, 48, 32, 24, 16]
    frames = [icon(s) for s in sizes]
    frames[0].save(OUT / "linda.ico", sizes=[(s, s) for s in sizes], append_images=frames[1:])
    icon(256).save(OUT / "linda.png")
    icon(512).save(OUT / "icon_512.png")
    store = OUT / "store_Assets"
    store.mkdir(exist_ok=True)
    for name, s in (("StoreLogo", 50), ("Square44x44Logo", 44), ("Square150x150Logo", 150)):
        icon(s).save(store / f"{name}.png")
    square().save(OUT / "logo_square.png")
    avatar().save(OUT / "avatar_512.png")
    wordmark(120).save(OUT / "logo_wordmark.png")            # прозрачный фон, для тёмной шапки сайта
    wordmark(120, bg=BG).save(OUT / "logo_wordmark_dark.png")
    wordmark(120, text=(20, 24, 33)).save(OUT / "logo_wordmark_light.png")
    wordmark(120, sub="assay", accent=(27, 161, 226)).save(OUT / "wordmark_assay.png")
    wordmark(120, sub="loupe", accent=TEAL).save(OUT / "wordmark_loupe.png")
    og().save(OUT / "og_image.png")
    banner().save(OUT / "readme_banner.png")
    wizard_big().save(OUT / "wizard.bmp")
    wizard_small().save(OUT / "wizard_small.bmp")
    buf = io.BytesIO()
    w = wordmark(120, bg=BG)
    w.resize((220, round(w.height * 220 / w.width)), Image.LANCZOS).save(buf, "PNG", optimize=True)
    (OUT / "wordmark_b64.txt").write_text(base64.b64encode(buf.getvalue()).decode(), encoding="ascii")
    print("brand ->", OUT, sorted(p.name for p in OUT.iterdir()))


APP_FILES = ["linda.ico", "linda.png", "logo_square.png", "logo_wordmark.png", "wizard.bmp", "wizard_small.bmp", "wordmark_b64.txt"]
SITE_FILES = ["linda.png", "logo_wordmark.png", "logo_square.png", "og_image.png"]


def install():
    root = Path(__file__).resolve().parents[1]
    for dst in (root / "assets", DESK / "github_public/Linda/desktop/assets"):
        for n in APP_FILES:
            shutil.copy2(OUT / n, dst / n)
        print("app assets ->", dst)
    for dst in (DESK / "Linda_site/assets", DESK / "Linda_site/public/assets"):
        if dst.exists():
            for n in SITE_FILES:
                shutil.copy2(OUT / n, dst / n)
            print("site assets ->", dst)


if __name__ == "__main__":
    build()
    if "--install" in sys.argv:
        install()
