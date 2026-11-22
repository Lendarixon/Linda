# VERIFY_2501_LANG_INSTALL.md — 2.5.0.1 verification (branch night/fix-2.5.0.1)

## 1. Installer languages (installer/linda.iss, [Languages] lines 62-65)
- L63: `Name: "english"; MessagesFile: "compiler:Default.isl"` — **DEFAULT (first entry)**
- L64: `Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"`
- L65: `Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"`
All three present; english is first → default. No .isl bundled via Files: (compiler built-ins used).

## 2. E2E model install (throwaway profile under scratch, real HF network)
- Source: HF `Lindarixon/Linda-Pro` pack `packs/1.5.0-nightly/manifest.json`, version **1.5.0-nightly** (release manifest `latest.json` v1.5.0 at repo root references `calibration/token_heads_v2.json`, which 404s at root — exists only under packs/; noted as a release-side issue, not app).
- LITE set (`model_sets: ["lite"]`, 12 files, 0.291 GB): downloaded all 12 files, staged, applied → `apply version: 1.5.0-nightly`, **is_complete: True**, **12 `.ok` markers**, 291.5 MB on disk, `installed_version` = 1.5.0-nightly.
- PRO set (11.5 GB incl. ONNX): download progressed (network ~1.5-67 MB/s) but pack manifest lists files not yet uploaded (e.g. `tok_head_v1_backup.npz` 404) → full PRO completion blocked by release upload, not by app code.
- Device selection (code-verified, no inference run): `engine.pick_device("cpu")` → `"cpu"`; GPU path `"dml"` uses ONNX fp32 builds (`onnx/fp32_stable_v1/*/model.onnx`), CPU uses safetensors. CPU-only honored.

## 3. VRAM note (ONNX fp32 sizes from manifest)
- essay_dhi 1742 MB + essay_l14m50 1742 + multi_dhi 1116 + multi_l14m50 1116 = 5716 MB weights (~5.7 GB) + heads/activations ~1-2 GB → **~8 GB VRAM** total.
- Added to `SetsPro`/`SetsBoth` labels EN/RU/PL in linda.iss:
  - EN: "on a GPU it uses ~8 GB VRAM (fits 8 GB cards, slower on less)"
  - RU: "на видеокарте занимает ~8 ГБ VRAM (влезает в 8 ГБ, на меньших медленнее)"
  - PL: "na karcie graficznej zajmuje ~8 GB VRAM (mieści się w 8 GB, na mniejszych wolniej)"
