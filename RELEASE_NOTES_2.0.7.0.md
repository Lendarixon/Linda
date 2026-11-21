# Linda 2.0.7.0 — 17 October 2026

App 2.0.7.0; model pack 1.3.4 (unchanged). No push to GitHub.

## What changed (audit 17.10.2026, issues 1–8 + tokenizer)

- Language-aware cleaning (`linda_pro/voters.py`): `clean_text(text, lang)` + NFC
  normalization. Routed backends pass `ru/pl/en` (`routed.py`), classic passes `en`
  (`core.py`, `rescue.py`), engine/single-model pass the backend language.
  Russian homoglyph handling no longer forced through Latin.
- Uniform sentence scoring (`linda_desktop/engine.py`, `single_model.py`):
  `hybrid/full/smooth/context` all score cleaned text, same as the document path.
  Token scores stay on the original offsets (documented limitation).
- Sentence splitter (`linda_desktop/sentences.py`): Ukrainian capitals split;
  `Dr./U.S./А. С./т.е.` no longer break highlighting; `U+200B/U+FEFF` no longer
  glue sentences.
- Unsupported languages (`linda_pro/routed.py`, `linda_desktop/engine.py`):
  German/French → `other` scored as `en` + `language_warning`;
  Ukrainian → `uk` scored as `ru` + own warning. Short English and empty text
  behaviour unchanged (`en`).
- Token-path fallback (`engine.py`): records `res["token_path_error"]` and logs
  `linda.token_path_fallback` instead of a silent downgrade.
- Dead code (`engine.py`): unreachable `len(chosen)==1` custom-verdict branch
  removed; single-model path via `single_model.run` unchanged.

Models, tokenizers and thresholds are unchanged in code. RU thresholds need
re-validation on held-out data after the cleaning change before any release
claims (calibration was done on the old EN-forced cleaning).

## Tests

- New: `tests/test_audit_fixes_2070.py` (7 tests: lang-aware cleaning + NFC,
  Ukrainian split, abbreviations, ZWSP, `other`/`uk` detection, routed fallback
  warnings, token-error shape).
- Relevant suites green (101 passed): audit fixes, routed, sentence offsets,
  lang routing, single-model contract, engine colours, tokens mode, lite reuse,
  heatmap labels.
- Full suite: 505 passed, 11 failed — all 11 are pre-existing environment
  failures under MS Store Python (`is_store_package()` true:
  `test_enterprise_review` ×3, `test_update_restart` ×4, `test_updater` ×2,
  `test_store_package` ×1, `test_restart_draft` ×1). No failures in the areas
  touched by this release.

## RU threshold re-validation (17.10.2026, held-out, current 1.3.4 thresholds)

Tool: `tools/ru_thresh_check_2070.py` (Assay RU-full, old `en` vs new `ru`
cleaning) + `tools/ru_flip_breakdown_2070.py`. Sample: `test_ru.jsonl`
30 hum + 30 ai, `pool_fpr_ru.jsonl` 60 hum. Logs: `logs/ru_thresh_2070_cpu.json`
(system Python, torch CPU, 278 s), `logs/ru_thresh_2070_gpu.json` (ROCm
`.venv-rocm`, 50 s).

- Humans (90): non-human verdicts 3→8 CPU (FPR 3.3%→8.9%), 4→8 GPU
  (4.4%→8.9%). Hard `→ai` flags: 1→1 on both (1.1%, unchanged). All new
  flags are `human→uncertain`.
- AI (30): TPR 93.3%→96.7% on both (one `uncertain→ai`).
- Shift is systematic upward: mean Δz +0.14 CPU / +0.16 GPU, max |Δz|
  1.73 / 2.18. Per-voter: essay_m +0.4…+0.7 z on flips, multi_m up to
  +5.0 z, stylo_d negligible. Cause: old en-forced cleaning Latinized
  Cyrillic lookalike words, depressing transformer scores; the fix restores
  real Russian input, so RU scores move up for humans and AI alike.
- CPU/GPU parity: identical verdicts except 1 borderline human
  (`gazeta:054367c`, flips on CPU only) — pre-existing bf16-vs-fp32 drift
  class, same as the documented DirectML drift in 2.0.6.0.

Decision: shipped 1.3.4 thresholds KEPT (no code change). Hard-ai FPR is
unchanged, the shift errs toward the safe `uncertain`, and TPR improves.
RU `uncertain`-rate on natural data rises ~5 pp — disclosed here; full
dev-set (`dev_ru.jsonl`, 800) threshold refit is scheduled follow-up work
before any renewed "1% FPR" claims for RU, not part of 2.0.7.0.

## RU 1.3.5 refit (18.10.2026) — candidate, NOT applied

Method: exact replica of `detektor/scripts/build_routing_131.py` quantile
rule on `dev_ru.jsonl` (400 hum), inputs scored with NEW (ru) cleaning,
mu/sd/weights KEPT from 1.3.4. Tool: `tools/ru_refit_135.py` (CPU, 44 min).
Candidate table: `calibration_routing_135/routing.json` (RU full tier only).
Live `%LOCALAPPDATA%/Linda-Pro` install untouched.

New vs shipped RU thresholds (old → new):
- ensemble: thr_sensitive -0.8471 → -0.3927, thr_p5 -2.0853 → -1.4037,
  thr_p1 -1.0531 → -0.5042, thr_p03 -0.6347 → -0.0949
  (dev FPR at sensitive 0.65% → 0.75%; order p5<sens<p03 holds)
- heat essay: thr_5 1.01 → 3.88, thr_05 3.89 → 7.29, thr_1 3.67 → 5.82,
  win_thr_1 3.40 → 5.58
- heat multi: thr_5 5.97 → 7.50, thr_05 8.70 → 9.78, thr_1 8.47 → 9.05,
  win_thr_1 8.10 → 8.97

Validation with new cleaning on full `test_ru` (406 hum + 406 ai) + 300
FPR-pool humans (`logs/ru_refit_135_valid.json`):
- hard FPR (→ai): 0.28% → 0.28% (same 2 texts, unchanged)
- non-human rate: 4.53% → 1.13% (design ~1% restored)
- TPR: 85.0% → 77.3% (−7.7 pp — the price of restored specificity)

Status: candidate ready for review. Applying = replacing the RU full tier
in the installed `routing.json` (with backup). A signed 1.3.5 release
through the update channel is a separate maintainer step.

## Humanizer (not in product, no code changes)

`детектор/experiments/style_benchmark_20261015/REPORT_V2.md` contradictions stay
as a research errata (perfect-retention 86.7% vs 73.3%, PL v1 40% vs 10%,
"97.5%→97.5%"). Recommendations unchanged: drop PL cross-lingual pairs or add
langid gate + regeneration, gate releases on "all facts + language" vs base,
blind human naturalness eval on ≥30 texts, fix the report numbers from raw logs.
