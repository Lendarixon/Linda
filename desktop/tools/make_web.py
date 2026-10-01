# -*- coding: utf-8 -*-
"""Builds web/index.html for the desktop app from the Linda-Pro demo page (the same sentence heat map UI): drops the access-code logic,
adds the local API token, the first-run download screen, update banner, licence dialog and settings dialog.
    python tools/make_web.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"C:\Users\ninja\Desktop\modal_demo\demo_pre_metro.html")  # pristine page; the Metro skin is injected below
OUT = ROOT / "web" / "index.html"

B64 = (ROOT / "assets" / "wordmark_b64.txt").read_text(encoding="ascii").strip()
t = SRC.read_text(encoding="utf-8")


def sub(a: str, b: str, count: int = 1) -> None:
    global t
    assert a in t, a[:70]
    t = t.replace(a, b) if count == 0 else t.replace(a, b, count)


# 1. fetch wrapper: local token instead of the access code
s = t.index("/* access code:")
e = t.index("})();", s) + len("})();")
t = t[:s] + """/* every API call carries the local session token (the page is served by the app itself, 127.0.0.1 only) */
(function () {
  const orig = window.fetch.bind(window);
  window.fetch = function (url, opts) {
    opts = Object.assign({}, opts || {});
    opts.headers = Object.assign({}, opts.headers || {}, { "x-linda-token": "__LINDA_TOKEN__" });
    return orig(url, opts);
  };
})();""" + t[e:]

# 2. names and header
sub('    <div class="brand-icon">⚡</div>\n', '', 1)
sub("Linda-Essay v3", "Linda-Essay-D", 0)
sub("Linda-Multi v2", "Linda-Multi-D", 0)
sub("Stylo7e (Stylometry)", "Stylo-D (Stylometry)")
sub("Stylo7e", "Stylo-D", 0)
sub("Linda-Pro 1.0 \u2014 AI Verification Report", "Linda-Pro 1.1 \u2014 AI Verification Report")
sub("""    Linda-Pro 1.0
    <span class="badge-commercial">Commercial Demo</span>
  </div>
  <div style="font-size:0.75rem;color:var(--text-muted);font-weight:600">
    Pangram-Style Sentence Origin Attribution
  </div>""", """    <img class="brand-logo" alt="Linda-Pro" height="36" src="data:image/png;base64,""" + B64 + """"> <span style="font-weight:600;color:var(--text-muted);font-size:.85rem">__LINDA_VERSION__</span>
    <span class="badge-commercial" id="licBadge" style="cursor:pointer" title="Licence">Free \u00b7 personal use</span>
  </div>
  <div style="font-size:0.75rem;color:var(--text-muted);font-weight:600">
    <span id="devInfo"></span> <button class="lp-link" id="btnSettings">\u2699 Settings</button>
  </div>""")

# 3. footer
fs = t.index('<div style="max-width:1100px;margin:28px auto 40px')
fe = t.index("</div>", fs) + len("</div>")
t = t[:fs] + """<div style="max-width:1100px;margin:28px auto 40px;padding:0 20px;color:#9aa2b6;font-size:.85rem;line-height:1.5">
<b>Limits.</b> English is the main language; Russian and Polish work at moderate quality (thresholds are tuned for English, results are indicative); up to 20,000 words (above ~3,600 words the 12 windows get wider, so highlighting is coarser). Sentence colours are indicative only: the models were calibrated on ~300-word windows, single sentences are much less reliable.
Essays by non-native writers of exam type can get false flags in <i>sensitive</i> mode; <i>precise</i> flags AI only when two independent signals agree. Not better than the best commercial detectors.
<b>Never use a verdict as the sole basis for a decision about a person.</b> Your text is analysed on this computer and is never uploaded.
Free for personal non-commercial use; commercial use needs a licence key (<a href="#" id="footLic" style="color:#8fa8ff">enter or buy a key</a>).
</div>""" + t[fe:]

# 4. overlays, banner, dialogs, logic
EXTRA_CSS = """
<style>
.lp-link{background:none;border:0;color:#8fa8ff;cursor:pointer;font:inherit}
.lp-overlay{position:fixed;inset:0;background:rgba(8,10,16,.88);z-index:50;display:none;align-items:center;justify-content:center;padding:20px}
.lp-overlay.show{display:flex}
.lp-card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:28px 30px;max-width:560px;width:100%;box-shadow:var(--shadow)}
.lp-card h2{font-size:1.35rem;margin-bottom:8px}.lp-card p{color:var(--text-muted);margin:8px 0}
.lp-btn{background:var(--accent);color:#fff;border:0;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font:inherit;font-weight:700}
.lp-btn.sec{background:var(--bg-elevated);color:var(--text);border:1px solid var(--border)}
.lp-bar{height:12px;background:var(--bg-elevated);border-radius:7px;overflow:hidden;margin:14px 0 6px}
.lp-bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#5b7cfa,#34d399);transition:width .4s}
.lp-banner{display:none;position:sticky;top:0;z-index:40;padding:10px 20px;background:#26325f;border-bottom:1px solid #3b4b8a;color:#dfe6ff;font-size:.9rem;align-items:center;gap:14px;flex-wrap:wrap}
.lp-banner.show{display:flex}.lp-banner.warn{background:#5a2330;border-color:#8a3b4b}
.lp-input{width:100%;background:var(--bg-elevated);border:1px solid var(--border);border-radius:9px;color:var(--text);padding:10px 12px;font:inherit;margin:8px 0}
.lp-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;align-items:center}
.lp-msg{font-size:.88rem;margin-top:8px;min-height:1.2em}.lp-msg.bad{color:#ff8a98}.lp-msg.ok{color:#5be0ae}
.lp-lic-note{display:none;margin:10px auto 0;max-width:1100px;padding:0 20px;color:#9aa2b6;font-size:.82rem}
</style>
"""
EXTRA_HTML = """
<div class="lp-banner" id="lpBanner"><span id="lpBannerText"></span><button class="lp-btn" id="lpBannerBtn"></button></div>

<div class="lp-overlay" id="lpSetup"><div class="lp-card">
  <h2>Welcome to Linda-Pro</h2>
  <p id="lpSetupText">First start: the detector models (<b id="lpSetupSize">\u2026</b>) are downloaded once and stay on this computer. Afterwards the app works fully offline.</p>
  <div class="lp-bar"><i id="lpSetupBar"></i></div>
  <p id="lpSetupProg" style="font-size:.85rem"></p>
  <div class="lp-msg bad" id="lpSetupErr"></div>
  <div class="lp-row"><button class="lp-btn" id="lpSetupGo">Download models</button><button class="lp-btn sec" id="lpSetupCancel" style="display:none">Pause</button></div>
</div></div>

<div class="lp-overlay" id="lpLic"><div class="lp-card">
  <h2>Licence</h2>
  <p id="lpLicState"></p>
  <p>Linda-Pro (the app, the command line tools and the models) is free for personal non-commercial use. Commercial use (paid work, clients, a business, a school or university, a product) needs a licence key; <b>one key covers the app, the command line tools and the models together</b>.</p>
  <input class="lp-input" id="lpKey" placeholder="LINDA-XXXXXXXX-\u2026" autocomplete="off" spellcheck="false">
  <div class="lp-msg" id="lpLicMsg"></div>
  <div class="lp-row"><button class="lp-btn" id="lpKeyGo">Activate</button><button class="lp-btn sec" id="lpKeyRemove" style="display:none">Remove key</button><button class="lp-btn sec" id="lpLicClose">Close</button></div>
  <p style="margin-top:16px;font-size:.88rem">Buy: <a class="lp-link" id="lpBuy1" href="#" target="_blank">Personal $10 / Team $30</a> \u00b7 <a class="lp-link" id="lpBuy2" href="#" target="_blank">Organization / University $500 per year</a> \u00b7 OEM, exclusive, custom calibration: <span id="lpMail"></span></p>
  <p style="font-size:.8rem">Activation sends only the key and a random device label to the licence server (Polar). Your texts never leave this computer.</p>
</div></div>

<div class="lp-overlay" id="lpSet"><div class="lp-card">
  <h2>Settings</h2>
  <p>Sentence highlighting</p>
  <select class="lp-input" id="lpSent"><option value="auto">Automatic: sliding windows, fast blocks for long texts on a CPU (recommended)</option><option value="smooth">Sliding windows of ~300 words: accurate boundaries, a few seconds more on a CPU</option><option value="windows">Fast: one colour per ~300-word block</option><option value="full">Single sentences (experimental, less reliable)</option></select>
  <p>Processor</p>
  <select class="lp-input" id="lpDev"><option value="auto">Automatic</option><option value="cpu">CPU</option><option value="cuda">GPU (NVIDIA CUDA)</option></select>
  <label style="display:flex;gap:12px;align-items:flex-start;margin:16px 0 4px;cursor:pointer"><input type="checkbox" id="lpPreload" style="margin-top:6px;width:18px;height:18px"><span><b>Load the models when the app starts</b> (recommended)<br><span class="note" style="color:var(--text-muted)">The models are put into memory in the background right after start, while updates are checked, so the first analysis is fast.</span></span></label>
  <div class="lp-msg" id="lpPreloadWarn" style="display:none;color:#fa6800;border-left:6px solid #fa6800;padding:8px 12px;background:rgba(250,104,0,.12)">Warning: with this off, the first analysis will take noticeably longer (roughly 5&ndash;15 s on a fast CPU, more on an older one), because the models are loaded at that moment. Later analyses are fast.</div>
  <p id="lpAbout" style="font-size:.82rem"></p>
  <div class="lp-row"><button class="lp-btn" id="lpSetSave">Save</button><button class="lp-btn sec" id="lpSetClose">Close</button><button class="lp-btn sec" id="lpCheckUpd">Check for updates</button></div>
  <div class="lp-msg" id="lpSetMsg"></div>
</div></div>
"""
EXTRA_JS = """
<script>
(function () {
  const $ = id => document.getElementById(id);
  const fmt = b => b >= 1e9 ? (b / 1e9).toFixed(2) + ' GB' : (b / 1e6).toFixed(0) + ' MB';
  const post = (u, b) => fetch(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b || {}) }).then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || ('HTTP ' + r.status)); return j; });
  let S = null, started = false;
  const tierName = { personal: 'Personal', team: 'Team', organization: 'Organization' };

  function render(s) {
    S = s;
    $('licBadge').textContent = s.license.licensed ? 'Licensed \u00b7 ' + (tierName[s.license.tier] || 'Commercial') : 'Free \u00b7 personal use';
    $('licBadge').style.background = s.license.licensed ? 'rgba(52,211,153,.18)' : '';
    const eng = s.engine.phase;
    $('devInfo').textContent = !s.models_ready ? '' : eng === 'loading' ? 'Loading models\u2026' : eng === 'error' ? 'Model loading failed' : ((eng === 'ready' ? 'Ready on ' : 'Models load on first use \u00b7 ') + (s.engine.device === 'cuda' ? 'GPU' : 'CPU') + ' \u00b7 models ' + (s.installed_version || '\u2014'));
    // first-run / download screen
    const d = s.download, setup = $('lpSetup');
    const busy = ['checking', 'downloading', 'finishing'].includes(d.phase);
    setup.classList.toggle('show', !s.models_ready);
    if (!s.models_ready) {
      const up = s.update;
      $('lpSetupSize').textContent = up && up.bytes_to_download ? fmt(up.bytes_to_download) : (d.total ? fmt(d.total) : '~2.7 GB');
      $('lpSetupBar').style.width = d.total ? Math.min(100, d.done / d.total * 100) + '%' : '0';
      $('lpSetupProg').textContent = busy ? (d.total ? fmt(d.done) + ' of ' + fmt(d.total) + (d.speed ? ' \u00b7 ' + (d.speed / 1e6).toFixed(1) + ' MB/s' : '') : 'Checking\u2026') : '';
      $('lpSetupErr').textContent = d.phase === 'error' ? d.error : (s.update_error && !up ? 'Cannot reach the update server: ' + s.update_error : '');
      $('lpSetupGo').style.display = busy ? 'none' : '';
      $('lpSetupGo').textContent = d.phase === 'error' || d.phase === 'cancelled' ? 'Try again / resume' : 'Download models';
      $('lpSetupCancel').style.display = busy ? '' : 'none';
      if (s.update && s.update.app_required) { $('lpSetupErr').textContent = 'This version of the app is too old for the current models. Please update the app first.'; }
    }
    // banner
    const ban = $('lpBanner'), up = s.update, ij = s.installer_job;
    let text = '', btn = '', act = null, warn = false;
    if (ij.phase === 'downloading') { text = 'Downloading the new app version\u2026 ' + (ij.total ? Math.round(ij.done / ij.total * 100) + '%' : ''); }
    else if (ij.phase === 'error') { text = 'App update failed: ' + ij.error; warn = true; }
    else if (up && up.app_required) { text = 'A new version of the app (' + (up.installer ? up.installer.version : '') + ') is required to use the latest models.'; btn = 'Update app'; act = 'app'; warn = true; }
    else if (up && up.app_new) { text = 'Linda-Pro ' + up.installer.version + ' is available.'; btn = 'Update app'; act = 'app'; }
    else if (up && up.weights_update && s.models_ready && !busy) { text = 'Model update ' + up.remote_version + ' is available' + (up.bytes_to_download ? ' (' + fmt(up.bytes_to_download) + ')' : '') + (up.notes ? ' \u2014 ' + up.notes : '') + '.'; btn = 'Update models'; act = 'models'; }
    else if (busy && s.models_ready) { text = 'Updating models\u2026 ' + (d.total ? Math.round(d.done / d.total * 100) + '%' : ''); }
    else if (d.phase === 'done' && up && !up.weights_update) { text = ''; }
    ban.classList.toggle('show', !!text); ban.classList.toggle('warn', warn);
    $('lpBannerText').textContent = text; $('lpBannerBtn').style.display = btn ? '' : 'none'; $('lpBannerBtn').textContent = btn; $('lpBannerBtn').dataset.act = act || '';
    // licence dialog state
    $('lpLicState').textContent = s.license.licensed ? 'Licensed (' + (tierName[s.license.tier] || 'commercial') + ') \u00b7 key ' + s.license.key_hint : (s.license.status === 'other_machine' ? 'This key was activated on another computer. Enter it again to activate it here (on the old computer use Remove key, or free the device in your Polar customer portal).' : s.license.status !== 'none' ? 'The saved key is no longer valid (' + s.license.status + '): it may have been revoked or removed. Enter it again to re-activate.' : 'No key entered \u2014 free personal use.');
    $('lpKeyRemove').style.display = s.license.key_hint ? '' : 'none';
    $('lpBuy1').href = s.buy.personal_team; $('lpBuy2').href = s.buy.org; $('lpMail').textContent = s.buy.email;
    $('lpAbout').textContent = 'App ' + s.app_version + ' \u00b7 models ' + (s.installed_version || 'not installed') + ' \u00b7 ' + (s.engine.device === 'cuda' ? 'GPU' : 'CPU') + ' \u00b7 data folder: %LOCALAPPDATA%\\\\Linda-Pro';
  }

  async function poll() {
    try { render(await (await fetch('/api/status')).json()); } catch (e) { /* app closing */ }
    const fast = S && (['checking', 'downloading', 'finishing'].includes(S.download.phase) || S.installer_job.phase === 'downloading');
    setTimeout(poll, fast ? 800 : 3000);
  }
  poll();
  setTimeout(() => { if (S && !S.models_ready && !S.update) post('/api/update/check').catch(() => {}); }, 600);

  $('lpSetupGo').onclick = () => post('/api/models/download').catch(e => { $('lpSetupErr').textContent = e.message; });
  $('lpSetupCancel').onclick = () => post('/api/models/cancel');
  $('lpBannerBtn').onclick = () => { const a = $('lpBannerBtn').dataset.act; (a === 'app' ? post('/api/app/update') : post('/api/models/download')).catch(e => alert(e.message)); };
  const show = (id, on) => $(id).classList.toggle('show', on);
  $('licBadge').onclick = () => show('lpLic', true); $('footLic').onclick = e => { e.preventDefault(); show('lpLic', true); };
  $('lpLicClose').onclick = () => show('lpLic', false);
  $('lpKeyGo').onclick = async () => { const m = $('lpLicMsg'); m.className = 'lp-msg'; m.textContent = 'Checking\u2026'; try { await post('/api/license/activate', { key: $('lpKey').value }); m.className = 'lp-msg ok'; m.textContent = 'Activated. Thank you!'; $('lpKey').value = ''; } catch (e) { m.className = 'lp-msg bad'; m.textContent = e.message; } };
  $('lpKeyRemove').onclick = async () => { await post('/api/license/remove'); $('lpLicMsg').textContent = 'Key removed from this computer.'; };
  const warnPre = () => { $('lpPreloadWarn').style.display = $('lpPreload').checked ? 'none' : 'block'; };
  $('lpPreload').onchange = warnPre;
  $('btnSettings').onclick = () => { if (S) { $('lpSent').value = S.settings.sentences || 'auto'; $('lpDev').value = S.settings.device || 'auto'; $('lpPreload').checked = S.settings.preload !== false; } warnPre(); show('lpSet', true); };
  $('lpSetClose').onclick = () => show('lpSet', false);
  $('lpSetSave').onclick = async () => { await post('/api/settings', { sentences: $('lpSent').value, device: $('lpDev').value, preload: $('lpPreload').checked }); $('lpSetMsg').className = 'lp-msg ok'; $('lpSetMsg').textContent = 'Saved.'; };
  $('lpCheckUpd').onclick = async () => { const m = $('lpSetMsg'); m.className = 'lp-msg'; m.textContent = 'Checking\u2026'; const r = await post('/api/update/check'); m.className = 'lp-msg ' + (r.error ? 'bad' : 'ok'); m.textContent = r.error ? r.error : (r.update && (r.update.weights_update || r.update.app_new) ? 'An update is available (see the banner on top).' : 'Everything is up to date.'); };
})();
(function () {
  /* explain coarse colouring: in fast mode every sentence of a ~300-word block shares the block's score */
  const rr = window.renderResults;
  if (typeof rr !== 'function') return;
  window.renderResults = function (r) {
    rr.apply(this, arguments);
    try {
      const card = document.getElementById('heatmapCard');
      let h = document.getElementById('lpGranHint');
      if (!h) { h = document.createElement('div'); h.id = 'lpGranHint'; h.style.cssText = 'padding:8px 20px;color:var(--text-muted);font-size:.78rem;border-bottom:1px solid var(--border)'; card.querySelector('.heatmap-header').insertAdjacentElement('afterend', h); }
      const g = r && r.sentence_stats && r.sentence_stats.granularity;
      h.textContent = g === 'window' ? 'Fast mode: colours show blocks of about 300 words (every sentence in a block gets the score of the block). Choose sliding windows in Settings for finer boundaries.' : g === 'smooth' ? 'Colours follow sliding windows of about 300 words, so boundaries are accurate to roughly 100 words; a single sentence is not scored on its own.' : g === 'sentence' ? 'Experimental: each sentence is scored on its own, which is much less reliable than a window of text.' : '';
      h.style.display = g ? '' : 'none';
    } catch (e) { /* cosmetic only */ }
  };
})();
</script>
"""
METRO = (ROOT / "tools" / "metro_override.css").read_text(encoding="utf-8")
sub("</head>", '<style id="metro">\n' + METRO + "</style>" + EXTRA_CSS + "</head>")
sub("<body>", "<body>" + EXTRA_HTML)
sub("</body>", EXTRA_JS + "</body>")
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(t, encoding="utf-8", newline="\n")
print("written", OUT, len(t))
