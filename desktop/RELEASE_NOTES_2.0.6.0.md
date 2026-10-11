# Linda 2.0.6.0

Assay uses stable FP32 DirectML on Windows and FP32 CUDA on Modal. Loupe runs on CPU. This fixes a measured CPU/GPU discrepancy and makes context sampling consistent across devices. FP32 uses more GPU memory; 8 GB or more is recommended, and 4 GB compatibility has not been validated for this release.

Token evidence, model identity, Unicode offsets and document extraction are corrected. Highlighting, sentence counts, word coverage, analytics and exports follow the selected source. Document confidence and local coverage remain separate quantities; models may disagree and short AI inserts may be missed. Model weights remain 1.3.4.

Validation: 486 desktop regression tests passed; the earlier diagnostic corpus covered 84 distinct texts. CPU/GPU checks covered 30 controls, plus the complete The Exit locally. These are development checks, not an independent accuracy certification. The release installer and live Modal endpoint receive separate smoke checks recorded in the release evidence.

Store package version: 2.0.6000.0. An MSIX build is not Microsoft Store certification. The standalone installer is not Authenticode signed.
