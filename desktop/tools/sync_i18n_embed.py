# -*- coding: utf-8 -*-
"""Пересобирает встроенный словарь window.LINDA_I18N в web/index.html из web/i18n/*.json.
    python tools/sync_i18n_embed.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "web" / "index.html"
lines = P.read_text(encoding="utf-8").split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("window.LINDA_I18N = "))
old = json.loads(lines[i][len("window.LINDA_I18N = "):].rstrip().rstrip(";"))
new = {lang: json.loads((ROOT / "web" / "i18n" / f"{lang}.json").read_text(encoding="utf-8")) for lang in old}
lines[i] = "window.LINDA_I18N = " + json.dumps(new, ensure_ascii=False, sort_keys=True).replace("</", "<\/") + ";"
P.write_text("\n".join(lines), encoding="utf-8")
print("embedded:", {k: len(v) for k, v in new.items()})
