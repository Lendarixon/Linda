# -*- coding: utf-8 -*-
import time

from fastapi.testclient import TestClient

from linda_desktop import updater
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


def make(monkeypatch, complete=True):
    core = Core()
    calls = []
    monkeypatch.setattr(updater, "is_complete", lambda *a, **k: complete)
    monkeypatch.setattr(core.engine, "ensure_loaded", lambda: calls.append(1) or {"x": 1})
    monkeypatch.setattr(core.engine, "_load_voters", lambda dets: calls.append(2))
    return core, calls


def wait(calls, n=1, t=3.0):
    t0 = time.time()
    while len(calls) < n and time.time() - t0 < t:
        time.sleep(0.02)


def test_preload_off_by_default_for_on_demand_loading(repo, monkeypatch):
    core, calls = make(monkeypatch)
    assert core.preload() is False
    assert calls == []


def test_preload_can_be_switched_off(repo, monkeypatch):
    core, calls = make(monkeypatch)
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    assert c.post("/api/settings", json={"preload": False}).json()["settings"]["preload"] is False
    assert core.preload() is False
    time.sleep(0.2)
    assert calls == []  # nothing is loaded until the first analysis
    assert c.get("/api/status").json()["settings"]["preload"] is False


def test_switching_on_loads_immediately(repo, monkeypatch):
    core, calls = make(monkeypatch)
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    c.post("/api/settings", json={"preload": False})
    c.post("/api/settings", json={"preload": True})
    wait(calls,2)
    assert calls == [1,2]


def test_no_preload_without_models_and_bad_value_ignored(repo, monkeypatch):
    core, calls = make(monkeypatch, complete=False)
    assert core.preload() is False
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    assert c.post("/api/settings", json={"preload": "yes"}).json()["settings"]["preload"] is False
    time.sleep(0.2)
    assert calls == []


def test_gpu_probe_and_safe_fallback(monkeypatch):
    import sys
    import types

    from linda_desktop import engine, onnx_gpu

    def fake_torch(available, hip=None, name="Fake GPU"):
        m = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: available, get_device_name=lambda i: name), version=types.SimpleNamespace(hip=hip))
        monkeypatch.setitem(sys.modules, "torch", m)

    monkeypatch.setattr(engine, "_adapter_names", lambda: ["AMD Radeon RX 9070 XT"])
    # no GPU at all
    fake_torch(False)
    monkeypatch.setattr(onnx_gpu, "available", lambda: False)
    assert engine.gpu_probe() == {"available": False, "backend": None, "name": "", "names": [], "discrete": False}
    assert engine.pick_device("cuda") == "cpu" and engine.pick_device("auto") == "cpu" and engine.pick_device("cpu") == "cpu"  # asking for a GPU never breaks the app
    # the Windows installer: CPU torch, but DirectML through ONNX Runtime
    monkeypatch.setattr(onnx_gpu, "available", lambda: True)
    assert engine.gpu_probe() == {"available": True, "backend": "DirectML", "name": "AMD Radeon RX 9070 XT", "names": ["AMD Radeon RX 9070 XT"], "discrete": True}
    assert engine.pick_device("auto") == "dml" and engine.pick_device("cuda") == "dml" and engine.pick_device("cpu") == "cpu"
    # development installs with a torch GPU backend win over DirectML
    fake_torch(True, hip="6.4", name="AMD Radeon RX 9070 XT")
    assert engine.gpu_probe() == {"available": True, "backend": "ROCm", "name": "AMD Radeon RX 9070 XT", "names": ["AMD Radeon RX 9070 XT"], "discrete": True}
    assert engine.pick_device("auto") == "cuda"
    fake_torch(True, hip=None, name="NVIDIA GeForce RTX 4060")
    assert engine.gpu_probe()["backend"] == "CUDA"


def test_auto_ignores_a_lone_integrated_gpu(monkeypatch):
    import sys
    import types

    from linda_desktop import engine, onnx_gpu

    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False), version=types.SimpleNamespace(hip=None)))
    monkeypatch.setattr(onnx_gpu, "available", lambda: True)
    for names, discrete in ((["AMD Radeon(TM) Graphics"], False), (["Intel(R) UHD Graphics 770"], False), (["Intel(R) Iris(R) Xe Graphics"], False),
                            (["AMD Radeon(TM) Graphics", "AMD Radeon RX 9070 XT"], True), (["NVIDIA GeForce RTX 4060 Laptop GPU", "Intel(R) UHD Graphics"], True),
                            (["Intel(R) Arc(TM) A770 Graphics"], True), (["AMD Radeon RX 7600M XT"], True)):
        monkeypatch.setattr(engine, "_adapter_names", lambda n=names: n)
        g = engine.gpu_probe()
        assert g["discrete"] is discrete, names
        assert engine.pick_device("auto") == ("dml" if discrete else "cpu"), names
        assert engine.pick_device("cuda") == "dml"  # an explicit choice is honoured even for an integrated GPU
