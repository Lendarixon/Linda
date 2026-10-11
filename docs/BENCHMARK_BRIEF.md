# Linda — benchmark brief

Evidence cut-off: 11 October 2026. Current app 2.0.6.0, package 1.3.4. Historical full-tier weights/routing were introduced as 1.3.1; Lite/Loupe measurements below were published for the packaged 1.3.3 student pipeline. **The following table is historical developer evidence, not a fresh complete 2.0.6.0 evaluation.** Token/markup changes and the FP32 route require separate interpretation. No independent audit or overall accuracy percentage is claimed.

## Definitions

TPR is the share of labelled AI-origin texts assigned `ai`. FNR below is **100 − TPR**: it includes both `uncertain` and `human` outcomes, not just confidently human errors. FPR is the share of labelled human texts assigned `ai`. An AI-only set cannot establish FPR. Document metrics do not establish sentence/word-boundary accuracy. Rates are sensitive to threshold, mode, generator, date and genre.

## Historical sensitive-mode document results

| Dataset / population | Language | n / denominator | Assay TPR | Loupe TPR | Assay / Loupe FNR | Provenance and limitation |
|---|---|---|---:|---:|---|---|
| HumanizerBench, 16 tools | EN | 1,675 AI-origin humanized texts | 81.0% | 69.4% | 19.0% / 30.6% | Public benchmark outputs; not a human negative control; related tools occur in other training sources |
| AI Humanizer Benchmark, October 2026 | EN | 363 AI-origin rewrites | 84.0% | 75.8% | 16.0% / 24.2% | October cycle held out; tools/cycles can still be correlated with training |
| Three unseen generators | EN | 889 AI texts | 95.5% | 83.0% | 4.5% / 17.0% | Exact generator identities not consolidated in this summary; no claim of complete generator independence |
| Chicago Booth, ordinary AI | EN | Assay published full set; Loupe random subset n=1,500 | 99.8% | 97.0% | 0.2% / 3.0% | GPT-4.1, Claude Opus 4/Sonnet 4, Gemini 2.0 Flash; news, blogs, resumes, reviews, fiction; denominators differ |
| Chicago after StealthGPT | EN | 7,966 AI-origin texts in technical report | 88.0% | 55.6% | 12.0% / 44.4% | Humanizer version/date specific; not a claim to beat Pangram |
| MAGE AI subset | EN | 1,400 AI texts | 46.6% | 21.0% | 53.4% / 79.0% | Short/older generators, OPT/T5/GPT families and others; broad failure case |
| Polish labelled test | PL | Assay historical denominator not reconciled; current file 406 AI | 79.4% | 72.2% | 20.6% / 27.8% | Public Śmigiel-derived and added controls; historical Assay rates fit n=350, report/current file differs; cannot pool results |
| Russian labelled test | RU | Assay historical denominator not reconciled; current file 406 AI | 80.3% | 77.3% | 19.7% / 22.7% | Multiple source/model families; articles, questions, reviews, prose, abstracts; historical/current denominators differ |

| Human negative control | n | Assay FPR | Loupe FPR | Caveat |
|---|---:|---:|---:|---|
| TOEFL non-native essays | 91 | 5.5% | 2.2% | Small, specialized population; not general English FPR |
| Chicago human texts | 1,992 | 0.2% | 0.0% | Zero observed events does not imply zero population risk |
| MAGE humans | 1,400 | 2.0% | 0.4% | Diverse domains; results differ from TOEFL |
| Polish humans | current file 404; historical Assay n=350 | 1.4% | 1.5% | Denominator linkage requires reconciliation before confidence intervals |
| Russian humans | current file 406; historical Assay n=350 | 0.6% | 1.2% | Same limitation |

## Data and provenance

The evidence directory records current dataset hashes and available model/domain/source counts without publishing texts. Evaluation may include Llama-family outputs even though current shipped-model training is documented as excluding them; training and evaluation are different populations. PL metadata lacks genres for most rows, and some generator identities are missing. Do not invent missing labels. Training lineage is described in DATA_BOM.md and the 6 October licence audit. Some ancestor data have non-commercial or unresolved conditions; the vendor's commercial offer does not itself establish that all third-party rights are cleared. Stylo-Clean is a separate historical lineage, not a cleanliness claim for Assay/Loupe.

Historical reports disclose candidate/rule selection among benchmark alternatives. Frozen thresholds alone do not make every reported test fully independent. Re-check exact and source-level overlaps, keep source documents grouped, and report changes in filters or sample sizes. Never tune against the final pilot holdout.

## Runtime and current verification

Current release evidence reports 486 regression tests and a genuine isolated EXE control on RX 9070 XT: 10,594-word document, 740 sentences, Assay DirectML FP32 p_ai=0.9063, Loupe CPU p_ai=0.6316; complete run 22.14 s. Assay's equal-context CPU control matched all 740 labels. This is a consistency control, not labelled span-accuracy certification. A previous 84-case diagnostic EN/RU/PL set is small and uses existing development material.

The 3,800-word Loupe timing of 2.8 s on four threads / 9.7 s on one thread was measured on Ryzen 7 7800X3D for app 2.0.5.1. The older office-CPU estimate is not a current hardware guarantee. Do not reuse Assay FP16 timing or 1.6 GB VRAM statements as measurements for FP32 2.0.6.0. No new heavy inference was run for this brief.

## Pilot measurement protocol

Freeze app, model and routing hashes before collecting results. Use at least 100 independently sourced human and 100 AI-origin texts **per target language**, grouped by source document and stratified by genre, length, writer language background and generator. Keep edited-human and humanized-AI classes separate; paired rewrites share a source group. Record exact generators/prompts/dates where available; unknowns remain unknown. Have reviewers label evidence independently before reading detector outputs. Do not treat all non-`ai` outcomes as confidently human.

Report counts, TPR/FPR/FNR with denominators and Wilson 95% intervals, uncertain rate, subgroup outcomes, failed imports, median/p95 full-check time and hardware. Independently labelled mixed spans are needed for sentence/word precision, recall and boundary accuracy. Proposed pilot gates: FPR ≤2%, AI TPR ≥75%, uncertain ≤20% in each primary language cell, no critical workflow failures, 100% correct source/export identity on checked reports. These are acceptance proposals, not measured results or guarantees. Reject expansion if the sample is insufficient or the confidence bounds are unacceptable to the participant.

## Sources

- Internal `eval/reports/sites_131b.json` and `sites_131b_extra.json`: historical Assay rates.
- Internal `Desktop/Linda_release_1_3_2/lite_numbers.json`: packaged Loupe published values.
- Internal `Desktop/Linda_commercial_release/outreach/Linda-Pro_1.3.2_Lite_technical_report.md`: method, denominators and caveats; its old speed/availability text is not current release evidence.
- [Public evidence pack](https://github.com/Lendarixon/Linda/blob/main/docs/EVIDENCE_PACK.md), section 9; [data BOM](https://github.com/Lendarixon/Linda/blob/main/docs/DATA_BOM.md).
- [Technical report DOI](https://doi.org/10.5281/zenodo.23261670): published report version can lag local revisions; no new Zenodo upload is implied.
- `logs/release_2060/RELEASE_RESULT.md`, `logs/model_compare_20261011/RESULT.md`: current engineering checks.
