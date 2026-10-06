# -*- coding: utf-8 -*-
"""Автовыбор видеокарты: дискретная определяется по объёму видеопамяти, а не только по имени; сильнейшая карта первой."""
from linda_desktop import engine

GB = 2**30


def test_discrete_by_vram_and_order(monkeypatch):
    monkeypatch.setattr(engine, "_registry_adapters", lambda: [("AMD Radeon(TM) Graphics", GB // 2), ("Some Unknown Card 9000", 8 * GB), ("AMD Radeon RX 7600", 8 * GB), ("NVIDIA T400", 2 * GB)])
    ads = engine._adapters()
    assert [a["discrete"] for a in ads] == [True, True, True, False]
    assert ads[-1]["name"].startswith("AMD Radeon(TM)")  # встроенная графика последней
    assert {a["name"] for a in ads[:3]} == {"Some Unknown Card 9000", "AMD Radeon RX 7600", "NVIDIA T400"}


def test_auto_uses_gpu_when_adapter_list_is_empty(monkeypatch):
    monkeypatch.setattr(engine, "_registry_adapters", lambda: [])
    monkeypatch.setattr(engine, "_wmi_names", lambda: [])
    import linda_desktop.onnx_gpu as og
    monkeypatch.setattr(og, "available", lambda: True)
    monkeypatch.setitem(__import__("sys").modules, "torch", None)  # без PyTorch GPU: идём через DirectML
    assert engine.gpu_probe()["discrete"] is True
    assert engine.pick_device("auto") == "dml"
