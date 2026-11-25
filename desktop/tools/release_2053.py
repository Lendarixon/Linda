# -*- coding: utf-8 -*-
"""Сборка выпуска 2.0.5.3 (исправления после переименования: краткий PDF, размеры в установщике, язык подсказки, значок в отчётах).
Модели не менялись (1.3.4). Иконка exe, плитки Store и файлы бренда — как в release_2052.py.
    python tools/release_2053.py bump | build | manifest
Публикация - tools/publish_2053.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_2052  # noqa: E402,F401  (настраивает release_2051: иконка exe, плитки Store, assets)
import release_2051 as r  # noqa: E402

r.VER, r.STORE_VER = "2.0.5.3", "2.0.5003.0"
r.BUILD = r.DESK / "Linda_build_2053"
r.URL = f"https://github.com/Lendarixon/Linda/releases/download/v{r.VER}/Linda-Setup.exe"
r.CHANGED = []
r.ENTRY = {"version": r.VER, "date": "2026-10-11",
 "title": {"ru": "Исправления после переименования", "en": "Fixes after the rename", "pl": "Poprawki po zmianie nazwy"},
 "notes": {
  "ru": "• Подсказки при первом запуске показываются на языке интерфейса (раньше всегда по-русски).\n• В заголовке отчётов (PDF и HTML) появился значок Linda; краткий PDF-отчёт больше не пишет старое название.\n• Установщик показывает правильный размер Linda Loupe — около 0,3 ГБ.\n• Модели, вердикты и ключи лицензий не изменились.",
  "en": "• First-run tips now use the interface language (they were always in Russian).\n• Reports (PDF and HTML) show the Linda mark in the header; the short PDF report no longer prints the old name.\n• The installer shows the correct Linda Loupe size, about 0.3 GB.\n• Models, verdicts and licence keys are unchanged.",
  "pl": "• Wskazówki przy pierwszym uruchomieniu są w języku interfejsu (wcześniej zawsze po rosyjsku).\n• Raporty (PDF i HTML) mają znak Linda w nagłówku; krótki raport PDF nie pokazuje już starej nazwy.\n• Instalator pokazuje poprawny rozmiar Linda Loupe — ok. 0,3 GB.\n• Modele, werdykty i klucze licencyjne bez zmian."}}

if __name__ == "__main__":
    {"bump": r.bump, "build": r.build, "manifest": r.manifest}[sys.argv[1]]()
