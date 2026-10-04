# -*- coding: utf-8 -*-
"""Отмена незаконченной проверки: новая проверка из окна одного текста прерывает старую, пакетные проверки не затрагиваются."""
import threading
import time

import pytest

from linda_desktop import engine
from linda_pro import voters


def _slow(eng, steps=400):
    """Подмена расчёта: «пакеты» с проверкой отмены, как в margins()."""
    def run_locked(text, mode="sensitive", models=None):
        for _ in range(steps):
            voters.check_cancel()
            time.sleep(0.01)
        return {"ok": True}
    eng._run_locked = run_locked


def test_running_cancellable_job_is_aborted_by_cancel():
    eng = engine.Engine()
    _slow(eng)
    out = {}

    def job():
        try:
            out["r"] = eng.run("x", cancellable=True)
        except voters.Cancelled:
            out["cancelled"] = True

    t = threading.Thread(target=job)
    t.start()
    time.sleep(0.15)
    assert eng.cancel_cancellable() == 1
    t.join(5)
    assert out.get("cancelled") and "r" not in out and not t.is_alive()
    assert voters.CANCEL is None  # хук снят


def test_waiting_job_is_cancelled_before_it_starts_and_next_runs_fine():
    eng = engine.Engine()
    _slow(eng, steps=30)
    first, second = {}, {}
    t1 = threading.Thread(target=lambda: first.update(r=eng.run("a", cancellable=False)))  # пакетная: не отменяется
    t1.start()
    time.sleep(0.05)

    def waiting():
        try:
            second["r"] = eng.run("b", cancellable=True)
        except voters.Cancelled:
            second["cancelled"] = True

    t2 = threading.Thread(target=waiting)
    t2.start()
    time.sleep(0.05)
    assert eng.cancel_cancellable() == 1  # затронута только отменяемая, ожидающая
    t1.join(5)
    t2.join(5)
    assert first.get("r") == {"ok": True}  # пакетная дошла до конца
    assert second.get("cancelled")
    eng._run_locked = lambda *a, **k: {"fine": True}
    assert eng.run("c", cancellable=True) == {"fine": True}  # очередь свободна


def test_adapter_names_discrete_first(monkeypatch):
    """Номер видеокарты в настройках = device_id DirectML: дискретная первой, встроенная последней."""
    class R:
        stdout = "AMD Radeon(TM) Graphics\nAMD Radeon RX 9070 XT\nMicrosoft Basic Display Adapter\n"
    monkeypatch.setattr(engine.subprocess, "run", lambda *a, **k: R())
    monkeypatch.setattr(engine.os, "name", "nt")
    assert engine._adapter_names() == ["AMD Radeon RX 9070 XT", "AMD Radeon(TM) Graphics"]


def test_gpu_index_migrated_to_zero_once(repo):
    from linda_desktop.app import Core
    engine.save_settings({**engine.load_settings(), "gpu_index": 1})
    Core()
    s = engine.load_settings()
    assert s["gpu_index"] == 0 and s["gpu_map"] == 2
    engine.save_settings({**s, "gpu_index": 1})  # выбор после миграции сохраняется
    Core()
    assert engine.load_settings()["gpu_index"] == 1


def test_verdict_probability_matches_verdict():
    """Показываемая вероятность ИИ согласована с вердиктом: человек < 0,5 <= неясно < 0,9 <= ИИ (раньше у человека было 80-90%)."""
    rules = {"ensemble": {"thr_5": 1.52, "thr_1": 1.95, "thr_05": 2.08}, "essay": {"thr_5": 6.0, "thr_1": 7.0, "thr_05": 8.0}}
    human = engine.verdict_probability({"ens_z": 0.9, "essay": 2.0, "verdict": "human"}, rules)
    unc = engine.verdict_probability({"ens_z": 1.7, "essay": 2.0, "verdict": "uncertain"}, rules)
    ai = engine.verdict_probability({"ens_z": 2.5, "essay": 9.0, "verdict": "ai"}, rules)
    assert human < 0.5 <= unc < 0.9 <= ai
    assert human < 0.15  # типичный человеческий текст (z около 0,9) — малая вероятность ИИ
