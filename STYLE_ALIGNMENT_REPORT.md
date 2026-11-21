# Style alignment: Linda-Pro web UI → lindarixon.github.io/Linda design system

Work item 2026-11-20 (owner). Branch `rc/2.4`, local commit only.
Scope: visual only — theme token **values**, plus a small number of hardcoded hex values in the
`web/index.html` / `web/cabinet.html` inline `<style>` blocks and in the decorative chart palettes
embedded in `cabinet.html` JS strings. No logic, no i18n keys, no test expectations changed.

Source of truth: live `linda.css` from the brand site (fetched 2026-11-20, 102,455 bytes).

---

## 1. Token mapping (old → new)

### Dark theme (`html:not([data-theme="light"]):not([data-theme="contrast"])`, and `:root` in index.html)

| App variable | Site variable | Old value | New value |
|---|---|---|---|
| `--bg` | `--bg` | `#16181d` (`#0d0f15` in index) | `#111418` |
| `--bg-card` | `--surface` | `#1d2027` (`#151822`/`#171a22`) | `#191c20` |
| `--bg-elevated` | `--raised` | `#252a33` (`#1b1f2c`/`#1f232d`/`#262a33`) | `#202429` |
| `--border` | `--line` | `#343b46` (`#282d3e`/`#2e323d`) | `#31363c` |
| `--text` | `--ink` | `#eceef3` (`#e9ecf2`) | `#eceff2` |
| `--text-muted` | `--muted` | `#b0b8c5` (`#8b93a7`/`#a8adb8`/`#b5bac6`/`#cfcfcf`) | `#b2b8bf` |
| `--accent` | `--accent` | `#5b7cfa` (`#1ba1e2`) | `#82bcfc` |
| `--accent-light` | `--soft` | `rgba(91,124,250,.15)` | `rgba(130,188,252,.15)` |
| `--cobalt` | `--primary` | `#0050ef` (`#0067c0`) | `#1364b0` |
| *(new)* `--primary-hover` | `--primary-hover` | — | `#2975c2` |
| `--ld-chrome` | `--header` | `#111318` | `#111418` |
| `--ld-hover` | `--sunken` (raised-ish) | `#292e38` | `#0b0d11` |
| `--ld-line-strong` | `--line-strong` | `#586270` (`#4a4f5c`/`#647687`/`#8a91a0`) | `#727880` |
| *(new)* `--sunken` | `--sunken` | — | `#0b0d11` |
| *(new)* `--ink`, `--muted`, `--surface`, `--raised`, `--line`, `--header`, `--on-primary` | ditto | — | mirror of the above |
| *(new)* `--id-*` (7 hues) | `--id-*` | — | `#1364b0` `#00787a` `#6a51a4` `#a14206` `#954074` `#137738` `#4d5969` |
| `--teal-deep` | `--id-teal` | `#00716f` / `#00aba9` | `#00787a` |
| `--purple` | `--id-violet` | `#6a00ff` / `#8a3ffc` | `#6a51a4` |
| `--green` | `--id-green` | `#008a00` | `#137738` |
| `--steel` | `--id-slate` | `#647687` | `#4d5969` |
| `--success-fill` *(new)* | `--success-fill` | — | `#03a14a` |
| `--warning-fill` *(new)* | `--warning-fill` | — | `#e19b1b` |
| `--danger-fill` *(new)* | `--danger-fill` | — | `#d9544b` |
| `--ai` (verdict: AI) | `--danger` fill | `#ff5768` / `#e51400` | `#d9544b` |
| `--ai-bg` / `--ai-border` | `--danger-soft` | `rgba(255,87,104,.16)` / `.4` | `rgba(217,84,75,.15)` / `.42` |
| `--human` / `--human-deep` | `--success` fill | `#34d399` / `#60a917` | `#03a14a` |
| `--human-bg` / `--human-border` | `--success-soft` | `rgba(52,211,153,.14)` / `.4` | `rgba(3,161,74,.14)` / `.42` |
| `--uncertain` / `--uncertain-deep` | `--warning` fill | `#f59e0b` / `#fa6800` | `#e19b1b` / `#a06c00` |
| `--uncertain-bg` / `--uncertain-border` | `--warning-soft` | `rgba(245,158,11,.15)` / `.4` | `rgba(225,155,27,.13)` / `.42` |

### Light theme (`html[data-theme="light"]`)

| App variable | Site variable | Old value | New value |
|---|---|---|---|
| `--bg` | `--bg` | `#f3f4f6` / `#eef1f6` | `#f3f5f7` |
| `--bg-card` | `--surface` | `#fff` | `#fff` (unchanged) |
| `--bg-elevated` | `--raised` | `#edf0f4` / `#e6ebf3` | `#ebeef2` |
| `--border` | `--line` | `#d3d8e1` / `#cfd6e3` | `#d7dbe1` |
| `--text` | `--ink` | `#1a1c21` / `#141821` | `#161a1f` |
| `--text-muted` | `--muted` | `#535e6e` / `#5b6474` / `#4a5262` | `#58616d` |
| `--accent` | `--accent` | `#0b6cab` / `#005fb8` | `#015ba6` |
| `--accent-light` | `--soft` | `rgba(0,95,184,.09)` | `rgba(1,91,166,.09)` |
| `--cobalt` | `--primary` | — | `#1364b0` |
| *(new)* `--primary-hover` | `--primary-hover` | — | `#08569a` |
| `--ld-chrome` | `--header` | `#e8ebf0` | `#ebeef2` |
| `--ld-hover` | `--sunken` | `#e4e9f0` | `#e4e6ea` |
| `--ld-line-strong` | `--line-strong` | `#8894a4` | `#7f858d` |
| *(new)* `--surface`/`--raised`/`--sunken`/`--line`/`--header`/`--ink`/`--muted`/`--on-primary` | ditto | — | `#fff` / `#ebeef2` / `#e4e6ea` / `#d7dbe1` / `#f3f5f7` / `#161a1f` / `#58616d` / `#fff` |
| *(new)* `--id-*` | `--id-*` | — | same 7 hues as dark |
| `--ai` (verdict) | site `--danger` | `#ff5768` | `#963730` |
| `--human` | site `--success` | `#34d399` | `#006e30` |
| `--uncertain` | site `--warning` | `#f59e0b` | `#905d00` |
| `--teal-deep` / `--purple` / `--green` / `--steel` | `--id-*` | `#00aba9` / `#6a00ff` / `#008a00` / `#647687` | `#00787a` / `#6a51a4` / `#137738` / `#4d5969` |

### Typography

| Where | Old | New |
|---|---|---|
| `body.ld-desktop` (desktop-shell.css) | `"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif` | `"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif` |
| `body` base style (index.html `<style>`) | `'Inter', -apple-system, sans-serif` | full site stack (Segoe UI Variable Text …) |
| Metro skin `body` + `textarea` | `"Segoe UI","Segoe UI Variable","Helvetica Neue",Arial` | full site stack |
| Display headings | (already site-equivalent) | unchanged |

### Controls / geometry

| Item | Old | New |
|---|---|---|
| `--ld-control` | `40px` | **`44px`** (site `--control`) |
| `--radius` *(new)* | — | `2px` |
| `--radius-lg/md/sm` | `14px / 10px / 6px` | `2px / 2px / 2px` |
| `border-radius` on nav, cards, buttons, inputs | 0 (Metro `*{border-radius:0!important}`) or 10–16px | `var(--radius)` (2px) via one targeted rule |

### Accessibility / contrast theme — intentionally preserved

`html[data-theme="contrast"]` keeps its yellow override (accent `#f5d020`, `--border:#fff`, black bg).
Site-named tokens were added there too so both naming schemes stay legible, and accent variants
(`data-accent="teal|purple|green|orange|cobalt"`) were scoped with `html:not([data-theme="contrast"])`
so they can **no longer** override the yellow accessibility accent (this was a pre-existing bug — the
contrast accent was `#63baff` before the change because the cobalt variant won the cascade).
Verified live: accent now resolves to `#f5d020`, bg `#000`, border `#fff`.

---

## 2. Files touched

5 files, all under `web/`:

| File | +/- | What changed |
|---|---|---|
| `web/desktop-shell.css` | +63 / −12 | Token block rewritten for dark/light/contrast; new site tokens; `--ld-control:44px`; `--radius:2px` + one targeted `border-radius` rule; verdict fills; Segoe stack; light-theme tile fix |
| `web/index.html` | +115 / −87 | `:root` token block; Metro skin `:root`; light/contrast token lines; accent variants (hue remap + contrast scoping); hardcoded surface/accent hexes in the inline styles; `--lp-radius` usage on `.lp-btn`/`.lp-input`, 44px control heights; `--on-primary` on `.lp-btn`; footer link hexes |
| `web/cabinet.html` | +35 / −35 | Hardcoded surface hexes in the `<style>` block; SVG chart palette constants in JS strings (`PAL`, histogram fills, grid strokes) now brand values; `.cab-btn`/`.modebar` 40px → 44px |
| `web/startup-panorama.css` | +11 / −11 | Splash surfaces/accent/text to brand values |
| `web/metro-dev.css` | +1 / −1 | Hover accent `#0042c7` → `#1364b0` |

**Not touched:** any `i18n` JSON, `linda_pro/`, `linda_desktop/`, `tests/`, JS logic
(note: only colour literals inside existing JS strings were changed in `cabinet.html` —
the SVG chart palettes; no control flow, no keys, no behaviour).

`.gitattributes` is absent and `core.autocrlf=false`, so CRLF normalisation was avoided deliberately:
all touched files are written LF-only, matching the committed blobs, so `git diff` shows only real
content changes (no whole-file rewrites).

---

## 3. Tests

Command (per STAGE_D):
```
cd D:/Linda_2100_Dev
unset PYTHONPATH PYTHONHOME
PYTHONIOENCODING=utf-8 C:/Users/ninja/Desktop/детектор/.venv/Scripts/python.exe -m pytest tests -q
```

| Run | Result |
|---|---|
| Baseline (before any edit) | **11 failed, 575 passed**, 1 warning — 142.45 s |
| After changes (run 1) | 12 failed, 574 passed — included `test_license_api::test_download_through_api_and_settings` |
| After changes (run 2, confirmation) | **11 failed, 575 passed**, 1 warning — 139.03 s |

The extra failure in run 1 was transient: `tests/test_license_api.py` passes 13/13 in isolation, and the
identical baseline failure set reproduced on the confirmation run. **No new failures.**

Failure set is byte-identical to the baseline (all pre-existing, all updater/installer/packaging):

```
test_enterprise_review::test_download_reserved_before_thread_can_start
test_enterprise_review::test_installer_flags_are_invisible_and_do_not_reboot
test_enterprise_review::test_staged_installer_rechecked_before_execution
test_restart_draft::test_restart_draft_write_failure_keeps_app_running
test_store_package::test_real_windows_process_is_unpacked
test_update_restart::test_dev_accepts_only_its_signed_app_identity
test_update_restart::test_dev_rejects_production_channel_even_with_valid_signature
test_update_restart::test_restart_launches_staged_installer
test_update_restart::test_staged_installer_newer_found_stale_removed
test_updater::test_app_required_and_installer_info
test_updater::test_installer_hash_checked
```

No test asserts any of the changed hex values (grepped `tests/` for all old and new values; the only
hex in tests is `#0050ef` as a *folder colour argument* in `test_history.py`, a data value, not CSS).
**Zero test expectations were changed.**

---

## 4. Screenshots

All at 1366×768, `work/` is gitignored:

```
D:/Linda_2100_Dev/work/ui_shots_20261120/index_dark_1366x768.png
D:/Linda_2100_Dev/work/ui_shots_20261120/index_light_1366x768.png
D:/Linda_2100_Dev/work/ui_shots_20261120/cabinet_dark_1366x768.png
D:/Linda_2100_Dev/work/ui_shots_20261120/cabinet_light_1366x768.png
D:/Linda_2100_Dev/work/ui_shots_20261120/index_contrast_1366x768.png   (extra: accessibility theme)
```

Captured through `tools/ui_overhaul_preview.py` (the project's own fixture server, which assembles
index + cabinet + splash + metro-dev + desktop-shell exactly as `linda_desktop/app.py` does), served on
127.0.0.1:18826 and killed afterwards (port verified closed, `curl` code 000).

Verified in the live DOM alongside the screenshots:
```
--bg=#111418  --surface=#191c20  --raised=#202429  --sunken=#0b0d11  --line=#31363c
--line-strong=#727880  --ink=#eceff2  --muted=#b2b8bf  --primary=#1364b0
--primary-hover=#2975c2  --id-blue=#1364b0  --success-fill=#03a14a
--radius=2px  --ld-control=44px
body font-family: "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif
```
Light theme: `--bg=#f3f5f7`, `--accent=#015ba6`, body background `rgb(243,245,247)`.
Contrast: `--accent=#f5d020`, `--bg=#000`, `--border=#fff`.

Screenshot review findings:
- **Dark index**: no overflow, no clipped controls, coherent neutral greys + light-blue accent.
- **Light index**: no white-on-white, borders visible, buttons not clipped, 44px controls fit at 1366px.
- **Cabinet dark/light**: full content rendered, tabs and table headers not clipped, no mismatched
  hardcoded backgrounds. Light theme now shows the five stat tiles as solid identity fills
  (blue/teal/orange/green/violet) with white numerals.
- **Contrast**: black bg, white/yellow borders, legible — the yellow accent is not overridden.

---

## 5. Known deviations from the brand site

1. **Radius is 2px, not 0.** The site is strictly square (Metro). A global `border-radius:0` already
   exists in the Metro skin, and zeroing radii app-wide was flagged as a layout risk. Instead a
   `--radius:2px` token was introduced and applied to the main containers only (nav, nav buttons, input
   box, verdict box, metric/voter/heatmap cards, guide, help card, model card, tile, modal card,
   language select, primary/secondary buttons, textarea, lp-input, cab-in/cab-sel). 2px reads as square
   at 1x but keeps anti-aliased corners on hi-dpi. **Decision:** 2px, because the site's own renders at
   high DPI show a hairline rounding and 2px matches the existing `--lp-radius` fallback already used in
   `index.html`. Radius was not forced on circular elements (`.spinner`, `.stat-dot`, `.model-check`),
   which keep `border-radius:50%`.
   *Note:* `html[data-accent="radius"]` user preference (`square`/`soft`/`round`) still works — the
   `soft`/`round` variants use `!important` at a higher specificity on the same elements and win, so the
   user's chosen rounding is never lost.
2. **`--ld-hover` maps to `--sunken`, not `--raised`.** The spec allowed either; `--sunken` (`#0b0d11`
   dark) gives the required *darker* hover on already-raised nav/chrome surfaces, where `--raised`
   would have been invisible against `--ld-chrome`.
3. **`--ai` / `--human` / `--uncertain` are retained as names** (they are referenced ~40× in inline
   styles) but their values are re-tuned to the site's status *fills* (`#d9544b` / `#03a14a` /
   `#e19b1b` dark; `#963730` / `#006e30` / `#905d00` light), matching `--danger-fill`/`--success-fill`/
   `--warning-fill`. The `-bg`/`-border` soft variants follow the site's `-soft` alphas.
4. **Light-theme stat tiles get solid identity fills.** `index.html` still forces `color:#fff` on
   `.tile`/`.tile *` (and `.an-t`, `.metric-card`) in light theme. In the baseline this produced
   **white text on a white card** — a real, pre-existing contrast bug (reproduced on the unmodified
   tree before changing anything). Because those text rules are unchanged and are outside the token
   scope, the tiles are now painted with `--id-blue`/`--id-teal`/`--id-orange`/`--id-green`/
   `--id-violet` fills, which is exactly how the brand site shows identity tiles. Deliberate deviation
   from "tokens only", documented here.
5. **Contrast theme accent changed from `#63baff` to `#f5d020`.** Not a regression: `#63baff` was the
   *cobalt variant* accidentally winning the cascade over the accessibility override. The yellow is what
   the theme was written to use. Fixed by scoping accent variants with
   `html:not([data-theme="contrast"])`.
6. **`--ld-control` 44px**: no fixed-height clipping found at 1366px. Grepped the fixed heights that
   matter (`.tabs-mode button` 40px, `.heatmap-switcher button` 40px, `.exp-fmt` 38px, `.tab` 34px,
   `.cab-btn` 40px) — the tab strip and segmented controls are allowed to stay at their own compact
   heights because the site also uses `--control-sm:36px` there; only primary/secondary action buttons
   were promoted to 44px.
7. **`--header` maps to `--bg`, not `--surface`**, because that is what the site's `linda.css` does
   (`--header:#111418` = `--bg` dark, `--header:#f3f5f7` = `--bg` light). The app's `.header` and
   `.ld-nav` already used `--ld-chrome`, so the visual result is a flat continuous chrome, which matches
   the site's `.header-inner` treatment.

---

## 6. Verification checklist

- [x] `git diff` limited to `web/*.css`, `web/index.html` inline styles, `web/cabinet.html` styles —
      plus colour literals inside existing `cabinet.html` SVG-chart JS strings (no logic changes).
- [x] `web/i18n/*.json` untouched (`git diff --numstat web/i18n/` → empty).
- [x] pytest **575 passed / 11 failed** — identical to baseline, no new failures, no changed expectations.
- [x] Screenshots for dark + light, index + cabinet (+ contrast), 5 files on disk.
- [x] `grep -c '#111418' web/desktop-shell.css` → **3**; `grep -c '#82bcfc' web/desktop-shell.css` → **2**;
      `#82bcfc` present 8× in `index.html`; `#015ba6` 3×; `#1364b0` 6×; `#727880` 1×.
- [x] No GPU/CUDA/ROCm touched; background HTTP server started and killed (port closed).
- [x] Local commit on `rc/2.4` only — **no push**.
