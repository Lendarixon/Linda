# -*- coding: utf-8 -*-
"""Checks internal links of the built static site (./public).
Catches: missing pages, bad #anchors, links to files that don't exist.
Usage: python check_links.py  (exit 0 = OK, exit 1 = problems)"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUB = ROOT / "public"

SKIP_PREFIXES = ("http://", "https://", "mailto:", "data:", "tel:", "javascript:")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []  # (attr, url, line)
        self.cur = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.add(d["id"])
        for a in ("href", "src"):
            if d.get(a):
                self.links.append((a, d[a], self.getpos()[0]))


def main() -> int:
    pages = sorted(PUB.glob("*.html"))
    if not pages:
        print("no pages in public/")
        return 1
    ids = {}
    pagelinks = {}
    assets = set()
    for p in pages:
        c = Collector()
        c.feed(p.read_text(encoding="utf-8"))
        ids[p.name] = c.ids
        pagelinks[p.name] = c.links
    files = {x.name for x in PUB.iterdir()} | {f"assets/{x.name}" for x in (PUB / "assets").iterdir()} if (PUB / "assets").is_dir() else {x.name for x in PUB.iterdir()}
    bad = 0
    for page, links in pagelinks.items():
        for attr, url, line in links:
            if url.startswith(SKIP_PREFIXES) or url.startswith("#") and False:
                pass
            if url.startswith(SKIP_PREFIXES):
                continue
            if url.startswith("#"):
                if url[1:] not in ids[page]:
                    print(f"BROKEN {page}:{line} anchor {url} (no such id)")
                    bad += 1
                continue
            m = re.match(r"^([^#?]+)(#.*)?$", url)
            if m is None:
                continue
            target, frag = m.group(1), (m.group(2) or "")[1:]
            if "/" in target or "\\" in target:
                # external path or subdir: only allow assets/...
                cand = PUB / target
                if not cand.is_file():
                    print(f"BROKEN {page}:{line} file {url} (missing)")
                    bad += 1
                continue
            if target not in files:
                print(f"BROKEN {page}:{line} page {url} (missing)")
                bad += 1
            elif frag and frag not in ids.get(target, set()):
                print(f"BROKEN {page}:{line} anchor {url} (no #{frag} in {target})")
                bad += 1
    print(f"pages: {len(pages)}, links checked: {sum(len(v) for v in pagelinks.values())}")
    print("links OK" if not bad else f"links FAILED ({bad})")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
