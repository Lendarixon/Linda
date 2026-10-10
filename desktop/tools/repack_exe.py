"""Пересборка Linda-Pro.exe из готового exe 2.0.4.x: подменяются только модули linda_desktop/linda_pro в PYZ (и при желании
скрипт запуска), всё остальное (загрузчик, ресурсы, библиотеки, остальные модули) копируется побайтово.

Зачем: исходник релизного дерева 2.0.4.x утерян (Desktop\\Linda_release_1_3 удалён 09.10), восстановленные модули совпадают с
байткодом 2.0.4.1 (`_recover/bccheck.py`), а полная пересборка PyInstaller без прежнего .spec рискует потерять файлы.

    python tools/repack_exe.py BASE.exe OUT.exe [--entry run_app|run_store]
"""
from __future__ import annotations

import argparse
import marshal
import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COOKIE = b"MEI\014\013\012\013\016"
COOKIE_FMT, TOC_FMT = "!8sIIII64s", "!IIIIBc"
PYZ_MODULE, PYZ_PKG = 0, 1
EXTRA_MODULES: set[str] = set()  # новые модули приложения: вписать сюда имя, чтобы он попал в exe


def our_modules() -> dict[str, tuple[int, object]]:
    """{имя модуля: (тип PYZ, code object)} для linda_desktop и linda_pro из исходников этого дерева."""
    out = {}
    for pkg in ("linda_desktop", "linda_pro"):
        for p in sorted((ROOT / pkg).rglob("*.py")):
            rel = p.relative_to(ROOT)
            parts = list(rel.with_suffix("").parts)
            is_pkg = parts[-1] == "__init__"
            name = ".".join(parts[:-1] if is_pkg else parts)
            code = compile(p.read_text(encoding="utf-8"), str(rel), "exec", dont_inherit=True, optimize=0)
            out[name] = (PYZ_PKG if is_pkg else PYZ_MODULE, code)
    return out


def rebuild_pyz(old: bytes) -> tuple[bytes, list[str], list[str]]:
    assert old[:4] == b"PYZ\0", "not a PYZ archive"
    header_magic = old[4:8]  # магия байткода Python (4 байта)
    (toc_off,) = struct.unpack("!i", old[8:12])
    toc = marshal.loads(old[toc_off:])
    toc = list(toc.items()) if isinstance(toc, dict) else list(toc)
    ours = our_modules()
    known = {n for n, _ in toc}
    buf = bytearray(b"\0" * 17)
    new_toc, replaced = [], []
    for name, (typ, off, ln) in toc:
        if name in ours:
            t, code = ours[name]
            data = zlib.compress(marshal.dumps(code), 6)
            new_toc.append((name, (t, len(buf), len(data))))
            buf += data
            replaced.append(name)
        else:
            new_toc.append((name, (typ, len(buf), ln)))
            buf += old[off: off + ln]
    # модули, которых не было в базовой сборке (linda_pro.loader — только для CLI), в exe не добавляются
    added = [n for n in ours if n not in known and n in EXTRA_MODULES]
    for name in added:
        t, code = ours[name]
        data = zlib.compress(marshal.dumps(code), 6)
        new_toc.append((name, (t, len(buf), len(data))))
        buf += data
    toc_offset = len(buf)
    buf += marshal.dumps(new_toc)
    buf[0:4] = b"PYZ\0"
    buf[4:8] = header_magic
    buf[8:12] = struct.pack("!i", toc_offset)
    return bytes(buf), replaced, added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--entry", choices=("run_app", "run_store"), help="заменить скрипт запуска (run_app.py или run_store.py в корне)")
    a = ap.parse_args()
    raw = Path(a.base).read_bytes()
    ck = raw.rfind(COOKIE)
    magic, arch_len, toc_off, toc_len, pyvers, pylib = struct.unpack(COOKIE_FMT, raw[ck: ck + struct.calcsize(COOKIE_FMT)])
    start = ck + struct.calcsize(COOKIE_FMT) - arch_len
    tail = raw[ck + struct.calcsize(COOKIE_FMT):]  # что-то после cookie (подпись и т.п.) — переносим как есть
    toc_raw = raw[start + toc_off: start + toc_off + toc_len]
    entries, pos = [], 0
    while pos < len(toc_raw):
        elen, eoff, dlen, ulen, cflag, tc = struct.unpack(TOC_FMT, toc_raw[pos: pos + struct.calcsize(TOC_FMT)])
        name = toc_raw[pos + struct.calcsize(TOC_FMT): pos + elen].rstrip(b"\0").decode("utf-8")
        entries.append([name, eoff, dlen, ulen, cflag, tc.decode()])
        pos += elen
    entry_names = {e[0] for e in entries if e[5] == "s"}
    body = bytearray()
    new_entries = []
    for name, eoff, dlen, ulen, cflag, tc in entries:
        data = raw[start + eoff: start + eoff + dlen]
        if tc == "z" and name.endswith(".pyz"):
            data, replaced, added = rebuild_pyz(data)
            ulen = len(data)
            print(f"PYZ: заменено {len(replaced)} модулей, добавлено {len(added)} {added}")
        elif tc == "s" and a.entry and name in ("run_app", "run_store"):
            src = ROOT / f"{a.entry}.py"
            code = compile(src.read_text(encoding="utf-8"), f"{a.entry}.py", "exec")
            plain = marshal.dumps(code)
            data, ulen, cflag, name = zlib.compress(plain, 9), len(plain), 1, a.entry
            print(f"скрипт запуска: {a.entry}")
        new_entries.append((name, len(body), len(data), ulen, cflag, tc))
        body += data
    toc_bytes = bytearray()
    for name, off, dlen, ulen, cflag, tc in new_entries:
        nb = name.encode("utf-8") + b"\0"
        nb += b"\0" * ((-(len(nb) + struct.calcsize(TOC_FMT))) % 16)
        toc_bytes += struct.pack(TOC_FMT, struct.calcsize(TOC_FMT) + len(nb), off, dlen, ulen, cflag, tc.encode()) + nb
    new_toc_off = len(body)
    arch = bytes(body) + bytes(toc_bytes)
    cookie = struct.pack(COOKIE_FMT, COOKIE, len(arch) + struct.calcsize(COOKIE_FMT), new_toc_off, len(toc_bytes), pyvers, pylib)
    Path(a.out).write_bytes(raw[:start] + arch + cookie + tail)
    print(f"готово: {a.out} ({len(raw[:start]) + len(arch) + len(cookie) + len(tail):,} байт), старый скрипт запуска: {sorted(entry_names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
