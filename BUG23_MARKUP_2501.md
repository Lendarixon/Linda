# BUG23_MARKUP_2501 — token markup speed + verdict/markup agreement

Branch `night/fix-2.5.0.1`, repro pack `pack_15_nightly` (read-only), CPU only.

## Bug 2 — markup slower than scan

**Finding:** the batched window path from fbb09bc is present and correct:
`FastSeqCls.token_scores` passes `hidden_batch` to `pro_token_scores`
(voters.py:365), and `pro_token_scores` runs one forward per batch of
`voter.batch` windows. Verified bit-identical to the per-window path
(max |score diff| = 0.0 on a 3000-word EN text). The remaining cost is
compute-bound on CPU (torch pinned to 4 threads), not loop overhead:

| text | per-window | batched | forwards |
|---|---:|---:|---|
| 900 w | 3.64 s | 3.65 s | 7 -> 1 batch |
| 3000 w | 11.02 s | 10.61 s | ~21 -> 3 batches |

On this CPU batching does not beat per-window wall time because every
window is full-length (max_len=256) and the model is compute-bound;
fbb09bc's 45->9 win was on a GPU-backed mixed-length workload. No
per-window Python loop remains on the Pro path — nothing further to fix
without changing the model.

## Bug 3 — verdict 78% AI vs markup 0% AI

**Head selection and sidecar are correct, verified live on the owner's
~90-word EN text (full tier):**

* essay voice = `essay_dhi_131_20261008` (routing.json `essay_m`), NOT l14m50;
* head file = `tok_head.npz`, schema 2, voice=essay, lang=en;
* sidecar `calibration/token_heads_v2.json` IS applied
  (`calibration_source: sidecar`, center 3.0304 / scale 1.6107);
* lang detection = en; aggregation = mean of essay/multi token probs at
  thr 0.20.

Observed on the owner text: verdict **AI, p_ai 0.9404** (essay margin 8.29
vs thr_5 3.20 — clearly AI at document level), but token z p50 = -0.78,
max 0.34, so sentence p_ai ≈ 0.06 → all sentences "human". The schema-2
essay_en head (test AUC 0.762) genuinely does not separate this short
document at token level; on a clearly AI paragraph the same head flags
all sentences (p_ai 0.28–0.34 ≥ 0.20), so markup does agree with the
verdict when the head fires. The 0%-vs-AI case is a real head/verdict
scale mismatch on short texts, not a wrong-head or missing-sidecar bug.

## Tests

`tests/test_markup_2501.py` (5 passed): batched `hidden_for_windows`
invoked (single-window callback never called), EN head = essay_dhi
tok_head.npz with sidecar center/scale overriding the npz, per-lang head
selection in shared l14m50 dirs (pl vs ru), AI verdict ⇒ ≥1 AI sentence,
and markup wall-time bound on a ~1000-word sample.

Related suite: test_token_batching / test_token_heads_v2 / test_tokens_mode /
test_report_markup_labels / test_audit_tokens_calibration — 77 passed,
1 pre-existing failure (`test_rendered_header_uses_executed_detector_before_any_hooks`,
also fails on the unmodified tree).
