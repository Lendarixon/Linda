# -*- coding: utf-8 -*-
"""Словарь серверных сообщений (detail-строки API) на трёх языках: ru/pl/en.

Фронт показывает `detail` как есть, поэтому язык выбирается по настройкам
пользователя (settings.json: language). Словари фронта лежат в web/i18n/*.json;
этот модуль сначала пробует загрузить их (один источник правды), иначе
использует встроенный минимум, чтобы переводы работали и без web-файлов.
"""
from __future__ import annotations

import json
from pathlib import Path

SUPPORTED = ("ru", "pl", "en")
DEFAULT_LANG = "ru"

# Встроенный минимум (ключи ошибок бэкенда). Полные тексты — в web/i18n/*.json.
_BUILTIN: dict[str, dict[str, str]] = {
    "err_forbidden": {"ru": "запрещено", "pl": "zabronione", "en": "forbidden"},
    "err_cannot_reach": {"ru": "нет связи с сервером обновлений", "pl": "brak połączenia z serwerem aktualizacji", "en": "cannot reach the update server"},
    "err_download_running": {"ru": "загрузка уже идёт", "pl": "pobieranie już trwa", "en": "a download is already running"},
    "err_check_not_found": {"ru": "проверка не найдена", "pl": "nie znaleziono sprawdzenia", "en": "check not found"},
    "err_no_pdf": {"ru": "PDF-библиотека не установлена", "pl": "biblioteka PDF nie jest zainstalowana", "en": "PDF library is not installed"},
    "err_cannot_reach": {"ru": "нет связи с сервером обновлений", "pl": "brak połączenia z serwerem aktualizacji", "en": "cannot reach the update server"},
    "err_download_running": {"ru": "загрузка уже идёт", "pl": "pobieranie już trwa", "en": "a download is already running"},
    "err_app_too_old": {"ru": "эта версия приложения слишком старая для новых моделей; сначала обновите приложение", "pl": "ta wersja aplikacji jest zbyt stara dla nowych modeli; najpierw zaktualizuj aplikację", "en": "this version of the app is too old for the latest models; update the app first"},
    "err_file_too_large": {"ru": "файл слишком большой (максимум 20 МБ)", "pl": "plik jest za duży (maks. 20 MB)", "en": "file is too large (max 20 MB)"},
    "err_could_not_read": {"ru": "не удалось прочитать файл", "pl": "nie można odczytać pliku", "en": "could not read the file"},
    "err_no_text": {"ru": "из файла не извлеклось ни одного слова", "pl": "nie udało się wyodrębnić tekstu z pliku", "en": "no text could be extracted from the file"},
    "err_models_not_installed": {"ru": "файлы моделей ещё не установлены", "pl": "pliki modeli nie są jeszcze zainstalowane", "en": "model files are not installed yet"},
    "err_bad_request": {"ru": "неверный запрос", "pl": "nieprawidłowe żądanie", "en": "bad request"},
    "err_text_min": {"ru": "нужно не меньше %d слов (сейчас %d)", "pl": "potrzeba co najmniej %d słów (obecnie %d)", "en": "at least %d words are needed (now %d)"},
    "err_text_words": {"ru": "нужно %d–%d слов (сейчас %d)", "pl": "potrzeba %d–%d słów (obecnie %d)", "en": "text must be %d-%d words (now %d)"},
    "err_license_required": {"ru": "коммерческая политика: для проверок нужен ключ", "pl": "zasady komercyjne: wymagany jest klucz licencyjny", "en": "commercial policy: a licence key is required"},
    "err_analysis_failed": {"ru": "проверка не удалась", "pl": "analiza nie powiodła się", "en": "analysis failed"},
    "err_not_found": {"ru": "не найдено", "pl": "nie znaleziono", "en": "not found"},
    "err_check_not_found": {"ru": "проверка не найдена", "pl": "nie znaleziono sprawdzenia", "en": "check not found"},
    "err_export_disabled": {"ru": "экспорт отчётов отключён политикой организации", "pl": "eksport raportów wyłączony przez politykę organizacji", "en": "export is disabled by organization policy"},
    "err_no_update": {"ru": "нет доступного обновления приложения", "pl": "brak dostępnej aktualizacji aplikacji", "en": "no application update available"},
    "err_already_downloading": {"ru": "загрузка уже идёт", "pl": "pobieranie już trwa", "en": "already downloading"},
    "err_need_folder": {"ru": "нужен путь к папке", "pl": "potrzebna jest ścieżka do folderu", "en": "bad request: need a folder path"},
    "err_need_check_or_text": {"ru": "нужен check_id или текст с результатом", "pl": "potrzebny jest check_id albo tekst z wynikiem", "en": "bad request: need check_id or text+result"},
    "err_folder_not_allowed": {"ru": "папка запрещена политикой организации", "pl": "folder zabroniony przez politykę organizacji", "en": "folder is not allowed by organization policy"},
    "err_folder_not_found": {"ru": "папка не найдена", "pl": "nie znaleziono folderu", "en": "folder not found"},
    "err_cannot_read_folder": {"ru": "не могу прочитать папку", "pl": "nie można odczytać folderu", "en": "cannot read the folder"},
    "err_pick_two": {"ru": "выберите минимум две проверки", "pl": "wybierz co najmniej dwa sprawdzenia", "en": "pick at least two checks"},
    "err_no_pdf": {"ru": "PDF-библиотека не установлена: откройте HTML-отчёт и используйте Печать → сохранить PDF", "pl": "biblioteka PDF nie jest zainstalowana: otwórz raport HTML i użyj Drukuj → zapisz PDF", "en": "PDF library is not installed: open the HTML report and use Print → save PDF"},
}

_CACHE: dict[str, dict[str, str]] = {}


def _web_dir() -> Path:
    from . import config as _config

    return _config.resource_dir() / "web" / "i18n"


def load_lang(lang: str) -> dict[str, str]:
    """Плоский словарь {ключ: текст} для языка (web/i18n/<lang>.json + встроенные ошибки)."""
    lang = lang if lang in SUPPORTED else DEFAULT_LANG
    if lang in _CACHE:
        return _CACHE[lang]
    merged = {k: v[lang] for k, v in _BUILTIN.items()}
    try:
        p = _web_dir() / f"{lang}.json"
        if p.is_file():
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                merged.update({k: str(v) for k, v in d.items()})
    except Exception:  # noqa: BLE001 — битый словарь не роняет бэкенд
        pass
    _CACHE[lang] = merged
    return merged


def resolve_lang(settings: dict | None) -> str:
    """Язык интерфейса из настроек (ru/pl/en, иначе ru)."""
    lang = (settings or {}).get("language", DEFAULT_LANG)
    return lang if lang in SUPPORTED else DEFAULT_LANG


def tr(key: str, lang: str = DEFAULT_LANG, *args) -> str:
    """Перевод по ключу; при нехватке аргументов форматирования — как есть."""
    text = load_lang(lang).get(key, _BUILTIN.get(key, {}).get(DEFAULT_LANG, key))
    if args:
        try:
            return text % args
        except (TypeError, ValueError):
            return text
    return text
