# -*- coding: utf-8 -*-
"""Builds modal_demo/demo.html (the page of the hosted Modal demo) from the pristine page: current model names, wordmark logo, language note, Metro skin.
    python tools/make_modal_demo.py     then:  cd modal_demo && modal deploy modal_app.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODAL = Path(r"C:\Users\ninja\Desktop\modal_demo")
t = (MODAL / "demo_pre_metro.html").read_text(encoding="utf-8")
B64 = (ROOT / "assets" / "wordmark_b64.txt").read_text(encoding="ascii").strip()
METRO = (ROOT / "tools" / "metro_override.css").read_text(encoding="utf-8")


def sub(a: str, b: str, count: int = 0) -> None:
    global t
    assert a in t, a[:60]
    t = t.replace(a, b) if count == 0 else t.replace(a, b, count)


sub("Linda-Essay v3", "Linda-Essay-D")
sub("Linda-Multi v2", "Linda-Multi-D")
sub("Stylo7e (Stylometry)", "Stylo-D (Stylometry)")
sub("Stylo7e", "Stylo-D")
sub("Linda-Pro 1.0 \u2014 AI Verification Report", "Linda-Pro 1.1 \u2014 AI Verification Report")
sub('    <div class="brand-icon">\u26a1</div>\n    Linda-Pro 1.0\n    <span class="badge-commercial">Commercial Demo</span>',
    '    <img class="brand-logo" alt="Linda-Pro" height="36" src="data:image/png;base64,' + B64 + '"> <span style="font-weight:600;color:var(--text-muted);font-size:.85rem">1.1</span>\n    <span class="badge-commercial">Demo</span>')
sub("<b>Limits.</b> Linda-Pro 1.1. English only;", "<b>Limits.</b> Linda-Pro 1.1. English is the main language; Russian and Polish work at moderate quality (thresholds are tuned for English, results are indicative);")
sub("</head>", '<style id="metro">\n' + METRO + "</style></head>", 1)
(MODAL / "demo.html").write_text(t, encoding="utf-8", newline="\n")
print("modal demo page written:", len(t), "bytes")
