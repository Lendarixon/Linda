# -*- coding: utf-8 -*-
"""python -m linda_pro файл.txt [--mode precise] [--windows] [--json]"""
import argparse
import json
import sys
from pathlib import Path

from .core import LindaPro


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="linda_pro", description="Linda-Pro: AI-text detector (English)")
    ap.add_argument("files", nargs="+", help="text files (UTF-8)")
    ap.add_argument("--mode", choices=["sensitive", "precise"], default="sensitive")
    ap.add_argument("--windows", action="store_true", help="print per-window scores")
    ap.add_argument("--json", action="store_true", help="print raw JSON")
    a = ap.parse_args(argv)
    det = LindaPro(mode=a.mode)
    texts = [Path(f).read_text(encoding="utf-8", errors="replace") for f in a.files]
    res = det.detect(texts)
    if a.json:
        print(json.dumps(res, ensure_ascii=True, indent=2))
        return 0
    for f, r in zip(a.files, res):
        print(f"{f}: {r['verdict'].upper()}  (essay={r['essay']:.2f}, ensemble_z={r['ens_z']:.2f}, ai_share={100 * r['ai_share']:.0f}%, windows={r['n_windows']}, mode={r['mode']})")
        if a.windows:
            for w in r["windows"]:
                print(f"    words {w['first_word']}-{w['last_word']}: essay={w['essay']:.2f} {'AI-like' if w['flag'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
