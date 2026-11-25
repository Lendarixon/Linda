# Linda 2.5.0.5 — 24 November 2026

Windows app 2.5.0.5 with model pack 1.5.0: fixes Humanizer-Full 4B falling back to Lite on 8 GB NVIDIA GPUs (such as RTX 5060) by unloading the detector before single-pass humanization, clearing the CUDA allocator cache, and adding universal hybrid GPU+CPU offload via `accelerate`.

Only the installer (`Linda-Setup.exe`) is attached to this release; the source code archives are added automatically by GitHub.

## What is new
- **Single-pass detector VRAM release (`app.py`, `engine.py`)**: `_humanize()` now unloads the detector before loading the humanizer (matching `_humanize_loop()`), and `Engine.unload()` calls `torch.cuda.empty_cache()` so freed CUDA VRAM is immediately available to `HumanizerBackend.load()`.
- **Universal hybrid GPU+CPU offload for Humanizer-Full 4B (`humanize_pack.py`)**: GPUs with `4.0–8.9 GB` free VRAM (including 8 GB cards like RTX 5060) now automatically split Qwen3-4B across CUDA VRAM and system RAM via `accelerate.infer_auto_device_map` + `dispatch_model` (`batch_chunks = 1`), while `9.0+ GB` free VRAM cards keep 100% GPU residency (`batch_chunks = 4`).
- **All 2.5.0.4 fixes included**: adaptive DirectML VRAM budget & cp1251 error decoding (`onnx_gpu.py`, `routed.py`), on-demand NVIDIA CUDA `cu128` runtime, token-based CPU humanizer budget (cap 420), Russian completeness/numeral/glued-word guards, and single-GPU UI hint hiding.

## Bug fixes
- Fixed `Humanizer-Full` (4B) falling back to `Lite` on 8 GB NVIDIA RTX 5060 when detector models remained resident in CUDA VRAM and when `bf16` 4B weights slightly exceeded free VRAM.
- Fixed `Engine.unload()` not releasing PyTorch's CUDA caching allocator memory.

## Licence and packs
Personal non-commercial use is free; commercial use and optional Trace and Humanizer packs require a licence key. Models download from Hugging Face `Lindarixon/Linda-Pro` (pack 1.5.0).

## Limits
Silent uninstall (`/SILENT`) always preserves downloaded models, settings and licence keys by design. External PL set (SMIGIEL/PolEval 2025, CC BY-4.0, n=6934 humans): FPR 2.86% — short prose is the known weak spot. RU token F1 at the fixed 0.20 threshold is conservative — read the AUC. The installer is unsigned, so Windows SmartScreen may warn.

**SHA-256 of Linda-Setup.exe:** 075725bf2fcf90e7de29037db4baddfe35775775ca05e5a35958b248807ce5fb

Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.
