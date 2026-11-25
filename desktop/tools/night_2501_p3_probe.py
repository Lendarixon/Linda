# -*- coding: utf-8 -*-
"""P3 probe: download every manifest file that the live repo actually serves with
matching size/sha, using the app's own Job._download_to, and report the mismatches.

The signed manifest (v1.5.0) lists 3 files whose bytes on HF no longer match the
signed size/sha256, so a real "download the lite set" run aborts with
'download is larger than announced'. This script proves which part of the path is
sound and pins the exact blocker.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.pop('PYTHONPATH', None)
os.environ.pop('PYTHONHOME', None)
ROOT = Path(r'D:/Linda_2100_Dev')
WORK = ROOT / 'work/night_2501'
sys.path.insert(0, str(ROOT))

from linda_desktop import config, updater  # noqa: E402


def main() -> int:
    root = WORK / 'models_probe'
    shutil.rmtree(root, ignore_errors=True)
    home = WORK / 'p3_probe_home'
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    os.environ['LINDA_HOME'] = str(home)
    config.set_models_root(root)
    (home / 'settings.json').write_text(json.dumps({'model_sets': ['lite', 'pro']}), encoding='utf-8')

    manifest, raw = updater.get_manifest()
    files = [f for f in manifest['files'] if f.get('set') != 'pro']
    print('manifest', manifest['version'], '| downloading', len(files), 'non-pro files', flush=True)

    job = updater.Job()
    t0 = time.time()
    ok, failed = [], []
    for f in files:
        staging = root / 'staging'
        try:
            job._download_to(f, staging, config.BASE_URL, t0)
            ok.append(f)
            print(f"  ok  {f['path']} {f['size']}", flush=True)
        except Exception as e:                       # noqa: BLE001
            failed.append({'path': f['path'], 'size': f['size'], 'error': str(e)})
            print(f"  ERR {f['path']} -> {e}", flush=True)
    elapsed = round(time.time() - t0, 1)
    got = sum((root / 'staging' / f['path']).stat().st_size for f in ok
              if (root / 'staging' / f['path']).is_file())

    # markers + sha as the job would write them
    verified = 0
    for f in ok:
        p = root / 'staging' / f['path']
        updater._write_ok_marker(p, f)
        if updater._ok_marker_matches(p, f):
            verified += 1

    out = {
        'manifest_version': manifest['version'],
        'base_url': config.BASE_URL,
        'files_requested': len(files),
        'files_ok': len(ok),
        'files_failed': failed,
        'bytes_downloaded': got,
        'seconds': elapsed,
        'avg_mb_s': round(got / 1e6 / elapsed, 2) if elapsed else None,
        'ok_markers_written_and_matching': verified,
        'all_sha256_match': len(ok) + len(failed) == len(files) and not failed,
    }
    (WORK / 'p3_probe.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
