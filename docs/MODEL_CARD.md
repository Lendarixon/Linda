# Model card — Linda-Pro 1.0

Intended use: screening English texts for AI generation, showing per-window scores; human review required. Not intended: sole evidence for misconduct, employment or legal decisions; non-English text.
Training: see DATA_BOM.md. Evaluation: EVIDENCE_PACK.md (public benchmarks, held-out human sets). Known weaknesses: exam-style ESL essays (TOEFL), humanizer-rewritten text (85% vs 98% for the strongest commercial detector), essays by newest models under the ensemble (use Linda-Essay component / sensitive mode).
Ethics: false positives disproportionately affect non-native writers in all detectors; the `precise` mode reduces this at the cost of recall.
