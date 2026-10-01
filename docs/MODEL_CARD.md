# Model card — Linda-Pro 1.1

Intended use: screening English texts for AI generation, showing per-window scores; human review required. Not for sole evidence of misconduct. English is the calibrated language; Russian and Polish work at moderate quality (indicative only: on our test sets the AI verdict catches about 63% of Russian and 51% of Polish AI texts at 0-1% false flags).
Architecture: ensemble of Stylo-D (LightGBM + n-grams, CPU), Linda-Essay-D (DeBERTa-v3-large, max_len 320) and Linda-Multi-D (mDeBERTa-v3-base, max_len 256), windowed scoring, calibration v6 on 14,980 held-out human texts.
Training: continued from Linda-Essay v3 / Linda-Multi v2 / stylo7e recipe on open-model AI texts, texts rewritten in humanizer styles, real outputs of commercial humanizers from two public CC BY 4.0 benchmarks, and human texts. See DATA_BOM.md.
Evaluation: EVIDENCE_PACK.md (sections 7-8). Known limits: humanizers evolve monthly, old small open models, non-native exam essays.
Licence: free for research and non-commercial use (CC BY-NC 4.0); commercial use needs a paid licence.
