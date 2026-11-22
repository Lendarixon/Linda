# -*- coding: utf-8 -*-
"""Installer E2E scenarios for Linda 2.5.0.1 (TestInstall build).

Runs each scenario with /SILENT into a fresh temp dir and records exit codes and
key files into work/night_2501/scenarios.md plus a JSON sidecar.

    python tools/night_2501_scenarios.py            # all
    python tools/night_2501_scenarios.py a c e      # selected
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r'D:/Linda_2100_Dev')
WORK = ROOT / 'work/night_2501'
SETUP = WORK / 'inst/Linda-Setup.exe'
TMP = WORK / 'tmp'
APPDATA_NAME = 'Linda-Pro (test)'          # TestInstall AppName -> %LOCALAPPDATA%\<name>
LOCAL = Path(os.environ['LOCALAPPDATA'])
DATA = LOCAL / APPDATA_NAME

results = []


def clean_env():
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
    env.pop('LINDA_HOME', None)
    env.pop('LINDA_MODELS_HOME', None)
    return env


def run_setup(args, timeout=600):
    t0 = time.time()
    p = subprocess.run([str(SETUP)] + args, env=clean_env(), timeout=timeout,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       errors='replace')
    return p.returncode, round(time.time() - t0, 1), (p.stdout or '')[-800:]


def snapshot(tag, dirs):
    """What landed on disk: install dir + data dir listing."""
    out = {}
    for name, d in dirs.items():
        d = Path(d)
        if not d.exists():
            out[name] = None
            continue
        files = sorted(str(p.relative_to(d)) for p in d.rglob('*') if p.is_file())
        out[name] = {'path': str(d), 'files': len(files),
                     'has_exe': (d / 'Linda-Pro.exe').is_file(),
                     'has_unins': any(f.startswith('unins') for f in files),
                     'sample': files[:8]}
    return out


def record(sid, title, code, secs, dirs, extra=None):
    r = {'id': sid, 'title': title, 'exit_code': code, 'seconds': secs,
         'disk': snapshot(sid, dirs), 'extra': extra or {}}
    results.append(r)
    print(f'== {sid} {title}: exit={code} {secs}s', flush=True)
    for k, v in r['disk'].items():
        print(f'   {k}: {v["files"] if v else None} files', flush=True)
    return r


def uninstall(dirpath, args=('/SILENT', '/SUPPRESSMSGBOXES')):
    for cand in Path(dirpath).glob('unins*.exe'):
        p = subprocess.run([str(cand)] + list(args), env=clean_env(), timeout=600,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           errors='replace')
        return cand.name, p.returncode
    return None, None


def fresh(name):
    d = TMP / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


def sc_a():
    """(a) fresh English install."""
    d = fresh('a_en')
    code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                  f'/DIR={d}', '/LANG=english', '/PACKS=none'])
    extra = {'stdout_tail': tail}
    return record('a', 'fresh EN install /SILENT', code, secs, {'install': d, 'data': DATA}, extra)


def sc_b():
    """(b) fresh Russian install."""
    d = fresh('b_ru')
    code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                  f'/DIR={d}', '/LANG=russian', '/PACKS=none'])
    choice = DATA / 'installer_choice.json'
    extra = {'stdout_tail': tail,
             'installer_choice': json.loads(choice.read_text(encoding='utf-8')) if choice.is_file() else None}
    return record('b', 'fresh RU install /LANG=russian', code, secs, {'install': d, 'data': DATA}, extra)


def sc_c():
    """(c) upgrade over a fake 2.5.0.0 install that already has a saved manifest."""
    d = fresh('c_upgrade')
    models = d / 'models_saved'
    models.mkdir(parents=True, exist_ok=True)
    (models / 'models' / 'linda_speed_131').mkdir(parents=True, exist_ok=True)
    payload = b'S' * 3000
    (models / 'models' / 'linda_speed_131' / 'model.onnx').write_bytes(payload)
    import hashlib
    (models / 'manifest.json').write_text(json.dumps({
        'schema': 1, 'version': '1.3.2', 'min_app': '1.0.0', 'notes': '',
        'files': [{'path': 'models/linda_speed_131/model.onnx', 'size': len(payload),
                   'sha256': hashlib.sha256(payload).hexdigest(), 'set': 'lite'}],
    }), encoding='utf-8')
    # the "old install": data dir pointing at the saved models, plus a 2.5.0.0 marker
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'models_location.json').write_text(json.dumps({'path': str(models)}), encoding='utf-8')
    (DATA / 'settings.json').write_text(json.dumps({'language': 'en', 'model_sets': ['lite']}), encoding='utf-8')
    code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                  f'/DIR={d}', '/LANG=english', '/PACKS=none'])
    before = set(p.name for p in (models / 'models' / 'linda_speed_131').iterdir())
    extra = {'saved_models_dir': str(models), 'files_before_upgrade': sorted(before),
             'manifest_still_there': (models / 'manifest.json').is_file(),
             'model_intact': (models / 'models' / 'linda_speed_131' / 'model.onnx').is_file(),
             'stdout_tail': tail}
    return record('c', 'upgrade over fake 2.5.0.0 with saved manifest -> reuse', code, secs,
                  {'install': d, 'data': DATA}, extra)


def sc_d():
    """(d) install while a copy of Linda-Pro.exe is running (process-kill path)."""
    d = fresh('d_running')
    # a harmless long-running process that carries the exact image name the
    # installer's FindProcessesByName('Linda-Pro.exe') looks for
    fake = d / 'Linda-Pro.exe'
    shutil.copy2('C:/Windows/System32/ping.exe', fake)
    proc = subprocess.Popen([str(fake), '-n', '900', '127.0.0.1'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    alive_before = proc.poll() is None
    code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                  f'/DIR={d}', '/LANG=english', '/PACKS=none'])
    time.sleep(2)
    alive_after = proc.poll() is None
    if alive_after:
        proc.kill()
    extra = {'helper_pid': proc.pid, 'alive_before': alive_before,
             'alive_after': alive_after, 'killed_by_installer': alive_before and not alive_after,
             'stdout_tail': tail}
    return record('d', 'install while Linda-Pro.exe runs -> process-kill path', code, secs,
                  {'install': d, 'data': DATA}, extra)


def sc_e():
    """(e) /MODELSET=lite and /MODELSET=pro."""
    out = {}
    for name in ('lite', 'pro'):
        d = fresh(f'e_{name}')
        code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                      f'/DIR={d}', '/LANG=english', '/PACKS=none',
                                      f'/MODELSET={name}'])
        choice = DATA / 'installer_choice.json'
        cj = json.loads(choice.read_text(encoding='utf-8')) if choice.is_file() else None
        out[name] = {'exit_code': code, 'seconds': secs,
                     'installer_choice': cj,
                     'sets_selected': (cj or {}).get('model_sets') or (cj or {}).get('sets'),
                     'files': len(list(d.rglob('*')))}
        if name == 'pro':
            record('e', '/MODELSET=lite then /MODELSET=pro', code, secs,
                   {'install': d, 'data': DATA},
                   {'lite': out['lite'], 'pro': out['pro'],
                    'choice_file': str(choice), 'choice': cj})
    return results[-1]


def sc_f():
    """(f) uninstall /SILENT keep-data vs full removal."""
    out = {}
    for mode in ('keep', 'full'):
        d = fresh(f'f_{mode}')
        code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                      f'/DIR={d}', '/LANG=english', '/PACKS=none'])
        (DATA / 'settings.json').write_text(json.dumps({'language': 'en'}), encoding='utf-8')
        un, ucode = uninstall(d)
        time.sleep(3)
        out[mode] = {'install_exit': code, 'uninstaller': un, 'uninstall_exit': ucode,
                     'install_dir_exists': d.exists(),
                     'exe_left': (d / 'Linda-Pro.exe').is_file(),
                     'data_dir_exists': DATA.exists(),
                     'settings_left': (DATA / 'settings.json').is_file(),
                     'stdout_tail': tail}
        record(f'f-{mode}', f'uninstall /SILENT ({mode} data)', ucode, secs,
               {'install': d, 'data': DATA}, out[mode])
    return results[-1]


def sc_g():
    """(g) corrupt manifest: BASE_URL pointed at a local stub returning 404."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_error(404)          # manifest, signature, every file

        do_HEAD = do_GET

    srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}'
    d = fresh('g_404')
    code, secs, tail = run_setup(['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                  f'/DIR={d}', '/LANG=english', '/PACKS=none'])
    # the app-level path: updater against the 404 stub in an isolated LINDA_HOME
    home = fresh('g_home')
    probe = subprocess.run(
        [sys.executable, '-c', PROBE_404, url, str(home)],
        env={**clean_env(), 'LINDA_HOME': str(home)}, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    srv.shutdown()
    extra = {'stub_url': url, 'install_exit': code, 'install_tail': tail,
             'updater_probe_stdout': probe.stdout.strip()[-1200:],
             'updater_probe_exit': probe.returncode}
    return record('g', 'corrupt manifest (404 stub) -> error banner path', code, secs,
                  {'install': d, 'data': DATA}, extra)


PROBE_404 = r'''
import json, sys
from pathlib import Path
from linda_desktop import config, updater
config.BASE_URL = sys.argv[1]
home = Path(sys.argv[2]); home.mkdir(parents=True, exist_ok=True)
out = {}
try:
    m, raw = updater.get_manifest()
    out['get_manifest'] = 'returned'
except Exception as e:
    out['get_manifest'] = f'{type(e).__name__}: {e}'
# update_status is what the UI banner reads
try:
    out['update_status'] = updater.update_status({})
except Exception as e:
    out['update_status'] = f'{type(e).__name__}: {e}'
try:
    j = updater.Job(); j.start({'version': '9.9.9', 'files': [], 'min_app': '1.0.0'}, b'{}')
    import time
    t0 = time.time()
    while j.running() and time.time() - t0 < 25:
        time.sleep(0.1)
    out['job'] = j.snapshot()
except Exception as e:
    out['job'] = f'{type(e).__name__}: {e}'
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
'''


def main():
    want = sys.argv[1:] or ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    TMP.mkdir(parents=True, exist_ok=True)
    fns = {'a': sc_a, 'b': sc_b, 'c': sc_c, 'd': sc_d, 'e': sc_e, 'f': sc_f, 'g': sc_g}
    for k in want:
        # each scenario starts from a clean data dir so reuse detection is honest
        shutil.rmtree(DATA, ignore_errors=True)
        try:
            fns[k]()
        except Exception as e:      # noqa: BLE001 — a scenario failure must not stop the pipeline
            results.append({'id': k, 'title': 'EXCEPTION', 'error': f'{type(e).__name__}: {e}'})
            print(f'!! {k} raised {type(e).__name__}: {e}', flush=True)
        (WORK / 'scenarios.json').write_text(json.dumps(results, indent=1, ensure_ascii=False),
                                             encoding='utf-8')
    print('WROTE', WORK / 'scenarios.json')


if __name__ == '__main__':
    main()
