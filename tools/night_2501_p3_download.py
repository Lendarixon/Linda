# -*- coding: utf-8 -*-
"""P3: real model-download E2E for the lite set, through linda_desktop.updater.

Uses the app's own updater functions against the real HF manifest (signed), into a
throw-away models root. Verifies .ok markers, sha256 of every file and is_complete(),
times the run, then computes the theoretical byte size of the pro set from the same
manifest (no download).

    python tools/night_2501_p3_download.py [--sets lite] [--root PATH]
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.pop('PYTHONPATH', None)
os.environ.pop('PYTHONHOME', None)
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
ROOT = Path(r'D:/Linda_2100_Dev')
WORK = ROOT / 'work/night_2501'
sys.path.insert(0, str(ROOT))

from linda_desktop import config, updater  # noqa: E402


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sets', default='lite')
    ap.add_argument('--root', default=str(WORK / 'models_lite'))
    ap.add_argument('--budget', type=int, default=480, help='seconds before we stop waiting')
    a = ap.parse_args()

    root = Path(a.root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    home = WORK / 'p3_home'
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True, exist_ok=True)
    os.environ['LINDA_HOME'] = str(home)
    config.set_models_root(root)
    (home / 'settings.json').write_text(json.dumps({'model_sets': a.sets.split(',')}), encoding='utf-8')

    print('BASE_URL', config.BASE_URL, flush=True)
    t0 = time.time()
    manifest, raw = updater.get_manifest()
    t_manifest = time.time() - t0
    sel = [f['path'] for f in manifest.get('files', [])]
    print('manifest version', manifest.get('version'),
          '| files for', a.sets, ':', len(sel), '| signature ok', bool(manifest.get('_signature')), flush=True)
    all_files = manifest.get('all_files') or manifest.get('files') or []
    set_bytes = {}
    for f in all_files:
        s = f.get('set') or 'shared'
        set_bytes[s] = set_bytes.get(s, 0) + int(f.get('size') or 0)
    print('bytes per set:', json.dumps(set_bytes), flush=True)

    job = updater.Job()
    job.start(manifest, raw)
    last = None
    while job.running():
        snap = job.snapshot()
        if snap.get('done') != last:
            last = snap.get('done')
            print(f"  {snap.get('phase')} {snap.get('done')}/{snap.get('total')} B "
                  f"({snap.get('done', 0) / 1e6:.0f} MB) {snap.get('speed', 0) / 1e6:.1f} MB/s", flush=True)
        if time.time() - t0 > a.budget:
            print('!! budget exceeded, stopping', flush=True)
            job.cancel()
            break
        time.sleep(2)
    snap = job.snapshot()
    elapsed = round(time.time() - t0, 1)
    print('final', json.dumps({k: snap.get(k) for k in ('phase', 'done', 'total', 'error', 'speed')}), flush=True)

    # --- verification: every manifest file on disk, .ok marker matching, sha256 ---
    bad, ok_markers, files_checked = [], [], 0
    total_bytes = 0
    for f in manifest.get('files', []):
        p = root / f['path']
        if not p.is_file():
            bad.append({'path': f['path'], 'why': 'missing'})
            continue
        files_checked += 1
        total_bytes += p.stat().st_size
        mk = p.with_name(p.name + updater.OK_SUFFIX)
        if not mk.is_file():
            bad.append({'path': f['path'], 'why': 'no .ok marker'})
        else:
            rec = mk.read_text(encoding='ascii').split()
            ok_markers.append({'path': f['path'], 'marker_matches': rec[:2] == [f['sha256'], str(f['size'])]})
            if rec[:2] != [f['sha256'], str(f['size'])]:
                bad.append({'path': f['path'], 'why': f'marker {rec[:2]} != manifest'})
        if p.stat().st_size != int(f['size']):
            bad.append({'path': f['path'], 'why': f'size {p.stat().st_size} != {f["size"]}'})
            continue
        got = sha256(p)
        if got != f['sha256']:
            bad.append({'path': f['path'], 'why': f'sha256 {got[:16]}… != {f["sha256"][:16]}…'})

    complete = updater.is_complete(manifest, root)
    result = {
        'sets': a.sets,
        'root': str(root),
        'base_url': config.BASE_URL,
        'manifest_version': manifest.get('version'),
        'manifest_seconds': round(t_manifest, 2),
        'download_seconds': elapsed,
        'phase': snap.get('phase'),
        'error': snap.get('error'),
        'avg_mb_s': round(total_bytes / 1e6 / elapsed, 2) if elapsed else None,
        'files_in_set': len(manifest.get('files', [])),
        'files_checked': files_checked,
        'bytes_downloaded': total_bytes,
        'ok_markers_all_match': all(m['marker_matches'] for m in ok_markers) and len(ok_markers) == files_checked,
        'is_complete': complete,
        'problems': bad,
        'bytes_per_set_from_manifest': set_bytes,
        'pro_set_bytes': set_bytes.get('pro', 0),
        'pro_set_gb': round(set_bytes.get('pro', 0) / 1e9, 2),
    }
    (WORK / f'p3_{a.sets}.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
    print(json.dumps(result, indent=1), flush=True)
    return 0 if (complete and not bad) else 1


if __name__ == '__main__':
    sys.exit(main())
