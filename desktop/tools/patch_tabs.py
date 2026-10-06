# -*- coding: utf-8 -*-
"""Вкладки для нескольких текстов: у каждой свой текст, файл и результат; переключение не теряет результаты."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "web" / "index.html"
t = P.read_text(encoding="utf-8")
if 'id="tabsBar"' in t:
    raise SystemExit("already patched")


def sub(old, new):
    global t
    if old not in t:
        raise SystemExit("not found: " + old[:90])
    t = t.replace(old, new, 1)


sub("</style>\n</head>", """.tabs-bar{display:flex;gap:2px;flex-wrap:wrap;margin:0 0 8px;align-items:stretch}
.tabs-bar .tab{display:inline-flex;align-items:center;gap:8px;max-width:210px;min-height:34px;padding:0 10px;background:#2b2b2b;color:#cfcfcf;border:0;font:600 .78rem inherit;cursor:pointer;white-space:nowrap}
.tabs-bar .tab:hover{background:#3a3a3a}.tabs-bar .tab.active{background:var(--cobalt,#2457d6);color:#fff}
.tabs-bar .tab span.t{overflow:hidden;text-overflow:ellipsis}
.tabs-bar .tab.done:not(.active)::after{content:"";width:8px;height:8px;border-radius:50%;background:var(--human,#34d399)}
.tabs-bar .tab .x{opacity:.65;font-size:1rem;line-height:1;padding:0 2px}.tabs-bar .tab .x:hover{opacity:1}
.tabs-bar .plus{min-width:34px;justify-content:center;font-size:1.1rem}
html[data-theme="light"] .tabs-bar .tab:not(.active){background:#dfe5ef;color:#141821}
html[data-theme="light"] .tabs-bar .tab:not(.active):hover{background:#cdd6e6}
html[data-theme="contrast"] .tabs-bar .tab.active{color:#000}
</style>
</head>""")
sub('    <div class="input-box" id="dropzoneBox">', '    <div class="tabs-bar" id="tabsBar" role="tablist"></div>\n    <div class="input-box" id="dropzoneBox">')

JS = r"""
// ВКЛАДКИ ДЛЯ НЕСКОЛЬКИХ ТЕКСТОВ: у каждой вкладки свой текст, файл и результат; программно загруженный текст не запускает «input» (иначе результат сбросился бы)
const tabsBar = document.getElementById('tabsBar');
let tabs = [{ id: 1, text: '', file: null, result: null, done: false }], activeTabId = 1, tabSeq = 1;
const curTab = () => tabs.find(x => x.id === activeTabId);
function tabTitle(x, i) {
  if (x.file) return x.file;
  const s = (x.id === activeTabId ? textInput.value : x.text || '').trim().replace(/\s+/g, ' ');
  return s ? s.slice(0, 22) + (s.length > 22 ? '…' : '') : window.LINDA_T('tab_default', { n: i + 1 });
}
function saveTab() { const x = curTab(); if (!x) return; x.text = textInput.value; x.file = filePill.classList.contains('hidden') ? null : filePillName.textContent; x.result = lastResult; }
function renderTabs() {
  tabsBar.innerHTML = '';
  tabs.forEach((x, i) => {
    const b = document.createElement('button');
    b.className = 'tab' + (x.id === activeTabId ? ' active' : '') + (x.done ? ' done' : '');
    b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', x.id === activeTabId ? 'true' : 'false');
    if (x.done && x.id !== activeTabId) b.title = window.LINDA_T('tab_done');
    const s = document.createElement('span'); s.className = 't'; s.textContent = tabTitle(x, i); b.appendChild(s);
    if (tabs.length > 1) { const c = document.createElement('span'); c.className = 'x'; c.textContent = '×'; c.title = window.LINDA_T('tab_close'); c.onclick = e => { e.stopPropagation(); closeTab(x.id); }; b.appendChild(c); }
    b.onclick = () => switchTab(x.id);
    tabsBar.appendChild(b);
  });
  if (tabs.length < 8) { const p = document.createElement('button'); p.className = 'tab plus'; p.textContent = '+'; p.title = window.LINDA_T('tab_new'); p.onclick = newTab; tabsBar.appendChild(p); }
}
function loadTab(x) {
  textInput.value = x.text || '';
  updateCounter();
  if (x.file) { filePillName.textContent = x.file; filePillSize.textContent = ''; filePill.classList.remove('hidden'); } else filePill.classList.add('hidden');
  lastResult = x.result || null;
  if (!checkCtl) statusIndicator.textContent = '';
  sentTooltip.style.display = 'none';
  document.documentElement.removeAttribute('data-detail');
  x.done = false;
  if (x.result) { renderResults(x.result); renderSentenceHeatmap(x.result); }
  else { resultsContent.classList.add('hidden'); emptyState.classList.remove('hidden'); heatmapCard.classList.add('hidden'); }
}
function switchTab(id) { if (id === activeTabId) return; saveTab(); activeTabId = id; loadTab(curTab()); renderTabs(); }
function newTab() { if (tabs.length >= 8) return; saveTab(); const x = { id: ++tabSeq, text: '', file: null, result: null, done: false }; tabs.push(x); activeTabId = x.id; loadTab(x); renderTabs(); textInput.focus(); }
function closeTab(id) {
  if (tabs.length < 2) return;
  if (id === runningTabId) cancelCheck();
  const i = tabs.findIndex(x => x.id === id); tabs.splice(i, 1);
  if (activeTabId === id) { activeTabId = tabs[Math.max(0, i - 1)].id; loadTab(curTab()); }
  renderTabs();
}
let runningTabId = null;
textInput.addEventListener('input', () => { clearTimeout(window.__tabT); window.__tabT = setTimeout(renderTabs, 300); });
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && (e.key === 't' || e.key === 'T')) { e.preventDefault(); newTab(); } });
document.addEventListener('linda-i18n', renderTabs);
if (typeof window.LINDA_T === 'function') renderTabs();
"""
sub("// ПРОГРЕСС ОБРАБОТКИ:", JS + "// ПРОГРЕСС ОБРАБОТКИ:")

# проверка привязывается к вкладке, из которой запущена
sub("  const myId = ++checkSeq, ctl = new AbortController();\n  checkCtl = ctl;\n  checkJob = newCheckId();",
    "  const myId = ++checkSeq, ctl = new AbortController();\n  const myTab = activeTabId; runningTabId = myTab;\n  checkCtl = ctl;\n  checkJob = newCheckId();")
sub("""    lastResult = data.result;
    lastResult._elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    lastResult._text = text;

    renderResults(lastResult);
    renderSentenceHeatmap(lastResult);
    statusIndicator.textContent = window.LINDA_T('ui_finished', {s: lastResult._elapsed});""",
    """    const fin = data.result;
    fin._elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    fin._text = text;
    const tb = tabs.find(x => x.id === myTab);
    if (tb) { tb.result = fin; tb.text = text; }
    if (myTab === activeTabId) {
      lastResult = fin;
      renderResults(lastResult);
      renderSentenceHeatmap(lastResult);
      statusIndicator.textContent = window.LINDA_T('ui_finished', {s: fin._elapsed});
    } else if (tb) { tb.done = true; renderTabs(); }  // проверка закончилась в фоновой вкладке: зелёная точка""")
sub("      progHide();\n      checkCtl = null;\n      checkJob = null;", "      progHide();\n      runningTabId = null;\n      checkCtl = null;\n      checkJob = null;")

# загрузка файла — в ту вкладку, где она началась
sub("  const myUpload = ++uploadSeq, ctl = new AbortController();", "  const myUpload = ++uploadSeq, ctl = new AbortController(), upTab = activeTabId;")
sub("""    uploadCtl = null;
    textInput.value = data.text;
    textInput.dispatchEvent(new Event('input'));
""", """    uploadCtl = null;
    if (upTab !== activeTabId) {  // пользователь переключил вкладку, пока файл читался: кладём текст в исходную
      const ux = tabs.find(x => x.id === upTab);
      if (ux) { ux.text = data.text; ux.file = data.filename; ux.result = null; renderTabs(); }
      return;
    }
    textInput.value = data.text;
    textInput.dispatchEvent(new Event('input'));
""")
P.write_text(t, encoding="utf-8")

NEW = {
    "ru": {"tab_default": "Текст {n}", "tab_new": "Новая вкладка (Ctrl+T)", "tab_close": "Закрыть вкладку", "tab_done": "Проверка закончилась"},
    "pl": {"tab_default": "Tekst {n}", "tab_new": "Nowa karta (Ctrl+T)", "tab_close": "Zamknij kartę", "tab_done": "Sprawdzanie zakończone"},
    "en": {"tab_default": "Text {n}", "tab_new": "New tab (Ctrl+T)", "tab_close": "Close tab", "tab_done": "Check finished"},
}
for lang, kv in NEW.items():
    f = ROOT / "web" / "i18n" / f"{lang}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d.update(kv)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
print("patched")
