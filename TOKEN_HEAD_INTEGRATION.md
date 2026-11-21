# TOKEN_HEAD_INTEGRATION — v2 token heads in Linda-Pro (rc/2.4)

Date: 2026-11-20. Branch `rc/2.4`, local commits only (no push).

Commits: `63adf6a` (engine, tests, i18n, this report). The `linda_pro/voters.py` half
(head loading, sidecar calibration, `token_head_info`) was committed concurrently in
`bc37148` — a security-fix commit by another session that swept the working tree; the code
is byte-identical to what is described here and `tests/test_backend_review_fixes.py` plus
`tests/test_token_heads_v2.py` pass together (37 tests).
Trained heads: `C:/Users/ninja/Desktop/детектор/tmp/tokenhead_20261120/` (`TRAIN_TOKEN_HEAD.md`).
Pack: `tmp/linda14/gpu_20261120/finalpack/pack_141h` (not a repo artifact).

## 1. What shipped

| # | Change | File |
|---|---|---|
| 1 | `load_token_head` reads the optional identity keys `schema` / `voice` / `lang` from the npz and applies a calibration sidecar (`tok_head_calibration.json` next to the head, or `<pack>/calibration/token_heads_v2.json`). v1 heads without those keys load exactly as before. | `linda_pro/voters.py:88` |
| 2 | `token_head_info(model_dir)` — schema, voice, lang, calibrated center/scale, `calibration_source`; `None` when no head, `schema: 1` when unreadable. | `linda_pro/voters.py:118` |
| 3 | `Engine.TOKEN_HEADS_V2` = `{(essay,en), (essay,pl), (multi,pl)}` — the pairs whose held-out test numbers beat the context path. | `linda_desktop/engine.py:662` |
| 4 | `Engine.document_language(det)` + `Engine.token_head_voice(det, voice)` — a head opts in only if schema ≥ 2, calibrated, and its own `voice`/`lang` keys match the **reported** document language (`Engine.doc_lang`, set in `run()` from the result, cleared by `unload()`). | `linda_desktop/engine.py:664` |
| 5 | `sentence_mode`: auto promotes to `tokens` for those pairs (Pro tier). Explicit settings (`tokens`, `context`, `smooth`, `windows`, `full`, `segmenter`) are untouched, as is `allow_tokens=False`. Docstring rewritten with the v2 numbers and the v1 refusal reason kept for context. | `linda_desktop/engine.py:706` |
| 6 | `Engine.doc_lang` — the language the document *reported*, kept separate from `det.cur_lang` (the routed backend). | `linda_desktop/engine.py:656,894` |
| 7 | Multi's token column runs its **own** pass when a validated v2 Multi head exists for the language (multi/pl); multi/en keeps the derived view (Essay evidence through Multi's calibration). | `linda_desktop/engine.py:922-945` |
| 8 | UI copy: `set_sent_auto` now says token markup applies "where the language has a validated head (English, Polish)". Key count unchanged (752 per language), `tools/sync_web_i18n.py` re-run. | `web/i18n/{en,ru,pl}.json`, `web/index.html` |

Model directories (product format, `tok_head.npz` + `tok_head_v1_backup.npz`, sidecar in the pack's `calibration/`):

| voice/lang | model dir | center | scale |
|---|---|---|---|
| essay/en | `qa_models/models/essay_dhi_131_20261008` | 3.0304 | 1.6107 |
| multi/en | `qa_models/models/multi_dhi_131_20261008` | 3.4091 | 1.3640 |
| essay/pl | `models/l14/essay_l14m50` | 3.6448 | 1.6126 |
| multi/pl | `models/l14/multi_l14m50` | 3.6177 | 1.7482 |

Install script: `work/install_token_heads_v2.py`.

## 2. Measured metrics (source: TRAIN_TOKEN_HEAD.md, held-out test, token level)

| voice/lang | AUC v1 → v2 | F1@0.20 v1 → v2 | neg-token FPR@0.20 |
|---|---|---|---|
| essay/en | 0.601 → **0.762** | 0.276 → **0.539** | 0.052 → 0.050 |
| essay/pl | 0.587 → **0.748** | 0.162 → **0.374** | 0.056 → 0.050 |
| multi/en | 0.564 → **0.720** | 0.207 → **0.251** | 0.101 → 0.050 |
| multi/pl | 0.536 → **0.708** | 0.164 → **0.320** | 0.110 → 0.050 |

Verdict applied: ship essay EN/PL + multi PL as the auto markup source; multi EN stays
opt-in (explicit `tokens` mode still uses it).

### 2.1 Does the head survive the transformer the product actually runs? (`work/tokenheads_v2_transfer_auc.json`)

The heads were trained on `*_dhi_131_20261008` hidden states for both languages, but
routing_141 renders PL through `*_l14m50`. 3 human + 3 AI documents per cell:

| voice/lang | transformer | AUC | human FPR@0.20 |
|---|---|---|---|
| essay/en | dhi_131 (in-domain) | 1.000 | 0.006 |
| essay/en | l14m50 (**wrong pairing**) | 0.974 | **0.177** |
| essay/pl | dhi_131 (in-domain) | 0.966 | 0.000 |
| essay/pl | l14m50 (product) | 0.878 | **0.055** |
| multi/pl | dhi_131 (in-domain) | 0.983 | 0.026 |
| multi/pl | l14m50 (product) | 0.987 | **0.075** |

The PL heads transfer (human FPR 5.5 %/7.5 % against the 5 % target). The wrong pairing
(essay/en head on the PL transformer) fires on 17.7 % of human tokens — which is exactly
what the `lang` identity gate in `token_head_voice` prevents.

## 3. Sentence-level markup quality on the 30-pair dev set

`work/tokenheads_v2_sentence_dev.py` (dev pairs + negatives, product-exact windowing,
sentence spans from the dataset's own `sentence_labels`) and
`work/tokenheads_v2_sentence_thresholds.py` (threshold picked on dev under a 10 %
human-sentence FPR budget, reported on held-out **test**).

| voice/lang | sentences | sentence F1@0.20 v1 → v2 (dev) | human-sentence FPR@0.20 v1 → v2 (neg) | test F1@dev-pick v2 (v1@0.20) | test human-sent FPR@pick |
|---|---|---|---|---|---|
| essay/en | 4154 dev / 4402 test | 0.161 → **0.313** | 0.114 → **0.010** | **0.297** @p=0.15 (0.007) | 0.081 |
| essay/pl | 577 / 583 | 0.208 → 0.080 | 0.312 → **0.040** | **0.408** @p=0.26 (0.105) | 0.093 |
| multi/en | 4154 / 4402 | 0.147 → 0.116 | 0.087 → **0.052** | 0.019 @p=0.20 (0.088) | 0.085 |
| multi/pl | 577 / 583 | 0.303 → 0.106 | 0.369 → **0.083** | 0.337 @p=0.23 (0.345) | 0.077 |

Reading this honestly:

* **Ranking improves everywhere.** Best-F1 on dev sentences rises for all four cells
  (0.314→0.486 essay/en, 0.350→0.406 essay/pl, 0.259→0.433 multi/en, 0.387→0.414 multi/pl),
  and human-sentence false positives at 0.20 drop 4-9×. That is the shipped default.
* **The token-level 0.20 threshold is not the sentence-level optimum.** Averaging token
  scores inside a sentence shrinks the spread, so at 0.20 recall is too low on PL
  (essay/pl F1 0.208→0.080 at 0.20, but 0.408 at the dev-picked 0.26).
* **This is not switched on silently.** The head's calibrated 0.20 stays in force; per-voice
  sentence thresholds would be a separate calibration decision (the numbers above are the
  evidence for it). What ships today is: better ranking, far fewer human sentences marked,
  and the same thresholds the pack's token band has always used.

## 4. Verdict regression — 20 texts, pack_141_final vs pack_141h

`work/token_heads_v2_regression.py` (auto + explicit tokens, per text, per mode) and
`work/compare_tokenheads_v2.py`:

```
auto   hybrid -> tokens : 20/20 texts
tokens tokens -> tokens : 20
OK: 20 texts x 2 modes — every verdict, p_ai, margin and voter score identical
```

**20/20 identical verdicts.** Document scores and margins do not move at all: the token path
only feeds sentence markup, and `res["verdict"]` is written before it runs. Markup genuinely
changed (5-25 labels per text, max |Δp_ai| 0.93) — that is the point of the change.

### 4.1 One real bug the pack smoke caught

`routed.py` sets `cur_lang` to `"en"` for any language it has no routing entry for
(`routed.py:217`), and to `"ru"` for the uk backend (`routed.py:233`). A gate that read
`cur_lang` therefore treated a **Ukrainian** document as English and took the `en` head —
the exact wrong pairing measured at **17.7 % human-token FPR** in §2.1. The pack smoke (40
texts incl. 13 RU/uk) flagged it as `auto markup took tokens for ru`.

Fixed by reading the *reported* language and refusing rather than guessing:
`document_language()` returns a language only for `en`/`pl`/`ru`, `None` otherwise; a `uk`
document keeps the context path. Two regression tests added
(`test_auto_uses_the_reported_language_not_the_routed_backend`,
`test_auto_reads_pl_from_the_report_when_the_backend_says_en`). Re-run: 40/40, no RU/uk
text on the token path.

This guard is load-bearing, not defensive: in pack_141h the RU language ships
`models/essay_l14m50` and `models/multi_l14m50` — the **same directories** as PL — so the
PL head physically sits in the RU voice directory (manifest `per_language.ru`). Without the
language check, RU documents would be coloured by a Polish head.

## 5. Pack pack_141h

Built by `tmp/linda14/gpu_20261120/finalpack/build_pack_141h.py` from `pack_141_final`:
4 v2 heads + `calibration/token_heads_v2.json`, **routing byte-identical to
`eval/reports/routing_141.json`** (`29ccc66d…`), `train_args` unchanged, weights untouched.

* manifest: schema 1, `signed=false`, 58 files, 5.66 GiB, per_language en 31 / pl 18 / ru 18.
* `check_manifest_141h.py`: every file's size and sha256 recomputed and matched, no unlisted
  files, routing == routing_141, every full-tier voice dir present per language, all four
  heads schema 2 with `voice`/`lang`, sidecar center == npz center. **MANIFEST OK.**
* `smoke_141h.py` (40 texts — 14 en, 13 pl, 13 ru/uk — CPU, two passes over both packs,
  595 s):
  `SMOKE PASS: 40/40 executed, 0 verdict flips, 0 exceptions, 0 contract problems`,
  **0 document scores moved** (max |Δscore| 0.0). Markup: `auto` resolves to `tokens` for
  every EN and PL text (`hybrid -> tokens`), stays `hybrid` for every RU text, and per
  sentence `p_ai` changed on 5-10 sentences per EN text and 7-8 per PL text. Explicit
  `tokens` mode returns the v2 scores in both packs. Results:
  `tmp/linda14/gpu_20261120/finalpack/smoke_141h_results.json`.

## 6. Tests

New: `tests/test_token_heads_v2.py` (25 tests) — v2 selection, v1 unchanged, backup never
loaded, sidecar override + 7 bad-sidecar cases, unreadable head, promotion for
essay-en/essay-pl/(essay,pl-with-multi-en), refusal for multi/en, ru, v1 heads, identity
mismatch, `allow_tokens=False`, explicit modes, Lite independence, and an end-to-end
auto-markup run asserting verdict invariance.

Full suite (`python -m pytest tests -q`, CPU, 175 s): **641 passed, 13 failed**.

12 of the 13 are the known environment-dependent set (updater / installer / Store-package
tests that need a real Windows installer pipeline; `work/_known.txt`), every one of which
also fails on `rc/2.4` before this change. The 13th is
`test_collection.py::test_runtime_temp_is_ignored_before_scanning[True]`, which spawns a
subprocess pytest with `timeout=30`: it passes in isolation and in a two-file run, and
fails only under the load of the full 3-minute suite. Nothing in this change touches
collection.

*(Note: bare `pytest` at the repo root also collects `evidence/ui_overhaul_20261024/test_dependencies/`,
a vendored numpy/colorama tree, and aborts collection. `pytest tests` is the suite the
616-passed baseline counts; the 641 here is that suite plus the 25 new tests.)*
