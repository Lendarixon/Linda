# -*- coding: utf-8 -*-
"""Тесты «на дурака»: кейсы сгенерированы Gemini (logs/emode/fool_cases.json), исполняются по API запущенного приложения.
Критерий: ни одного 500 / зависания / трейсбека с путями в ответе, понятная ошибка вместо падения, сервер жив после каждого кейса.
    python tools/fool_tests.py http://127.0.0.1:PORT/ [--skip-big]"""
import io
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

base = sys.argv[1].rstrip("/") + "/"
SKIP_BIG = "--skip-big" in sys.argv
tok = re.search(r"""x-linda-token['"]?\s*[,:]\s*['"]([^'"]+)['"]""", urllib.request.urlopen(base).read().decode()).group(1)
results = []


def call(path, body=None, method=None, headers=None, raw=None, ctype="application/json", timeout=180, token=True):
    h = {"Content-Type": ctype} if (body is not None or raw is not None) else {}
    if token:
        h["x-linda-token"] = tok
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path.lstrip("/"), data=data, method=method or ("POST" if data is not None else "GET"), headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        txt, code = e.read(), e.code
    except Exception as e:  # noqa: BLE001
        return -1, {"detail": f"{type(e).__name__}: {e}"}, time.time() - t0
    try:
        j = json.loads(txt)
    except Exception:  # noqa: BLE001
        j = {"raw": txt[:200].decode("utf-8", "replace")}
    return code, j, time.time() - t0


def alive():
    return call("api/status", timeout=20)[0] == 200


def record(cid, what, ok, note):
    results.append((cid, what, ok, note))
    print(("PASS " if ok else "FAIL ") + cid + " " + what[:50] + " | " + str(note)[:110], flush=True)


def clean_error(j):
    d = json.dumps(j, ensure_ascii=False)
    return not re.search(r"Traceback|File \"|C:\\\\Users|C:/Users|\.py\", line", d)


def gen(spec):
    spec = spec if isinstance(spec, str) else str(spec)
    m = re.fullmatch(r"(.+?)\*(\d+)", spec, re.S)
    if m:
        unit = m.group(1)
        unit = {"word": "word "}.get(unit, unit)
        unit = unit.replace("\\n", "\n")
        return unit * int(m.group(2))
    return spec.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\\x00", "\x00").replace("\\x07", "\x07").replace("\\x08", "\x08").replace("\\x1b", "\x1b").replace("\\u200B", "\u200b").replace("\\u200C", "\u200c").replace("\\u200D", "\u200d").replace("\\uFEFF", "\ufeff")


# ---------- 1. текстовые кейсы Gemini ----------
cases = json.loads((Path(__file__).resolve().parents[1] / "tools" / "fool_cases.json").read_text(encoding="utf-8"))
for c in cases[:35]:
    cid = "T%02d" % int(c["id"])
    text = gen(c.get("input", ""))
    if SKIP_BIG and len(text) > 1_000_000:
        record(cid, c["do"], True, "skipped (big)")
        continue
    code, j, dt = call("api/detect", {"text": text, "mode": "sensitive"}, timeout=240)
    ok = code in (200, 400, 413) and clean_error(j) and dt < 200
    if code == 200:
        ok = ok and j.get("result", {}).get("verdict") in ("ai", "human", "uncertain")
    note = "HTTP %s %.1fs %s" % (code, dt, (j.get("detail") or j.get("result", {}).get("verdict") or j)) if code != -1 else j
    record(cid, c["do"], ok and alive(), note)

# ---------- 2. файлы ----------
def zip_with(entries):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in entries:
            z.writestr(n, d)
    return b.getvalue()


def multipart(name, data):
    bd = "----fool%d" % int(time.time() * 1000)
    body = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode("utf-8") + data + f"\r\n--{bd}--\r\n".encode()
    return body, "multipart/form-data; boundary=" + bd


good_docx = zip_with([("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>"), ("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>" + "Обычный текст документа. " * 60 + "</w:t></w:r></w:p></w:body></w:document>")])
try:
    import docx as _docx
    _b = io.BytesIO(); _d = _docx.Document(); _d.add_paragraph("Обычный текст документа для проверки. " * 30); _d.save(_b); good_docx = _b.getvalue()
except Exception:  # noqa: BLE001
    pass
FILES = {
    "F01 .exe renamed .txt": ("sample.txt", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + bytes(range(256)) * 40),
    "F02 empty file": ("empty.txt", b""),
    "F03 corrupted docx": ("broken_header.docx", b"PK\x03\x04" + b"\x00" * 30 + b"garbage"),
    "F04 corrupted pdf": ("malformed.pdf", b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n" + b"junk" * 50),
    "F05 encrypted-like pdf": ("protected.pdf", b"%PDF-1.6\n1 0 obj<</Filter/Standard/V 4/R 4/O(x)/U(y)>>endobj\ntrailer<</Encrypt 1 0 R>>\n%%EOF"),
    "F06a 21 MB txt": ("big21.txt", (b"word " * (21 * 1024 * 1024 // 5))),
    "F06b 25 MB txt": ("big25.txt", (b"word " * (25 * 1024 * 1024 // 5))),
    "F07 cyrillic name with spaces": ("отчет по проверке текста.docx", good_docx),
    "F08 300-char name": ("a" * 296 + ".txt", ("Нормальный текст. " * 40).encode("utf-8")),
    "F09 zip bomb docx": ("zipbomb.docx", zip_with([("[Content_Types].xml", "<Types/>"), ("word/document.xml", "A" * 300_000_000)])),
    "F10 jpg": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 2000),
    "F11 txt in cp1251": ("cp1251.txt", ("Текст в старой кодировке Windows. " * 40).encode("cp1251")),
    "F12 txt with BOM utf-16": ("utf16.txt", "\ufeff" + ("Текст в utf-16. " * 40)),
}
for name, (fname, data) in FILES.items():
    if SKIP_BIG and len(data) > 5_000_000:
        record(name.split()[0], name, True, "skipped (big)")
        continue
    if isinstance(data, str):
        data = data.encode("utf-16")
    body, ct = multipart(fname, data)
    code, j, dt = call("api/upload", raw=body, ctype=ct, timeout=120)
    ok = code in (200, 400, 413, 415, 422) and clean_error(j) and dt < 100 and alive()
    record(name.split()[0], name, ok, "HTTP %s %.1fs %s" % (code, dt, (j.get("detail") or ("%s words" % j.get("words")) or j)))

# ---------- 3. API ----------
tests = [
    ("A01 detect {}", lambda: call("api/detect", {}), (400, 422)),
    ("A02 text as number", lambda: call("api/detect", {"text": 123456}), (200, 400, 422)),
    ("A03 text list", lambda: call("api/detect", {"text": ["a", "b"]}), (400, 422)),
    ("A04 bad mode", lambda: call("api/detect", {"text": "word " * 50, "mode": "xyz"}), (400,)),
    ("A05 bad models", lambda: call("api/detect", {"text": "word " * 50, "models": ["../../etc"]}), (400,)),
    ("A06 wrong token", lambda: call("api/status", headers={"x-linda-token": "wrong"}, token=False), (401, 403)),
    ("A07 no token", lambda: call("api/status", token=False), (401, 403)),
    ("A08 bad job id", lambda: call("api/progress/not%20valid!!"), (400, 404, 422)),
    ("A09 unknown job id", lambda: call("api/progress/abc123"), (200,)),
    ("A10 open_path traversal", lambda: call("api/open_path", {"path": "..\\..\\Windows\\win.ini"}), (403,)),
    ("A11 open_path abs", lambda: call("api/open_path", {"path": "C:\\Windows\\win.ini"}), (403,)),
    ("A12 not json body", lambda: call("api/detect", raw=b"not json", ctype="application/json"), (400, 422)),
    ("A13 settings garbage", lambda: call("api/settings", {"theme": "<script>", "font_scale": "999", "language": "xx", "ui_mode": 5}), (200,)),
    ("A14 history bad id", lambda: call("api/history/abc"), (400, 404, 422)),
    ("A15 unknown route", lambda: call("api/nope"), (404,)),
]
if not SKIP_BIG:
    tests.append(("A16 100 MB body", lambda: call("api/detect", raw=b'{"text": "' + b"a" * (100 * 1024 * 1024) + b'"}', timeout=240), (400, 413, 422, 200, -1)))
for name, fn, expect in tests:
    code, j, dt = fn()
    record(name.split()[0], name, code in expect and clean_error(j) and alive(), "HTTP %s %.1fs %s" % (code, dt, str(j.get("detail", ""))[:60]))

# ---------- 4. папка для моделей ----------
cur = call("api/models/location")[1]["path"]
for name, path, expect in [
    ("L01 relative path", "relative\\dir", (400,)), ("L02 missing drive Z:", "Z:\\models", (400,)), ("L03 UNC share", "\\\\server\\share\\models", (400,)),
    ("L04 300+ chars", "C:\\" + "x" * 300, (400,)), ("L05 same folder", cur, (200,)), ("L06 file instead of folder", str(Path(__file__)), (400,)),
]:
    code, j, dt = call("api/models/location", {"path": path})
    after = call("api/models/location")[1]["path"]
    record(name.split()[0], name, code in expect and after == cur and alive(), "HTTP %s path_unchanged=%s %s" % (code, after == cur, str(j.get("detail", ""))[:60]))

bad = [r for r in results if not r[2]]
print("\nTOTAL %d  PASS %d  FAIL %d" % (len(results), len(results) - len(bad), len(bad)))
for r in bad:
    print("  FAIL", r[0], r[1], "|", r[3])
sys.exit(1 if bad else 0)
