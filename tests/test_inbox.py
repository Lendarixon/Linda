# -*- coding: utf-8 -*-
"""Тесты входящих: расширения, размер, устаревание, дубликаты, is_allowed."""
import json
import time

from linda_desktop import config, inbox


def _mk(tmp_path, name, size=10):
    """Создать файл с заданным именем и размером, вернуть путь строкой."""
    p = tmp_path / name
    p.write_bytes(b"x" * size)
    return str(p)


def test_allowed_extensions(repo, tmp_path):
    """Разрешённые расширения кладутся и забираются."""
    for ext in (".docx", ".pdf", ".txt", ".md"):
        f = _mk(tmp_path, f"ok{ext}")
        assert inbox.push(f) is True
        assert inbox.is_allowed(f) is True
    got = inbox.take()
    assert len(got) == 4
    # Второй забор пуст — записи удалены.
    assert inbox.take() == []


def test_allowed_uppercase(repo, tmp_path):
    """Расширение сравнивается без учёта регистра."""
    f = _mk(tmp_path, "upper.DOCX")
    assert inbox.push(f) is True
    assert inbox.take() != []


def test_forbidden(repo, tmp_path):
    """Запрещённые расширения, папка и отсутствующий файл отклоняются."""
    bad_exe = _mk(tmp_path, "bad.exe")
    bad_noext = _mk(tmp_path, "noext")
    assert inbox.push(bad_exe) is False
    assert inbox.push(bad_noext) is False
    assert inbox.push(str(tmp_path / "missing.txt")) is False
    assert inbox.push(str(tmp_path)) is False  # папка — не файл
    assert inbox.is_allowed(bad_exe) is False
    assert inbox.take() == []


def test_size_limit(repo, tmp_path, monkeypatch):
    """Файлы больше лимита отклоняются (лимит — 20 МБ)."""
    assert inbox.MAX_SIZE == 20 * 1024 * 1024
    # Уменьшаем лимит, чтобы не писать 20 МБ на диск.
    monkeypatch.setattr(inbox, "MAX_SIZE", 10)
    assert inbox.push(_mk(tmp_path, "small.txt", size=10)) is True
    assert inbox.push(_mk(tmp_path, "big.txt", size=11)) is False


def test_expired_ignored(repo, tmp_path):
    """Записи старше 10 минут не возвращаются и чистятся."""
    f = _mk(tmp_path, "old.txt")
    assert inbox.push(f) is True
    d = config.data_dir() / "inbox"
    (fp,) = list(d.glob("*.json"))
    # Состариваем запись на 11 минут.
    data = json.loads(fp.read_text(encoding="utf-8"))
    data["ts"] = time.time() - 11 * 60
    fp.write_text(json.dumps(data), encoding="utf-8")
    assert inbox.is_allowed(f) is False
    assert inbox.take() == []
    # Устаревшая запись удалена.
    assert list(d.glob("*.json")) == []


def test_duplicates_collapsed(repo, tmp_path):
    """Дубликаты одного пути возвращаются один раз."""
    f = _mk(tmp_path, "dup.txt")
    assert inbox.push(f) is True
    assert inbox.push(f) is True
    got = inbox.take()
    assert got == [inbox._norm(f)]


def test_is_allowed_strict(repo, tmp_path):
    """Чужой путь запрещён; после забора или удаления файла — тоже."""
    f = _mk(tmp_path, "a.txt")
    other = _mk(tmp_path, "b.txt")
    assert inbox.is_allowed(f) is False  # ещё не положен
    assert inbox.push(f) is True
    assert inbox.is_allowed(f) is True
    assert inbox.is_allowed(other) is False  # произвольный файл
    assert inbox.is_allowed(str(tmp_path / "ghost.txt")) is False
    assert inbox.take() != []
    assert inbox.is_allowed(f) is False  # запись уже забрана
    # Положен заново, но файл удалён — снова запрещено.
    assert inbox.push(f) is True
    import os

    os.remove(f)
    assert inbox.is_allowed(f) is False
    assert inbox.take() == []


def test_take_rerechecks_file(repo, tmp_path):
    """Удалённый после push файл не возвращается."""
    f = _mk(tmp_path, "gone.pdf")
    assert inbox.push(f) is True
    import os

    os.remove(f)
    assert inbox.take() == []


def test_explicit_root(tmp_path):
    """Явный root пишет в root/'inbox', а не в data_dir."""
    root = tmp_path / "custom"
    f = _mk(tmp_path, "c.md")
    assert inbox.push(f, root=root) is True
    assert inbox.is_allowed(f, root=root) is True
    assert (root / "inbox").is_dir()
    assert inbox.take(root=root) == [inbox._norm(f)]
