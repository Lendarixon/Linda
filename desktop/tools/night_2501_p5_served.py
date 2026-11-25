# -*- coding: utf-8 -*-
"""P5: build the served page exactly like create_app() and write it for a static preview.

Same injection order as linda_desktop/app.py so screenshots show the real product UI.
Adds a fetch mock for /api/* so start/sets/update/verdict screens render without a backend.
"""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(r'D:/Linda_2100_Dev')
WEB = ROOT / 'web'
OUT = ROOT / 'work/night_2501/ui'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from linda_desktop import config  # noqa: E402


def build() -> Path:
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    cabinet = (WEB / 'cabinet.html').read_text(encoding='utf-8')
    metro = (WEB / 'metro-dev.css').read_text(encoding='utf-8')
    splash = (WEB / 'startup.html').read_text(encoding='utf-8')
    dcss = (WEB / 'desktop-shell.css').read_text(encoding='utf-8')
    djs = (WEB / 'desktop-shell.js').read_text(encoding='utf-8')

    html = html.replace('</body>', cabinet + '\n</body>', 1)
    html = html.replace('</head>', '<style>' + metro + '</style></head>', 1)
    html = html.replace('<body>', '<body>' + splash, 1)
    html = html.replace('</head>', '<style>' + dcss + '</style></head>', 1)
    html = html.replace('</body>', '<script>' + djs + '</script></body>', 1)

    boot = json.dumps({'language': 'en', 'settings': {'language': 'en', 'model_sets': ['lite'],
                                                     'theme': 'dark'},
                       'version': config.APP_VERSION}, ensure_ascii=True).replace('<', '\\u003c')
    html = html.replace('__LINDA_TOKEN__', 'preview')
    html = html.replace('__LINDA_VERSION__', config.APP_VERSION)
    html = html.replace('__LINDA_BOOT_B64__', base64.b64encode(boot.encode('ascii')).decode('ascii'))
    html = html.replace('</body>', '<script>' + MOCK + '</script></body>', 1)
    p = OUT / 'served_index.html'
    p.write_text(html, encoding='utf-8')
    print('wrote', p, len(html), 'chars')
    return p


MOCK = r"""
(function(){
  const J = (o, code) => new Response(JSON.stringify(o), {status: code || 200,
      headers: {'Content-Type': 'application/json'}});
  const status = {
    models_ready: true, license: {licensed: false, configured: true, status: 'none', tier: null, key_hint: ''},
    download: {phase: 'idle', done: 0, total: 0, file: '', error: ''},
    engine: {tier: 'lite', have_pro: false, have_lite: true, device: 'cpu', phase: 'ready', error: '', gpu: {available: true, discrete: true, backend: 'DirectML', name: 'AMD Radeon RX 9070 XT'}},
    models: {version: '1.5.0', installed: '1.5.0'}, update: {}, pending: {}, sets: {
      pro: {installed: false, size: 2919176888}, lite: {installed: true, size: 295683811},
      selected: ['lite'], recommended: 'lite'
    },
    version: '2.5.0.1', app_version: '2.5.0.1', models_version: '1.5.0',
    gpu: {available: true, discrete: true, backend: 'DirectML', name: 'AMD Radeon RX 9070 XT'},
    history_count: 3, first_run: false, preload: 'ready'
  };
  const verdict = {
    ok: true, words: 412, sentences: 18, score: 71.4, z: 1.92, verdict: 'ai', mode: 'sensitive',
    p_ai: 0.714, elapsed: 3.4, device: 'cpu', tier: 'lite',
    margins: {essay: 0.71, multi: 0.66, stylo: 0.58},
    auth: {ai: 118, human: 246, uncertain: 48},
    labels: [], heatmap: [], windows: [],
    sentences: [
      {text:'The relationship between urban green space and public health has been extensively studied in recent decades.', start:0, end:108, p_ai:0.82, label:'ai'},
      {text:'Furthermore, numerous meta-analyses demonstrate a consistent association between park access and reduced all-cause mortality.', start:109, end:234, p_ai:0.91, label:'ai'},
      {text:'It is worth noting that these findings hold across diverse socioeconomic contexts.', start:235, end:318, p_ai:0.77, label:'ai'},
      {text:'One long walk through the old market cured my doubt about the plan.', start:319, end:384, p_ai:0.12, label:'human'},
      {text:'Moreover, the physiological pathways involved appear to operate synergistically.', start:385, end:463, p_ai:0.69, label:'ai'},
      {text:'Planners I spoke to were sceptical, and rightly so.', start:464, end:512, p_ai:0.21, label:'human'},
      {text:'In conclusion, the evidence base is substantial and warrants policy attention.', start:513, end:591, p_ai:0.74, label:'ai'}
    ],
    sentence_stats: {granularity:'tokens', thresholds:{ai:0.58, uncertain:0.38}, total:7},
    metrics: {words: 412, sents: 18, avg_sent: 22.9,
      burst: 0.41, div: 0.47, rep: 0.012, stock: 1.4},
    text: 'The relationship between urban green space and public health has been extensively studied.'
  };
  const orig = window.fetch;
  window.fetch = function(url, opts){
    const u = String(url);
    if (!u.includes('/api/')) return orig.apply(this, arguments);
    if (u.includes('/api/status')) return Promise.resolve(J(status));
    if (u.includes('/api/i18n')) return Promise.resolve(J({lang: 'en', strings: {}}));
    if (u.includes('/api/models/update/status')) return Promise.resolve(J({phase: 'downloading', done: 134217728, total: 295683811, file: 'models/linda_speed_131/model.onnx', error: '', speed: 18e6}));
    if (u.includes('/api/update/check')) return Promise.resolve(J({update: {weights_missing: false, app_new: false}, version: '1.5.0'}));
    if (u.includes('/api/models/sets')) return Promise.resolve(J(status.sets));
    if (u.includes('/api/history')) return Promise.resolve(J({items: [], total: 0}));
    if (u.includes('/api/detect')) return Promise.resolve(J({ok: true, result: verdict}));
    if (u.includes('/api/analyze')) return Promise.resolve(J(verdict));
    return Promise.resolve(J({ok: true}));
  };
  window.__LINDA_PREVIEW__ = {status, verdict};
})();
"""

if __name__ == '__main__':
    build()
