# P0 fix report — Neon UI audit (2026-11-20)

Scope: the four P0 findings of `UI_AUDIT_NEON_20261120.md` §5, fixed in `web/` + `tests/` only.
Branch `rc/2.4`, local commits, no push. No GPU/ROCm code touched.

Verification scripts (kept out of the shipped tree): `work/wcag.py`, `work/check_i18n_keys.py`,
`work/contrast_table.txt`. The same contrast maths lives in `tests/test_ui_wcag_contrast.py`,
which prints the table when run directly.

---

## P0-1 — light-theme accent presets were unreadable on white

**Problem.** `data-accent` presets in `web/index.html` only had dark-theme values (`#5ecbcb`,
`#88ca95`, `#eca47f`, …). In `data-theme="light"` they were applied unchanged → 1.76:1 … 2.73:1.

**Change.** Two mirrored blocks, one per stylesheet the backend appends
(`linda_desktop/app.py` loads `desktop-shell.css` after `index.html`):

| File | Lines | What |
|---|---|---|
| `web/index.html` | 746–757 (new) | `html[data-theme="light"][data-accent=…]` for cobalt/teal/green/orange/amber/purple/rose/magenta/graphite/slate |
| `web/desktop-shell.css` | 59–67 (new) | same set, grouped selectors |

Each block sets `--accent`, `--accent-light`, `--cobalt` and `--border-focus` to the brand
identity hue, so links, section headings, focus rings and the `--cobalt`-filled buttons agree.
Specificity is equal to the dark presets (`html:not([data-theme=…])[data-accent=…]`), and the new
rules sit later in the sheet, so light wins — asserted by
`test_light_theme_accent_presets_override_the_dark_ones`.

`amber` maps to `#a14206` and `rose`/`magenta` to `#954074` because no separate brand hue exists
for them; `graphite`/`slate` map to `#4d5969`.

Contrast on `#fff` (WCAG 2.1 relative luminance, sRGB):

| theme | accent | `--accent` | on `#fff` | on `#f3f5f7` | on `#ebeef2` | before |
|---|---|---|---|---|---|---|
| light | teal | `#00787a` | **5.29** | 4.84 | 4.55 | 1.92 |
| light | green | `#137738` | **5.64** | 5.16 | 4.85 | 1.76 |
| light | amber / orange | `#a14206` | **6.37** | 5.83 | 5.47 | 2.15 |
| light | rose / magenta | `#954074` | **6.43** | 5.89 | 5.53 | 2.73 |
| light | graphite / slate | `#4d5969` | **7.12** | 6.52 | 6.12 | 2.56 |
| light | purple | `#6a51a4` | **6.31** | 5.78 | 5.43 | (not preset) |
| light | cobalt (default) | `#015ba6` | **6.89** | 6.30 | 5.92 | 6.89 |

---

## P0-2 — semantic verdict colours failed AA

**Change.** Dark and light values now line up across all three definition sites
(`index.html:root`, `index.html:style#metro`, `desktop-shell.css`), including the
`-bg` / `-border` / `-deep` companions, so no theme block is left with the old hue.

| Token | Theme | Old | New | Where |
|---|---|---|---|---|
| `--ai` | dark | `#d9544b` (4.33:1) | `#e8635a` | `index.html:58`, `index.html:651`, `desktop-shell.css:18` |
| `--ai-deep` | dark | `#d9544b` | `#b03a30` | same |
| `--human-deep` | dark | `#03a14a` (3.39:1 with white) | `#056c3a` | same |
| `--ai` | light | `#963730` (7.28:1 on `#fff`, but not the cabinet value) | `#c4302b` | `index.html:732`, `desktop-shell.css:36` |
| `--human` / `--human-deep` | light | `#006e30` | `#0d7a3e` | same |
| `--uncertain` | light | `#905d00` | `#8f5f00` | same |
| `--ai` | contrast | `#ff6b6b` (6.80:1 on `#161616`) | `#ff8080` | `index.html:735`, `desktop-shell.css:52` |

**Deviation from the audit, on purpose.** The audit proposed `--uncertain: #9a6700` for light.
Measured: 4.87:1 on `#ffffff` but **4.18:1 on `--bg-elevated` `#ebeef2`**, where `.stat-pill` and
`table th` actually put it — still a FAIL. Shipped `#8f5f00` instead: 5.52 / 5.05 / 4.74 on
`#fff` / `#f3f5f7` / `#ebeef2`. `--ai: #c4302b` is 4.74:1 on `#ebeef2` and 4.88:1 on its own
tint, so it holds. `--human: #0d7a3e` is 4.66:1 on `#ebeef2`.

Dark `--ai` was also checked on `--bg-elevated` `#202429` (4.73:1) and on its own 16 % tint over
the card (4.76:1), because `.voters-card` and `.stat-pill` are elevated surfaces.

Contrast table (all 3 themes × 8 accents × 6 text tokens × 3 surfaces, plus white-on-fill):

| Theme | Token | On | Ratio | Before |
|---|---|---|---|---|
| dark | `--ai` | `#191c20` | **5.18** | 4.33 FAIL |
| dark | `--ai` | `#202429` | **4.73** | — |
| dark | `--human` | `#191c20` | **5.05** | 5.05 ok |
| dark | `--uncertain` | `#191c20` | **7.25** | 7.25 ok |
| light | `--ai` | `#ffffff` | **5.52** | 3.83 FAIL (audit) |
| light | `--human` | `#ffffff` | **5.43** | 3.34 FAIL (audit) |
| light | `--uncertain` | `#ffffff` | **5.52** | 2.33 FAIL (audit) |
| light | `--ai` | `#ebeef2` | **4.74** | — |
| light | `--human` | `#ebeef2` | **4.66** | — |
| light | `--uncertain` | `#ebeef2` | **4.74** | — |
| contrast | `--ai` | `#161616` | **7.97** | 6.80 FAIL |
| any | `#fff` on `--ai-deep` (all themes) | — | ≥ **5.43** | 3.95 FAIL (dark badge) |

Full machine output: `work/contrast_table.txt` — 512 measured pairs, **0 FAIL**, lowest ratio
4.53:1 (`#fff` on `--uncertain-deep #a06c00` in dark, unchanged and still AA).

---

## P0-3 — i18n key coverage

**Finding: `task_stopping` already existed** in all three files before this change
(`en` "Stopping…", `ru` "Останавливаем…", `pl` "Zatrzymywanie…"), 748 keys per language, key sets
identical. `git log -S'task_stopping' -- web/i18n/en.json` shows it arrived in `e1f6ffc`
(baseline). So the audit's file:line (`desktop-shell.js:356`) pointed at a real call site but not
at a real gap — the key resolves. Nothing was added or renamed; adding a duplicate would have
broken `test_embedded_offline_dictionaries_match_json_sources`.

**What was actually missing was the check.** The contract test only compared the JSON files with
the copy embedded in `index.html`, so nothing verified the keys the shell asks for (that is how
the audit reasoned itself into the finding).

**New scanner** `work/check_i18n_keys.py` — extracts four reference styles from every
`web/*.js` + `web/*.html`, including both branches of a ternary `LINDA_T(cond ? 'a' : 'b')` and
skipping `=== 'ai'`-style comparisons, then resolves:

* `LINDA_T('…')`, `data-i18n`, `data-i18n-ph`, `data-i18n-title`, `data-i18n-html` → `web/i18n/*.json`
* `data-ld-text="…"` → the `COPY` table inside `desktop-shell.js` (a different mechanism with its own source)

Result:

```
scanned 4 files; json-resolved keys: 389; desktop-shell keys: 17
  cabinet.html       json:148  ld-text:  0
  desktop-shell.js   json:  9  ld-text: 17
  index.html         json:244  ld-text:  1
  startup.html       json:  0  ld-text:  0
en/ru/pl: 748 keys each, missing 0
en/ru/pl: 66 desktop-shell COPY keys each, missing 0
TOTAL MISSING: 0
```

**Missing keys found: none.** The new `about` / `about_desc` labels added for P0-4 live in the
three `COPY` tables only (that is the mechanism `data-ld-text` resolves against, via `T()`), so the
JSON files are unchanged at 748 keys and the count stays at zero.

`tests/test_ui_localization_contract.py` extended (+54 lines, 2 new tests):
`test_every_key_resolved_by_the_shell_and_pages_exists_in_all_languages` now scans
`desktop-shell.js` as well, and `test_desktop_shell_copy_covers_every_data_ld_text_key` covers the
COPY-table path plus key-set parity between ru/en/pl.

---

## P0-4 — `audit` and `about` unreachable

`desktop-shell.css:200` hides `#cabView > .cab-top`, where all 11 cabinet tabs lived. Only 10
routes were carried into the sidebar.

| File | Line | Old | New |
|---|---|---|---|
| `web/desktop-shell.js` | 196 | `['models','settings','help','license']` | `['models','settings','audit','about','help','license']` (group `app`) |
| `web/desktop-shell.js` | 163 | — | `about` icon path |
| `web/desktop-shell.js` | 186–191 (new) | — | `#desktopAbout` section: version + licence cards, button to updates |
| `web/desktop-shell.js` | 247–252 (new) | — | `fillAbout()` reads `#desktopAppVersion` / `#licBadge` |
| `web/desktop-shell.js` | 262 | — | `activate()` toggles `about.hidden` and fills it when routed |
| `web/desktop-shell.js` | 293 | — | `#desktopAboutUpdates` → `navigate('settings')` + `setting('updates')` |
| `web/desktop-shell.js` | 295 | — | `#lpOpenAbout` → `navigate('about')` |
| `web/index.html` | 1032 | Updates row had 2 buttons | adds `#lpOpenAbout` ("About Linda") in Settings › Updates and about |

`audit` needs no route logic — `paneMap` already mapped `audit → 'audit'` and
`auditSwitch` (history ⇄ audit) already existed; only the sidebar button was missing.

New `tests/test_ui_navigation_reachability.py` (6 tests, static like every other UI test here):
`audit`/`about` are in the `app` group, every sidebar route has an `activate()`/`navigate()`
branch, every `.cab-tab[data-pane]` has a sidebar route while `#cabView>.cab-top` is still
hidden, the About ↔ Settings links exist, and all four labels are translated three times.

---

## Tests

| Stage | Passed | Failed |
|---|---|---|
| baseline (before) | 574–575 | 11–12 (flaky `test_license_api`) |
| after, full suite | **587** | **11** |

+12 passing tests = the 12 new/extended cases above (2 in `test_ui_localization_contract.py`,
4 in `test_ui_wcag_contrast.py`, 6 in `test_ui_navigation_reachability.py`).

Failure set is unchanged and pre-existing — updater / Store / installer only:
`test_enterprise_review.py` (3), `test_restart_draft.py` (1), `test_store_package.py` (1),
`test_update_restart.py` (4), `test_updater.py` (2). `test_license_api` passed in this run (it is
the known flaky one and may appear in either column).

```
11 failed, 587 passed, 1 warning in 154.38s
```

`node --check web/desktop-shell.js` passes; `tests/test_web_js_syntax.py` green.

## Constraints honoured

CPU only, no GPU/ROCm imports, foreground runs < 10 min, local commits only, `web/`, `web/i18n/`,
`tests/`, `P0_FIX_REPORT.md` touched. `cabinet.html` deliberately untouched — P0-4's `about` link
went into `index.html`'s settings block and the shell's About screen instead.
