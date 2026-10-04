# -*- coding: utf-8 -*-
"""Применение фонового обновления при старте (до загрузки моделей и FastAPI).

Если есть staging/<version>/READY — файлы переносятся в data атомарно (os.replace),
с бэкапом изменённых файлов; при сбое — откат, в логе «Откат выполнен».
Вызывается из __main__.main() самым первым шагом. Без сети, только файловые операции.
"""
from __future__ import annotations

from pathlib import Path


def run_if_pending(root: Path | None = None) -> dict:
    """Применить ожидающее обновление, если оно есть. Возвращает словарь результата."""
    from . import updater

    try:
        res = updater.apply_pending(root)
    except Exception as e:  # noqa: BLE001 — apply не должен ронять старт приложения
        res = {"applied": [], "version": None, "removed": [], "rolled_back": True,
               "error": "Откат выполнен: %s: %s" % (type(e).__name__, e)}
    try:
        from . import config

        log = (root or config.data_dir()) / "update_apply.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write("apply: version=%s applied=%s removed=%s rolled_back=%s error=%s\n" % (
                res.get("version"), len(res.get("applied", [])), res.get("removed"),
                res.get("rolled_back"), (res.get("error") or "")[:300]))
    except OSError:
        pass
    return res
