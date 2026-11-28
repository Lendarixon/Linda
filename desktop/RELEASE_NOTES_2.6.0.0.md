# Linda 2.6.0.0 & Model Pack 1.5.1 (Local Release, Unsigned)

## Highlights
- **Model Pack 1.5.1 (`D:\Linda_pack_1_5_1`)**:
  - Added `seg_v3` one-pass ONNX span segmenter (`mmBERT-small`, opset 17, `max |torch - ort| = 2.22e-06`).
  - Measured on 60 held-out EN/PL/RU documents (`l14_seg_dev.jsonl`, CPU 4 threads): **Sentence F1@0.5 = 0.9538** (EN 0.8702, PL 0.9396, RU 0.9946), **183 ms/doc** (up from 0.4249 F1 on v2 token heads).
- **Detector Engine (`linda_desktop/engine.py`, `linda_pro/segmenter.py`)**:
  - `auto` mode in Pro now prefers `seg_v3` when installed (with clean fallback to v2 token heads / window reuse), and reports `markup_backend`.
  - Added thread-safe 64-entry LRU result cache in `Engine.run()` (bypassed with `no_cache=True`, cleared on `unload()`).
  - `Segmenter.close()` releases ONNX session and tokenizer memory on `unload()`.
- **Humanizer (`linda_desktop/stylize_core.py`, `linda_desktop/humanize_pack.py`)**:
  - Added `strip_meta_wrapper()` (strips `<text>` tags and EN/RU/PL LLM preamble phrases), markdown-injection guard, and Latin/Cyrillic glued-word guards.
  - Added `pick_best_candidate()` ranking by natural edit distance (`~0.68` similarity) and length parity, plus `stats` in `humanize()` responses.
- **UI & EULA (`web/`, `installer/EULA.txt`)**:
  - Ported Linda Probe 2.0 polish: single-perimeter `:focus-within` rings, `LD_a11y` focus helper, accessible toast notifications, `Ctrl+Enter` / `Esc` shortcuts, quick EN/PL/RU sample chips, `Segmenter v3` / `Cached` header pills, and Humanizer word-level diff toggle.
  - Synced `installer/EULA.txt` with GitHub commit `611fd3d8`.
