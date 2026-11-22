# -*- coding: utf-8 -*-
"""2.5.0.1 installer regression test (Fixer 2).

The Inno Setup script has no unit-test harness, so this test guards the three
invariants that the fixes depend on and that are cheap to check without ISCC:

A) The installer really offers to reuse a licence key that already exists on the
   computer: [Code] must define the detection helper, the reuse radio must exist,
   and the found key must be copyable into the install dir profile.
C) The brand mark keeps its blue tile everywhere it is drawn (installer icon,
   exe icon, web header, startup icon). A stripped tile leaves bars + red only,
   which is exactly the 2.5.0.0 regression.
E) Uninstall keeps user data by default and [UninstallDelete] never touches
   %LOCALAPPDATA% profiles.

Run:  python -m pytest tests/test_installer_2501.py -q
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "installer" / "linda.iss"
CYAN = (27, 161, 226)      # #1ba1e2 — the brand tile
RED = (229, 20, 0)         # #e51400 — the highlighted word
WHITE = (255, 255, 255)
BLUE_HEX = "#1ba1e2"


# --------------------------------------------------------------------------- A
def _iss() -> str:
    return ISS.read_text(encoding="utf-8")


def test_iss_exists():
    assert ISS.is_file(), "installer/linda.iss missing"


def test_code_defines_license_detection():
    s = _iss()
    assert "function FindExistingLicense: String;" in s
    assert "function LicenseFileUsable(F: String): Boolean;" in s
    assert "function CopyExistingLicense: Boolean;" in s


def test_detection_covers_both_documented_locations():
    """Both profile layouts from the bug report must be searched."""
    s = _iss()
    assert "Linda-Pro*" in s, "versioned EXE data folders not searched"
    assert "Packages" in s and "LocalState" in s, "MSIX profile not searched"


def test_reuse_radio_wired_into_licence_page():
    s = _iss()
    assert "LicReuseRadio: TRadioButton;" in s
    assert "LicReuseRadio.OnClick := @LicModeChanged;" in s
    # reuse must satisfy the "you need a key" gate and the pack gate
    assert "Result := (LicenseKey <> '') or ReuseChosen;" in s
    assert "not LicReuseRadio.Checked" in s


def test_reuse_copies_into_install_profile():
    s = _iss()
    # the copy target is the app data dir, never the install folder
    assert "CopyFile(ExistingLicense, DataDir + '\\license.json', False)" in s
    # a key that is already present must not be clobbered
    assert "do not clobber" in s


def test_reuse_messages_in_all_three_languages():
    s = _iss()
    for lang in ("english", "russian", "polish"):
        assert f"{lang}.LicReuseMode=" in s
        assert f"{lang}.LicReuseNote=" in s


def test_revoked_licence_is_not_offered():
    s = _iss()
    assert 'Pos(\'"revoked"\', T) = 0' in s


# --------------------------------------------------------------------------- C
def _png_pixels(path: Path):
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    return im, im.load()


def _coverage(path: Path, colour, tol: int = 8) -> float:
    im, px = _png_pixels(path)
    w, h = im.size
    hit = 0
    total = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            total += 1
            if abs(r - colour[0]) <= tol and abs(g - colour[1]) <= tol and abs(b - colour[2]) <= tol:
                hit += 1
    return hit / total if total else 0.0


def _ico_frames(path: Path):
    """Decode every frame of a PNG-compressed .ico as PIL images."""
    import io

    from PIL import Image

    d = path.read_bytes()
    n = struct.unpack("<H", d[4:6])[0]
    out = []
    for i in range(n):
        e = 6 + i * 16
        w, h, _c, _r, _p, _b, size, off = struct.unpack("<BBBBHHII", d[e:e + 16])
        blob = d[off:off + size]
        assert blob[:4] == b"\x89PNG", "icon frame is not PNG-compressed"
        out.append(((w or 256), (h or 256), Image.open(io.BytesIO(blob)).convert("RGBA")))
    return out


@pytest.mark.parametrize("name", ["linda.png", "logo_square.png", "logo_wordmark.png"])
def test_png_assets_keep_blue(name):
    p = ROOT / "assets" / name
    assert p.is_file(), f"assets/{name} missing"
    assert _coverage(p, CYAN) > 0.05, f"{name}: blue tile missing or too small"


def test_installer_icon_has_blue_at_every_size():
    ico = ROOT / "assets" / "linda.ico"
    assert ico.is_file(), "assets/linda.ico missing"
    frames = _ico_frames(ico)
    assert len(frames) >= 5, "icon should carry the usual size ladder"
    for w, h, im in frames:
        px = im.load()
        blue = sum(1 for y in range(h) for x in range(w)
                   if px[x, y][3] > 128 and px[x, y][:3] == CYAN)
        ratio = blue / float(w * h)
        assert ratio > 0.30, f"icon frame {w}x{h}: blue tile coverage {ratio:.2%} too low"


def test_web_header_logo_draws_blue_tile():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<span class="brand-logo".*?</svg>', html, re.S)
    assert m, "brand-logo mark not found in web/index.html"
    svg = m.group(0)
    assert BLUE_HEX in svg, "brand mark lost its blue tile (2.5.0.0 regression)"
    # the tile must be the first, full-bleed rect
    assert re.search(r'<svg[^>]*>\s*<rect width="100" height="100" fill="#1ba1e2"/>', svg)


def test_web_header_logo_keeps_bars_and_red():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    svg = re.search(r'<span class="brand-logo".*?</svg>', html, re.S).group(0)
    assert svg.count('fill="#fff"') == 3, "expected three white bars"
    assert svg.count('fill="#e51400"') == 1, "expected one red bar"


def test_startup_icon_draws_blue_tile():
    html = (ROOT / "web" / "startup.html").read_text(encoding="utf-8")
    m = re.search(r'<div class="startup-icon".*?</svg>', html, re.S)
    assert m, "startup icon not found"
    assert BLUE_HEX in m.group(0), "startup icon lost its blue tile"


def test_served_index_logo_matches_source():
    """web/served/index.html is the copy the app ships; it must not lag behind."""
    src = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    served = (ROOT / "web" / "served" / "index.html").read_text(encoding="utf-8")
    mark = re.compile(r'<span class="brand-logo".*?</svg>', re.S)
    a, b = mark.search(src), mark.search(served)
    assert a and b, "brand mark missing in one of the two files"
    assert BLUE_HEX in b.group(0), "served copy still has the old (blue-less) mark"


# --------------------------------------------------------------------------- E
def test_uninstall_delete_only_touches_app_dir():
    s = _iss()
    block = s.split("[UninstallDelete]", 1)[1].split("[Code]", 1)[0]
    assert "{app}" in block
    assert "localappdata" not in block.lower(), "[UninstallDelete] must not reach user profiles"
    assert "Linda-Pro" not in block.replace("{app}", ""), "[UninstallDelete] must not name a profile"


def test_uninstall_keeps_data_by_default():
    s = _iss()
    assert "english.UninstallKeep=" in s
    # keeping is the default button, deleting requires an explicit No
    assert "MB_YESNO or MB_DEFBUTTON1" in s
    assert "= IDNO then" in s


def test_uninstall_still_offers_to_delete():
    """Keeping by default must not remove the ability to clean up."""
    s = _iss()
    fn = s.split("procedure CurUninstallStepChanged", 1)[1]
    assert "DelTree(DataDir" in fn
    assert "models" in fn and "onnx" in fn
