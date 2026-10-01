# -*- coding: utf-8 -*-
"""Packaged app: GPU (DirectML) versus CPU on real models, from a clean data folder (ONNX export happens inside the frozen app). ASCII output.
    python tools/e2e_gpu.py APP_EXE HOME_DIR"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

exe, home = Path(sys.argv[1]), Path(sys.argv[2])
env = dict(os.environ, LINDA_HOME=str(home), LINDA_ALLOW_MULTI="1")
env["PATH"] = ";".join(x for x in os.environ["PATH"].split(";") if not re.search(r"python|scripts|git", x, re.I))
rows = [json.loads(l) for l in open(r"C:\Users\ninja\Desktop\детектор\data\external\hum_extra\holdout.jsonl", encoding="utf-8")]
pool = " ".join(r["text"] for r in rows if r["cohort"] == "x1_oct")
tx = lambda n: " ".join(pool.split()[:n])


def start():
    (home / "instance.json").unlink(missing_ok=True)
    p = subprocess.Popen([str(exe), "--no-ui"], env=env)
    for _ in range(200):
        try:
            d = json.loads((home / "instance.json").read_text())
            url = "http://127.0.0.1:%d/" % d["port"]
            html = urllib.request.urlopen(url, timeout=2).read().decode()
            return p, url, re.search(r'"x-linda-token": "([^"]+)"', html).group(1)
        except Exception:
            time.sleep(0.25)
    raise SystemExit("no start")


def api(url, tok, path, body=None):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers={"x-linda-token": tok, "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


out = {}
for dev in ("auto", "cpu"):
    (home / "settings.json").write_text(json.dumps({"device": dev, "sentences": "windows", "preload": True}))
    p, url, tok = start()
    t0 = time.time()
    seen = []
    while time.time() - t0 < 300:
        e = api(url, tok, "api/status")["engine"]
        key = (e["phase"], e.get("note", ""))
        if not seen or seen[-1] != key:
            seen.append(key)
        if e["phase"] in ("ready", "error"):
            break
        time.sleep(1)
    load = time.time() - t0
    e = api(url, tok, "api/status")["engine"]
    print("== setting %-4s -> device %s | ready after %.0f s | gpu probe: %s | gpu_error: %s" % (dev, e["device"], load, e["gpu"], e["gpu_error"] or "none"))
    print("   phases:", " -> ".join("%s%s" % (a, (" [" + b + "]") if b else "") for a, b in seen))
    for n in (300, 1000, 3000):
        api(url, tok, "api/detect", {"text": tx(n), "mode": "sensitive"})
        t = time.time()
        r = api(url, tok, "api/detect", {"text": tx(n), "mode": "sensitive"})["result"]
        out[(dev, n)] = r
        print("   %5d words: %.2f s | essay %.3f multi %.3f ens_z %.3f verdict %s" % (n, time.time() - t, r["voters"]["linda_essay"], r["voters"]["linda_multi_v2"], r["ens_z"], r["verdict"]))
    p.terminate()
    time.sleep(2)
for n in (300, 1000, 3000):
    a, b = out[("auto", n)], out[("cpu", n)]
    print("parity %d words: |d essay| %.4f |d multi| %.4f same verdict %s" % (n, abs(a["voters"]["linda_essay"] - b["voters"]["linda_essay"]), abs(a["voters"]["linda_multi_v2"] - b["voters"]["linda_multi_v2"]), a["verdict"] == b["verdict"]))
