# -*- coding: utf-8 -*-
"""Манифест обновления для 2.0.4.2: берётся живой latest.json с Hugging Face (проверяется его подпись), меняется только установщик
(версия, ссылка, размер, sha256) и в changelog добавляется запись 2.0.4.2; веса (1.3.3) и список файлов не трогаются. Подпись — Ed25519
ключом Linda_desktop/keys/linda_signing.key, затем проверка публичным ключом приложения. Результат — manifest_2042/latest.json(.sig).
    python tools/make_manifest_2042.py"""
import base64
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from linda_desktop import config  # noqa: E402
from linda_desktop.updater import verify_signature  # noqa: E402

KEYFILE = Path(r"C:\Users\ninja\Desktop\Linda_desktop\keys\linda_signing.key")
SETUP = ROOT / "dist" / "Linda-Setup.exe"
URL = "https://github.com/Lendarixon/Linda/releases/download/v2.0.4.2/Linda-Setup.exe"
BASE = "https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/"

raw = urllib.request.urlopen(BASE + "latest.json", timeout=60).read()
sig = urllib.request.urlopen(BASE + "latest.json.sig", timeout=60).read()
verify_signature(raw, sig)  # живой манифест подлинный
m = json.loads(raw)
assert m["installer"]["version"] == "2.0.4.1", m["installer"]["version"]
data = SETUP.read_bytes()
m["installer"].update(version="2.0.4.2", url=URL, size=len(data), sha256=hashlib.sha256(data).hexdigest())
entry = json.loads((ROOT / "CHANGELOG.json").read_text(encoding="utf-8"))[0]
assert entry["version"] == "2.0.4.2"
cl = [e for e in m.get("changelog", []) if e.get("version") != "2.0.4.2"]
pos = 0  # самая новая запись — первой
cl.insert(pos, entry)
m["changelog"] = cl
new = json.dumps(m, indent=1, ensure_ascii=False).encode("utf-8")
key = serialization.load_pem_private_key(KEYFILE.read_bytes(), password=None)
new_sig = base64.b64encode(key.sign(new))
verify_signature(new, new_sig)  # подпись принимается публичным ключом, зашитым в приложение
out = ROOT / "manifest_2042"
out.mkdir(exist_ok=True)
(out / "latest.json").write_bytes(new)
(out / "latest.json.sig").write_bytes(new_sig)
print("signed manifest: installer", m["installer"]["version"], m["installer"]["size"], m["installer"]["sha256"][:16], "| weights", m["version"],
      "| changelog head", [e["version"] for e in cl[:3]], "| pubkey", config.SIGNING_PUBKEY_B64[:8])
