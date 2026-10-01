# -*- coding: utf-8 -*-
"""Update test of the INSTALLED app: weights delta update + application self-update through the signed manifest. ASCII output.
    python tools/e2e_update.py INSTALL_DIR HOME_DIR REPO_URL REQUEST_LOG [--bad-hash]"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

inst, home, base, reqlog = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
exe = inst / "Linda-Pro.exe"
env = dict(os.environ)  # a real user session environment, but with every Python entry removed from PATH (a business PC has no Python)
env["PATH"] = ";".join(x for x in os.environ["PATH"].split(";") if not re.search(r"python|scripts|git", x, re.I))
env.update(LINDA_BASE_URL=base, LINDA_HOME=str(home), LINDA_ALLOW_HTTP="1")
env.pop("PYTHONPATH", None)
env.pop("VIRTUAL_ENV", None)


def reg_version():
    r = subprocess.run(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B6D1E7F4-5E1C-4B8E-9D2A-4C8F0A11D0A1}_is1", "/v", "DisplayVersion"], capture_output=True, text=True)
    m = re.search(r"DisplayVersion\s+REG_SZ\s+(\S+)", r.stdout)
    return m.group(1) if m else None


def start():
    (home / "instance.json").unlink(missing_ok=True)
    p = subprocess.Popen([str(exe), "--no-ui"], cwd=str(home.parent), env=env)
    for _ in range(300):
        try:
            d = json.loads((home / "instance.json").read_text())
            url = "http://127.0.0.1:%d/" % d["port"]
            html = urllib.request.urlopen(url, timeout=2).read().decode()
            return p, url, re.search(r'"x-linda-token": "([^"]+)"', html).group(1)
        except Exception:
            time.sleep(0.5)
    raise SystemExit("app did not start")


def mk_call(url, tok):
    def call(path, body=None, method="POST"):
        req = urllib.request.Request(url + path.lstrip("/"), data=(json.dumps(body or {}).encode() if method == "POST" else None), method=method,
                                     headers={"x-linda-token": tok, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    return call


print("registry version before:", reg_version())
p, url, tok = start()
call = mk_call(url, tok)
st = call("/api/status", method="GET")[1]
print("app", st["app_version"], "| installed models", st["installed_version"], "| ready", st["models_ready"])
reqlog.write_text("")
u = call("/api/update/check")[1]["update"]
print("update announced: remote %s, weights_update %s, app_new %s (installer %s), bytes_to_download %s, notes: %s" % (
    u["remote_version"], u["weights_update"], u["app_new"], (u["installer"] or {}).get("version"), u.get("bytes_to_download"), u["notes"]))
print("download weights ->", call("/api/models/download")[0])
for _ in range(120):
    d = call("/api/status", method="GET")[1]["download"]
    if d["phase"] in ("done", "error"):
        break
    time.sleep(0.5)
print("delta download:", d["phase"], d["error"], "| bytes", d["total"])
fetched = [l.split()[0] for l in reqlog.read_text().splitlines() if not l.startswith("latest") and not l.startswith("Linda-Setup")]
print("files fetched during the update:", fetched)
st = call("/api/status", method="GET")[1]
print("installed models now:", st["installed_version"], "| ready", st["models_ready"], "| release_notes.txt present:", (home / "calibration" / "release_notes.txt").exists())
det = call("/api/detect", {"text": "word " * 60})
print("analysis after the weights update works:", det[0] in (200,))

old_pid = json.loads((home / "instance.json").read_text())["pid"]
print("app update ->", call("/api/app/update"))
t0 = time.time()
last = None
while time.time() - t0 < 180:
    try:
        j = call("/api/status", method="GET")[1]["installer_job"]
        if j != last:
            print("  installer job:", j["phase"], j.get("error", ""))
            last = j
        if j["phase"] == "error":
            break
    except Exception:
        break  # the app exited to let the installer replace it
    time.sleep(0.7)
print("registry version after:", reg_version())
for _ in range(120):
    time.sleep(1)
    if reg_version() == "1.1.1":
        break
time.sleep(10)
print("registry version final:", reg_version())
try:
    d = json.loads((home / "instance.json").read_text())
    print("app restarted by the installer:", d["pid"] != old_pid, "(pid %s -> %s)" % (old_pid, d["pid"]))
except Exception as e:
    print("instance.json:", e)
