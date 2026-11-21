# -*- coding: utf-8 -*-
"""Живой счётчик слов/символов (web/index.html собирается из tools/make_web.py).

Регрессия: render() опрашивает /api/status каждые 0.8-3 с и каждый раз зовёт
LINDA_applyI18n(), которая перерисовывала #charCounter из замороженных
data-c="0" data-w="0" — счётчик вечно показывал 0. Фикс: updateCounter()
пишет живые значения в dataset, а событие linda-i18n перерисовывает счётчик
после каждой смены языка/опроса.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def test_counter_handler_updates_dataset():
    assert "function updateCounter" in HTML
    assert "charCounter.dataset.c" in HTML
    assert "charCounter.dataset.w" in HTML
    assert "textInput.addEventListener('input', updateCounter)" in HTML


def test_counter_rerenders_on_language_change():
    assert "addEventListener('linda-i18n', updateCounter)" in HTML


def test_counter_words_formula():
    assert "t.trim() ? t.trim().split(/\\s+/).length : 0" in HTML


def test_counter_key_has_placeholders_in_all_langs():
    for lang in ("ru", "pl", "en"):
        d = json.loads((ROOT / "web" / "i18n" / (lang + ".json")).read_text(encoding="utf-8"))
        assert "{c}" in d["ui_counter"] and "{w}" in d["ui_counter"], lang


def test_settings_sections_full_width_in_order():
    body = HTML[HTML.index('id="lpSet"'):HTML.index('id="lpSetSave"')]
    secs = re.findall(r'data-i18n="(set_appearance|set_language|set_sec_device|set_sec_updates)"', body)
    assert secs == ["set_appearance", "set_language", "set_sec_device", "set_sec_updates"], secs
    assert "lp-sec{grid-column:1/-1" in HTML.replace(" ", "")
    assert body.index("set_proc") < body.index("set_gpu_num")  # Чем считать и видеокарта рядом
    assert 'data-i18n="set_gpu_hint"' in body
