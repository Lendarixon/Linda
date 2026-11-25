# Linda 2.5.0.3 — 22 November 2026

Windows app 2.5.0.3 with model pack 1.5.0: automatic first-launch download of installer-selected licensed packs and faster, bounded CPU generation for Humanizer-Lite, alongside all 2.5.0.1–2.5.0.2 detector, markup and installer fixes.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Installer-selected pack auto-download (`packs.maybe_install_installer_packs`)**: licensed Trace, Humanizer-Lite and Humanizer-Full packs selected during setup (`installer_choice.json["packs"]`) are now downloaded automatically on first licensed startup instead of requiring manual installation inside the app.
- **Faster, bounded Humanizer-Lite on CPU (`humanize_pack.py`)**: CPU runs now use 2 candidates (`_default_candidates`), single-chunk batching (`batch_chunks = 1`), explicit `eos_token_id` including `<|im_end|>`, chunk-sized `max_new_tokens` (<=220) and a 45 s per-chunk `max_time` cap so short texts never hang indefinitely.
- **Model pack 1.5.0 (`Lindarixon/Linda-Pro`)**: unchanged with all 61 SHA-256 verified files (~5.8 GB Pro on disk: EN `dhi` + PL/RU `l14m50`) and valid Ed25519 signature; DirectML peak VRAM ~3.9 GB on AMD Radeon RX 9070 XT.

## Bug fixes
- Fixed `installer_choice.json["packs"]` being ignored on startup after installation.
- Fixed Humanizer-Lite CPU generation hanging on short texts due to missing `<|im_end|>` stop token, prompt-inflated `max_new_tokens` and 4×4 FP32 CPU sequence batching.
- Retained all 2.5.0.1–2.5.0.2 fixes: zero-forward window-reuse markup fallback (`engine.py`), unified Pro token-markup threshold (`pro_token_thr_eff`), single checking spinner (`web/index.html`), installer `LicenseFileUsable` guard (`installer/linda.iss`), Python 3.12 repack guard (`tools/repack_exe.py`), model updater 0% / 32 MB stall fix, optional `routing.with_lite.json` fallback and restored PL/RU `l14m50` weights on Hugging Face.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design (the interactive keep/delete prompt is skipped unattended). External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC. The installer is unsigned, so Windows SmartScreen may warn.

**SHA-256 of Linda-Setup.exe:** 442b42176968bdc474ee6763ec32dcf7b36df58fc955e393a40282677c4ba4fe

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
