# REVIEW_MARKUP_NEON_20261120 — TOKEN-MARKUP UI, post-63adf6a (rc/2.4)

Ветка: `rc/2.4`, HEAD `1ac5906`, интеграция `63adf6a feat(tokens): v2 token heads for EN/PL (essay+multi PL), calibrated; auto markup uses them` — подтверждена через `git log --oneline -3`.
Метод: статический аудит `web/index.html` + `web/desktop-shell.css` + `linda_desktop/engine.py` + рендер с мокнутым `/api` на порту 18890 (work/mock_markup_server.py), 3 темы, viewport 390px. Порт 18877 не трогался.

## 1. Copy vs behavior (gran_* / set_sent_* vs engine)

- Engine после 63adf6a: `sentence_mode()` в `linda_desktop/engine.py` (~726-776) — auto = tokens только для пар из `TOKEN_HEADS_V2 = {("essay","en"), ("essay","pl"), ("multi","pl")}` (строка 664), остальное — hybrid/context; lang-gate в `document_language()` (строка 666-682) читает reported `language` из результата и возвращает None для всего вне en/pl/ru — uk отклоняется, а не мапится на EN-голову. UI-копирайт `set_sent_auto` («токеновая разметка там, где для языка есть проверенная голова (английский, польский); иначе предложения и контекст») — соответствует поведению. OK.
- sv_uk: ключ есть во всех 3 языках и реально вызывается — `web/index.html:3122` (`cyr > 40 && /[їєґ]/ && !/[ыэ]/` → `T('sv_uk')`). OK.
- **M1 (low): мёртвый ключ `gran_tokens_sentence`.** Engine выставляет `granularity: "tokens"` для токенового пути (`engine.py:1118`, маппинг только в «tokens»), а UI мапит `tokens → gran_tokens` (`index.html:3226`). `gran_tokens_sentence` достижим только если бэкенд пришлёт literally `"tokens_sentence"` — такого значения engine не генерирует. Оба ключаänglish/русские формулировки близки по смыслу, функциональной ошибки нет, но ключ — leftover.
- `gran_segment` достижим только при установленном seg_l14 — соответствует `segmenter_available()`; OK.

## 2. WCAG контраст (вычислено, 3 темы)

Фоновые тинты подсветки сами по себе ~1.2:1 — но текст поверх них наследует `--text`, т.е. контраст определяется `ink vs surface`: dark 14.81:1, light 17.48:1, contrast 21:1 — во всех темах AA/AAA. OK.
Границы/бордеры подсветки (декоративно, не текст): dark 4.61-7.25:1, light 4.66-5.52:1, contrast 7.78-16.64:1 — все ≥3:1 для non-text UI. OK.
- **M2 (medium): бейдж `sent-tag.ai` в тёмной теме — белый текст на `#e8635a` = 3.30:1**, ниже AA 4.5:1 для мелкого жирного текста (0.6rem). В light (`#c4302b`, 5.52:1) и contrast (`#8a0010`, 10.06:1) — ок. Примечание: в contrast-теме инлайн-стиль `index.html:696` жёстко красит `.heatmap-card` в `#191c20!important`, игнорируя `--bg-card:#0a0a0a` — фон остаётся тёмным, текст `#d1d5db` (контраст ок), но жёлтая рамка темы на тёмной карточке — визуально рассогласовано, функционально не критично.

## 3. Mobile 390px

CDP-override 390x844: `scrollWidth == innerWidth == 390`, горизонтального скролла нет, все `.sent-span` на месте, тултип позиционируется fixed. Медиа-запросы до 600px в `desktop-shell.css:350` покрывают раскладку. OK.

## 4. Onboarding / disclaimers

- `auth_note` («Доли слов по меткам, а не измеренное авторство…») присутствует во всех 3 языках и рендерится в cabinet (`cabinet.html:1002`); в main view аналог — `ui_markup_percent_note` (`index.html:1213`). OK.
- `ui_no_ai` / `ui_no_ai_plain` / `ui_no_ai_md` — присутствуют, рендерятся в экспортной секции при пустой разметке (проверено моком: состояние отрисовалось). OK.
- `foot_limits_text`, `pdf_how_text`, `local_document_disagreement_note` (показ при verdict ai/uncertain + 0 AI-предложений, `index.html:2119`), `ui_heatmap_unavailable` — на месте. OK.
- `verdict_short_warn`/`sv_short` — предупреждение о коротком тексте рендерится **в блоке вердикта над/рядом с результатом** (`index.html:2032`), что соответствует решению судьи «above input». OK.

## 5. Leftover references to removed modes

Кроме M1 (`gran_tokens_sentence`), ничего не найдено: все 8 gran_* ключей мапятся на гранулярности, которые engine реально эмитит; set_sent_* опции (auto/full/smooth/windows/segmenter) все достижимы.

## Severity list

- M2 (medium): белый текст на AI-бейдже в тёмной теме 3.30:1 < 4.5:1 (WCAG AA fail для текста бейджа).
- M1 (low): мёртвый i18n-ключ `gran_tokens_sentence`.
- L1 (low): contrast-тема — инлайн-оверрайд красит heatmap-card в фиксированный `#191c20` mimo переменных темы.

## VERDICT

ГОДЕН К РЕЛИЗУ с одним medium: поднять контраст AI-бейджа в тёмной теме (затемнить `--ai` для фона тега или тёмный текст). Копирайт gran_*/set_sent_* соответствует поведению engine после 63adf6a, lang-gate uk→refuse работает и выводится через sv_uk, дисклеймеры на месте, 390px без скролла.

## FIXES (2026-11-20, rc/2.4)

FIXED in 795a362 — M2, M1, L1.

- **M2 (medium) — AI badge contrast.** `.sent-tag.ai` (index.html:501) now fills with `var(--ai-deep)`: white ink **6.01:1** in dark (was 3.30:1 on `#e8635a`), 5.52:1 light, 6.01:1 contrast. The same pair was applied to `.verdict-badge.ai` (dark/light only — the contrast theme keeps `--ai` `#ff8080` with black `--verdict-ink`, 8.65:1), and to `cabinet.html` `.cab-badge.ai` / `.v-pill.ai`. The contrast-theme `.sent-tag.ai` override stays `#8a0010` (10.06:1). Verified by `tests/test_ui_wcag_contrast.py::test_ai_badge_white_ink_meets_aa_in_every_theme`; `web/served/index.html` updated with the same rules.
- **M1 (low) — dead key `gran_tokens_sentence`.** Removed from `web/i18n/{en,pl,ru}.json`, from the embedded `window.LINDA_I18N` block and from the granularity map at `index.html:3226`. Engine still emits only `"tokens"`, so `gran_tokens` remains the single reachable key.
- **L1 (low) — heatmap card surface.** `index.html:696` no longer pins `.heatmap-card` to `#191c20`: it reads `var(--bg-card,#191c20)`, so the contrast theme's `#0a0a0a` surface applies and the yellow border sits on a matching card.

Tests: `pytest tests/test_ui_wcag_contrast.py tests/test_ui_navigation_reachability.py tests/test_ui_localization_contract.py -q` → 27 passed.
