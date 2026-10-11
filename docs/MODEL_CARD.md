# Model card — Linda Assay and Linda Loupe

Current distribution: model package 1.3.4; Windows app 2.0.6.0 (11 October 2026). Old names: Linda-Pro and Linda-Pro Lite. Repository identifiers remain unchanged.

Assay: merged Essay-M (DeBERTa-v3-large), Multi-M (mDeBERTa-v3-base) and Stylo-D (LightGBM/ngrams). Document windows about 300 words, top25 aggregation; EN weights 0.8 Essay / 0 Multi / 0.2 style, PL/RU equal thirds. Multi can still provide independent local evidence for EN. Loupe: distilled ONNX student plus stylometry; EN 0.8 student / 0.2 style, RU/PL 0.8 student / 0.1 Stylo-D / 0.1 language-specific style. Decision rules are frozen in routing.json.

The current Loupe encoder config has 12 layers, hidden size 768 and 12 heads, consistent with multilingual-e5-base. The packaged speed_args.json still says e5-small; that provenance metadata inconsistency is disclosed and is not silently rewritten in a signed model release.

The Windows app uses Assay FP32 stable DirectML or CPU; Loupe CPU. Languages EN/PL/RU. Use for screening with human review, never as sole evidence of authorship or misconduct. Global confidence and local coverage are distinct. Short inserts and human-edited AI can be missed. Recommended Assay GPU memory is 8 GB; 4 GB unvalidated.

Historical full-tier weights were introduced as 1.3.1; Loupe historical document metrics were measured for the packaged 1.3.3 pipeline. Package 1.3.4 adds token outputs/heads. Small token heads are not independently validated for span accuracy; automatic Assay markup uses sentence/context evidence. [Benchmark brief](BENCHMARK_BRIEF.md) distinguishes historical accuracy and current engineering verification. No independent accuracy certification is claimed.

Training lineage, non-Llama filtering claims and limitations: DATA_BOM.md. Source rights are not fully consolidated; some ancestor data have NC/unresolved conditions. The separate Stylo-Clean model is not the same lineage as Assay's Stylo-D. Free personal non-commercial use under CC BY-NC 4.0; commercial licences cover app, CLI and models, with a separate free internal-evaluation pilot. See root licensing files.
