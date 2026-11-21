# Redesign apply — Neon pass (branch `rc/2.4`)

Applied and verified the Neon redesign plus the client's P0/P1 defect list.
Report written after the implementation commits landed; every number below is
measured on `HEAD`, not copied from a brief.

| | |
|---|---|
| Branch | `rc/2.4` |
| Implementation commits | `a40825f`, `43a2a37`, `188aef7`, `f18fa3e` |
| Follow-up commits (this session) | `ea24d26` (tests), `13558d6` (hover-token fix) |
| Test baseline | 593 passed / 12 env-failed → **610 passed / 11 env-failed** |
| Screenshots | `work/ui_shots_20261120_redesign/01..12.png` |

---

## 1. Change list (C-01 … C-08)

Line numbers are on `HEAD` (`13558d6`).

| ID | Change | Location |
|---|---|---|
| C-01 | One flat ACTION fill. The old `cobalt → accent` gradient ended on `#82bcfc`, putting white label text at 1.99:1. Now `--primary #1364b0` with `--on-primary #fff`. | `web/index.html:686-689` |
| C-02 | The contrast-theme blanket `color:#000!important` no longer paints the CTA or cabinet actions; they take `--on-primary`. | `web/index.html:740-744`, `:930` |
| C-03 | Calm guidance: the 300-word suitability note is a 13px `--text-muted` line with an 8px warning dot, not a banner. | `web/desktop-shell.css:188-190` |
| C-04 | Failure state is a flat banner with a real **Retry** instead of a bare `textContent` write (no space before the message, pink-on-grey below AA). | `web/index.html:1887-1910` (`showAnalysisError`), `web/desktop-shell.css:208-209` |
| C-05 | Draft survives F5 with no backend: every edit mirrors into `localStorage`, restored when the server copy is unavailable. | `web/index.html:1820-1840` (`saveLocalDraft`/`restoreLocalDraft`) |
| C-06 | Modern Metro: `--radius:0`, `--radius-lg/md/sm:0`, all pill radii flattened across `index.html`, `desktop-shell.css`, `cabinet.html`. | `web/index.html:70-73`, `:771-772`; `web/desktop-shell.css:3` |
| C-07 | Two control heights only: `--ld-control:44px`, `--ld-control-sm:36px`, wired to primary/nav and secondary/rail tiers. | `web/desktop-shell.css:3`, `:80-89` |
| C-08 | Nine nav items in three groups; `Pro` tag on the two licensed tools (trace, humanize); About/Help moved into the details screen. | `web/desktop-shell.js:207-211`, `web/desktop-shell.css:135-139` |

## 2. Client defect list (1 … 10)

| Bug | Symptom | Fix | Location |
|---|---|---|---|
| 2 | Light theme showed dark chips with grey text (hardcoded `#202429`) | Chips tokenised; active chip uses the ACTION pair | `web/index.html:894-898` |
| 3 | "Models and packages" was a dead end — every row "not installed", nothing to press | First-run CTA prepended, hidden once models are present | `web/desktop-shell.js:183-190`, `:270`; `web/index.html:2843` |
| 4 | Language switch waited on `POST /api/settings` and bailed silently, so the UI only changed on a second click | Apply the language first, persist in the background | `web/index.html:3146-3160` |
| 6 | "AI 0%" beside a verdict of "AI" read as a defect | Show a dash, not a misleading zero, when there is no sentence markup | `web/cabinet.html:1273-1276` |
| 7 | Black ink on the contrast-theme CTA (3.33:1) and on `--human-deep`/`--uncertain-deep` | CTA + status chips take `--on-primary`; status fills take `--verdict-ink` (black) | `web/index.html:744`, `:930`; `web/desktop-shell.css:41-56` |
| 10 | Protected draft dropped on F5 with no backend | `localStorage` mirror (same code as C-05) | `web/index.html:1820-1846` |

Bugs 1, 5, 8, 9 carry no in-code marker, and no brief file exists in the tree
(`work/`, `docs/`) naming them, so they cannot be attributed to a `file:line`
without guessing. Nothing in the diff was left unimplemented — the gap is
documentation, not code.

## 3. Measured contrast (WCAG 2.1 AA = 4.5:1)

Produced by `tests/test_ui_wcag_contrast.py` over 3 themes × 8 accents.

| Pair | Ratio |
|---|---|
| CTA — white on `--primary` (dark / light) | **6.04:1** |
| CTA — contrast theme, `--on-primary` on `--primary #015ba6` | **6.89:1** |
| Status badges — black on contrast fills `#7bff9e` / `#ffb020` / `#ff8080` | **16.64 / 11.48 / 8.65** |
| Worst pair overall — white on `--uncertain-deep #a06c00` (dark theme) | **4.53:1** |
| CTA hover — white on `--primary-hover #0f5596` (added this session) | 7.61:1 |

Two figures in the hand-off brief do not reproduce: it quotes a 4.75:1 worst
pair and a 6.31:1 contrast-theme CTA. Measured values are 4.53:1 and 6.89:1.
6.31:1 is what `--cobalt #005fb8` yields, and `.btn-analyze` is filled from
`--primary`, not `--cobalt` — the brief appears to have measured the wrong
token. The tree is comfortably above AA either way; the numbers above are the
ones the passing tests assert.

## 4. Tests

| File | Result |
|---|---|
| `tests/test_ui_wcag_contrast.py` (8 tests) | pass |
| `tests/test_ui_navigation_reachability.py` | pass |
| `tests/test_ui_localization_contract.py` | pass |
| UI subset total | **23 passed** |
| Full suite (`pytest tests/`) | **610 passed, 11 failed** |

The 11 failures are the known environment set (installer/updater/store paths
that need a signed Windows installer): `test_enterprise_review` (3),
`test_update_restart` (3), `test_updater` (2), `test_restart_draft`,
`test_store_package`. Each passes in isolation or fails only on the
Store-deployment guard; none touches the web UI.

`tests/test_license_api.py::test_download_through_api_and_settings` is
additionally flaky under the full run (it passes alone, 13/13) and makes the
tally read 12 failed / 609 passed on roughly one run in three. Two consecutive
full runs both settled at **610 passed / 11 failed**; treat that as the stable
number and the 12 as that flake, not a redesign regression.

`tests/test_bare_tokenizer.py` (160 tests) arrived with `a40825f` and is part of
the `fbb09bc` token-batching work; it is green here but is not counted as a
redesign change.

### Four new a11y guards (`ea24d26`)

`test_action_button_uses_the_on_primary_pair_in_every_theme`,
`test_deep_verdict_inks_are_not_painted_black_in_the_contrast_theme`,
`test_control_heights_are_only_44_and_36`, `test_corners_are_square_everywhere`.

Two of the four as originally drafted asserted CSS that the shipped files never
contain (`--verdict-ink:#000` declared in the contrast block, and
`min-height:32px!important` in the shell). Both were rewritten to assert the
real contract — the token's `#000` fallback, and the two-tier token wiring with
a closed allow-list of chrome heights — rather than changing product CSS to
satisfy a test nobody had verified. All four were mutation-checked: injecting a
gradient, a black CTA rule, a stray radius or an ad-hoc 50px control height each
turns the corresponding test red.

## 5. Deviation found and fixed (not in the original brief)

`43a2a37` rewrote `--primary-hover` to `var(--primary-hover)` in
`web/index.html` (×2), `web/desktop-shell.css:12` and the mirrored
`web/served/index.html`. A self-referential custom property is invalid at
computed-value time, so `background: var(--primary-hover)` on
`.btn-analyze:hover` resolved to nothing: **the primary action had no hover
state in any theme**. Fixed in `13558d6` with a literal `#0f5596` (white text
7.61:1). `#2975c2` was deliberately not reused — it is the retired gradient stop
and is asserted absent from the tree. Guarded by two new tests
(`test_no_token_resolves_to_itself`,
`test_action_button_hover_has_a_real_colour`).

## 6. Tree sanity

| Check | Expected | Measured |
|---|---|---|
| `grep -c 2975c2 web/index.html web/desktop-shell.css` | 0 | **0 / 0** |
| Nav items (`web/desktop-shell.js:211`) | 9 | **9** — check, batch, history / compare, trace, humanize / models, settings, audit |
| `json.load(web/i18n/ru.json)` keys | 748 | **752** |
| Screenshots `work/ui_shots_20261120_redesign/` | 01–12 | **12 files** |

`ru.json` holds 752 keys, not 748: `188aef7` added `err_retry`,
`pack_dl_models`, `pack_need_models`, `pro_tag` and removed none. 748 was the
count at `a40825f`; the addition is the intended i18n fix, so the brief's 748 is
stale rather than the tree being wrong. `en.json` and `pl.json` are also at 752
with zero key drift in either direction.

## 7. Screenshots

`work/ui_shots_20261120_redesign/` — 12 PNGs:
`01_main_dark`, `02_main_light`, `03_main_contrast`, `04_result_dark`,
`05_result_contrast`, `06_result_light`, `07_models_cta`,
`08_cabinet_history`, `09_licence_gate`, `10_error_banner`, `11_mobile_390`,
`12_mobile_480`.

## 8. Cleanup

A leftover `python -m http.server 18880` (PID 21276, parent 28868) from the
previous run was terminated. Port 18880 is closed (no listener, `curl` exit 7).
The owner's preview on **18877 is untouched** (PID 29768 still listening).

Working tree is clean apart from `RELEASE_NOTES_2.4.0.0_draft_check.md`, which
was already untracked before this task and is deliberately left alone.
