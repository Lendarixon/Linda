# -*- coding: utf-8 -*-
"""Checks i18n dictionaries for missing/extra keys and token mismatches.
    python check_i18n.py  (exit 0 = OK, exit 1 = problems)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANGS = ("en", "ru", "pl")
TOKENS = ("__MAIL_LINK__", "__DOI_URL__", "__MAIL__")
ALLOW_EMPTY = {("en", "legal_prevails")}


def main() -> int:
    dicts = {}
    for lang in LANGS:
        p = ROOT / "i18n" / f"{lang}.json"
        dicts[lang] = json.loads(p.read_text(encoding="utf-8"))
    base = set(dicts["en"])
    ok = True
    for lang in ("ru", "pl"):
        keys = set(dicts[lang])
        for k in sorted(base - keys):
            print(f"MISSING {lang}: {k}")
            ok = False
        for k in sorted(keys - base):
            print(f"EXTRA   {lang}: {k}")
            ok = False
    for lang in LANGS:
        for k, v in dicts[lang].items():
            if not isinstance(v, str) or (not v and (lang, k) not in ALLOW_EMPTY):
                print(f"EMPTY   {lang}: {k}")
                ok = False
            for t in TOKENS:
                has_base, has_v = t in dicts["en"].get(k, ""), t in v if isinstance(v, str) else False
                if has_base != has_v:
                    print(f"TOKEN   {lang}:{k} {t} en={has_base} {lang}={has_v}")
                    ok = False
    print(f"keys: en={len(dicts['en'])} ru={len(dicts['ru'])} pl={len(dicts['pl'])}")
    print("i18n OK" if ok else "i18n FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
