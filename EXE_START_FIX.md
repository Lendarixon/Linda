# EXE_START_FIX — Linda 2.5.0.1 silently does not start

## Root cause
`tools/repack_exe.py` was run with the **local Python 3.13**, but the BASE exe (and the shipped 2.5.0.1 exe) embeds **python312.dll (Python 3.12)**. The repack compiles `linda_desktop`/`linda_pro` sources via `compile()` + `marshal.dumps()` into the PYZ — Python 3.13 bytecode is incompatible with the 3.12 loader, so the exe dies instantly at the first `import linda_desktop` (exit code 0/−1, no output; windowed mode hides the traceback).

## Evidence
- TOC 's' entry of 2.5.0.0 vs 2.5.0.1: both `run_app`, pyver 312, python312.dll — loader identical.
- `_internal` trees: 18040 entries each, zero diff — webview/web/assets all present.
- `main()` bytecode in 2.5.0.1 exe starts `5e 00 95 00…` (3.13 opcodes) vs working 2.5.0.0 `00 00 2d 00…` (3.12 opcodes). Same source, different bytecode → wrong interpreter compiled it.
- Reproduced: 2.5.0.1 exe exits rc=0 in ~0.5 s with no log; 2.5.0.0 exe serves HTTP 200 on 127.0.0.1 in ~1 s.

## Fix
`tools/repack_exe.py` now self-checks `sys.version_info` and re-execs under Python 3.12 (`%LOCALAPPDATA%/Programs/Python/Python312/python.exe` or `LINDA_PY312`), failing loudly if 3.12 is missing. Repacked with 3.12.10 → `main` bytecode matches the working 2.5.0.0 exe byte-for-byte.

## Proof
Test exe (repacked from 2.5.0.0 base with current sources, Python 3.12) + full `_internal`:
`Linda-Pro.exe --no-ui` → instance.json written → `curl http://127.0.0.1:<port>/` → **HTTP 200, version 2.5.0.1, 2.2 s**.
