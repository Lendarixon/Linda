# Night 2501 — Linda 2.5.0.1 release readiness

Branch `night/fix-2.5.0.1`. Work dir `work/night_2501/`. All runs foreground on CPU
(`PYTHONPATH`/`PYTHONHOME` unset), no release, no push of the release artifact.
HF repo `Lindarixon/Linda-Pro`, models version **1.5.0** (59 manifest files, 3.22 GB).

## Verdict

**Release-ready after the root-file restore.** The one release blocker — three HF
root files that no longer matched the signed manifest — is fixed and all 59 manifest
paths now verify. Two installer findings are documented below; one is now fixed in
`installer/linda.iss`, one is accepted as a known limitation.

## P1 — test suite

`pytest` on the branch: **732 passed, 0 failed, 0 skipped** in 149.1 s (2:29).
Log: `work/night_2501/p1_pytest_final.log`.

## P2 — installer E2E scenarios a–g

Build: `work/night_2501/inst/Linda-Setup.exe` (ISCC 6, `/DTestInstall=1` → own AppId
`{E57A11B0-…}`, own data dir `%LOCALAPPDATA%\Linda-Pro (test)`, payload from
`Desktop\Linda_2.5.0.1\app`). Runner `tools/night_2501_scenarios.py`.
Details: `work/night_2501/scenarios.md`, machine-readable `scenarios.json`.

| # | Scenario | Exit | Time |
|---|----------|------|------|
| a | fresh EN `/SILENT /LANG=english` | 0 | 58.2 s |
| b | fresh RU `/LANG=russian` | 0 | 58.8 s |
| c | upgrade over fake 2.5.0.0 + saved manifest | 0 | 62.6 s |
| d | install while `Linda-Pro.exe` runs | 0 | 62.1 s |
| e | `/MODELSET=lite`, `/MODELSET=pro` | 0 / 0 | 61.9 / 62.5 s |
| f | uninstall `/SILENT` keep-data vs full | 0 / 0 | 62.6 / 61.7 s |
| g | corrupt manifest (404 stub) | 0 | 59.8 s |

All seven exit 0. (a) installs 15 780 files with `Linda-Pro.exe` + `unins000.exe`;
(c) reuses the saved model folder and leaves `manifest.json` byte-intact;
(d) terminates the running image; (e) writes `["lite"]` / `["pro"]` into the choice
file; (g) yields `UpdateError` + job `phase=error`.

## P3 — real model download (this is where the blocker was)

Original lite run: **20/21 files**, then abort —
`calibration/routing.json` → `download is larger than announced`
(`work/night_2501/p3_lite.json`, `p3_probe.json`). Cause: root copy of
`routing.json` was 8206 B / `645224c7…` while the signed manifest lists 4561 B /
`29ccc66d…`; the same drift hit `models/essay_dhi_131_20261008/tok_head.npz`
(5368 vs 6130 B) and `models/multi_dhi_131_20261008/tok_head.npz` (4344 vs 5106 B).
The manifest-correct bytes were still present under `packs/1.5.0-nightly/`.

Fix: those three `packs/1.5.0-nightly/` blobs were sha-verified against the manifest
and committed back to the root paths in one HF commit —
`restore manifest-consistent calibration+tok_head files at root`.

Re-verify after the fix (`tools/night_2501_p3_download.py --sets lite`):
**21/21 files, sha256 all match, `.ok` markers match, `is_complete: true`,
0 problems**, 300 562 238 B in 6.9 s (43.6 MB/s). Set sizes from the manifest:
shared 4.9 MB, lite 295.7 MB, **pro 2 919 176 888 B = 2.92 GB**.

Manifest-path sweep of the live repo: **59/59 HEAD 200 and 59/59 size match**
(3 219.7 MB total). Signature still valid: `updater.get_manifest()` verified the
Ed25519 signature over the unchanged `latest.json` (v1.5.0).

## P4 — VRAM under DirectML

`work/night_2501/p4_vram_dml.json`: ONNX essay_fp32 (graph 1741.9 MB), max_len 256,
`DmlExecutionProvider`, AMD RX 9070 XT 16 GB. Load 2.5 s.
Peak after forward: **3997.5 MB ≈ 3.9 GB** (shared 3979.0 MB) — under the 4 GB
target.

## P5 — UI screenshots

`tools/night_2501_p5_served.py` served the real page (same injection order as
`linda_desktop/app.py`). **5 PNGs, all valid**, 1560 px wide:
`01_start.png`, `02_models.png`, `03_update_downloading.png`,
`04_update_failed.png`, `05_verdict.png` (`work/night_2501/ui/`).
The failed-update shot is the P3 blocker as the user would have seen it.

## P6 — build artifacts

`Desktop\Linda_2.5.0.1\SHA256.json`:

- `Linda-Setup.exe` — 509 276 837 B, sha256 `b134193c088e5c5b3c29457973cc44082b7d1ce274a493f6da6c0d6c5c1e6fc2`
- `app\Linda-Pro.exe` — 79 048 541 B, sha256 `6f07217f861c523b7f8834535012075f42ac9618bee90f28a95cf99b90043c90`

Both match the recorded `.sha256` sidecar files.

## Findings

### F1 — silent uninstall cannot remove data (accepted, documented)

`CurUninstallStepChanged` (installer/linda.iss) runs its delete branch only under
`and (not UninstallSilent)`, and the branch is the body of an interactive MsgBox.
Inno cannot show a dialog in silent mode, so a `/SILENT` uninstall always keeps
models/settings/licence. **Decision: acceptable for 2.5.0.1.** It is a fail-safe
direction (never destroys GB of models or a licence key unattended), and the
keep/delete question has no safe non-interactive default. Documented as a known
limitation; a `/KEEPDATA=0` parameter is the follow-up if corporate rollout needs
silent cleanup. Code reference: `CurUninstallStepChanged`, `UninstallKeep` message.

### F2 — `reuse_models: true` on a *fresh* install (fixed)

Scenario (b) wrote `"reuse_models": true, "reuse_version": "1.3.4.1"` into a fresh
install's `installer_choice.json`. Cause: `FindSavedModels` stage 2 scanned every
`%LOCALAPPDATA%\Linda-Pro*` folder, so the TestInstall build adopted the owner's real
2.5.0.0 profile. The reuse branch itself was correct — the scan was too broad.

Fix in `installer/linda.iss` (35+/6-):

- new `AllowForeignProfileReuse` — returns False under `#ifdef TestInstall`, True for
  production. Deliberately **not** gated on `WizardSilent`, because the app's own
  `/SILENT` self-update depends on reuse finding the previous profile.
- new `IsLindaProfile(P)` — a foreign folder is only a candidate if it carries a
  profile marker (`license.json`, `settings.json`, `installer_choice.json`,
  `models_location.json`); stray `Linda-Pro*` leftovers no longer qualify.
- stage 2 additionally skips the candidate whose path equals the current `DataDir`
  (already handled in stage 1) and stage 3 is gated by the same flag.

Both `installer/linda.iss` and `installer/linda.iss /DTestInstall=1` recompile with
ISCC 6: **successful compile, 0 errors, 0 warnings**. Production reuse across
profiles, including silent self-update, is unchanged.

### F3 — HF root drift (fixed)

See P3. Three root files restored from `packs/1.5.0-nightly/`, sha-verified before
upload, single commit, `latest.json` untouched so the signature remains valid.

## Open items

- The owner's real `%LOCALAPPDATA%\Linda-Pro-2500` profile makes this machine
  non-clean for "fresh install" scenarios; the F2 fix makes the test build ignore it,
  so future scenario runs are meaningful without moving profiles away.
- F1 `/KEEPDATA` parameter: backlog, not blocking.
- P6 hashes above are for the current `Desktop\Linda_2.5.0.1` build; a rebuilt
  installer with the F2 fix will need fresh hashes before publishing.
