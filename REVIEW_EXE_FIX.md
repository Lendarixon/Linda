# REVIEW_EXE_FIX.md — Second-Opinion Review (2.5.0.1 EXE Start Fix)

**Verdict: FAIL** (root-cause diagnosis and 3.12 rebuild are sound, but commit `55cb499` has a Windows `os.execv` race/import defect in `tools/repack_exe.py`, lacks base-exe header/cookie assertions, Desktop `2.5.0.1` artifacts are still un-rebuilt, and `--no-ui` alone is insufficient for final GUI sign-off).

---

## Findings by Review Question

### (a) Diagnosis (Python 3.12 vs 3.13 bytecode mismatch) — CONFIRMED
- `C:\Users\ninja\Desktop\Linda_2.5.0.1\app\_internal\python312.dll` is embedded, and the PyInstaller CArchive cookie in `Linda-Pro.exe` (`2.3.0.2`, `2.4.0.0`, `2.5.0.0`, `2.5.0.1`) reports `pyvers=312`, `pylib=b'python312.dll'`, with PYZ header magic `cb0d0d0a` (Python 3.12).
- `tools/repack_exe.py` compiles `linda_desktop`/`linda_pro` modules and `run_app.py` via the active interpreter's `compile()` + `marshal.dumps()`, while copying `header_magic = old[4:8]` (`cb0d0d0a`) verbatim from the base PYZ.
- Direct binary inspection of `C:\Users\ninja\Desktop\Linda_2.5.0.1\app\Linda-Pro.exe` (built `2026-11-22 01:36`) confirms `run_app`, `linda_desktop`, and `linda_desktop.__main__` all start with opcode `149` (Python 3.13 `RESUME`; `co_code[:8]` of `linda_desktop.__main__` is `9500530072005301`, `main()` is `5e00950064006313`), whereas working `2.3.0.2`/`2.4.0.0`/`2.5.0.0` start with opcode `151` (Python 3.12 `RESUME`; `linda_desktop.__main__` `970064005a006401`, `main()` `8700970089008013`).
- Because both 3.12 and 3.13 use `marshal.version == 4` and `repack_exe.py` preserves `cb0d0d0a`, `python312.dll` unmarshals 3.13 code objects without error; in 3.12 opcode `149` is `COPY_FREE_VARS` followed by `RETURN_VALUE` at offset 2, causing `run_app` to exit immediately (`exitCode=0`, no `instance.json`, no `app.log` — reproduced directly on Desktop `2.5.0.1`).
- *(Minor doc note: `EXE_START_FIX.md` line 9 lists `00 00 2d 00…` for `2.5.0.0` `main()`, whereas actual `2.5.0.0` `main()` starts `87 00 97 00 89 00 80 13`.)*

### (b) Proposed Fix & Bytecode Compatibility — DEFECTS IN `55cb499`
- **Bytecode output:** Running `tools/repack_exe.py` under Python `3.12.10` (`magic=cb0d0d0a`, `marshal=4`, `RESUME=151`) produces byte-for-byte matching bytecode (`linda_desktop.__main__`: `970064005a006401`, `main()`: `8700970089008013`) and boots `--no-ui` cleanly (`HTTP 200`, `version=2.5.0.1`, `1.86s`).
- **Defect 1 — Windows `os.execv` race & quoting bug (`tools/repack_exe.py:29`):** On Windows, `os.execv` wraps MSVC `_execv`, which spawns a detached child process and immediately terminates the caller with `rc=0`. Tested empirically from Python 3.13: a `subprocess.run()` parent returned in `0.11s` with `rc=0` while a `1.5s` child ran asynchronously, and `_execv` split whitespace-containing args unquoted. Any build script invoking `repack_exe.py` via Python 3.13 can race `stamp()`/`ISCC` against an unfinished exe write and swallow errors.
- **Defect 2 — Top-level side-effect (`tools/repack_exe.py:24-32`):** Putting the re-exec guard at module top-level breaks `import repack_exe` under Python 3.13 (e.g., `tools/verify_release_2100.py:13` immediately re-execs `repack_exe.py` as `__main__` instead of importing constants/helpers, exiting `0`).
- **Defect 3 — Shipped/Desktop artifacts not yet rebuilt:** `C:\Users\ninja\Desktop\Linda_2.5.0.1\app\Linda-Pro.exe` (`01:36`) and `Linda-Setup.exe` (`01:38`) still contain the broken 3.13 bytecode.

### (c) Python 3.13-Only Constructs — CLEAN
- `compile(..., dont_inherit=True, optimize=0)` under Python `3.12.10` passed on all **68** files (`linda_desktop/**`, `linda_pro/**`, `run_app.py`, `run_store.py`) with **0** errors.
- AST scan across all 68 files for 3.13-only constructs (PEP 696 type-param defaults, `copy.replace`, `glob.translate`, `warnings.deprecated`, `base64.z85*`, `argparse.deprecated`, `functools.Placeholder`, `pathlib.Path.full_match`, `os.process_cpu_count`, `itertools.batched(..., strict=...)`) found **0** hits.

### (d) Proof-of-Start Test (`--no-ui` + curl `instance.json`) — NECESSARY, NOT SUFFICIENT
- `--no-ui` + `curl http://127.0.0.1:<port>/` verifies PyInstaller bootstrap, `python312.dll`, `run_app`, `PYZ` unmarshaling, `uvicorn`/FastAPI startup, and `instance.json` creation (catches the 3.13 bytecode bug).
- However, `linda_desktop/__main__.py:239-280` skips `linda_desktop.splash.show_splash` (`tkinter`/`tcl86t.dll`/`tk86t.dll`), `pywebview` (`webview.create_window`/`start`, WebView2, `window_recovery`), lazy model/corpus imports (`torch`, `transformers`, `linda_desktop.trace_corpora`, `linda_pro.segmenter`), and `/api/status`/`/api/detect` when `--no-ui` is set.

### (e) `release_2400.py` & Future Releases Guard
- `tools/release_2400.py:100` (and `tools/release_2501.py:100`, `tools/build_store_2400.py:50`) already assert `sys.version_info[:2] == (3, 12)` in `build()`, and pass `sys.executable` to `repack_exe.py`.
- Note: `release_2400.py` / `release_2501.py` `resume` branch (`if sys.argv[1:] == ['resume']:`) skips the 3.12 assert (safe today since `resume` only runs ISCC+finalize), and `tools/release_2501.py` is currently untracked in git (with stale `2.4.0.0` docstring).
- `tools/repack_exe.py` had no guard before `55cb499` when invoked directly, and still lacks validation that the BASE exe's `pyvers` cookie and `PYZ` `header_magic` match the running Python (`importlib.util.MAGIC_NUMBER[:4]`).

---

## Required Changes Before Sign-Off
1. **Fix `tools/repack_exe.py` guard:** Move the Python 3.12 check into `main()` (keep module import-safe for `verify_release_2100.py`), and either fail loudly with `assert sys.version_info[:2] == (3, 12)` / `SystemExit` or replace `os.execv(...)` with synchronous `raise SystemExit(subprocess.call([_py312, str(Path(__file__).resolve()), *sys.argv[1:]]))` so callers never race or lose exit codes/quoted args on Windows.
2. **Validate BASE exe Python compatibility in `tools/repack_exe.py`:** Assert `pyvers == sys.version_info[0] * 100 + sys.version_info[1]` (cookie) and `header_magic == importlib.util.MAGIC_NUMBER[:4]` (`rebuild_pyz`) so future Python upgrades cannot silently produce corrupt bytecode.
3. **Rebuild & commit release script:** Rebuild `Linda_2.5.0.1` (`Linda-Pro.exe`, `Linda-Setup.exe`, `SHA256.json`) via `tools/release_2501.py` under Python 3.12 (and track/clean up `tools/release_2501.py` docstring).
4. **Run full post-rebuild verification:** Run `tools/qa_smoke_2400.py` against the rebuilt `Linda_2.5.0.1\app\Linda-Pro.exe` AND verify at least one windowed (non-`--no-ui`) launch confirms splash + WebView2 window startup.
