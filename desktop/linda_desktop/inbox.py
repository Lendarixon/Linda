# -*- coding: utf-8 -*-
"""Входящие для пункта «Проверить в Linda-Pro» из меню проводника.

Второй экземпляр программы кладёт путь к файлу сюда, а уже работающий
экземпляр забирает пути через :func:`take`. Только стандартная библиотека.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from . import config

# Разрешённые расширения (в нижнем регистре, с точкой).
ALLOWED_SUFFIXES = frozenset({".docx", ".pdf", ".txt", ".md"})
# Предел размера файла: 20 МБ.
MAX_SIZE = 20 * 1024 * 1024
# Время жизни записи во входящих: 10 минут.
TTL_SECONDS = 10 * 60


def _inbox_dir(root: Path | None = None) -> Path:
    """Папка входящих: ``root/'inbox'`` (по умолчанию ``config.data_dir()``)."""
    base = Path(root) if root is not None else config.data_dir()
    d = base / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _norm(path: str) -> str:
    """Нормализованный абсолютный путь для сравнения записей."""
    try:
        # resolve() убирает ".." и приводит регистр/формат к каноническому.
        return str(Path(path).expanduser().resolve())
    except (OSError, ValueError, RuntimeError):
        # Если resolve не удался — сравниваем по абсолютному пути как есть.
        return str(Path(path).expanduser().absolute())


def _file_ok(path: str) -> bool:
    """Повторная проверка файла: существует, это файл, расширение и размер."""
    try:
        p = Path(path)
    except (OSError, ValueError, TypeError):
        return False
    try:
        if not p.is_file():
            return False
        # Расширение сравниваем без учёта регистра.
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            return False
        if p.stat().st_size > MAX_SIZE:
            return False
    except OSError:
        return False
    return True


def push(path: str, root: Path | None = None) -> bool:
    """Положить путь к файлу во входящие.

    Проверяет файл и пишет json-файл ``{path, ts}`` с уникальным именем.
    Возвращает True при успехе, False если файл не подходит.
    """
    if not _file_ok(path):
        return False
    d = _inbox_dir(root)
    # Уникальное имя, чтобы два процесса не перезаписали друг друга.
    name = f"{time.time_ns()}-{uuid.uuid4().hex}.json"
    payload = {"path": _norm(path), "ts": time.time()}
    try:
        (d / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return False
    return True


def _read_entry(fp: Path) -> dict | None:
    """Прочитать одну запись; битые файлы — None (вызывающий их удаляет)."""
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("path"), str) or not isinstance(data.get("ts"), (int, float)):
        return None
    return data


def take(root: Path | None = None) -> list[str]:
    """Забрать пути из входящих и удалить записи.

    Возвращает пути не старше 10 минут, файл перепроверяется,
    дубликаты убираются (первое вхождение по времени записи).
    """
    d = _inbox_dir(root)
    now = time.time()
    try:
        files = sorted(d.glob("*.json"))
    except OSError:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for fp in files:
        entry = _read_entry(fp)
        if entry is None:
            # Битый файл — удаляем, чтобы не копился мусор.
            try:
                fp.unlink(missing_ok=True)
            except OSError:
                pass
            continue
        stored = entry["path"]
        ts = float(entry["ts"])
        expired = (now - ts) > TTL_SECONDS
        if expired or not _file_ok(stored):
            # Устаревшие и невалидные записи удаляем и не возвращаем.
            try:
                fp.unlink(missing_ok=True)
            except OSError:
                pass
            continue
        key = _norm(stored)
        if key not in seen:
            seen.add(key)
            out.append(stored)
        # Использованные записи удаляем в любом случае.
        try:
            fp.unlink(missing_ok=True)
        except OSError:
            pass
    return out


def is_allowed(path: str, root: Path | None = None) -> bool:
    """True, только если путь сейчас лежит в живых входящих.

    Проверяет неистёкшие записи и сам файл, ничего не удаляет.
    """
    d = _inbox_dir(root)
    now = time.time()
    want = _norm(path)
    try:
        files = d.glob("*.json")
    except OSError:
        return False
    for fp in files:
        entry = _read_entry(fp)
        if entry is None:
            continue
        try:
            ts = float(entry["ts"])
        except (TypeError, ValueError):
            continue
        if (now - ts) > TTL_SECONDS:
            continue
        if _norm(entry["path"]) != want:
            continue
        # Путь заявлен — убеждаемся, что файл до сих пор подходит.
        if _file_ok(entry["path"]):
            return True
    return False
