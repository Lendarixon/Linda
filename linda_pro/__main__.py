# -*- coding: utf-8 -*-
"""python -m linda_pro file.txt [--lite | --tier {auto,full,lite}] [--mode precise] [--windows] [--json]"""
import argparse
import json
import sys
from pathlib import Path

from .loader import TIERS, load_detector


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="linda_pro", description="Linda-Pro: AI-text detector (English, Polish, Russian; language is detected automatically)")
    ap.add_argument("files", nargs="+", help="text files (UTF-8)")
    ap.add_argument("--mode", choices=["sensitive", "precise"], default="sensitive")
    tier = ap.add_mutually_exclusive_group()
    tier.add_argument("--tier", choices=TIERS, default="auto",
                      help="which installed weights to use: auto (default; full if installed, otherwise lite), full (Linda-Pro) or lite (Linda-Pro Lite)")
    tier.add_argument("--lite", dest="tier", action="store_const", const="lite", help="shortcut for --tier lite")
    ap.add_argument("--device", default=None, help="cuda or cpu (default: auto)")
    ap.add_argument("--windows", action="store_true", help="print per-window scores")
    ap.add_argument("--json", action="store_true", help="print raw JSON")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    missing = [f for f in a.files if not Path(f).is_file()]
    if missing:
        ap.error("file not found: " + ", ".join(missing))
    try:
        det = load_detector(a.mode, device=a.device, tier=a.tier)
    except FileNotFoundError as e:
        print(f"linda_pro: error: {e}", file=sys.stderr)
        return 2
    tier_name = "lite" if getattr(det, "tier_pref", None) == "speed" else "full"
    texts = [Path(f).read_text(encoding="utf-8", errors="replace") for f in a.files]
    res = [{k: v for k, v in r.items() if not k.startswith("_")} for r in det.detect(texts)]  # drop internal fields (Lite token scores)
    if a.json:
        print(json.dumps(res, ensure_ascii=True, indent=2))
        return 0
    for f, r in zip(a.files, res):
        lang = f", language={r['language']}, tier={tier_name}" if r.get("language") else ""
        print(f"{f}: {r['verdict'].upper()}  (essay={r['essay']:.2f}, ensemble_z={r['ens_z']:.2f}, ai_share={100 * r['ai_share']:.0f}%, windows={r['n_windows']}, mode={r['mode']}{lang})")
        if a.windows:
            for w in r["windows"]:
                print(f"    words {w['first_word']}-{w['last_word']}: essay={w['essay']:.2f} {'AI-like' if w['flag'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
