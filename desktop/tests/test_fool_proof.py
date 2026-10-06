# -*- coding: utf-8 -*-
"""Защита от дурака: двоичный файл под видом .txt, неподдерживаемое письмо, понятные ошибки без имён внутренних исключений."""
import pytest
from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, documents, updater


def test_binary_file_is_not_text():
    with pytest.raises(ValueError):
        documents.extract("x.txt", b"MZ" + bytes([0, 0]) + b"abc" * 100)


def test_encodings_cp1251_and_utf16():
    assert documents.extract("a.txt", "Привет мир".encode("cp1251")) == "Привет мир"
    assert documents.extract("b.txt", ("\ufeff" + "hello").encode("utf-16")) == "hello"


def test_api_unsupported_script_and_friendly_errors(repo, monkeypatch):
    monkeypatch.setattr(updater, "is_complete", lambda: True)
    core = app_mod.Core()
    with TestClient(app_mod.create_app(core, token="t")) as c:
        c.headers["x-linda-token"] = "t"
        r = c.post("/api/detect", json={"text": "الذكاء الاصطناعي " * 40})
        assert r.status_code == 400 and "язык" in r.json()["detail"].lower()
        r = c.post("/api/detect", json={"text": "人工智能技术的快速发展正在深刻地改变着各行各业的运作模式" * 3})
        assert r.status_code == 400
        r = c.post("/api/upload", files={"file": ("broken.docx", b"PK\x03\x04" + b"\x00" * 30, "application/octet-stream")})
        assert r.status_code == 400 and "BadZip" not in r.json()["detail"] and "KeyError" not in r.json()["detail"]
        r = c.post("/api/upload", files={"file": ("fake.txt", b"MZ\x00\x00" + b"x" * 500, "text/plain")})
        assert r.status_code == 400 and "двоичные" in r.json()["detail"]
