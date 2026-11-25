# Linda 2.5.0.1 — 22 November 2026

Windows app 2.5.0.1 with model pack 1.5.0: unified document-to-sentence markup channel, installer reuse and multi-pack improvements, Python 3.12 packaging fix, and model updater fixes.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Unified Pro verdict and sentence-markup channel**: when the calibrated document ensemble reports a strong AI/uncertain signal (`p_doc > 0.80`), Pro token-head markup smoothly lowers its AI threshold (`pro_token_thr_eff`) toward `0.05`, and in `auto` mode automatically falls back to the document voters' own `hybrid`/`context` sentence scoring if the token head still flags 0 AI sentences — preserving 0% AI on human texts and Lite's `0.815` calibration.
- **Installer UX, packs and reuse**: EN (default), RU and PL languages; independent checkboxes for optional Trace, Humanizer-Lite and Humanizer-Full packs; dynamic model and cache size estimates; cross-profile reuse of saved models and licence keys on reinstall; interactive keep-data uninstall prompt; automatic shutdown of running `Linda-Pro.exe` instances before replacing files.
- **Model pack 1.5.0 verified (`Lindarixon/Linda-Pro`)**: all 61 manifest files (~5.8 GB Pro on disk: EN `dhi` + PL/RU `l14m50`) SHA-256 verified with valid Ed25519 signature; DirectML peak VRAM measured at ~3.9 GB on AMD Radeon RX 9070 XT.

## Bug fixes
- Python 3.12 repack guard added in `tools/repack_exe.py` (fixes silent exit on startup caused by 3.13 bytecode in PYZ).
- Model updater 0% / 32 MB stall fixed via effective-manifest `files_to_fetch` / `is_complete` calculation.
- Optional `calibration/routing.with_lite.json` HTTP 404 now falls back cleanly to `calibration/routing.json`.
- Duplicate checking spinner removed in `web/index.html` (spinner stays inside the Check button only).
- Installer `LicenseFileUsable` now skips stale/unvalidated `license.json` stubs with `expires_at: null` (without `gift` or `perpetual: true`), so valid licences from other profiles are picked up reliably.
- Orphan `.ok` markers no longer block set folder removal; perpetual Polar keys (`expires_at: null`) no longer fail closed; test-build profile isolation (F2) fixed.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design (the interactive keep/delete prompt is skipped unattended). External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC. The installer is unsigned, so Windows SmartScreen may warn.

**SHA-256 of Linda-Setup.exe:** de4d4142ce1c158f99ce19bd331aa20bd664357590f22775ec0e2d8ca062da69

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
