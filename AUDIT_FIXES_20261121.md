# AUDIT_FIXES_20261121 — устранение замечаний AUDIT_BACKEND_NEON_PRE_PUB / AUDIT_FRONTEND_NEON_PRE_PUB
Дата: 2026-11-21. Аудит: `AUDIT_BACKEND_NEON_PRE_PUB.md` (night/release-2.5 @ f289cd6). Каждый раздел пишет свой фиксер, дописывая только свой блок в конец файла.

## Fixer B (pack)
Закрывает P1 №3 аудита: «`speed_conformal.json` отсутствует в pack_15_nightly, conformal недоступен в ship-артефакте» (§2, §7).

**1. Где файл ожидается.** `SpeedOnnx.load_conformal()` (`linda_pro/voters.py:432-449`) читает `self.model_dir / "speed_conformal.json"`, где `model_dir` — каталог speed-модели. В паке это `models/linda_speed_131/speed_conformal.json` (рядом с `model.onnx`, `speed_args.json`, `vocab_map.npy`), т.е. `<pack>/models/linda_speed_131/` — совпадает с layout манифеста.

**2. Схема файла.** Парсятся ровно три поля: `bins` (список пар `[lo, hi)` во float, длины = длине `thresholds`), `thresholds` (float ≥ 0, finite), `abstain_margin` (по умолчанию 0.05). Прочие поля игнорируются. Сгенерировано из `tmp/night_20261121/lite_conformal_143.json` (`bin_thresholds[i].thr` + `abstain_margin`), комментарий-поле `source` оставлено для трассировки.

```json
{"bins": [[0,100],[100,300],[300,800],[800,1000000000]],
 "thresholds": [0.8843550800859761, 0.7601844131910936, 0.6696283548720097, 0.8021797627199255],
 "abstain_margin": 0.05,
 "source": "generated from lite_conformal_143.json (...)"}
```

**3. Артефакт и манифест.** `pack_15_nightly/models/linda_speed_131/speed_conformal.json` — 431 B, sha256 `3445f59a4b65226bca237d14c018ce66dd33903ddd864a0f3122d10548e91ee7`. В `manifest.json`: запись в `files` (`path`/`size`/`sha256`), путь добавлен в `per_language.en` (builder-паритет: `build_pack_15.py:106-109` относит `models/linda_speed_131/*` к `en`), `source` дополнен. `schema=1`, `signed=false`, `signature=UNSIGNED-local-no-publish` — не менялись. Ранее путь был в `files`, но отсутствовал в `per_language.en` → расхождение с builder'ом; устранено, `shared_hashes` пересчитан и совпадает.

**4. Проверка манифеста.** `check_manifest_15.py` → **exit 0**: 69 файлов, все sha256/size совпадают, лишних файлов на диске нет, routing байт-идентичен routing_141, 6 schema-2 голов + sidecar консистентны. Дополнительно проверен builder-паритет (`files`, `per_language`, `shared_hashes` пересчитаны независимо — совпадают), т.е. пересборка пака даст тот же манифест.

**5. Eval по файлу из пака (не fallback).** `tmp/night_20261121/lite_conformal_pack_verify.py` берёт пороги **только** из `pack_15_nightly/models/linda_speed_131/speed_conformal.json` через реальный `SpeedOnnx.load_conformal()` и падает с exit 2, если вернулся `None`. Результат (`lite_conformal_pack_verify.json`), конформал применяется только при `backend=="pl"` (как в `routed.py:291`), RU — flat-порог:

| срез | путь | FPR@thr | TPR@thr | abstain |
|---|---|---|---|---|
| test_pl | conformal | **0.00% (0/350)** | 26.86% (94/350) | 44/700 |
| pool_fpr_pl | conformal | 0.00% (0/700) | — | 0 |
| pool_fpr_ru | flat(ref) | 0.00% (0/700) | — | 0 |
| kaggle_human_ru | flat(ref) | 3.40% (22/648) | — | 0 |

5 известных FP: `test_pl` w=43 z=0.816 → human; w=50 z=0.669 → human; w=43 z=0.664 → human; `pool_fpr_pl` w=153 z=0.363 → human; w=248 z=0.499 → human. **5/5 разрешены, 0 AI-вердиктов**, полностью совпадает с `LITE_CONFORMAL_NIGHT.md` (0/350 FPR, 26.86%, abstain 44, kaggle_ru 3.40%).

**Остаётся (не в scope Fixer B):** P1-двойная недостижимость в шипе — `routed.py:291` требует `tier_pref=="speed"` + `backend=="pl"`, а `routing.json` не содержит speed-тира (`manifest.lite.reachable_via_shipped_routing=false`; lite доступен только через `calibration/routing.with_lite.json`). Файл теперь в паке и парсится, но в shipped-routing путь lite по-прежнему не активируется — это решение по routing/тирам, не по артефакту. Также нет теста на интеграцию conformal в `routed.py` (§6 аудита).

## Fixer A (backend security/locks) — commit 316dd2f

**P1 license fail-open** (`licensing.py:238-255`): fail-closed теперь срабатывает и на пустом/отсутствующем `expires_at` (`""`/`null`), не только на truthy; исключение — dev mode (`DEV_INSTALLER_ENABLED`). Тесты: corrupt + empty (`""`, `null`) в `tests/test_backend_review_fixes.py`.

**P1 humanizer deadlock + batch lock**: `ensure()` теперь берёт `_runtime_lock` → `_lock` (тот же порядок, что в `unload`/`generate`), AB/BA-deadlock устранён; `/api/humanize/batch` (`app.py`) переведён на `tool_work(..., exclusive=True)` — batch сериализуется с одиночным humanize. Тесты: concurrent ensure+unload без дедлока, `_backend_busy` во время generate, batch держит exclusive-lock (409 для второго job).

**P2 packs job stuck in "running"**: `packs.download()` уже выставлял `phase="error"` в except — проверено тестом, что после ошибки `try_start` снова разрешает запуск (регрессии нет, фикс зафиксирован тестом).

**DEFERRED**: P2 не-ASCII токен → 500 вместо 403 (`app.py:290`) — нетривиально (hmac на non-ASCII), оставлено; unsigned license.json — требует подписи манифеста, вне объёма; rate limiting — нет готового механизма, DEFERRED.

**Тесты**: `tests/test_backend_review_fixes.py` + `test_humanizer_batch.py` — 20 passed. Полный suite: 665 passed / 17 failed — все 17 падают и на чистом f289cd6 (окружение: нет installer/signature артефактов), к фиксам не относятся.


## Fixer C (frontend)

- WCAG audit `work/audit_wcag_full_20261121.py`: **FAIL 188 -> 105** (WARN 123 unchanged; 311 -> 212 raw records).
  `--verdict-ink` now defined per theme (dark/light #fff, contrast #000); dark accent presets carry
  `:not([data-theme="light"])` (specificity 0,3,1) so all 8 accents resolve in dark (§2 fixed);
  exp-main gradient end #0b7f8c (4.74:1); cab-btn.danger/tile.c1 on --ai-deep; contrast -deep fills brightened.
- Pause button (`lpSetupCancel`) now visible during checking/downloading and wired to `/api/models/cancel`.
- i18n: 0 missing keys (en=pl=ru=751); `test_ui_localization_contract` green.
- Tests: `test_ui_wcag_contrast.py` + `test_ui_navigation_reachability.py` + `test_ui_localization_contract.py` = **29 passed**.
- Mirrored into `web/served/index.html` (CRLF preserved).
