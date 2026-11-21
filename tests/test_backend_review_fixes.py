# -*- coding: utf-8 -*-
"""Regression tests for the Neon backend review fixes (2026-11-20, rc/2.4).

Covers: P0 trace corpora license gates, P1 packs TOCTOU + unlocked snapshot,
P1 humanize_pack ensure_runtime/unload/generate races, P1 SpeedOnnx special
token ids, P1 licensing fail-closed on corrupt expires_at.
"""
import threading

import pytest
from fastapi.testclient import TestClient

from linda_desktop import config, licensing, packs
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


@pytest.fixture()
def client(repo):
    return TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})


@pytest.fixture()
def licensed(monkeypatch):
    monkeypatch.setattr(licensing, "public_state",
                        lambda st=None: {"licensed": True, "kind": "gift", "tier": "personal",
                                         "key_hint": "T", "status": "granted", "configured": True})


# ---- P0: /api/trace/corpora* must require the trace license ----

def test_trace_corpora_routes_refuse_without_license(client):
    client.post("/api/settings", json={"language": "en"})
    assert client.get("/api/trace/corpora").status_code == 403
    assert client.get("/api/trace/corpora/x").status_code == 403
    assert client.post("/api/trace/corpora", json={"name": "c", "documents": []}).status_code == 403
    assert client.delete("/api/trace/corpora/x").status_code == 403


def test_trace_corpora_routes_pass_gate_when_licensed(client, licensed):
    client.post("/api/settings", json={"language": "en"})
    # past the gate the handlers run for real; whatever they return, it is not 403
    assert client.get("/api/trace/corpora").status_code != 403
    assert client.get("/api/trace/corpora/missing").status_code == 404
    assert client.post("/api/trace/corpora", json={"name": "", "documents": []}).status_code != 403
    assert client.delete("/api/trace/corpora/missing").status_code == 404


# ---- P1: packs download TOCTOU + job_snapshot locking ----

def test_packs_try_start_is_atomic():
    packs._pack_job.update(phase="idle", pack="", error="")
    assert packs.try_start("trace") is True
    assert packs.job_snapshot()["phase"] == "running"
    assert packs.try_start("humanizer-lite") is False  # second start refused
    with _pack_lock_probe():
        pass
    packs._pack_job.update(phase="idle")


class _pack_lock_probe:
    def __enter__(self):
        return packs._pack_lock

    def __exit__(self, *a):
        return False


def test_packs_job_snapshot_returns_copy_under_lock():
    snap = packs.job_snapshot()
    snap["phase"] = "mutated"
    assert packs.job_snapshot()["phase"] != "mutated"


def test_packs_download_refuses_concurrent_other_pack():
    packs._pack_job.update(phase="running", pack="trace")
    with pytest.raises(RuntimeError):
        packs.download("humanizer-lite")
    packs._pack_job.update(phase="idle", pack="")


# ---- P1: humanize_pack runtime races ----

def test_humanize_unload_refused_while_generating(monkeypatch):
    from linda_desktop import humanize_pack

    class FakeBackend:
        unloaded = False

        def unload(self):
            self.unloaded = True

    monkeypatch.setattr(humanize_pack, "_backend", FakeBackend())
    monkeypatch.setattr(humanize_pack, "_backend_busy", True)
    humanize_pack.unload()
    assert humanize_pack._backend.unloaded is False
    monkeypatch.setattr(humanize_pack, "_backend_busy", False)
    humanize_pack.unload()
    assert humanize_pack._backend.unloaded is True
    monkeypatch.setattr(humanize_pack, "_backend", None)


def test_humanize_ensure_runtime_serialized(monkeypatch):
    from linda_desktop import humanize_pack
    calls = []

    def fake_have(m):
        calls.append(m)
        return True

    monkeypatch.setattr(humanize_pack, "_RUNTIME_OK", False)
    monkeypatch.setattr(humanize_pack, "_have", fake_have)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda _: humanize_pack.ensure_runtime(), range(4)))
    assert humanize_pack._RUNTIME_OK is True
    monkeypatch.setattr(humanize_pack, "_RUNTIME_OK", False)


# ---- P1: SpeedOnnx.token_scores applies special ids ----

def test_speed_onnx_token_scores_uses_special_ids():
    import numpy as np
    from linda_pro.voters import SpeedOnnx

    class FakeEnc:
        def __init__(self, ids):
            self.ids = ids
            self.offsets = [(i, i + 1) for i in range(len(ids))]

    class FakeTok:
        def token_to_id(self, t):
            return None  # mmBERT-style: no <s>/</s>/<pad> in vocab

        def encode(self, text, add_special_tokens=False):
            return FakeEnc([10, 11, 12])

    class FakeOut:
        name = "tok"

    class FakeSess:
        def get_outputs(self):
            return [FakeOut()]

        def run(self, names, feed):
            ids = feed["input_ids"]
            return [np.zeros(ids.shape, dtype=np.float64)]

    v = SpeedOnnx.__new__(SpeedOnnx)
    v.sess = FakeSess()
    v.tok = FakeTok()
    v.max_len = 16
    v.batch = 2
    v.vmap = None
    v.special_ids = (0, 2, 1)  # bos/eos/pad overrides from speed_args.json
    import linda_pro.voters as voters
    orig = voters.check_cancel
    voters.check_cancel = lambda: None
    try:
        res = v.token_scores("abc")
    finally:
        voters.check_cancel = orig
    assert len(res) == 3
    assert all(isinstance(s, float) for _, _, s in res)


# ---- P1: licensing fails closed on corrupt expires_at ----

def test_licensing_fail_closed_on_corrupt_expires_at(monkeypatch):
    monkeypatch.setattr(config, "DEV_INSTALLER_ENABLED", False)
    st = {"key": "k", "status": "granted", "kind": "purchase",
          "machine": licensing.machine_id(), "expires_at": "not-a-date"}
    assert licensing.public_state(st)["licensed"] is False


def test_licensing_dev_mode_keeps_fail_open(monkeypatch):
    monkeypatch.setattr(config, "DEV_INSTALLER_ENABLED", True)
    st = {"key": "k", "status": "granted", "kind": "purchase",
          "machine": licensing.machine_id(), "expires_at": "not-a-date"}
    assert licensing.public_state(st)["licensed"] is True
