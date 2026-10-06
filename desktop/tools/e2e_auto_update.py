# -*- coding: utf-8 -*-
"""Автообновление моделей 1.1.0 -> 1.3.0 без клика: приложение стартует на копии старых моделей, само скачивает новые, старые удаляются, проверка работает. ASCII-вывод.
    LINDA_BASE_URL=http://127.0.0.1:8099 python tools/e2e_auto_update.py HOME"""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

home = Path(sys.argv[1]).resolve()
ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ, LINDA_HOME=str(home), LINDA_BASE_URL=os.environ.get("LINDA_BASE_URL", "http://127.0.0.1:8099"), PYTHONIOENCODING="utf-8")
(home / "instance.json").unlink(missing_ok=True)
EXE = os.environ.get("E2E_EXE")
if EXE:  # собранное приложение с урезанным окружением, как у клиента
    env = {"SystemRoot": os.environ["SystemRoot"], "PATH": os.path.join(os.environ["SystemRoot"], "System32"), "TEMP": os.environ["TEMP"], "LOCALAPPDATA": str(home / "appdata"), "USERPROFILE": str(home), "LINDA_HOME": str(home), "LINDA_BASE_URL": env["LINDA_BASE_URL"]}
    p = subprocess.Popen([EXE, "--no-ui"], cwd=str(home.parent), env=env)
    for _ in range(300):
        try:
            url = "http://127.0.0.1:%d/" % json.loads((home / "instance.json").read_text())["port"]; urllib.request.urlopen(url, timeout=2).read(10); break
        except Exception:
            time.sleep(0.5)
else:
    p = subprocess.Popen([sys.executable, "-m", "linda_desktop", "--no-ui"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = p.stdout.readline().strip()
tok = re.search(r"""x-linda-token['"]?\s*[,:]\s*['"]([^'"]+)['"]""", urllib.request.urlopen(url).read().decode()).group(1)
api = lambda path, body=None: json.loads(urllib.request.urlopen(urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers={"x-linda-token": tok, "Content-Type": "application/json"}, method="POST" if body is not None else "GET"), timeout=300).read())
try:
    st = api("api/status"); print("start: weights", st["installed_version"], "auto_models", st["settings"].get("auto_models"))
    t0 = time.time(); seen = set()
    while time.time() - t0 < 300:
        st = api("api/status"); ph = st["download"]["phase"]
        if ph not in seen: seen.add(ph); print("  phase:", ph, "%.0fs" % (time.time() - t0), flush=True)
        if st["installed_version"] == "1.3.0" and ph in ("done", "idle"): break
        if ph in ("idle",) and time.time() - t0 > 40 and st["installed_version"] != "1.3.0": api("api/update/check", {})
        time.sleep(1)
    print("weights now", st["installed_version"], "models_ready", st["models_ready"])
    print("models:", sorted(x.name for x in (home / "models").iterdir()), "onnx:", sorted(x.name for x in (home / "onnx").iterdir()) if (home / "onnx").exists() else [])
    r = api("api/detect", {"text": "Это тестовый текст для проверки после автоматического обновления моделей. " * 12, "mode": "sensitive"}); print("detect after update: ok", r["result"]["verdict"])
finally:
    p.terminate()
