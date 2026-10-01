# -*- coding: utf-8 -*-
"""End-to-end test with the REAL weights: starts the app like a user's first run (clean data folder), downloads the models from a local stand-in repository,
analyses a text and prints timings. ASCII output only.
    python tools/e2e_real.py [base_url] [home_dir] [--keep]"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"
home = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "_e2e_home")
if home.exists() and "--keep" not in sys.argv:
    shutil.rmtree(home)
env = dict(os.environ, LINDA_BASE_URL=base, LINDA_HOME=str(home), PYTHONIOENCODING="utf-8")
EXE = os.environ.get("E2E_EXE")
if EXE:  # the packaged app, started with a stripped-down environment (no Python on PATH), like on a clean business PC
    env = {"SystemRoot": os.environ["SystemRoot"], "PATH": os.path.join(os.environ["SystemRoot"], "System32"), "TEMP": os.environ["TEMP"], "LOCALAPPDATA": str(home / "appdata"),
           "USERPROFILE": str(home), "LINDA_BASE_URL": base, "LINDA_HOME": str(home)}
    p = subprocess.Popen([EXE, "--no-ui"], cwd=str(home.parent), env=env)
    for _ in range(300):
        f = home / "instance.json"
        if f.exists():
            try:
                url = "http://127.0.0.1:%d/" % json.loads(f.read_text())["port"]
                urllib.request.urlopen(url, timeout=2).read(10)
                break
            except Exception:
                pass
        time.sleep(0.5)
else:
    p = subprocess.Popen([sys.executable, "-m", "linda_desktop", "--no-ui"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = p.stdout.readline().strip()
print("app at", url)
tok = re.search(r'"x-linda-token": "([^"]+)"', urllib.request.urlopen(url).read().decode()).group(1)


def call(path, body=None, method="POST"):
    req = urllib.request.Request(url + path.lstrip("/"), data=(json.dumps(body or {}).encode() if method == "POST" else None), method=method,
                                 headers={"x-linda-token": tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


try:
    st = call("/api/status", method="GET")[1]
    print("first run: models_ready =", st["models_ready"], "| licence:", st["license"]["licensed"])
    print("detect before install ->", call("/api/detect", {"text": "word " * 50})[0])
    print("check ->", call("/api/update/check")[1]["update"]["remote_version"])
    t0 = time.time()
    print("download ->", call("/api/models/download")[0])
    last = -1
    while True:
        d = call("/api/status", method="GET")[1]["download"]
        if int(d["done"] / 1e8) != last:
            last = int(d["done"] / 1e8)
            print("  %s %.2f / %.2f GB %.0f MB/s" % (d["phase"], d["done"] / 1e9, d["total"] / 1e9, d["speed"] / 1e6))
        if d["phase"] in ("done", "error", "cancelled"):
            break
        time.sleep(1)
    print("download phase:", d["phase"], d["error"], "| %.0f s" % (time.time() - t0))
    st = call("/api/status", method="GET")[1]
    print("models_ready =", st["models_ready"], "| installed", st["installed_version"])
    rows = [json.loads(l) for l in open(r"C:\Users\ninja\Desktop\детектор\data\external\hum_extra\holdout.jsonl", encoding="utf-8")]
    text = [r["text"] for r in rows if r["cohort"] == "x1_oct"][3]
    print("text words:", len(text.split()))
    for i in range(2):
        t1 = time.time()
        code, j = call("/api/detect", {"text": text, "mode": "sensitive"})
        r = j.get("result", {})
        if code != 200:
            print("   error detail:", str(j)[:600])
        print("detect #%d: HTTP %s, %.1f s, verdict %s, essay %.3f, ens_z %.3f, windows %s, sentences %s (%s), device %s" % (
            i + 1, code, time.time() - t1, r.get("verdict"), r.get("essay", 0), r.get("ens_z", 0), r.get("n_windows"), r.get("sentence_stats", {}).get("total"),
            r.get("sentence_stats", {}).get("granularity"), call("/api/status", method="GET")[1]["engine"]["device"]))
finally:
    p.terminate()
