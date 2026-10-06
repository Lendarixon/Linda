# -*- coding: utf-8 -*-
"""Манифест обновления 1.3 (stable): как make_manifest.py build + поля живого манифеста (channel, installer.app_id, notes_i18n), затем подпись.
    python tools/make_manifest_13.py PACK_DIR OUT_DIR [--installer-file F --installer-url URL]
Версия весов 1.3.0 (в живом манифесте 1.1.0), min_app = версия приложения: старые клиенты сначала обновят приложение."""
import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_manifest as mm  # noqa: E402

ROOT = mm.ROOT
APP_ID = "B6D1E7F4-5E1C-4B8E-9D2A-4C8F0A11D0A1"  # AppId установщика (installer/linda.iss), тот же, что у выпуска 2.0.2.20

ap = argparse.ArgumentParser()
ap.add_argument("pack")
ap.add_argument("out")
ap.add_argument("--installer-file")
ap.add_argument("--installer-url")
a = ap.parse_args()
log = json.loads((ROOT / "CHANGELOG.json").read_text(encoding="utf-8"))
cur = log[0]
version_app = cur["version"]
ns = argparse.Namespace(src=a.pack, version="1.3.0", min_app=version_app, notes=cur["notes"]["en"], notes_ru=cur["notes"]["ru"], notes_pl=cur["notes"]["pl"], notes_en=cur["notes"]["en"],
                        title_ru=cur["title"]["ru"], title_pl=cur["title"]["pl"], title_en=cur["title"]["en"], changelog_json="", installer_url=a.installer_url,
                        installer_file=a.installer_file, installer_version=version_app, out=a.out)
mm.build(ns)
out = Path(a.out)
m = json.loads((out / "latest.json").read_text(encoding="utf-8"))
m["changelog"] = log[:10]  # как в живом манифесте: записи CHANGELOG.json как есть
if m.get("installer"):
    m["installer"]["app_id"] = APP_ID
m["channel"] = "stable"
m["notes_i18n"] = cur["notes"]
raw = json.dumps(m, indent=1, ensure_ascii=False).encode("utf-8")
(out / "latest.json").write_bytes(raw)
(out / "latest.json.sig").write_bytes(base64.b64encode(mm.load_key().sign(raw)))
print("manifest 1.3.0 signed:", len(m["files"]), "files", sum(f["size"] for f in m["files"]) / 1e9, "GB; installer:", bool(m.get("installer")))
