# Linda 2.5.0.4 — 23 November 2026

Windows app 2.5.0.4 with model pack 1.5.0: fixes DirectML VRAM out-of-memory and GPU reset crashes on 4 GB and 8 GB graphics cards, fixes Russian text truncation and numeral agreement in Humanizer, and adds on-demand PyTorch CUDA (cu128) runtime support for Humanizer-Full 4B on 8+ GB NVIDIA GPUs.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Adaptive DirectML VRAM budget & error decoding (`onnx_gpu.py`, `engine.py`, `routed.py`)**: `ModelPool` now scales its VRAM budget to the actual GPU (`2000 MB` on 4 GB cards like GTX 1650 SUPER, `3200 MB` on 6–8 GB cards like RTX 5060, `5200 MB` on 12+ GB cards) and evicts resident models / main sessions before loading `model_tok.onnx`, preventing simultaneous 3-session VRAM OOM (`0x8007000E`) and driver TDR resets (`0x887A0006/7`). Non-English Windows cp1251/mbcs DirectML errors are now decoded properly instead of masking the cause behind `UnicodeDecodeError`, with automatic `device_id` fallback on `887A0002` and metacommand retry on TDR.
- **On-demand NVIDIA CUDA (cu128) runtime for Humanizer-Full 4B (`humanize_pack.py`, `__init__.py`, `app.py`)**: lowers `FULL_MEM_GB` from `9.0` to `7.5` GB so 8 GB GPUs (e.g. RTX 5060) qualify, installs the matching PyTorch `cu128` wheel into `packs/humanizer/cuda_lib` without requiring `pip` in the frozen bundle, prompts for restart instead of silently falling back to `lite`, and surfaces `fallback_reason` in UI/logs whenever a fallback occurs.
- **Token-based CPU budget & Russian quality guards (`humanize_pack.py`, `stylize_core.py`)**: CPU `max_new_tokens` is now computed from actual chunk tokens (`min(420, int(raw_toks * 1.35) + 24)`) instead of `words * 1.6` capped at `220`, preventing silent mid-paragraph truncation on Russian (~2.2–2.4 tokens/word). Added Russian completeness, numeral-agreement (`1,8 процента`, `4 процента`), and glued-word (`берБанка`) candidate guards.
- **UI polish (`web/index.html`)**: hides the multi-GPU selection hint (`#lpGpuHint`) when only one graphics card is present and displays `fallback_reason` in the Humanizer status line.

## Bug fixes
- Fixed `RuntimeError: DirectML session is unavailable` (`E_OUTOFMEMORY` `0xcd` / `DEVICE_HUNG` `0xc3` masked by UTF-8 decoding) on 4 GB and 8 GB NVIDIA GPUs.
- Fixed Humanizer-Lite CPU truncation on Russian paragraphs longer than ~93 words.
- Fixed Humanizer-Full 4B silently falling back to Lite on 8+ GB NVIDIA GPUs due to the bundled `torch+cpu` build and `9.0` GB gate.
- Fixed Russian decimal/integer numeral agreement errors and glued CamelCase words passing candidate filtering.
- Fixed the stray "If the wrong card is used, try another one" hint remaining visible on single-GPU systems.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design. External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC. The installer is unsigned, so Windows SmartScreen may warn.

**SHA-256 of Linda-Setup.exe:** e7b081e9e9020bcb33cc8860a2beec4d10f846c1e182633f43a5df559372349f

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
