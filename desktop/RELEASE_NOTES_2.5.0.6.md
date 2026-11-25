# Linda 2.5.0.6 — 25 November 2026

Windows app 2.5.0.6 with model pack 1.5.0: the models folder space check now uses the real size of the model pack instead of a fixed 6 GB, and the app and the installer say how much room the GPU model cache can take.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Models folder space from the real pack size**: Linda Assay with model pack 1.5.0 is about 5.8 GB (English networks plus the Polish/Russian pair), not the 2.9 GB the old fixed limit assumed. When you choose or move the models folder, the app now needs the size of your selected models plus a 1.5 GB margin (about 7 GB for Assay, about 2 GB for Loupe) and shows the exact figure if the folder is too small.
- **GPU model cache shown as a warning**: on a DirectX 12 graphics card the app saves a GPU copy of each Assay network the first time it is used (up to about 10 GB if you check all three languages with highlighting). The models page warns when the folder may not hold it (about 17 GB in total); it does not refuse the folder, because computers without such a card never build this cache.
- **Installer estimate**: the models page of the installer shows about 16 GB for Assay with cache instead of 8.7 GB.
- **All 2.5.0.5 fixes included**: detector VRAM release before humanization, hybrid GPU+CPU offload for Humanizer-Full 4B, adaptive DirectML VRAM budget, on-demand CUDA runtime, Russian Humanizer guards.

## Bug fixes
- The models folder check accepted folders with only 6 GB free, which cannot hold Assay's 5.8 GB of models plus room to stage an update.
- The "not enough space" message always said "about 6 GB"; it now shows the computed figure in English, Polish and Russian.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0, unchanged).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design. External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC.

**SHA-256 of Linda-Setup.exe:** 5cf7807cef544ddde806414d437ee53ce81017721230d26432aad0a5839d687d

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
