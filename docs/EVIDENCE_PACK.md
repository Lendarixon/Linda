# Linda-Pro: evidence package (updated 08.10.2026 for version 1.3.1)

> Version 1.3.1 results are in section 9; sections 1-8 describe versions 1.0 and 1.1 and are kept for history.


> Version 1.1 results (retrained against AI humanizers) are in section 8; sections 1-7 describe version 1.0.

> Note: sections 1-6 describe calibration v4; section 7 (v5) updates the production-mode numbers and supersedes them where they differ (e.g. TOEFL false positives 11.0% -> 8.8%). File paths below (`scripts/`, `eval/`, `models/`) refer to the internal development repository and are not part of this package.

What it is: a local (no cloud, no API) AI text detector for the English language. Composition: stylo7e (stylometry, CPU, strictly clean data), Linda-Essay v3 (DeBERTa-v3-large), Linda-Multi v2 (mDeBERTa). Text is cut into windows of ~300 words; verdict by the rule "Essay OR ensemble" (thresholds of 0.5% false positives for each; `uncertain` — gray zone 5%); outputs AI share by windows (mixed authorship). Code `scripts/linda_pro.py`, calibration `models/linda_pro/calibration_windowed_v4.json` (12 280 humans: essays, books, arXiv, ASAP, ELLIPSE, web, news, reviews, long texts), tests 42 (without models).

## 1. Against Pangram / GPTZero / Originality (Chicago Booth set, 1% threshold on set humans; competitor estimates — from the set authors' repository)
| system | standard AI (GPT-4.1, Claude Opus 4/Sonnet 4, Gemini 2.0), TPR % | after StealthGPT, TPR % |
|---|---:|---:|
| Pangram | 99.9 | 98.1 |
| GPTZero | 98.6 | 44.3 |
| Originality.ai | 94.2 | 29.1 |
| Linda-Pro (windows, ensemble stylo7e + Essay v3 + Multi v2) | 99.7 | 85.4 |
| Linda-Essay v3 (windows) | 99.2 | 73.0 |
We do not outperform Pangram; we are at its level on standard AI and noticeably higher than GPTZero and Originality on "humanized" texts.

## 2. Production mode (single threshold across diverse humans), "ai" shares %
Humans: Chicago (news, blogs, reviews, resumes, books) 0.2; ELL schoolchildren (ELLIPSE, 1500) 0.7; long humans (1030) 0.0; **TOEFL essays (91 texts) 11.0 — weak spot**. AI: Chicago 99.0; StealthGPT 67.8 (90.1 with "uncertain"); known AI control caught.
Linda-Essay v3 separately (windows, 1% threshold): Chicago false positives 0.45%.

## 3. Against open detectors (market benchmark, TPR@1%, average across 7 sets)
Linda-Essay v3 93.9; GigaCheck 88.4; EditLens (open Pangram) 65.4; Desklib 58.5; Binoculars 56.0. On tests of newest models: 92 and 95.

## 4. Mixed authorship
300 artificial documents from human/AI segments with known boundaries: correlation of AI share with true 0.94, MAE 0.088, segment AUC 0.94 (underestimates shares at 25–50%).

## 5. Limitations (honestly)
- English language. Russian and Polish: Linda-Multi v3 is trained, but when calibrated on web data false positives on Polish tests are 7–10% — not ready.
- Essays of adult non-native speakers (TOEFL): ~11% false positives on 91 texts.
- Competitor estimates are taken from public data of the set authors (2025), the set is easy (half of the humans are pre-2000 books); comparison with Pangram/GPTZero is not an independent audit.
- Not the sole basis for decisions on academic dishonesty.

## 6. Data provenance (levels)
- stylo7e: strictly clean line (open/permitted sources + generations by open models gpt-oss-20b and Gemma-4-12b; filters `scripts/stylo_strict.py`).
- Linda-Essay v3 and Linda-Multi: fine-tuned on data including frontier language model outputs from public datasets and own generations; full bill of materials — DATA_BOM.md.
- Calibration and tests: open corpora before 2022, list in reports; contamination checked (0 out of 9960 Chicago texts in training data).
Reproducibility: `eval/chicago_bench.py`, `eval/windowed_full.py`, `eval/esl_bench.py`, `eval/mixed_authorship_test.py`, reports in `eval/reports/`.

## 7. Update (v5): adult ESL, two modes, comparison with competitors on ESL
Calibration v5 (`calibration_windowed_v5.json`): 14 980 humans, added essays of adult English learners (W&I+LOCNESS, PELIC — calibration and verification only, not training: NC licenses). Two verdict modes:
- **sensitive** (by default, rule "Essay OR ensemble"); **precise** (for schools and universities: "ai" only if Essay is above 1% threshold AND stylometry is above 5% threshold).
Share of "ai" verdict on humans (test sets not participating in calibration), %:
| human set | sensitive | precise |
|---|---:|---:|
| Chicago (news, reviews, blogs, resumes, books), 1992 | 0.2 | 0.0 |
| ELLIPSE, ELL schoolchildren, 1500 | 0.7 | 0.1 |
| PELIC, adult ESL, 1000 | 0.8 | 0.3 |
| W&I, adult ESL, 280 | 1.1 | 0.0 |
| TOEFL (Liang), 91 | 8.8 | 1.1 |
| long humans, 1030 | 0.0 | 0.0 |
AI detection: Chicago 99.0 / 97.1; StealthGPT 67.2 / 46.2.
Competitors on ESL (vendor data, not an independent audit; default vendor thresholds): Pangram — ELLIPSE 0% (3907), ICNALE 0% (5600), PELIC 0.019% (15,423), TOEFL 0% (91), total 0.012% (Pangram blog, updated May 2026); GPTZero itself reports 1.1% on TOEFL (+6.6% "possibly AI"); Turnitin 1.4% on ESL according to Pangram's measurement. Fresh independent numbers not found (see `docs/research/gemini_modern_evals_20260930.md`). Our thresholds are 1% (theirs are on the order of 0.01%): in terms of strictness we are not comparable; on ELLIPSE, PELIC, W&I we are around 1% and below, on TOEFL 8.8% (sensitive) / 1.1% (precise).

## 8. Linda-Pro 1.1 (October 2026)
Changed: Linda-Essay-D and Linda-Multi-D (continued from v3 / v2), Stylo-D (stylometry retrained with the same data, no longer strict-clean), calibration v6 (same 14,980 human texts, thresholds recomputed). Sections 1-7 describe version 1.0.
Added training data: (a) 4,689 AI texts from open-weight models (gpt-oss-120b, qwen3-30b-a3b, llama-3.1-8b) through a commercial API, 2,344 of them rewritten in humanizer styles; (b) 817 real outputs of commercial AI humanizers
from two public benchmarks (AI Humanizer Benchmark, September 2026 cycle; independent humanizer audit record, June-July 2026), CC BY 4.0; (c) human texts as before. **HumanizerBench was not used for training** (untouched test).
Held out from training: the October 2026 cycle of the first benchmark (363 texts, 11 tools) and the August 2026 cycle of the second (231 texts).

Share of `ai` verdicts, `sensitive` mode, % (95% Wilson interval), AI-only sets unless marked:
| set | n | 1.0 | 1.1 |
|---|---:|---|---|
| HumanizerBench, all humanized texts (16 tools) | 1675 | 31.4 [29-34] | **69.9** [68-72] |
| HumanizerBench, September 2026 cycle (13 tools; the other 3 tools are in the all-texts row) | 361 | 34.3 [30-39] | 74.0 [69-78] |
| AI Humanizer Benchmark, October 2026 (held out) | 363 | 46.8 [42-52] | 81.8 [78-85] |
| AI texts of three unseen generators | 889 | 92.6 [91-94] | 93.0 [91-94] |
| MAGE subset, AI (short texts, many old small models) | 1400 | 50.5 [48-53] | 44.5 [42-47] |
| MAGE subset, humans (false positives) | 1400 | 0.9 [0-2] | 1.1 [1-2] |
| TOEFL essays, humans (false positives) | 91 | 8.8 [4-16] | 4.4 [2-11] |
`precise` mode: HumanizerBench 24.1 -> 57.7; October 2026 benchmark 35.5 -> 68.0; unseen generators 74.4 -> 79.4; MAGE AI 27.6 -> 20.2; TOEFL humans 1.1 -> 0.0.
False `ai` verdicts on other held-out humans (sensitive / precise), 1.0 -> 1.1: Chicago 0.2 / 0.1 -> 0.2 / 0.1; school ELL (ELLIPSE, 1500) 0.7 / 0.1 -> 1.1 / 0.2; adult ESL (PELIC, 1000) 0.8 / 0.3 -> 0.7 / 0.4; (W&I, 280) 1.1 / 0.0 -> 1.8 / 0.0; long texts (1030) 0.0 / 0.0 -> 0.0 / 0.0.
Public Chicago Booth benchmark (2025 humanizer version, windowed, 1% threshold on its humans): plain AI 99.7, after StealthGPT 82.9 (1.0: 85.4).
Commercial detectors on the same HumanizerBench texts (the benchmark operators' verdicts; we assume raw_score < 0.5 means detected; their thresholds are unknown, so false-positive rates are not comparable): Copyleaks 39.2%, GPTZero 47.7%, Originality.ai 47.2%, Winston 34.8%, ZeroGPT 19.3% (n = 1658-1675).
Caveats: (1) both benchmark operators are humanizer vendors or rankers, but publish all texts and verdicts; (2) the second benchmark's August cycle uses the same tools as its training cycles, so its near-100% is not independent evidence; HumanizerBench tools writehuman and stealthgpt also appear in the training sources, so only the all-texts row is clean;
(3) humanizers change monthly, so these numbers date quickly; (4) differences of 1-2 points on small human sets (W&I n=280, TOEFL n=91) are within sampling error; (5) not an independent audit.

## 9. Linda-Pro 1.3.1 (October 2026)
Weights 1.3.1: same architecture as 1.3.0 (merged Essay and Multi, Stylo-D, one rule per language), retrained without text generated by Llama 3.x models; learner essays (ASAP 2.0, IELTS sets) added; final Essay weights interpolated 50/50 with the preceding non-Llama model. Thresholds frozen on development human texts; the check sets below were not used for selection (the rule family and the candidate were chosen among alternatives on a benchmark that is also reported, so there is no clean out-of-sample guarantee). The 1.3.0 and 1.3.1 columns were computed with the same code and threshold rule on cached votes.
Share of `ai` verdicts, `sensitive` mode, %:
| set | n | 1.0 | 1.1 | 1.3.0 | 1.3.1 |
|---|---:|---:|---:|---:|---:|
| HumanizerBench, 16 tools | 1675 | 31.4 | 69.9 | 80.8 | **81.0** [79-83] |
| AI Humanizer Benchmark, Oct 2026 (held out) | 363 | 46.8 | 81.8 | 81.3 | 84.0 [80-87] |
| AI texts of three unseen generators | 889 | 92.6 | 93.0 | 94.6 | 95.5 [94-97] |
| MAGE subset, AI | 1400 | 50.5 | 44.5 | 45.9 | 46.6 [44-49] |
| Chicago Booth, plain AI (1% on set humans) | - | 99.7 | 99.7 | 99.8 | 99.8 |
| Chicago Booth, after StealthGPT | - | 85.4 | 82.9 | 86.6 | 88.0 |
| TOEFL humans (false positives) | 91 | 8.8 | 4.4 | 6.6 | 5.5 [2-12] |
| Chicago humans | 1992 | 0.2 | 0.2 | 0.1 | 0.2 |
| ELLIPSE humans | 1500 | 0.7 | 1.1 | 0.5 | 0.4 |
| PELIC humans | 1000 | 0.8 | 0.7 | 0.4 | 0.4 |
| W&I humans | 280 | 1.1 | 1.8 | 0.4 | 0.4 |
| MAGE humans | 1400 | 0.9 | 1.1 | 0.9 | **2.0** [1.4-2.9] |
Polish and Russian (our own sets): Polish test AI 79.4 [75-83] at 1.4% false flags (1.3.0: 80.0 at 0.9); Russian test AI 80.3 [76-84] at 0.6% (1.3.0: 78.3 at 0.6); one commercial model, Polish 95.7 / Russian 92.0; same model asked to humanize, Polish 56.1 / Russian 59.4 (1.3.0: 48.0 / 50.0); Russian school-essay AI texts 86.7 (n = 30; 1.3.0: 93.3). Precise mode was measured only for 1.3.0 (HumanizerBench about 69%, TOEFL 1.1%).
Caveats as in section 8, plus: false flags on MAGE human texts and on the Polish human test set are higher than in 1.3.0; evaluation is by the developer, not an independent audit.
