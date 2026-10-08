# -*- coding: utf-8 -*-
"""Smoke-test of the built exe: starts in a temp home, checks status, then POST /api/models/restart with a fake READY staging dir (expects relaunch with a new PID). ASCII output.
    python tools/e2e_models_restart.py EXE HOME"""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

exe, home = sys.argv[1], Path(sys.argv[2]).resolve()
home.mkdir(parents=True, exist_ok=True)
env = {"SystemRoot": os.environ["SystemRoot"], "PATH": os.path.join(os.environ["SystemRoot"], "System32"), "TEMP": os.environ["TEMP"],
       "LOCALAPPDATA": str(home / "appdata"), "USERPROFILE": str(home), "LINDA_HOME": str(home)}
(home / "instance.json").unlink(missing_ok=True)
p = subprocess.Popen([exe], env=env)
for _ in range(120):
    if (home / "instance.json").exists():
        break
    time.sleep(1)
else:
    print("FAIL: no instance.json, exit", p.poll())
    sys.exit(1)
inst = json.loads((home / "instance.json").read_text())
base = "http://127.0.0.1:%d" % inst["port"]
page = urllib.request.urlopen(base + "/", timeout=30).read().decode("utf-8")
tok = re.search(r"__lindaToken = '([^']+)'", page).group(1)
print("page ok, models_restart ui:", "mrestart" in page)


def call(path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers={"x-linda-token": tok, "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


print("status", call("/api/status")[0])
print("restart without staging:", call("/api/models/restart", {}))
st = home / "models" / "staging" / "9.9.9"
for cand in (home / "staging" / "9.9.9", st):
    cand.mkdir(parents=True, exist_ok=True)
    (cand / "READY").write_text(json.dumps({"version": "9.9.9", "ts": time.time()}))
print("pending:", call("/api/status")[1][:0], "restart with READY:", call("/api/models/restart", {}))
time.sleep(12)
(home / "instance.json").exists()
inst2 = json.loads((home / "instance.json").read_text()) if (home / "instance.json").exists() else {}
print("old pid alive:", p.poll() is None, "| new instance pid:", inst2.get("pid"), "old:", inst["pid"])
if inst2.get("pid") and inst2["pid"] != inst["pid"]:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(inst2["pid"])], capture_output=True)
subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
