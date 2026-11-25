# -*- coding: utf-8 -*-
"""Лёгкий дым-тест собранного 2.3.0.1: старт EXE на изолированном профиле, boot-версия, i18n-ключи, packs API."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r'C:\Users\ninja\Desktop\Linda_2.3.0.1\app\Linda-Pro.exe')
OUT = ROOT / 'evidence' / 'real-exe-2301'
OUT.mkdir(parents=True, exist_ok=True)
profile = OUT / 'smoke-profile'
if profile.exists():
    import shutil
    shutil.rmtree(profile)
profile.mkdir()
(profile / 'settings.json').write_text(json.dumps({
    'language': 'ru', 'language_source': 'manual', 'quality': 'lite', 'device': 'cpu',
    'preload': False, 'preload_v2': True, 'gpu_map': 2, 'gpu_index': 0, 'auto_models': False,
    'tour_done': True, 'save_history': False, 'model_sets': ['pro', 'lite'], 'sentences': 'auto',
}), encoding='utf-8')
env = {**os.environ, 'LINDA_HOME': str(profile),
       'LINDA_MODELS_HOME': str(ROOT / 'qa_models'),
       'LINDA_ALLOW_MULTI': '1', 'LINDA_BASE_URL': 'http://127.0.0.1:9',
       'PYTHONIOENCODING': 'utf-8'}
p = subprocess.Popen([str(EXE), '--no-ui'], env=env, creationflags=0x08000000)
print('START', p.pid, flush=True)
try:
    deadline = time.monotonic() + 180
    while not (profile / 'instance.json').exists():
        assert p.poll() is None, 'EXE exited %s' % p.returncode
        assert time.monotonic() < deadline, 'server startup timeout'
        time.sleep(0.2)
    inst = json.loads((profile / 'instance.json').read_text())
    base = 'http://127.0.0.1:%s' % inst['port']
    html = urllib.request.urlopen(base, timeout=60).read().decode()
    assert '2.3.0.1' in html, 'no 2.3.0.1 in html'
    assert 'id="lindaStartup"' in html
    token = re.search(r"window.__lindaToken = '([^']+)'", html).group(1)

    def api(path):
        req = urllib.request.Request(base + path, headers={'x-linda-token': token})
        return json.loads(urllib.request.urlopen(req, timeout=60).read())

    ru = api('/api/i18n/ru')
    for key in ('hum_log', 'hum_words', 'hum_short_warn', 'hum_no_log', 'pack_all', 'pack_of',
                'err_hum_oom', 'err_hum_lowmem', 'err_hum_cpu_full', 'hum_auto'):
        assert key in ru['strings'], 'missing i18n key: %s' % key
    st = api('/api/packs/status')
    assert 'humanizer' in st and 'job' in st, st.keys()
    assert set(st['humanizer'].get('device', {})) >= {'tier', 'vram_gb', 'ram_gb', 'free_vram_gb', 'free_ram_gb'}, st['humanizer'].get('device')
    print('SMOKE 2.3.0.1 PASSED: boot ok, i18n 10 keys ok, packs status ok, device plan ok', flush=True)
finally:
    p.terminate()
    p.wait(timeout=30)
    print('exit', p.returncode, flush=True)
