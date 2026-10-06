# -*- coding: utf-8 -*-
"""Диагностический архив для письма в поддержку: ZIP собирается в памяти.

Внутри system.json (сведения о приложении и настройки без полей с текстом),
logs/<имя>.txt — последние 300 строк каждого лога из info['log_files'] и
README.txt с описанием содержимого. Тексты проверок и история в архив не
попадают. В логах путь домашней папки заменяется на %USERPROFILE%, отсутствующие
и нечитаемые файлы пропускаются. Итоговый ZIP не больше MAX_ZIP_BYTES: при
необходимости логи обрезаются с головы, свежие строки хвоста остаются.
Только стандартная библиотека: zipfile, json, io.
"""
from __future__ import annotations

import io
import json
import os
import zipfile

MAX_ZIP_BYTES = 2 * 1024 * 1024   # жёсткий предел размера вложения
MAX_LOG_LINES = 300               # сколько последних строк берём из каждого лога
_TAIL_BYTES = 4 * 1024 * 1024     # читаем только хвост файла: гигабайтный лог не роняет память
_TEXT_LIMIT = 64                  # строка длиннее — это пользовательский текст, а не настройка
# Имена полей настроек, которые по определению содержат текст пользователя.
_TEXT_KEYS = frozenset({'text', 'prompt', 'content', 'draft', 'note', 'comment',
                        'reply', 'snippet', 'excerpt', 'message', 'body'})

README = (
    "Linda-Pro — архив диагностики для письма в поддержку.\n"
    "\n"
    "Что внутри:\n"
    "  system.json — версия приложения, версия весов, устройство, список видеокарт\n"
    "                и настройки (без полей с текстом);\n"
    "  logs/       — последние 300 строк каждого лога, путь домашней папки\n"
    "                заменён на %USERPROFILE%.\n"
    "\n"
    "Что НЕ включено: тексты проверок, история проверок и любые пользовательские\n"
    "тексты. Архив не больше 2 МБ: при необходимости старые строки логов обрезаются.\n"
)


def _decode(raw: bytes) -> str:
    """UTF-8, а старые логи Windows — cp1251; битые байты не роняют сборку."""
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1251', errors='replace')


def _redact(text: str) -> str:
    """Путь домашней папки -> %USERPROFILE%: личное имя не уезжает в поддержку."""
    home = os.path.expanduser('~')
    return text.replace(home, '%USERPROFILE%') if home and home != '~' else text


def _read_tail(path) -> list[str] | None:
    """Последние MAX_LOG_LINES строк одного лога; None — файла нет или он не читается."""
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - _TAIL_BYTES)
            f.seek(start)
            raw = f.read()
    except (OSError, TypeError, ValueError):  # отсутствие, права, каталог вместо файла
        return None
    lines = _decode(raw).splitlines()
    if start > 0 and lines:
        lines = lines[1:]  # первая строка могла обрезаться при чтении хвоста файла
    return [_redact(line) for line in lines[-MAX_LOG_LINES:]]


def _is_text_key(key) -> bool:
    """Имя поля похоже на поле с текстом: custom_text, prompt, check_note, ..."""
    return any(word.lower() in _TEXT_KEYS for word in str(key).replace('-', '_').split('_'))


def _is_text_value(value) -> bool:
    """Значение похоже на пользовательский текст: длинная строка."""
    return isinstance(value, str) and len(value) > _TEXT_LIMIT


def _scrub(value):
    """Убрать из настроек поля с текстом; рекурсивно проходит словари и списки."""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()
                if not (_is_text_key(k) or _is_text_value(v))}
    if isinstance(value, list):
        return [_scrub(v) for v in value if not _is_text_value(v)]
    return value


def _log_name(path, index: int, used: set) -> str:
    """Имя файла в архиве logs/<имя>.txt; тёзки из разных папок не конфликтуют."""
    name = os.path.basename(str(path)) or 'log_%d' % index
    if not name.lower().endswith('.txt'):
        name += '.txt'
    base, n = name, 1
    while name.lower() in used:
        n += 1
        name = '%d_%s' % (n, base)
    used.add(name.lower())
    return name


def _render(system_json: bytes, logs: list) -> bytes:
    """Собрать ZIP: system.json, logs/*.txt, README.txt."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('system.json', system_json)
        for name, lines in logs:
            z.writestr('logs/' + name, ('\n'.join(lines) + '\n') if lines else '')
        z.writestr('README.txt', README)
    return buf.getvalue()


def build_zip(info: dict) -> bytes:
    """Собрать ZIP в памяти для письма в поддержку.

    info берётся как есть (версия приложения, версия весов, устройство, список
    видеокарт, настройки, log_files — список путей к логам); из настроек убираются
    поля с текстом, отсутствующие и нечитаемые логи пропускаются, итоговый размер
    не превышает MAX_ZIP_BYTES (лишние строки логов обрезаются, свежие остаются).
    Исходный словарь info не изменяется.
    """
    payload = dict(info)
    if isinstance(payload.get('settings'), dict):
        payload['settings'] = _scrub(payload['settings'])
    system_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode('utf-8')

    logs, used = [], set()
    for i, path in enumerate(info.get('log_files') or []):
        lines = _read_tail(path)
        if lines is None:
            continue  # файла нет или он не читается — молча пропускаем
        logs.append([_log_name(path, i, used), lines])

    data = _render(system_json, logs)
    while len(data) > MAX_ZIP_BYTES and logs:
        # Слишком большой: отрезаем половину старых строк каждого лога, хвост свежий сохраняем.
        for entry in logs:
            entry[1] = entry[1][max(1, len(entry[1]) // 2):]
        if all(not lines for _, lines in logs):
            logs.clear()  # и пустые хвосты не влезают — убираем логи совсем
        data = _render(system_json, logs)
    if len(data) > MAX_ZIP_BYTES:  # достигнуть нечем: system.json + README одни больше лимита
        raise ValueError('Диагностика не влезает в %d байт даже без логов' % MAX_ZIP_BYTES)
    return data
