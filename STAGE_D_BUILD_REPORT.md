# Stage D — локальная сборка Linda 2.4.0.0 (20.11.2026)

Статус: **OK**. Собрано локально, ничего не опубликовано: нет push, нет `publish_*.py`,
нет Store/MSIX, нет подписи манифеста, feed обновлений не менялся, старые сборки не тронуты.

Ветка `rc/2.4`, база сборки — готовое приложение `C:/Users/ninja/Desktop/Linda_2.3.0.2/app`.
Артефакты: `C:/Users/ninja/Desktop/Linda_2.4.0.0/` (новая папка, `Linda_2.3.0.2` осталась как была).

## 1. Что изменено в дереве

| Файл | Изменение |
|---|---|
| `linda_desktop/__init__.py` | `__version__` 2.3.0.2 → **2.4.0.0** |
| `CHANGELOG.json` (gitignored) + `linda_desktop/data/CHANGELOG.json` (tracked) | новая запись 2.4.0.0 с `title`/`notes` на **en/pl/ru** (тот же формат, что у предыдущих 35 записей; файл после вставки парсится как JSON, отступы/порядок сохранены) |
| `tools/repack_exe.py` | в `EXTRA_MODULES` добавлены `linda_desktop.trace_corpora` и `linda_pro.segmenter` (см. §5 — без этого фичи 2.4.0.0 не попадали в exe) |
| `tools/release_2400.py` | новый скрипт локальной сборки (адаптация `release_2302.py` под 2.4.0.0) |
| `tools/qa_smoke_2400.py` | новый QA smoke на реальном exe (адаптация `qa_smoke_2302.py`) |
| `installer/linda.iss` | `AppVersion` 2.4.0.0 (файл gitignored — правится локально, коммита нет) |

Grep по `2.3.0.2` в дереве: остались только исторические файлы (`OPENCODE_RELEASE_2302.md`,
`tools/release_2302.py`, `build_store_2302.py`, `publish_2302.py`, `work/_bump2302_*.py`,
`qa_smoke_2302.py`, первая запись CHANGELOG) — это летопись прошлого релиза, не версии
текущей сборки, поэтому не трогались. Никаких других «живых» версионных констант нет:
`config.APP_VERSION` берётся из `__version__`.

## 2. Тесты

`pytest tests -q`, venv `C:/Users/ninja/Desktop/детектор/.venv/Scripts/python.exe`
(Python 3.13.14), `PYTHONPATH`/`PYTHONHOME` сняты, `LINDA_HOME`/`LINDA_MODELS_HOME` —
scratch-каталог под `%LOCALAPPDATA%/hermes/cache/scratch`, `qa_models` не изменялся.

```
12 failed, 574 passed, 1 warning in 136.03s
```

Ровно база 574/12, список падающих совпадает дословно (pre-existing, env updater/Store/installer):

- `test_enterprise_review.py::test_download_reserved_before_thread_can_start`
- `test_enterprise_review.py::test_installer_flags_are_invisible_and_do_not_reboot`
- `test_enterprise_review.py::test_staged_installer_rechecked_before_execution`
- `test_license_api.py::test_download_through_api_and_settings`
- `test_restart_draft.py::test_restart_draft_write_failure_keeps_app_running`
- `test_store_package.py::test_real_windows_process_is_unpacked`
- `test_update_restart.py::test_staged_installer_newer_found_stale_removed`
- `test_update_restart.py::test_restart_launches_staged_installer`
- `test_update_restart.py::test_dev_rejects_production_channel_even_with_valid_signature`
- `test_update_restart.py::test_dev_accepts_only_its_signed_app_identity`
- `test_updater.py::test_app_required_and_installer_info`
- `test_updater.py::test_installer_hash_checked`

Замечание: один прогон дал `11 failed, 575 passed` — `test_license_api::test_download_through_api_and_settings`
флакнул (в изоляции `13 passed`, повторный полный прогон снова 12/574). Это известный
нестабильный updater-тест, а не регрессия; тесты не правились.

## 3. Сборка — команды и коды возврата

```
# 1) python 3.12 (C:/Users/ninja/AppData/Local/Programs/Python/Python312/python.exe)
python tools/release_2400.py
```
Шаги внутри: копирование `_internal` базы → импортная проверка бандла (`-I -S`) →
`tools/repack_exe.py … --entry run_app` → штамп версии → подкладка CHANGELOG →
ISCC `installer/linda.iss` → `SHA256.json`.

| Команда | Код | Время |
|---|---|---|
| `release_2400.py` (полная сборка) | **0** | ~6 мин (копирование 1,3 ГБ + сжатие установщика 116 с) |
| `tools/build_document_parser.py` (пересборка PDF-парсера) | **0** | 14 с |
| `tools/qa_smoke_2400.py` | **0** | ~55 с |

Первые две попытки упали и были исправлены **в скрипте сборки, не в обход**:
1. `_verify_bundle` падала на `RuntimeError: operator torchvision::nms does not exist` —
   глобальный `torchvision` из site-packages 3.12 цеплялся к бандл-торчу. Исправлено
   запуском проверки с `-I -S` (изолированно от глобального site-packages); сам бандл был цел
   (`transformers 4.57.6 / peft 0.17.1 / torch 2.14.1+cpu`).
2. Установщик собирался, но QA показал ratio 1.72 на PDF — см. §5.

## 4. Артефакты

| Артефакт | Размер | SHA-256 |
|---|---|---|
| `app/Linda-Pro.exe` | 79 027 572 | `47c8e748b5f5a6a0dacfaa95873b4dacc3f83f21f81ff4608467ef9d7f31f159` |
| `Linda-Setup.exe` | 509 078 021 | `e609cb4fa3919ec34520e497b4e9ca281759f3f2afdee5b986fbf5b338fcb2c6` |

`app/` целиком — 1,3 ГБ. `SHA256.json` лежит рядом и содержит оба хеша; рядом с каждым
файлом также `*.sha256`.

Проверено на самом exe:
- ресурс версии `FileVersion 2.4.0.0 / ProductVersion 2.4.0.0` (чтение через `version.dll`);
- в PYZ реального exe `linda_desktop.__version__ == "2.4.0.0"`, модули
  `linda_desktop.trace_corpora` и `linda_pro.segmenter` присутствуют;
- `_internal/linda_desktop/data/CHANGELOG.json` содержит запись 2.4.0.0;
- `_internal/assets/document-parser/Linda-Document-Worker.exe` побайтово равен свежесобранному;
- установщик собирался из `installer/linda.iss` с `AppVersion=2.4.0.0` и
  `LicenseFile=installer/EULA.txt` (11 строк, sha256 `921e73ad…033039`).

## 5. Найдено и исправлено по ходу (важно для релиза)

**(а) Фичи 2.4.0.0 не попадали в exe.** `tools/repack_exe.py` пересобирает только PYZ и
добавляет в него модули из `EXTRA_MODULES`. В rc/2.4 появились два модуля, которых нет в
базовом 2.3.0.2 и которых не было в allowlist: `linda_desktop.trace_corpora` (SVG-графики,
сравнение с корпусом, конструктор корпусов — импортируется лениво из `app.py`) и
`linda_pro.segmenter` (opt-in сегментер из `engine.py`). Без правки exe падал бы на этих
фичах `ImportError` при первом обращении. Добавлены в allowlist, наличие в собранном PYZ
проверено; QA дергает `/api/trace/corpora` на реальном exe — отвечает.

**(б) Фикс импорта PDF не доезжал до приложения.** В frozen-режиме PDF/DOCX парсит не
PYZ, а отдельный предсобранный `assets/document-parser/Linda-Document-Worker.exe`. В дереве
он был от 24.10 и **побайтово совпадал с 2.3.0.2** — то есть `fix/import` (дедупликация
слоёв/XObject) в сборке отсутствовал, хотя тесты на исходниках зелёные. Пересобран
`tools/build_document_parser.py` из текущих `document_worker.py`/`document_formats.py`;
новый exe на тестовом slide-PDF даёт 72 слова против 124 у старого. После пересборки
приложения QA показывает ratio 1.0.

**(в) Том D: не поддерживает integrity level** — `icacls /setintegritylevel` на D: возвращает
«Отказано в доступе» даже владельцу, на C: проходит. Из-за этого LPAC-песочница парсера
не поднимается, если `LINDA_HOME` на D:, и импорт документов падает с
«Document sandbox integrity could not be enabled». Реальная установка ставит профиль в
`%LOCALAPPDATA%` (C:), поэтому это ограничение QA-окружения, а не продукта; QA-профиль
перенесён на C: (см. `PROFILE_ROOT` в `qa_smoke_2400.py`). Стоит знать: пользователь,
перенёсший профиль на D:, получит именно эту ошибку импорта.

**(г) `repack_exe.py` / `__init__.py` имели смешанные переводы строк** — после правки
Python-редактором файлы стали CRLF, из-за чего diff раздувался на 325 строк. Возвращены
к LF; итоговый diff — 3 строки в `repack_exe.py` и 1 в `__init__.py`.

## 6. QA smoke на реальном exe

`python tools/qa_smoke_2400.py` → **exit 0**, отчёт `evidence/real-exe-2400/SMOKE_2400.json`
(gitignored), лог `evidence/real-exe-2400/smoke.log`.

Изолированный профиль на C:, `LINDA_MODELS_HOME` → `qa_models` (только чтение), `--no-ui`,
cpu, lite. Что проверено на собранном EXE:

| Проверка | Результат |
|---|---|
| Запуск, `/` отдаёт страницу | ok, в HTML `2.4.0.0`, `id="lindaStartup"` |
| i18n `/api/i18n/{en,pl,ru}` | по **748** ключей в каждом, ключи hum_/pack_/tr_/st_ на месте |
| `/api/packs/status` | ok (`humanizer`, `trace`, `licensed`, `job`) |
| `/api/trace/corpora` (новый модуль) | ok: `builtin_academic_en`, `builtin_academic_ru` |
| Готовность моделей | `ready`, device `cpu` |
| detect EN | `p_ai 0.90`, verdict `ai`, 7 предложений, 0.9 с |
| detect PL | `p_ai 0.5856`, verdict `uncertain`, 6 предложений, 0.16 с |
| detect RU | `p_ai 0.9312`, verdict `ai`, 6 предложений, 0.14 с |
| Импорт PDF, чистый slide-документ | 72 слова |
| Импорт PDF, тот же текст в двух слоях | 72 слова |
| **double-emission ratio** | **1.000** (было 1.722 на сборке со старым парсером) |
| `/api/changelog` | `app_version 2.4.0.0`, записи `2.4.0.0, 2.3.0.2, 2.3.0.1` |

Оговорки QA:
- detect PL даёт `uncertain` (0.586) на нейтральном бытовом тексте — это ожидаемое поведение
  порогов для человека-текста, не ошибка сборки; проверялось, что язык определён как `pl`.
- Обновление через локальный манифест НЕ проверялось: по решению судьи feed не меняется,
  подпись манифеста не делается, а `updater` в этом окружении и так известные 12 падений.
- Проверка Trace UI в живом окне (не headless) не делалась — QA headless через API;
  скриншотная проверка UI остаётся за verifier-этапом.

## 7. Границы выполненного

- НЕ публиковалось: нет push, нет `publish_*.py`, нет Store/MSIX, нет подписи манифеста.
- `Linda_2.3.0.2` не тронута (проверено: файлы на месте).
- `qa_models` только читался; `D:/Linda_wt_*` не трогались; GPU не использовался.
- Тесты не правились.
- `CHANGELOG.json` в корне и `installer/` — gitignored по `.gitignore`; версия в корневом
  CHANGELOG и `AppVersion` в .iss живут только локально (в коммит попал tracked-дубль
  `linda_desktop/data/CHANGELOG.json`).
