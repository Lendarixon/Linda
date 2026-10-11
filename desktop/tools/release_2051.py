# -*- coding: utf-8 -*-
"""Сборка выпуска 2.0.5.1 (Lite: токены из окон вердикта) и манифеста весов 1.3.4 - всё локально, без публикации.
    python tools/release_2050.py bump        # версия 2.0.4.2 -> 2.0.5.0, CHANGELOG
    python tools/release_2050.py build       # exe (app/store) поверх 2.0.4.1, установщик, MSIX 2.0.5000.0
    python tools/release_2050.py manifest    # latest.json(.sig): установщик 2.0.5.0 + изменённые файлы моделей 1.3.4
Публикация - tools/publish_2050.py."""
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = Path(r"C:\Users\ninja\Desktop")
SCR = Path(r"C:\Users\ninja\AppData\Local\Temp\claude\C--Users-ninja-Desktop---------\78b86c83-004f-42e2-abed-a292aa38d513\scratchpad")
BASE_TREE = SCR / "msix41"                      # распакованный MSIX 2.0.4001.0 (app/, AppxManifest.xml, Assets/)
BUILD = DESK / "Linda_build_2051"
PACK = DESK / "Linda_release_1_3_4" / "pack"
OUT = DESK / "Linda_release_1_3_4" / "repo"
PY = sys.executable
VER, STORE_VER, WVER = "2.0.5.1", "2.0.5001.0", "1.3.4"
URL = f"https://github.com/Lendarixon/Linda/releases/download/v{VER}/Linda-Setup.exe"
CHANGED = []  # модели не менялись (1.3.4)

ENTRY = {"version": VER, "date": "2026-10-10",
 "title": {"ru": "Linda-Pro Lite: разметка вдвое быстрее", "en": "Linda-Pro Lite: highlighting twice as fast", "pl": "Linda-Pro Lite: podświetlanie dwa razy szybsze"},
 "notes": {
  "ru": "• Linda-Pro Lite берёт оценки токенов для разметки из тех же проходов модели, что считают вердикт, и дочитывает только остальной текст: разметка примерно в 2 раза быстрее (наш замер: 2,1 → 1,0 с на 1 000 слов на 4 потоках), точность разметки не ниже прежней (на смешанных текстах 85% верных меток слов, ложная метка «ИИ» у 3% человеческих слов).\n• Вердикты не изменились.",
  "en": "• Linda-Pro Lite takes the token scores for highlighting from the same model passes that compute the verdict and reads only the rest of the text: highlighting is about 2x faster (our measurement: 2.1 -> 1.0 s per 1,000 words on 4 threads) with no loss of highlighting accuracy (85% of words labelled correctly on mixed texts, false AI mark on 3% of human words).\n• Verdicts are unchanged.",
  "pl": "• Linda-Pro Lite bierze oceny tokenów do podświetlania z tych samych przebiegów modelu, które liczą werdykt, i doczytuje tylko resztę tekstu: podświetlanie ok. 2 razy szybsze (nasz pomiar: 2,1 -> 1,0 s na 1000 słów przy 4 wątkach) bez utraty dokładności (85% poprawnych etykiet słów na tekstach mieszanych, fałszywe AI u 3% słów ludzkich).\n• Werdykty bez zmian."}}
WNOTES = {"en": "• Models 1.3.4: Linda-Pro Lite gets a per-token output and Linda-Pro small per-token heads (about 10 KB) for fast sentence highlighting. Verdicts are unchanged.",
          "ru": "• Модели 1.3.4: у Linda-Pro Lite появился потокенный выход, у Linda-Pro — маленькие потокенные слои (около 10 КБ) для быстрой разметки предложений. Вердикты не изменились.",
          "pl": "• Modele 1.3.4: Linda-Pro Lite dostaje wyjście na poziomie tokenów, a Linda-Pro małe warstwy tokenowe (ok. 10 KB) do szybkiego podświetlania zdań. Werdykty bez zmian."}


def sh(cmd, **kw):
    print(">", cmd if isinstance(cmd, str) else " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)


def bump():
    p = ROOT / "linda_desktop/__init__.py"
    s = p.read_text(encoding="utf-8")
    if VER not in s:
        p.write_text(re.sub(r'__version__ = "[0-9.]+"', f'__version__ = "{VER}"', s), encoding="utf-8")
    p = ROOT / "installer/linda.iss"
    p.write_text(re.sub(r'#define AppVersion "[0-9.]+"', f'#define AppVersion "{VER}"', p.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    cl = json.loads((ROOT / "CHANGELOG.json").read_text(encoding="utf-8"))
    cl = [e for e in cl if e.get("version") != VER]
    cl.insert(0, ENTRY)
    (ROOT / "CHANGELOG.json").write_text(json.dumps(cl, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(ROOT / "CHANGELOG.json", ROOT / "linda_desktop/data/CHANGELOG.json")
    print("bumped", VER)


def tree(dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(BASE_TREE / "app", dst)
    for p in sorted(dst.rglob("*"), key=lambda x: -len(str(x))):  # MSIX хранит пробелы в именах как %20
        if "%" in p.name:
            p.rename(p.with_name(urllib.request.unquote(p.name)))
    shutil.copy2(ROOT / "web/index.html", dst / "_internal/web/index.html")
    shutil.copy2(ROOT / "web/cabinet.html", dst / "_internal/web/cabinet.html")
    shutil.copy2(ROOT / "CHANGELOG.json", dst / "_internal/linda_desktop/data/CHANGELOG.json")


def build():
    base_exe = BASE_TREE / "app" / "Linda-Pro.exe"
    app, store = BUILD / "app", BUILD / "store"
    tree(app)
    sh([PY, str(ROOT / "tools/repack_exe.py"), str(base_exe), str(app / "Linda-Pro.exe"), "--entry", "run_app"])
    if store.exists():
        shutil.rmtree(store)
    store.mkdir(parents=True)
    tree(store / "app")
    sh([PY, str(ROOT / "tools/repack_exe.py"), str(base_exe), str(store / "app" / "Linda-Pro.exe")])
    shutil.copytree(BASE_TREE / "Assets", store / "Assets")
    m = (BASE_TREE / "AppxManifest.xml").read_text(encoding="utf-8")
    (store / "AppxManifest.xml").write_text(re.sub(r'Version="2\.0\.\d+\.0"', f'Version="{STORE_VER}"', m, count=1), encoding="utf-8")
    dist = ROOT / "dist"
    if (dist / "Linda-Pro").exists():
        shutil.rmtree(dist / "Linda-Pro")
    shutil.copytree(app, dist / "Linda-Pro")
    iscc = r"C:\Users\ninja\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe"
    sh([iscc, "linda.iss"], cwd=ROOT / "installer", stdout=subprocess.DEVNULL)
    msix = DESK / "Linda_Store_upload" / f"Linda-Pro_{STORE_VER}_x64.msix"
    makeappx = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"
    sh([makeappx, "pack", "/d", str(store), "/p", str(msix), "/o"], stdout=subprocess.DEVNULL)
    print("installer", (dist / "Linda-Setup.exe").stat().st_size, "msix", msix, msix.stat().st_size)


def manifest():
    sys.path.insert(0, str(ROOT))
    from cryptography.hazmat.primitives import serialization
    from linda_desktop.updater import verify_signature
    base = "https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/"
    raw = urllib.request.urlopen(base + "latest.json", timeout=60).read()
    verify_signature(raw, urllib.request.urlopen(base + "latest.json.sig", timeout=60).read())
    m = json.loads(raw)
    files = {f["path"]: f for f in m["files"]}
    for rel in CHANGED:
        p = PACK / rel
        data = p.read_bytes()
        old = files.get(rel)
        files[rel] = {"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                      "set": old["set"] if old else ("lite" if "speed" in rel else "pro")}
    m["files"] = [files[k] for k in sorted(files)] if False else list(files.values())
    if CHANGED:
        m["version"], m["released"] = WVER, "2026-10-10"
        m["notes"], m["notes_i18n"] = WNOTES["en"], WNOTES
    setup = (ROOT / "dist" / "Linda-Setup.exe").read_bytes()
    m["installer"].update(version=VER, url=URL, size=len(setup), sha256=hashlib.sha256(setup).hexdigest())
    wentry = {"version": WVER, "date": "2026-10-10", "notes": WNOTES["en"], "notes_ru": WNOTES["ru"], "notes_pl": WNOTES["pl"], "notes_en": WNOTES["en"],
              "notes_i18n": WNOTES, "title_i18n": {"ru": "Модели 1.3.4: потокенная разметка", "en": "Models 1.3.4: per-token highlighting", "pl": "Modele 1.3.4: podświetlanie tokenowe"}}
    cl = [e for e in m.get("changelog", []) if e.get("version") != VER and (CHANGED or True)]
    m["changelog"] = [ENTRY] + ([wentry] + [e for e in cl if e.get("version") != WVER] if CHANGED else cl)
    new = json.dumps(m, indent=1, ensure_ascii=False).encode("utf-8")
    key = serialization.load_pem_private_key((DESK / "Linda_desktop/keys/linda_signing.key").read_bytes(), password=None)
    sig = base64.b64encode(key.sign(new))
    verify_signature(new, sig)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_bytes(new)
    (OUT / "latest.json.sig").write_bytes(sig)
    print("manifest signed: weights", WVER, "installer", VER, "files", len(m["files"]), "changed", CHANGED)


if __name__ == "__main__":
    {"bump": bump, "build": build, "manifest": manifest}[sys.argv[1]]()
