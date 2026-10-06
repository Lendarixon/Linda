# -*- coding: utf-8 -*-
"""Прогрев моделей в фоне и «Проверить в Linda-Pro»: собранное приложение стартует, через 35 с первая проверка быстрая; второй запуск с файлом кладёт его во входящие. ASCII-вывод.
    python tools/e2e_warm_inbox.py EXE HOME"""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

exe, home = Path(sys.argv[1]), Path(sys.argv[2])
env = {"SystemRoot": os.environ["SystemRoot"], "PATH": os.path.join(os.environ["SystemRoot"], "System32"), "TEMP": os.environ["TEMP"], "LOCALAPPDATA": str(home / "appdata"), "USERPROFILE": str(home), "LINDA_HOME": str(home)}
(home / "instance.json").unlink(missing_ok=True)
p = subprocess.Popen([str(exe), "--no-ui"], env=env, cwd=str(home.parent))
for _ in range(300):
    try:
        d = json.loads((home / "instance.json").read_text()); url = "http://127.0.0.1:%d/" % d["port"]
        html = urllib.request.urlopen(url, timeout=2).read().decode(); tok = re.search(r"""x-linda-token['"]?\s*[,:]\s*['"]([^'"]+)['"]""", html).group(1); break
    except Exception:
        time.sleep(0.5)


def api(path, body=None):
    r = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers={"x-linda-token": tok, "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r, timeout=300).read())


try:
    t0 = time.time()
    while time.time() - t0 < 90:
        e = api("api/status")["engine"]
        if e["phase"] == "ready":
            break
        time.sleep(1)
    print("engine phase", e["phase"], "device", e["device"], "ready after %.0f s" % (time.time() - t0))
    text = "Это тестовый текст для проверки скорости первой проверки после прогрева моделей в фоне. " * 12
    t1 = time.time(); r = api("api/detect", {"text": text, "mode": "sensitive"}); print("first detect after warm-up: %.1f s verdict %s" % (time.time() - t1, r["result"]["verdict"]))
    f = home / "from_explorer.txt"; f.write_text("Документ из проводника. " * 40, encoding="utf-8")
    p2 = subprocess.Popen([str(exe), str(f)], env=dict(env, BROWSER="true"), cwd=str(home.parent)); p2.wait(timeout=60)
    time.sleep(1)
    files = api("api/inbox")["files"]; print("inbox:", [x["name"] for x in files])
    o = api("api/open_path", {"path": files[0]["path"]}); print("opened:", o["filename"], o["words"], "words")
    try:
        api("api/open_path", {"path": str(home / "settings.json")}); print("NOT BLOCKED")
    except Exception as ex:
        print("arbitrary path blocked:", type(ex).__name__)
finally:
    p.terminate()
