# Разрешение незавершённого merge `feat/style` → `rc/2.4`

Репозиторий: `D:/Linda_2100_Dev`, ветка `rc/2.4`.
MERGE_HEAD был `02dec83` (`feat/style`), merge base — `e1f6ffc` (baseline 2026-11-20).
Итоговый коммит: **`9a559c5`** `Merge branch 'feat/style' into rc/2.4`.
Push не выполнялся, GPU-задачи не запускались, worktree-ы `D:/Linda_wt_*` не изменялись, `qa_models` не тронут.

## 1. В чём был конфликт

Конфликт был **только в одном файле** — `web/index.html` (статус `UU`). Остальные 7 файлов
(`app.py`, `trace_corpora.py`, `cabinet.html`, `web/i18n/{en,pl,ru}.json`, `tests/test_trace_corpora_api.py`)
git смёржил автоматически и корректно — обе стороны присутствуют (проверено: `compare_corpus`,
`MDS Dim`, `tr_corpora` в `cabinet.html`; `trace_corpora_*` роуты в `app.py`).

Причина «конфликта на весь файл» (маркеры на строках 1 / 2233 / 3163 / 5395 / 6325) — **перевод строк**:

| версия | байт | CRLF | LF-строк |
|---|---|---|---|
| `e1f6ffc` (base) | 337 102 | 0 | 3161 |
| `9e83fa8` (rc/2.4, «ours») | 337 913 | 0 | 3161 |
| `02dec83` (feat/style, «theirs») | 342 985 | 3161 | 3161 |

`feat/style` пересохранил файл в CRLF. `core.autocrlf=false`, `.gitattributes` нет → git увидел
«переписаны все 3161 строк» и выдал конфликт на весь файл, хотя содержательно различие было одно.

Сравнение после нормализации `\r\n` → `\n` показало: **между «ours» и «theirs» отличается ровно
одна строка — № 2622**, а именно блоб встроенного словаря `window.LINDA_I18N`. Весь остальной
HTML/JS идентичен (включая уникальные фичи обеих сторон).

По этой строке:

| версия | ключей en | чего не хватало |
|---|---|---|
| base `e1f6ffc` | 725 | 23 ключа |
| ours `9e83fa8` | 729 | 19 ключей (все `tr_*` от feat/style) |
| theirs `02dec83` | 744 | 4 ключа: `cmp_add_files`, `cmp_clear_files`, `cmp_drop_many`, `cmp_scope_added` (из fix/import) |
| `web/i18n/en.json` (после авто-мёржа) | **748** | — |

То есть **обе** стороны конфликта были неполными: ea0644a синхронизировал только 4 `cmp_*`-ключа,
feat/style — только 19 `tr_*`. Ни один из вариантов не совпадал с JSON-источником.

## 2. Как разрешено

Выбран не «ours» и не «theirs», а регенерация словаря (это ровно то, что делает
`tools/sync_web_i18n.py` и чего требует `tests/test_ui_localization_contract.py`):

1. Тело файла взято с стороны `rc/2.4` (LF, 3161 строка) — CRLF-конверсию feat/style не сохранял,
   чтобы не устроить шумовой diff на весь файл; содержимое вне словаря у сторон идентично.
2. Блок `window.LINDA_I18N` целиком перегенерирован из `web/i18n/{en,pl,ru}.json`
   (`json.dumps(..., ensure_ascii=False, separators=(',',':'))`), т.е. 748 ключей × 3 языка.

Итог: сохранены **и** 19 `tr_*`-ключей Trace UI (feat/style), **и** 4 `cmp_*`-ключа импорта
(fix/import), плюс всё, что было в base. Потерь нет ни с одной стороны.

Проверки после разрешения:
- маркеров конфликта в `web/index.html` / `web/cabinet.html` нет (единственное совпадение с `=======` —
  строка 2232, это литерал-разделитель внутри JS-шаблона экспорта промпта, не маркер git);
- `embedded[lang] == json.load(web/i18n/<lang>.json)` — **True** для en/pl/ru, по 748 ключей.

## 3. Тесты

venv: `C:/Users/ninja/Desktop/детектор/.venv/Scripts/python.exe` (Python 3.13.14, pytest 9.1.1).
`PYTHONPATH`/`PYTHONHOME` сняты, `LINDA_HOME`/`LINDA_MODELS_HOME` указывают на scratch-каталог
под `%LOCALAPPDATA%/hermes/cache/scratch`, `qa_models` не использовался.

**Целевые тесты (до коммита):**

```
tests/test_web_js_syntax.py tests/test_ui_localization_contract.py
tests/test_trace_corpora_api.py tests/test_import_fixes.py
→ 11 passed
```

**Полный набор (`pytest tests -q`), после мёржа (9a559c5):**

```
12 failed, 574 passed  (139.68 s)
```

**Контрольный прогон на дереве ДО мёржа** (временный worktree на `9e83fa8`, тот же venv,
тот же scratch-окружение, `installer/` скопирован, т.к. он gitignored и отсутствует в worktree):

```
12 failed, 574 passed  (136.48 s)
```

Списки падающих тестов **совпадают дословно** (12 из 12) — новых падений нет:

- `test_enterprise_review.py`: `test_download_reserved_before_thread_can_start`,
  `test_installer_flags_are_invisible_and_do_not_reboot`,
  `test_staged_installer_rechecked_before_execution`
- `test_license_api.py::test_download_through_api_and_settings`
- `test_restart_draft.py::test_restart_draft_write_failure_keeps_app_running`
- `test_store_package.py::test_real_windows_process_is_unpacked`
- `test_update_restart.py`: `test_staged_installer_newer_found_stale_removed`,
  `test_restart_launches_staged_installer`,
  `test_dev_rejects_production_channel_even_with_valid_signature`,
  `test_dev_accepts_only_its_signed_app_identity`
- `test_updater.py`: `test_app_required_and_installer_info`, `test_installer_hash_checked`

Все 12 — **pre-existing**, ни один не связан с мёржем: это окружение обновлятора/Store/установщика
(`linda_desktop.updater.UpdateError: Application updates are managed by Microsoft Store / Windows
package deployment` и родственные). Совпадает с оценкой APP_VERIFY.md («~12 pre-existing, updater/
store/installer env»).

Отдельно: `test_startup_2100::test_installer_language_configuration`, который в worktree-ах падал
из-за отсутствия gitignored `installer/`, в основном дереве **проходит** — `installer/` на месте.

## 4. Состояние

- `web/index.html` — 0 маркеров конфликта, `window.LINDA_I18N` == `web/i18n/*.json` (748 ключей × 3).
- `MERGE_HEAD` отсутствует, merge завершён коммитом `9a559c5`.
- `git status` — чисто (все изменения закоммичены).
- Временный worktree `.verify_wt_base` удалён; `git worktree list` содержит только исходные
  `D:/Linda_2100_Dev` + 4 `D:/Linda_wt_*`.
- Открытые (не блокирующие, унаследованы) замечания из ночных отчётов: двойная эмиссия слов на
  slide-PDF (PACKS/IMPORT отчёт), нет встроенного польского академического корпуса в Trace.
