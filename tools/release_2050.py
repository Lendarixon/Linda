# -*- coding: utf-8 -*-
"""Сборка выпуска 2.0.5.0 (токенная разметка) и манифеста весов 1.3.4 - всё локально, без публикации.
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
BUILD = DESK / "Linda_build_2050"
PACK = DESK / "Linda_release_1_3_4" / "pack"
OUT = DESK / "Linda_release_1_3_4" / "repo"
PY = sys.executable
VER, STORE_VER, WVER = "2.0.5.0", "2.0.5000.0", "1.3.4"
URL = f"https://github.com/Lendarixon/Linda/releases/download/v{VER}/Linda-Setup.exe"
CHANGED = ["models/linda_speed_131/model.onnx", "models/essay_dhi_131_20261008/tok_head.npz", "models/multi_dhi_131_20261008/tok_head.npz"]

ENTRY = {"version": VER, "date": "2026-10-10",
 "title": {"ru": "Версия 2.5: разметка по токенам — точнее при той же скорости", "en": "Version 2.5: token-level highlighting, more accurate at the same speed",
           "pl": "Wersja 2.5: podświetlanie na poziomie tokenów, dokładniejsze przy tej samej szybkości"},
 "notes": {
  "ru": "• Разметка предложений теперь строится по токенам за тот же проход модели, что и вердикт, а не повторными прогонами по кускам текста. Linda-Pro Lite размечает текст в 3 800 слов примерно за 4–6 с на современном процессоре вместо огромных однородных кусков в 2.0.4.x.\n• Точность разметки на смешанных текстах «человек + ИИ» с известной границей (наш замер, EN/RU/PL): Linda-Pro — верная метка у 90% слов (2.0.4.x: 90% ценой многих повторных прогонов), Linda-Pro Lite — 88% (2.0.4.x: 67%); у человеческих слов ложная метка «ИИ» около 3%.\n• Вердикт и его точность не изменились: модели те же, пороги те же.\n• Если документ в целом «неясно», а ИИ отмечен почти во всём тексте, в блоке «Авторство» пишется «ИИ»; если не отмечено ничего — «неясно», а не «смешанное».\n• Прокрутка текста больше не пропадает после смены набора моделей.\n• Быстрее открываются история и сравнение документов.",
  "en": "• Sentence highlighting is now computed from tokens in the same model pass as the verdict instead of repeated passes over pieces of the text. Linda-Pro Lite highlights a 3,800-word text in about 4-6 s on a modern processor, without the huge uniform blocks of 2.0.4.x.\n• Highlighting accuracy on mixed human + AI texts with a known boundary (our measurement, EN/RU/PL): Linda-Pro labels 90% of words correctly (2.0.4.x: 90% at the cost of many repeated passes), Linda-Pro Lite 88% (2.0.4.x: 67%); about 3% of human words get a false \"AI\" mark.\n• The verdict and its accuracy are unchanged: same models, same thresholds.\n• If the document as a whole is \"unclear\" but AI is marked in almost all of the text, the Authorship box says \"AI\"; if nothing is marked it says \"unclear\" instead of \"mixed\".\n• Text scrolling no longer stops working after the model set is changed.\n• History and document comparison open faster.",
  "pl": "• Podświetlanie zdań liczone jest teraz z tokenów w tym samym przebiegu modelu co werdykt, zamiast wielokrotnych przebiegów po fragmentach tekstu. Linda-Pro Lite podświetla tekst 3800 słów w ok. 4-6 s na nowoczesnym procesorze, bez ogromnych jednolitych bloków z 2.0.4.x.\n• Dokładność podświetlania na tekstach mieszanych człowiek + AI ze znaną granicą (nasz pomiar, EN/RU/PL): Linda-Pro - poprawna etykieta 90% słów (2.0.4.x: 90% kosztem wielu przebiegów), Linda-Pro Lite - 88% (2.0.4.x: 67%); ok. 3% słów ludzkich dostaje fałszywe oznaczenie „AI”.\n• Werdykt i jego dokładność bez zmian: te same modele, te same progi.\n• Gdy dokument jako całość jest „niejasny”, a AI zaznaczono prawie w całym tekście, blok „Autorstwo” pokazuje „AI”; gdy nic nie zaznaczono - „niejasne” zamiast „mieszane”.\n• Przewijanie tekstu nie przestaje działać po zmianie zestawu modeli.\n• Historia i porównanie dokumentów otwierają się szybciej."}}
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
    m["version"], m["released"] = WVER, "2026-10-10"
    m["notes"], m["notes_i18n"] = WNOTES["en"], WNOTES
    setup = (ROOT / "dist" / "Linda-Setup.exe").read_bytes()
    m["installer"].update(version=VER, url=URL, size=len(setup), sha256=hashlib.sha256(setup).hexdigest())
    wentry = {"version": WVER, "date": "2026-10-10", "notes": WNOTES["en"], "notes_ru": WNOTES["ru"], "notes_pl": WNOTES["pl"], "notes_en": WNOTES["en"],
              "notes_i18n": WNOTES, "title_i18n": {"ru": "Модели 1.3.4: потокенная разметка", "en": "Models 1.3.4: per-token highlighting", "pl": "Modele 1.3.4: podświetlanie tokenowe"}}
    cl = [e for e in m.get("changelog", []) if e.get("version") not in (VER, WVER)]
    m["changelog"] = [ENTRY, wentry] + cl
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
