# Linda-Pro: evidence packet (30.09.2026)

> Note: sections 1-6 describe calibration v4; section 7 (v5) updates the production-mode numbers and supersedes them where they differ (e.g. TOEFL false positives 11.0% -> 8.8%). File paths below (`scripts/`, `eval/`, `models/`) refer to the internal development repository and are not part of this package.

What it is: local (no cloud, no API) AI text detector for the English language. Composition: stylo7e (stylometry, CPU, strictly clean data), Linda-Essay v3 (DeBERTa-v3-large), Linda-Multi v2 (mDeBERTa). Text is split into windows of ~300 words; verdict by the "Essay OR ensemble" rule (thresholds of 0.5% false positives for each; `uncertain` — gray zone 5%); outputs AI share by windows (mixed authorship). Code `scripts/linda_pro.py`, calibration `models/linda_pro/calibration_windowed_v4.json` (12 280 humans: essays, books, arXiv, ASAP, ELLIPSE, web, news, reviews, long texts), tests 42 (without models).

## 1. Against Pangram / GPTZero / Originality (Chicago Booth set, 1% threshold on set humans; competitor scores — from the set authors' repository)
| system | regular AI (GPT-4.1, Claude Opus 4/Sonnet 4, Gemini 2.0), TPR % | after StealthGPT, TPR % |
|---|---:|---:|
| Pangram | 99.9 | 98.1 |
| GPTZero | 98.6 | 44.3 |
| Originality.ai | 94.2 | 29.1 |
| Linda-Pro (windows, ensemble stylo7e + Essay v3 + Multi v2) | 99.7 | 85.4 |
| Linda-Essay v3 (windows) | 99.2 | 73.0 |
We do not outperform Pangram; we are on its level on regular AI and noticeably higher than GPTZero and Originality on "humanized" texts.

## 2. Production mode (single threshold across diverse humans), "ai" shares %
Humans: Chicago (news, blogs, reviews, resumes, books) 0.2; ELL school students (ELLIPSE, 1500) 0.7; long humans (1030) 0.0; **TOEFL essays (91 texts) 11.0 — weak spot**. AI: Chicago 99.0; StealthGPT 67.8 (90.1 with "uncertain"); known AI control caught.
Linda-Essay v3 separately (windows, 1% threshold): Chicago false positives 0.45%.

## 3. Against open detectors (market benchmark, TPR@1%, average across 7 sets)
Linda-Essay v3 93.9; GigaCheck 88.4; EditLens (open Pangram) 65.4; Desklib 58.5; Binoculars 56.0. On tests of newest models: 92 and 95.

## 4. Mixed authorship
300 synthetic documents from human/AI segments with known boundaries: correlation of AI share with the true one 0.94, MAE 0.088, segment AUC 0.94 (underestimates shares at 25–50%).

## 5. Limitations (honestly)
- English language. Russian and Polish: Linda-Multi v3 is trained, but with web calibration false positives on Polish tests are 7–10% — not ready.
- Essays of adult non-native speakers (TOEFL): ~11% false positives on 91 texts.
- Competitor scores are taken from public data of the set authors (2025), the set is easy (half of the humans are pre-2000 books); comparison with Pangram/GPTZero is not an independent audit.
- Not the sole basis for decisions on academic dishonesty.

## 6. Data provenance (levels)
- stylo7e: strictly clean lineage (open/permitted sources + generations by open models gpt-oss-20b and Gemma-4-12b; filters `scripts/stylo_strict.py`).
- Linda-Essay v3 and Linda-Multi: fine-tuned on data including frontier language model outputs from public datasets and own generations; full bill of materials — DATA_BOM.md.
- Calibration and tests: open corpora before 2022, list in reports; leakage checked (0 out of 9960 Chicago texts in training data).
Reproducibility: `eval/chicago_bench.py`, `eval/windowed_full.py`, `eval/esl_bench.py`, `eval/mixed_authorship_test.py`, reports in `eval/reports/`.

## 7. Update (v5): adult ESL, two modes, comparison with competitors on ESL
Calibration v5 (`calibration_windowed_v5.json`): 14 980 humans, added essays of adult English learners (W&I+LOCNESS, PELIC — calibration and validation only, not training: NC licenses). Two verdict modes:
- **sensitive** (default, "Essay OR ensemble" rule); **precise** (for schools and universities: "ai" only if Essay is above the 1% threshold AND stylometry is above the 5% threshold).
Share of "ai" verdict on humans (validation sets not involved in calibration), %:
| human set | sensitive | precise |
|---|---:|---:|
| Chicago (news, reviews, blogs, resumes, books), 1992 | 0.2 | 0.0 |
| ELLIPSE, ELL school students, 1500 | 0.7 | 0.1 |
| PELIC, adult ESL, 1000 | 0.8 | 0.3 |
| W&I, adult ESL, 280 | 1.1 | 0.0 |
| TOEFL (Liang), 91 | 8.8 | 1.1 |
| long humans, 1030 | 0.0 | 0.0 |
AI detection: Chicago 99.0 / 97.1; StealthGPT 67.2 / 46.2.
Competitors on ESL (vendor data, not an independent audit; vendor default thresholds): Pangram — ELLIPSE 0% (3907), ICNALE 0% (5600), PELIC 0.019% (15,423), TOEFL 0% (91), total 0.012% (Pangram blog, updated May 2026); GPTZero itself reports 1.1% on TOEFL (+6.6% "possibly AI"); Turnitin 1.4% on ESL as measured by Pangram. Recent independent numbers not found (see `docs/research/gemini_modern_evals_20260930.md`). Our thresholds are 1% (theirs are on the order of 0.01%): in terms of strictness we are not comparable; on ELLIPSE, PELIC, W&I we are around 1% and below, on TOEFL 8.8% (sensitive) / 1.1% (precise).
