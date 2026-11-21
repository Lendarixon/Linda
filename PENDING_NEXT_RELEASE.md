# Историческая очередь от 18.10.2026 — включена в локальную сборку 2.1.0.0

23.10.2026: перечисленные правки вошли в EXE/установщик/MSIX 2.1.0.0 и проверены. Публичный канал обновления не менялся. Актуальное состояние — `HANDOFF.md` и `C:\Users\ninja\Desktop\Linda_2.1.0.0\RELEASE_RESULT.md`. Текст ниже оставлен как история.

Если ты делаешь следующее обновление приложения — эти правки уже лежат в исходниках, но в собранный EXE/установщик/Store они не попали.

## Что изменено в `web/index.html`
1. Предупреждение о коротком тексте под полем ввода (`#preflightWarning`) — жирным (`<strong>`) для сообщений «Very short text…» и «Short text…» (EN/PL/RU, ключи `below` и `short` в `PREFLIGHT_COPY`). Замечание про структуру/списки (`structure`) остаётся обычным.
2. Предупреждение в блоке вердикта `#shortWarn` — жирным (CSS `#shortWarn{font-weight:700}` после правила `.short-warn`).
Проверено: `pytest tests -k "ui or i18n or preflight"` — 130 passed (python из `Linda_desktop\.venv`). Сборка и ручная проверка в живом EXE НЕ делались.

## Что делать
- Прогнать полный набор тестов, пересобрать (`tools/build_app.py`, потом установщик, манифест, Store — см. `docs/COMMERCIAL.md` §4), записать пункт в `CHANGELOG.json` (копия в `linda_desktop/data/`) и поднять версию.
- Жёлтое предупреждение в приложении осталось ПОД полем ввода. В онлайн-демо владелец попросил поставить его НАД полем — для приложения не просил; спросить, нужно ли так же.

## Связанное (онлайн-демо и стилизация, 18.10.2026)
Описано в `docs/HANDOFF.md` (раздел «18.10.2026») и в `CLAUDE.md` («Демо 18.10.2026»). В приложение стилизатор не встроен: модели 4B/0.6B с PyTorch в ONNX-клиент не помещаются, решение (локальный сервер или облако) за владельцем.


## SpeedOnnx: bos/eos/pad from speed_args.json (Linda 1.4 work)
- `linda_pro/voters.py`: `SpeedOnnx` reads optional `bos_id`/`eos_id`/`pad_id` from `speed_args.json` (needed by mmBERT students; old packs unchanged, max score diff 0.0 on 40 texts). Backup: `voters.py.bak-pre-mmbert`.
- Tests: 510 passed; the 35 failures (updater, store package, fpdf) fail the same way with the old file in the research venv (missing deps).
