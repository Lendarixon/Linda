# -*- coding: utf-8 -*-
"""Model sets: Linda-Pro (pro) and Linda-Pro Lite (lite) are downloaded, kept and removed independently; shared files always come along."""
import base64
import json
import time

from linda_desktop import config, updater

FILES = {"models/essay_dhi_x/model.bin": b"E" * 5000, "models/linda_speed_131/model.onnx": b"S" * 3000, "models/stylo_d/en.lgb.txt": b"D" * 200, "calibration/routing.json": b"{}"}
SETS = {"models/essay_dhi_x/model.bin": "pro", "models/linda_speed_131/model.onnx": "lite", "models/stylo_d/en.lgb.txt": "shared", "calibration/routing.json": "shared"}


def publish(repo, version="1.3.2"):
    m = repo.publish(FILES, version)
    for f in m["files"]:
        f["set"] = SETS[f["path"]]
    raw = json.dumps(m).encode()
    (repo.root / "latest.json").write_bytes(raw)
    (repo.root / "latest.json.sig").write_bytes(base64.b64encode(repo.key.sign(raw)))
    return m


def run_job(m, raw):
    job = updater.Job()
    job.start(m, raw)
    t0 = time.time()
    while job.running() and time.time() - t0 < 30:
        time.sleep(0.05)
    return job.snapshot()


def choose(sets):
    (config.data_dir()).mkdir(parents=True, exist_ok=True)
    (config.data_dir() / "settings.json").write_text(json.dumps({"model_sets": sets}), encoding="utf-8")


def test_only_lite_downloads_lite_and_shared(repo):
    publish(repo)
    choose(["lite"])
    m, raw = updater.get_manifest()
    assert {f["path"] for f in m["files"]} == {"models/linda_speed_131/model.onnx", "models/stylo_d/en.lgb.txt", "calibration/routing.json"}
    assert len(m["all_files"]) == 4
    assert run_job(m, raw)["phase"] == "done"
    root = config.models_root()
    assert (root / "models/linda_speed_131/model.onnx").is_file() and not (root / "models/essay_dhi_x").exists()
    assert updater.is_complete()
    info = updater.set_info(m)
    assert info["lite"]["installed"] and not info["pro"]["installed"] and info["pro"]["size"] == 5000


def test_adding_and_removing_a_set(repo):
    publish(repo)
    choose(["lite"])
    m, raw = updater.get_manifest()
    run_job(m, raw)
    choose(["pro", "lite"])
    m, raw = updater.get_manifest()
    st = updater.update_status(m)
    assert st["weights_missing"] and st["bytes_to_download"] == 5000  # only the Pro set is missing
    assert run_job(m, raw)["phase"] == "done"
    assert updater.is_complete()
    choose(["pro"])
    removed = updater.remove_unselected()
    assert removed == ["models/linda_speed_131/model.onnx"]
    root = config.models_root()
    assert not (root / "models/linda_speed_131").exists() and (root / "models/essay_dhi_x/model.bin").is_file()
    assert updater.is_complete()  # complete for the selection that is left


def test_selection_sources(repo):
    d = config.data_dir()
    d.mkdir(parents=True, exist_ok=True)
    assert updater.selected_sets() == ["pro"]  # nothing known: Linda-Pro
    (d / "installer_choice.json").write_text(json.dumps({"model_sets": ["lite"]}), encoding="utf-8")
    assert updater.selected_sets() == ["lite"]  # the installer's choice
    choose(["pro", "lite"])
    assert updater.selected_sets() == ["pro", "lite"]  # the user's choice wins
    (d / "settings.json").write_text(json.dumps({"model_sets": ["nonsense"]}), encoding="utf-8")
    assert updater.selected_sets() == ["lite"]  # invalid settings fall back to the installer's choice


def test_old_manifest_without_sets_installs_everything(repo):
    repo.publish(FILES, "1.3.1")  # a manifest from before the sets existed
    choose(["lite"])
    m, raw = updater.get_manifest()
    assert len(m["files"]) == 4
