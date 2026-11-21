# -*- coding: utf-8 -*-
"""Model sets: choosing a set while another one is installed must not re-download what is on the disk, must not start a second download
job, and the status must stop advertising a download once the job is done (the "endless download that multiplies on every click" report)."""
import json
import threading
import time

from fastapi.testclient import TestClient

from linda_desktop import config, updater
from linda_desktop.app import Core, create_app

TOKEN = "t0k"

FILES = {"models/essay_dhi_x/model.bin": b"E" * 5000, "models/linda_speed_131/model.onnx": b"S" * 3000,
         "models/stylo_d/en.lgb.txt": b"D" * 200, "calibration/routing.json": b"{}"}
SETS = {"models/essay_dhi_x/model.bin": "pro", "models/linda_speed_131/model.onnx": "lite",
        "models/stylo_d/en.lgb.txt": "shared", "calibration/routing.json": "shared"}
PRO_BYTES = 5000 + 200 + 2
LITE_BYTES = 3000


def publish(repo, version="1.3.2"):
    m = repo.publish(FILES, version)
    for f in m["files"]:
        f["set"] = SETS[f["path"]]
    raw = json.dumps(m).encode()
    (repo.root / "latest.json").write_bytes(raw)
    (repo.root / "latest.json.sig").write_bytes(__import__("base64").b64encode(repo.key.sign(raw)))
    return m


def choose(sets):
    (config.data_dir()).mkdir(parents=True, exist_ok=True)
    (config.data_dir() / "settings.json").write_text(json.dumps({"model_sets": sets}), encoding="utf-8")


def wait_idle(client, limit=150):
    for _ in range(limit):
        d = client.get("/api/status").json()["download"]
        if d["phase"] in ("done", "error", "cancelled", "idle"):
            return d
        time.sleep(0.05)
    return client.get("/api/status").json()["download"]


def post_sets(client, sets, limit=100):
    """The page's Apply/Download button, but honest about the 409 the backend returns while the previous job thread is still exiting."""
    for _ in range(limit):
        r = client.post("/api/models/sets", json={"sets": sets})
        if r.status_code != 409:
            return r
        time.sleep(0.05)
    return r


def make_client(repo):
    return TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})


def weight_gets(repo):
    return [rel for rel, _ in repo.log if rel in FILES]


def test_second_click_while_downloading_is_refused_and_does_not_spawn_a_job(repo, monkeypatch):
    """(a) Choosing both at the first run and pressing Download twice: exactly one job, the second call gets 409."""
    publish(repo)
    started, release = threading.Event(), threading.Event()
    calls = []

    def blocking_run(self, manifest, raw, root, base):
        calls.append(manifest["version"])
        self._set(phase="downloading", total=1, done=0)
        started.set()
        release.wait(10)
        self._set(phase="done")

    monkeypatch.setattr(updater.Job, "_run", blocking_run)
    client = make_client(repo)
    try:
        assert client.post("/api/update/check").json()["update"]["weights_missing"]
        assert client.post("/api/models/sets", json={"sets": ["pro", "lite"]}).status_code == 200
        assert started.wait(5)
        assert client.post("/api/models/download").status_code == 409          # the page's Download button
        assert client.post("/api/models/sets", json={"sets": ["pro", "lite"]}).status_code == 409  # the page's Apply button
        assert len(calls) == 1, calls
    finally:
        release.set()


def test_adding_lite_while_pro_is_installed_downloads_only_lite(repo):
    """(b) Only the lite files are missing once the pro set is on the disk; the effective manifest lists them all."""
    publish(repo)
    choose(["pro"])
    client = make_client(repo)
    client.post("/api/update/check")
    assert client.post("/api/models/download").status_code == 200
    assert wait_idle(client)["phase"] == "done"
    assert updater.is_complete()

    before = len(weight_gets(repo))
    assert post_sets(client, ["pro", "lite"]).status_code == 200
    assert wait_idle(client)["phase"] == "done"

    fetched = weight_gets(repo)[before:]
    assert fetched and all("linda_speed" in rel for rel in fetched), fetched
    st = client.get("/api/status").json()
    assert st["model_sets"]["info"]["lite"]["installed"] and st["model_sets"]["info"]["pro"]["installed"]
    # (c) after a finished download the status must not keep advertising the same download
    assert st["update"]["weights_missing"] is False and not st["update"].get("bytes_to_download")


def test_status_is_fresh_after_download_and_a_redundant_click_does_not_redo_it(repo):
    """(c)+(e) The reported loop: 'models not installed' + a download that repeats on every click."""
    publish(repo)
    choose(["pro", "lite"])
    client = make_client(repo)
    client.post("/api/update/check")
    assert client.post("/api/models/download").status_code == 200
    assert wait_idle(client)["phase"] == "done"

    st = client.get("/api/status").json()
    assert st["models_ready"] is True
    assert st["update"]["weights_missing"] is False, "weights_missing stayed true after a finished download"
    assert not st["update"].get("bytes_to_download")
    assert all(st["model_sets"]["info"][s]["installed"] for s in ("pro", "lite"))

    before = len(repo.log)
    assert client.post("/api/models/download").status_code == 200  # a stale button press must be harmless
    assert wait_idle(client)["phase"] == "done"
    assert repo.log[before:] == [], "a redundant download re-fetched files: %s" % repo.log[before:]


def test_switching_back_to_pro_removes_lite_and_shows_it_missing(repo):
    """(d) Removing a set deletes its files, the UI reports it as not installed and re-adding it fetches only lite again."""
    publish(repo)
    choose(["pro", "lite"])
    client = make_client(repo)
    client.post("/api/update/check")
    client.post("/api/models/download")
    assert wait_idle(client)["phase"] == "done"

    assert post_sets(client, ["pro"]).status_code == 200
    st = client.get("/api/status").json()
    assert st["model_sets"]["info"]["lite"]["installed"] is False
    assert st["model_sets"]["info"]["pro"]["installed"] is True
    assert st["update"]["weights_missing"] is False
    root = config.models_root()
    assert not (root / "models/linda_speed_131/model.onnx").exists()

    before = len(weight_gets(repo))
    assert post_sets(client, ["pro", "lite"]).status_code == 200
    assert wait_idle(client)["phase"] == "done"
    fetched = weight_gets(repo)[before:]
    assert fetched == ["models/linda_speed_131/model.onnx"], fetched


HTML = (config.resource_dir() / "web" / "index.html")


def _busy_helper():
    import re
    html = HTML.read_text(encoding="utf-8")
    m = re.search(r"window\.LINDA_downloadBusy = function \(\) \{(.*?)\n  \};", html, re.S)
    assert m, "the download-busy helper is gone: the buttons lost their guard"
    return "function busy(S) {%s}" % m.group(1)


def test_download_buttons_are_guarded_while_a_job_runs():
    """(f) The page must not fire a second download (or a sets change) while one is running, and the buttons must be disabled."""
    html = HTML.read_text(encoding="utf-8")
    assert "if (window.LINDA_downloadBusy())" in html.split("$('lpSetupGo').onclick")[1].split("};")[0]
    assert "if (window.LINDA_downloadBusy())" in html.split("$('lpSetsApply').onclick")[1].split("};")[0]
    busy_block = html.split("if (!s.models_ready) {")[1].split("// banner")[0]
    assert "$('lpSetupGo').disabled = dlBusy" in busy_block
    assert "r.disabled = _busy" in html
    assert "window.LINDA_syncModelsCta" in html


def test_busy_helper_covers_every_download_phase(tmp_path):
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable")
    script = _busy_helper() + """
const assert=require('node:assert/strict');
for (const p of ['checking','downloading','verifying','applying','finishing']) assert.equal(busy({download:{phase:p}}), true, p);
for (const p of ['idle','done','error','cancelled']) assert.equal(busy({download:{phase:p}}), false, p);
assert.equal(busy(null), false);
console.log('ok');
"""
    path = tmp_path / "busy.js"
    path.write_text(script, encoding="utf-8")
    r = subprocess.run([node, str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads('"ok"') == "ok"
