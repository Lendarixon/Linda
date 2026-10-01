# -*- coding: utf-8 -*-
"""Update manifest tools (run on the owner's machine).

    python tools/make_manifest.py keygen                      # once: creates keys/linda_signing.key (PRIVATE, back it up) and prints the public key
    python tools/make_manifest.py build SRC_DIR --version 1.1.0 [--min-app 1.1.0] [--notes "..."] [--installer-url URL --installer-file Linda-Setup.exe --installer-version 1.1.0] [--out DIR]
        SRC_DIR is the package folder that holds models/ and calibration/; writes latest.json and latest.json.sig into --out (default: SRC_DIR)

The private key is read from keys/linda_signing.key (or LINDA_SIGNING_KEY_FILE) and is never printed."""
import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
KEYFILE = Path(os.environ.get("LINDA_SIGNING_KEY_FILE", ROOT / "keys" / "linda_signing.key"))
MANAGED = ("models", "calibration")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while c := f.read(1 << 20):
            h.update(c)
    return h.hexdigest()


def pub_b64(priv: Ed25519PrivateKey) -> str:
    return base64.b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def load_key() -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(KEYFILE.read_bytes(), password=None)


def keygen() -> None:
    if KEYFILE.exists():
        sys.exit(f"{KEYFILE} already exists; refusing to overwrite")
    KEYFILE.parent.mkdir(parents=True, exist_ok=True)
    k = Ed25519PrivateKey.generate()
    KEYFILE.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    print("private key written to", KEYFILE, "(keep it secret, make a backup)")
    print("public key (put into linda_desktop/config.py SIGNING_PUBKEY_B64):", pub_b64(k))


def build(a) -> None:
    src = Path(a.src)
    files = []
    for top in MANAGED:
        for p in sorted((src / top).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".part"):
                files.append({"path": p.relative_to(src).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)})
    m = {"schema": 1, "version": a.version, "released": date.today().isoformat(), "min_app": a.min_app, "notes": a.notes, "files": files}
    if a.installer_file:
        f = Path(a.installer_file)
        m["installer"] = {"version": a.installer_version or a.version, "url": a.installer_url, "size": f.stat().st_size, "sha256": sha256(f)}
    raw = json.dumps(m, indent=1, ensure_ascii=False).encode("utf-8")
    out = Path(a.out or src)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_bytes(raw)
    (out / "latest.json.sig").write_bytes(base64.b64encode(load_key().sign(raw)))
    print(f"latest.json: version {a.version}, {len(files)} files, {sum(f['size'] for f in files) / 1e9:.2f} GB; signed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("keygen")
    b = sp.add_parser("build")
    b.add_argument("src")
    b.add_argument("--version", required=True)
    b.add_argument("--min-app", default="1.1.0")
    b.add_argument("--notes", default="")
    b.add_argument("--installer-url")
    b.add_argument("--installer-file")
    b.add_argument("--installer-version")
    b.add_argument("--out")
    a = ap.parse_args()
    keygen() if a.cmd == "keygen" else build(a)
