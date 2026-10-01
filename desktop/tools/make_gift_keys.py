# -*- coding: utf-8 -*-
"""Gift / complimentary licence keys, signed with the owner's licence key (Ed25519) and verified offline by the app.
Key format:  LINDA-<P|T>-<4 digits>-<base32 signature>   P = Personal, T = Team.  Revoke by adding the id (e.g. P-0007) to keys/revoked.txt and re-signing the update manifest.

    python tools/make_gift_keys.py --personal 100 --team 10      # generates new keys (ids continue from the last run), writes CSV files into keys/
    python tools/make_gift_keys.py --pubkey                      # prints the public key to put into linda_desktop/config.py (LICENSE_PUBKEY_B64)"""
import argparse
import base64
import csv
import json
import sys
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / "keys"
KEYFILE = KEYS / "linda_license.key"
STATE = KEYS / "gift_issued.json"


def load_or_create() -> Ed25519PrivateKey:
    KEYS.mkdir(exist_ok=True)
    if KEYFILE.exists():
        return serialization.load_pem_private_key(KEYFILE.read_bytes(), password=None)
    k = Ed25519PrivateKey.generate()
    KEYFILE.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return k


def pub_b64(k: Ed25519PrivateKey) -> str:
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def make_key(priv: Ed25519PrivateKey, code: str, num: int) -> str:
    sig = priv.sign(f"linda-gift|{code}|{num:04d}".encode())
    b32 = base64.b32encode(sig).decode().rstrip("=")
    groups = "-".join(b32[i:i + 8] for i in range(0, len(b32), 8))
    return f"LINDA-{code}-{num:04d}-{groups}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--personal", type=int, default=0)
    ap.add_argument("--team", type=int, default=0)
    ap.add_argument("--pubkey", action="store_true")
    a = ap.parse_args()
    priv = load_or_create()
    if a.pubkey or not (a.personal or a.team):
        print("public key:", pub_b64(priv))
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {"P": 0, "T": 0}
    rows = []
    for code, n, name in (("P", a.personal, "Personal"), ("T", a.team, "Team")):
        for _ in range(n):
            state[code] += 1
            rows.append({"tier": name, "id": f"{code}-{state[code]:04d}", "key": make_key(priv, code, state[code]), "given_to": "", "note": ""})
    STATE.write_text(json.dumps(state))
    out = KEYS / f"gift_keys_{date.today():%Y%m%d}_{a.personal}P_{a.team}T.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "id", "key", "given_to", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} keys written to {out}")


if __name__ == "__main__":
    sys.exit(main())
