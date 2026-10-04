# -*- coding: utf-8 -*-
"""Задачи D (персонализация) и E (i18n): настройки интерфейса и переводы."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from linda_desktop import i18n as ui18n
from linda_desktop.app import Core, create_app
from linda_desktop.engine import DEFAULT_SETTINGS, load_settings

TOKEN = "t0k"
ROOT = Path(__file__).resolve().parents[1]


def make_client():
    return TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})


def test_settings_defaults_have_ui_prefs(repo):
    s = load_settings()
    for k in ("theme", "accent", "density", "font_scale", "radius", "sidebar", "language"):
        assert k in s, k
        assert s[k] == DEFAULT_SETTINGS[k]


def test_settings_accepts_ui_prefs(repo):
    c = make_client()
    r = c.post("/api/settings", json={"theme": "light", "accent": "teal", "density": "compact",
                                       "font_scale": 110, "radius": "round", "sidebar": "right", "language": "pl"})
    assert r.status_code == 200
    s = r.json()["settings"]
    assert (s["theme"], s["accent"], s["density"], s["font_scale"], s["radius"], s["sidebar"], s["language"]) == \
        ("light", "teal", "compact", 110, "round", "right", "pl")
    assert "light" in c.get("/").text  # страница отдаётся


def test_settings_rejects_bad_ui_prefs(repo):
    c = make_client()
    c.post("/api/settings", json={"theme": "dark", "font_scale": 100, "language": "ru"})
    r = c.post("/api/settings", json={"theme": "neon", "accent": "", "font_scale": 999,
                                       "radius": "oval", "sidebar": "top", "language": "de"})
    s = r.json()["settings"]
    assert (s["theme"], s["font_scale"], s["language"]) == ("dark", 100, "ru")


def test_backend_errors_follow_language(repo):
    c = make_client()
    bad = {"file": ("a.exe", b"MZ", "application/octet-stream")}
    ru = c.post("/api/upload", files=bad).json()["detail"]
    assert "прочитать" in ru  # дефолт ru
    c.post("/api/settings", json={"language": "en"})
    en = c.post("/api/upload", files=bad).json()["detail"]
    assert "could not read" in en
    assert c.post("/api/detect", json={"text": "word " * 100}).status_code == 409
    assert "not installed yet" in c.post("/api/detect", json={"text": "word " * 100}).json()["detail"]


def test_i18n_endpoint(repo):
    c = make_client()
    for lang in ("ru", "pl", "en"):
        d = c.get("/api/i18n/" + lang).json()
        assert d["lang"] == lang and len(d["strings"]) > 300
    assert c.get("/api/i18n/xx").json()["lang"] == "ru"  # фолбэк
    assert ui18n.tr("no_such_key", "pl") == "no_such_key"
    assert ui18n.resolve_lang({"language": "de"}) == "ru"


def test_dictionaries_parity():
    dicts = {l: json.loads((ROOT / "web" / "i18n" / (l + ".json")).read_text(encoding="utf-8")) for l in ("ru", "pl", "en")}
    assert set(dicts["ru"]) == set(dicts["pl"]) == set(dicts["en"])
