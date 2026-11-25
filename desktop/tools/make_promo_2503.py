"""Generate 4 Metro-style 1600x900 PNG promo cards for Linda 2.5.0.3 (Models 1.5.0)."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path.home() / "Desktop" / "Linda_2.5.0.3_Promo"
APP_SHOT = Path("C:/Users/ninja/Desktop/Linda_site/assets/shot-app-en.png")
REPORT_SHOT = Path("C:/Users/ninja/Desktop/Linda_site/assets/shot-report-en.png")

FONTS_DIR = Path("C:/Windows/Fonts")
F_LIGHT = str(FONTS_DIR / "segoeuil.ttf")
F_REG = str(FONTS_DIR / "segoeui.ttf")
F_SEMI = str(FONTS_DIR / "seguisb.ttf")
F_BOLD = str(FONTS_DIR / "segoeuib.ttf")

W, H = 1600, 900
MARGIN_X = 64

# Palette matching the reference Metro cards
ACCENT_BLUE = (80, 128, 255)
TEXT_WHITE = (255, 255, 255)
TEXT_SOFT = (238, 243, 252)
TEXT_MUTED = (154, 166, 186)
TEXT_FOOTER = (138, 150, 170)

TILE_COLORS = {
    "blue": (0, 80, 239),
    "green": (16, 124, 16),
    "purple": (122, 63, 228),
    "magenta": (195, 0, 82),
    "orange": (202, 90, 18),
    "slate": (92, 107, 122),
}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def make_background() -> Image.Image:
    """Create smooth dark navy gradient canvas matching the reference cards."""
    base = Image.new("RGB", (W, H), (10, 14, 24))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    # Soft upper-center/right radial glow
    for r, alpha in [(720, 10), (540, 14), (380, 16)]:
        d.ellipse((1080 - r, 220 - r, 1080 + r, 220 + r), fill=(26, 44, 86, alpha))
    for r, alpha in [(620, 8), (420, 10)]:
        d.ellipse((340 - r, 460 - r, 340 + r, 460 + r), fill=(18, 30, 58, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    out = Image.alpha_composite(base.convert("RGBA"), glow)
    return out.convert("RGB")


def draw_header(
    img: Image.Image,
    title_parts: list[tuple[str, tuple[int, int, int]]],
    subtitle: str,
) -> None:
    """Draw top-left Linda-Pro brand, large display headline, and subtitle."""
    d = ImageDraw.Draw(img)
    f_brand = font(F_BOLD, 34)
    bx = MARGIN_X
    by = 48
    d.text((bx, by), "Linda-", font=f_brand, fill=TEXT_WHITE)
    w_linda = d.textlength("Linda-", font=f_brand)
    d.text((bx + w_linda, by), "Pro", font=f_brand, fill=ACCENT_BLUE)

    f_title = font(F_LIGHT, 94)
    tx = MARGIN_X
    ty = 112
    for text, color in title_parts:
        d.text((tx, ty), text, font=f_title, fill=color)
        tx += d.textlength(text, font=f_title)

    f_sub = font(F_LIGHT, 25)
    d.text((MARGIN_X, 232), subtitle, font=f_sub, fill=TEXT_MUTED)


def draw_footer(img: Image.Image) -> None:
    """Draw bottom-right site URL."""
    d = ImageDraw.Draw(img)
    f_foot = font(F_LIGHT, 25)
    label = "lendarixon.github.io/Linda"
    tw = d.textlength(label, font=f_foot)
    d.text((W - MARGIN_X - tw, 840), label, font=f_foot, fill=TEXT_FOOTER)


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if draw.textlength(cand, font=fnt) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_small_tile(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color_key: str,
    title: str,
    sub: str,
) -> None:
    """Draw a crisp 0px-radius Metro tile with bold title and light/regular subtitle."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=TILE_COLORS[color_key])
    pad_x = 24
    max_w = (x1 - x0) - pad_x * 2
    f_t = font(F_BOLD, 27)
    f_s = font(F_LIGHT, 23)

    t_lines = wrap_lines(draw, title, f_t, max_w)
    s_lines = wrap_lines(draw, sub, f_s, max_w)

    line_h_t = 34
    line_h_s = 30
    gap = 6
    total_h = len(t_lines) * line_h_t + gap + len(s_lines) * line_h_s
    cy = y0 + ((y1 - y0) - total_h) // 2 - 2

    for line in t_lines:
        draw.text((x0 + pad_x, cy), line, font=f_t, fill=TEXT_WHITE)
        cy += line_h_t
    cy += gap
    for line in s_lines:
        draw.text((x0 + pad_x, cy), line, font=f_s, fill=TEXT_SOFT)
        cy += line_h_s


def draw_2x3_tiles(
    img: Image.Image,
    specs: list[tuple[str, str, str]],
) -> None:
    """Draw a 2-column by 3-row Metro tile grid on the left side."""
    d = ImageDraw.Draw(img)
    col_w = 386
    row_h = 136
    gap = 20
    start_x = MARGIN_X
    start_y = 312
    for idx, (color_key, title, sub) in enumerate(specs):
        row = idx // 2
        col = idx % 2
        x0 = start_x + col * (col_w + gap)
        y0 = start_y + row * (row_h + gap)
        draw_small_tile(d, (x0, y0, x0 + col_w, y0 + row_h), color_key, title, sub)


def paste_rounded_card(
    canvas: Image.Image,
    card_img: Image.Image,
    target_box: tuple[int, int, int, int],
    radius: int = 14,
    border_color: tuple[int, int, int, int] = (46, 58, 84, 220),
) -> None:
    """Resize card_img cleanly into target_box with rounded corners, shadow, and thin border."""
    tx0, ty0, tx1, ty1 = target_box
    tw = tx1 - tx0
    th = ty1 - ty0
    resized = card_img.convert("RGBA").resize((tw, th), Image.Resampling.LANCZOS)

    # Drop shadow
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.rounded_rectangle(
        (tx0 + 4, ty0 + 10, tx1 + 4, ty1 + 14),
        radius=radius + 2,
        fill=(0, 0, 0, 140),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(16))

    mask = Image.new("L", (tw, th), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, tw - 1, th - 1), radius=radius, fill=255)

    out = canvas.convert("RGBA")
    out = Image.alpha_composite(out, shadow_layer)
    out.paste(resized, (tx0, ty0), mask)

    bd = ImageDraw.Draw(out)
    bd.rounded_rectangle((tx0, ty0, tx1, ty1), radius=radius, outline=border_color, width=2)
    canvas.paste(out.convert("RGB"))


def prepare_app_shot() -> Image.Image:
    """Load dark app screenshot and cleanly update version labels to 2.5.0.3."""
    im = Image.open(APP_SHOT).convert("RGB")
    d = ImageDraw.Draw(im)
    bg = (17, 19, 24)
    # Remove header 2.3.0.0 badge (2.5 removes version string from header)
    d.rectangle((120, 24, 168, 45), fill=bg)
    # Update bottom-right footer version
    d.rectangle((1358, 875, 1432, 895), fill=bg)
    f_ver = font(F_REG, 11)
    d.text((1364, 878), "Linda 2.5.0.3", font=f_ver, fill=(138, 146, 160))
    return im


def prepare_report_shot() -> Image.Image:
    """Load light report screenshot, crop cleanly to card, update version to v2.5.0.3."""
    im = Image.open(REPORT_SHOT).convert("RGB")
    d = ImageDraw.Draw(im)
    # Replace v2.3.0.0 at (823..862, 127..131) on white background
    d.rectangle((806, 121, 868, 140), fill=(255, 255, 255))
    f_ver = font(F_REG, 12)
    txt = "v2.5.0.3"
    tw = d.textlength(txt, font=f_ver)
    d.text((862 - tw, 122), txt, font=f_ver, fill=(100, 110, 125))
    # Crop neatly to the white report card
    return im.crop((186, 26, 888, 885))


def build_card_1() -> Path:
    img = make_background()
    draw_header(
        img,
        [("2.5", ACCENT_BLUE), (" is out", TEXT_WHITE)],
        "Local AI-text detector for Windows. App 2.5.0.3 · Models 1.5.0.",
    )
    draw_2x3_tiles(
        img,
        [
            ("blue", "New models 1.5", "Polish AI 79% → 89%, fewer FPs"),
            ("green", "2.55× faster", "static-batch ONNX on GPU"),
            ("purple", "Token markup v2", "higher AUC on all 6 pairs"),
            ("magenta", "Full Trace UI", "MDS map, SVG charts & corpora"),
            ("orange", "Faster Humanizer", "batched GPU + fixed CPU Lite"),
            ("slate", "Ed25519-signed", "61-file pack · RU · PL · EN"),
        ],
    )
    shot = prepare_app_shot()
    # Aspect 1440:900 = 1.6 -> width 644 => height 402
    paste_rounded_card(img, shot, (892, 318, 1536, 720), radius=12)
    draw_footer(img)
    out = OUT_DIR / "01_linda_2.5_is_out.png"
    img.save(out, format="PNG")
    return out


def build_card_2() -> Path:
    img = make_background()
    draw_header(
        img,
        [("New models ", TEXT_WHITE), ("1.5", ACCENT_BLUE)],
        "Assay 1.5.0, Loupe split-conformal calibration and token-level markup v2.",
    )
    d = ImageDraw.Draw(img)
    tiles = [
        ("blue", "Polish AI (Assay)", "AI text caught, held-out test set (n=350)", "79.4% → 88.9%"),
        ("green", "Human false alarms", "Assay on Polish (n=350) & Russian (n=648) humans", "PL 0.9% · RU 0.0%"),
        ("purple", "Loupe (Polish FPR)", "Split-conformal calibration with abstention band", "3.14% → 0.00%"),
        ("magenta", "Token markup v2", "Essay AUC: English 0.60→0.76 · Polish 0.59→0.75", "6 / 6 pairs up"),
    ]
    tile_w = 726
    tile_h = 205
    gap = 20
    start_y = 304

    f_title = font(F_BOLD, 30)
    f_sub = font(F_LIGHT, 23)
    f_big = font(F_SEMI, 62)

    for idx, (ck, title, sub, big) in enumerate(tiles):
        r, c = idx // 2, idx % 2
        x0 = MARGIN_X + c * (tile_w + gap)
        y0 = start_y + r * (tile_h + gap)
        d.rectangle((x0, y0, x0 + tile_w, y0 + tile_h), fill=TILE_COLORS[ck])
        d.text((x0 + 30, y0 + 24), title, font=f_title, fill=TEXT_WHITE)
        d.text((x0 + 30, y0 + 66), sub, font=f_sub, fill=TEXT_SOFT)
        d.text((x0 + 30, y0 + 108), big, font=f_big, fill=TEXT_WHITE)

    f_note = font(F_LIGHT, 20)
    d.text(
        (MARGIN_X, 766),
        "Models 1.3.2 → 1.5.0. English Assay benchmarks unchanged by design (HumanizerBench 81.0%, StealthGPT 88.0%). PolEval 2025: 82.3% TPR, 0.967 AUROC.",
        font=f_note,
        fill=TEXT_MUTED,
    )
    d.text(
        (MARGIN_X, 796),
        "Honest note: Loupe trades AI recall (32–52%) for CPU speed; Russian token-level F1 stays low under conservative calibration (read AUC: 0.52 → 0.64).",
        font=f_note,
        fill=TEXT_MUTED,
    )
    draw_footer(img)
    out = OUT_DIR / "02_new_models_1.5.png"
    img.save(out, format="PNG")
    return out


def build_card_3() -> Path:
    img = make_background()
    draw_header(
        img,
        [("Faster ", TEXT_WHITE), ("& clearer", ACCENT_BLUE)],
        "Batched inference, unified markup, full Trace workspace and clean PDF reports.",
    )
    draw_2x3_tiles(
        img,
        [
            ("blue", "2.55× GPU speed", "static-batch ONNX, ~3.9 GB VRAM"),
            ("green", "7.5× faster fallback", "zero extra forwards on markup"),
            ("purple", "Trace workspace", "3 modes, MDS map & SVG charts"),
            ("magenta", "Humanizer 4.8×", "486 tok/s Lite · 338 tok/s Full"),
            ("orange", "Fixed PDF import", "no doubled words from slides"),
            ("slate", "WCAG AA contrast", "512 pairs · 753 EN/PL/RU strings"),
        ],
    )
    report_crop = prepare_report_shot()
    # report_crop is 702 x 859; fit height ~486 -> width ~397; place centered on right (x=1016..1413) or wider crop top
    # Use top portion of report card matching aspect ~1.22 (702 x 575) so bars + gauge are crisp and large
    report_top = report_crop.crop((0, 0, report_crop.width, 610))
    # 702:610 -> at width 560 => height 487
    paste_rounded_card(img, report_top, (944, 294, 1504, 781), radius=12, border_color=(210, 220, 238, 220))
    draw_footer(img)
    out = OUT_DIR / "03_faster_and_clearer.png"
    img.save(out, format="PNG")
    return out


def build_card_4() -> Path:
    img = make_background()
    draw_header(
        img,
        [("Installer ", TEXT_WHITE), ("& reliability", ACCENT_BLUE)],
        "Signed manifests, automatic pack downloads and verified releases.",
    )
    draw_2x3_tiles(
        img,
        [
            ("blue", "Signed manifest", "Ed25519 + 61/61 SHA-256 checks"),
            ("green", "Auto-install packs", "Trace & Humanizer on first start"),
            ("purple", "4× downloads", "parallel fetch + Pause button"),
            ("magenta", "CPU Lite fixes", "EOS stop & 45s per-chunk cap"),
            ("orange", "Strict access", "403 without licence, fail-closed"),
            ("slate", "842+ checks", "732 pytest · 110 reg · 7 E2E"),
        ],
    )

    # Custom dark modal card on the right matching Ref 4
    mx0, my0, mx1, my1 = 918, 298, 1510, 718
    rgba = img.convert("RGBA")
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((mx0 + 4, my0 + 10, mx1 + 4, my1 + 14), radius=14, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    rgba = Image.alpha_composite(rgba, shadow)
    md = ImageDraw.Draw(rgba)

    md.rounded_rectangle(
        (mx0, my0, mx1, my1),
        radius=12,
        fill=(22, 28, 41, 255),
        outline=(54, 68, 94, 255),
        width=2,
    )

    f_mh = font(F_BOLD, 30)
    f_mb = font(F_LIGHT, 21)
    f_ib = font(F_REG, 21)
    f_is = font(F_LIGHT, 19)
    f_btn = font(F_SEMI, 20)

    px = mx0 + 34
    md.text((px, my0 + 30), "Linda 2.5.0.3 · Pack 1.5.0", font=f_mh, fill=TEXT_WHITE)

    body = (
        "First start verifies the Ed25519 signature and downloads only the packs "
        "you selected. Everything runs offline afterwards."
    )
    by = my0 + 82
    for line in wrap_lines(md, body, f_mb, (mx1 - mx0) - 68):
        md.text((px, by), line, font=f_mb, fill=TEXT_MUTED)
        by += 29

    # Inner dark inset box with blue left bar
    ix0, iy0, ix1, iy1 = px, my0 + 190, mx1 - 34, my1 - 32
    md.rounded_rectangle(
        (ix0, iy0, ix1, iy1),
        radius=6,
        fill=(14, 19, 29, 255),
        outline=(42, 52, 72, 255),
        width=1,
    )
    md.rectangle((ix0, iy0 + 2, ix0 + 5, iy1 - 2), fill=(0, 120, 212, 255))

    md.text((ix0 + 22, iy0 + 20), "Model pack: 1.5.0 (61 files · 6.08 GB)", font=f_ib, fill=TEXT_WHITE)
    md.text((ix0 + 22, iy0 + 54), "Assay 5.77 GB · Loupe 0.30 GB · Ed25519 OK", font=f_is, fill=TEXT_MUTED)

    bx0, by0, bx1, by1 = ix0 + 22, iy0 + 104, ix0 + 258, iy0 + 150
    md.rounded_rectangle((bx0, by0, bx1, by1), radius=6, fill=(0, 102, 204, 255))
    btn_txt = "Verified · Offline ready"
    btw = md.textlength(btn_txt, font=f_btn)
    md.text((bx0 + (bx1 - bx0 - btw) / 2, by0 + 10), btn_txt, font=f_btn, fill=TEXT_WHITE)

    # Caption directly below modal card
    f_cap = font(F_LIGHT, 21)
    cap = "Updating from 2.3.0.2 keeps your licence and settings and updates models automatically — no manual install."
    cy = my1 + 26
    for line in wrap_lines(md, cap, f_cap, mx1 - mx0 + 20):
        md.text((mx0 - 10, cy), line, font=f_cap, fill=TEXT_MUTED)
        cy += 28

    img = rgba.convert("RGB")
    draw_footer(img)
    out = OUT_DIR / "04_installer_and_reliability.png"
    img.save(out, format="PNG")
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [build_card_1(), build_card_2(), build_card_3(), build_card_4()]
    for p in paths:
        im = Image.open(p)
        print(f"WROTE: {p} size={im.size}")


if __name__ == "__main__":
    main()
