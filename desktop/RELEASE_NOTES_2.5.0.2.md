# Linda 2.5.0.2 — 22 November 2026

Windows app 2.5.0.2 hotfix with model pack 1.5.0: instant zero-forward sentence-markup fallback removing DirectML/CPU slowdowns on short and medium texts, plus all 2.5.0.1 installer, updater and unified-channel fixes.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Instant zero-forward window-reuse fallback (`engine.py`)**: in Pro `auto` mode, when the document ensemble signals strong AI/uncertain (`p_doc > 0.80`) and the token head marks 0 AI sentences, markup now reuses the scan windows already computed during `detect()` (`0` extra model forwards instead of running extra per-sentence passes). Verified 7.5x faster on CPU (`1.56s` vs `11.72s` on a 160-word report) and eliminates sequential `batch=1` DirectML GPU stalls.
- **Model pack 1.5.0 (`Lindarixon/Linda-Pro`)**: unchanged with all 61 SHA-256 verified files (~5.8 GB Pro on disk: EN `dhi` + PL/RU `l14m50`) and valid Ed25519 signature; DirectML peak VRAM remains ~3.9 GB on AMD Radeon RX 9070 XT.

## Bug fixes
- Removed the slow `hybrid`/`context` fallback loop from 2.5.0.1 that triggered `4 × N` sequential `batch=1` DirectML forwards when token-head fallback fired.
- Retained all 2.5.0.1 fixes: unified Pro token-markup threshold (`pro_token_thr_eff`), single checking spinner (`web/index.html`), installer `LicenseFileUsable` guard (`installer/linda.iss`), Python 3.12 repack guard (`tools/repack_exe.py`), model updater 0% / 32 MB stall fix, optional `routing.with_lite.json` fallback, and restored PL/RU `l14m50` weights on Hugging Face.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design (the interactive keep/delete prompt is skipped unattended). External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC. The installer is unsigned, so Windows SmartScreen may warn.

**SHA-256 of Linda-Setup.exe:** f36afc4c1bbdd71a2274608cf2c281f96c062ee468f611fe6bdbd03d4334b529

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
