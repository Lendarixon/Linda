# -*- coding: utf-8 -*-
"""Простой режим по умолчанию + тур на 3 шага при первом запуске (web/index.html, словари, настройки сервера)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "web" / "index.html"
t = P.read_text(encoding="utf-8")
if 'id="simpleVerdict"' in t:
    raise SystemExit("already patched")


def sub(old, new):
    global t
    if old not in t:
        raise SystemExit("not found: " + old[:90])
    t = t.replace(old, new, 1)


CSS = """
/* ПРОСТОЙ РЕЖИМ: без левой панели и технических карточек; «Подробнее» показывает всё */
#simpleVerdict,.ui-sw{display:none}
html[data-ui="simple"] #simpleVerdict{display:block}
html[data-ui="simple"] .panel-left{display:none}
html[data-ui="simple"] .main-grid{grid-template-columns:1fr 360px}
@media (max-width:1180px){html[data-ui="simple"] .main-grid{grid-template-columns:1fr}}
html[data-ui="simple"]:not([data-detail="1"]) #resultsContent>*:not(.verdict-box):not(#simpleVerdict){display:none!important}
html[data-ui="simple"]:not([data-detail="1"]) #verdictMeta,html[data-ui="simple"]:not([data-detail="1"]) #verdictPctLabel,html[data-ui="simple"]:not([data-detail="1"]) #verdictHeader{display:none}
html[data-ui="simple"]:not([data-detail="1"]) .heatmap-switcher,html[data-ui="simple"]:not([data-detail="1"]) #sentenceStatsBar{display:none}
html[data-ui="simple"][data-detail="1"] #svMore{display:none}
.sv{margin:14px 0;padding:14px 16px;background:var(--bg-elevated);border-left:8px solid var(--text-muted)}
.sv.ai{border-left-color:var(--ai)}.sv.uncertain{border-left-color:var(--uncertain)}.sv.human{border-left-color:var(--human)}
.sv-title{font-size:1.15rem;font-weight:600;margin-bottom:6px}.sv-adv{color:var(--text-muted);font-size:.92rem}
.sv-warn{margin-top:8px;color:var(--uncertain);font-size:.85rem}.sv .lp-btn{margin-top:12px}
.ui-sw{display:inline-flex;margin-right:12px;vertical-align:middle}
.ui-sw button{background:#2b2b2b;color:#cfcfcf;border:0;padding:5px 12px;font:600 .72rem inherit;letter-spacing:.06em;cursor:pointer}
.ui-sw button:hover{background:#3a3a3a}.ui-sw button.active{background:var(--cobalt,#2457d6);color:#fff}
.ui-sw{display:inline-flex}
/* ТУР ПЕРВОГО ЗАПУСКА */
.tour{position:fixed;inset:0;z-index:500;pointer-events:none}
.tour.hidden{display:none}
.tour-card{pointer-events:auto;position:fixed;left:50%;bottom:28px;transform:translateX(-50%);width:min(560px,92vw);background:var(--bg-card);border:1px solid var(--accent);padding:18px 20px;box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:520}
.tour-step{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.tour-card h3{margin:6px 0 6px;font-size:1.15rem}.tour-card p{margin:0 0 10px;color:var(--text-muted);font-size:.92rem}
.tour-legend{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 10px}
.tour-legend span{padding:4px 10px;font-size:.78rem;font-weight:600;color:#fff}
.tour-legend .a{background:var(--ai)}.tour-legend .u{background:#b97800}.tour-legend .h{background:#1f9d73}
.tour-btns{display:flex;gap:8px;align-items:center}.tour-btns .grow{flex:1}
.tour-hl{position:relative!important;z-index:510!important;outline:3px solid var(--accent);box-shadow:0 0 0 9999px rgba(5,7,12,.72)}
"""
sub("</style>\n</head>", CSS + "</style>\n</head>")

# переключатель вида в шапке (перед языком)
sub('<span class="lang-sw" id="langSw"',
    '<span class="lang-sw ui-sw" id="uiSw" role="group"><button data-m="simple" data-i18n="ui_sw_simple">Simple</button><button data-m="expert" data-i18n="ui_sw_expert">Detailed</button></span><span class="lang-sw" id="langSw"')

# простой вердикт под блоком вердикта
sub('      <div class="metrics-grid">',
    '''      <div class="sv" id="simpleVerdict"><div class="sv-title" id="svTitle"></div><div class="sv-adv" id="svAdv"></div><div class="sv-warn" id="svWarn"></div>
        <button class="lp-btn sec small" id="svMore" data-i18n="sv_more">More details</button></div>

      <div class="metrics-grid">''', )

# тур: разметка перед <script> с состоянием
sub("<!-- FLOATING TOOLTIP FOR HOVER -->", """<div class="tour hidden" id="tour" role="dialog" aria-modal="true" aria-labelledby="tourTitle"><div class="tour-card">
  <div class="tour-step" id="tourStep"></div><h3 id="tourTitle"></h3><p id="tourText"></p>
  <div class="tour-legend" id="tourLegend" style="display:none"><span class="a" data-i18n="tour_l_ai">Looks like AI</span><span class="u" data-i18n="tour_l_unc">Hard to say</span><span class="h" data-i18n="tour_l_hum">Looks human</span></div>
  <div class="tour-btns"><button class="lp-btn sec small" id="tourSkip" data-i18n="tour_skip">Skip</button><span class="grow"></span><button class="lp-btn sec small" id="tourBack" data-i18n="tour_back">Back</button><button class="lp-btn small" id="tourNext" data-i18n="tour_next">Next</button></div>
</div></div>

<!-- FLOATING TOOLTIP FOR HOVER -->""")

# кнопка «показать подсказки снова» в настройках (раздел вида)
sub('  <h3 class="lp-sec" id="lpSecLang"',
    '  <div class="lp-field lp-full"><button class="lp-btn sec small" id="lpTourAgain" data-i18n="tour_again">Show the tips again</button></div>\n  <h3 class="lp-sec" id="lpSecLang"')

# data-ui на корне
sub("    r.setAttribute('data-sidebar', st.sidebar || 'left');", "    r.setAttribute('data-sidebar', st.sidebar || 'left');\n    r.setAttribute('data-ui', st.ui_mode === 'expert' ? 'expert' : 'simple');")

JS = r"""
  // ПРОСТОЙ РЕЖИМ: переключатель вида, вердикт простыми словами, «Подробнее»
  function setUiMode(m) {
    document.documentElement.removeAttribute('data-detail');
    return post('/api/settings', { ui_mode: m }).then(r => { if (S) S.settings = r.settings; window.LINDA_applyUi(r.settings); syncUiSw(); });
  }
  function syncUiSw() { const m = document.documentElement.getAttribute('data-ui'); document.querySelectorAll('#uiSw button').forEach(b => b.classList.toggle('active', b.dataset.m === m)); }
  document.querySelectorAll('#uiSw button').forEach(b => b.onclick = () => setUiMode(b.dataset.m).catch(() => { }));
  $('svMore').onclick = () => document.documentElement.setAttribute('data-detail', '1');
  window.renderSimpleVerdict = function (r) {
    const v = (r.custom_verdict && r.custom_verdict.verdict) || r.verdict || 'human';
    const box = $('simpleVerdict'), words = (r._text || '').trim().split(/\s+/).filter(Boolean).length;
    const txt = v === 'ai' ? [T('sv_ai_t'), T('sv_ai_a')] : v === 'uncertain' ? [T('sv_unc_t'), T('sv_unc_a')] : [T('sv_hum_t'), T('sv_hum_a')];
    box.className = 'sv ' + (v === 'ai' ? 'ai' : v === 'uncertain' ? 'uncertain' : 'human');
    $('svTitle').textContent = txt[0]; $('svAdv').textContent = txt[1];
    $('svWarn').textContent = words && words < 150 ? T('sv_short', { n: words }) : '';
    document.documentElement.removeAttribute('data-detail');
  };
  const _renderResults = window.renderResults;
  window.renderResults = function (r) { _renderResults(r); try { window.renderSimpleVerdict(r); } catch (e) { } };
  document.addEventListener('linda-i18n', () => { try { if (lastResult) window.renderSimpleVerdict(lastResult); syncUiSw(); } catch (e) { } });

  // ТУР НА 3 ШАГА при первом запуске (Пропустить / Назад / Далее; «Показать подсказки снова» — в настройках)
  const tourSteps = [
    { sel: '#dropzoneBox', t: 'tour_1_t', b: 'tour_1_b', legend: false },
    { sel: '#btnAnalyze', t: 'tour_2_t', b: 'tour_2_b', legend: false },
    { sel: '.panel-right', t: 'tour_3_t', b: 'tour_3_b', legend: true },
  ];
  let tourI = 0, tourOn = false;
  function tourClear() { document.querySelectorAll('.tour-hl').forEach(e => e.classList.remove('tour-hl')); }
  function tourShow() {
    tourClear();
    const s = tourSteps[tourI], el = document.querySelector(s.sel);
    if (el) { el.classList.add('tour-hl'); try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (e) { } }
    $('tourStep').textContent = T('tour_step', { n: tourI + 1, total: tourSteps.length });
    $('tourTitle').textContent = T(s.t); $('tourText').textContent = T(s.b);
    $('tourLegend').style.display = s.legend ? '' : 'none';
    $('tourBack').style.visibility = tourI ? 'visible' : 'hidden';
    $('tourNext').textContent = T(tourI === tourSteps.length - 1 ? 'tour_done' : 'tour_next');
  }
  function tourStart() { if (tourOn) return; tourOn = true; tourI = 0; $('tour').classList.remove('hidden'); tourShow(); }
  function tourEnd() { tourOn = false; tourClear(); $('tour').classList.add('hidden'); post('/api/settings', { tour_done: true }).then(r => { if (S) S.settings = r.settings; }).catch(() => { }); }
  $('tourNext').onclick = () => { if (tourI >= tourSteps.length - 1) tourEnd(); else { tourI++; tourShow(); } };
  $('tourBack').onclick = () => { if (tourI > 0) { tourI--; tourShow(); } };
  $('tourSkip').onclick = tourEnd;
  document.addEventListener('keydown', e => { if (tourOn && e.key === 'Escape') tourEnd(); });
  $('lpTourAgain').onclick = () => { show('lpSet', false); document.documentElement.removeAttribute('data-detail'); setTimeout(tourStart, 300); };
  let tourChecked = false;
  window.LINDA_maybeTour = function (s) {
    if (tourChecked || !s || !s.models_ready || (s.settings || {}).tour_done === true || $('lpSetup').classList.contains('show')) return;
    tourChecked = true; setTimeout(tourStart, 900);
  };
"""
sub("  // ЯЗЫК В ШАПКЕ И БЫСТРЫЕ НАСТРОЙКИ", JS + "  // ЯЗЫК В ШАПКЕ И БЫСТРЫЕ НАСТРОЙКИ")
sub("    try { syncQuick(s); renderLoc(s); } catch (e) { }", "    try { syncQuick(s); renderLoc(s); syncUiSw(); window.LINDA_maybeTour(s); } catch (e) { }")
# новая проверка прячет «Подробнее»-режим предыдущего результата
sub("  progPollCheck(checkJob, myId);", "  document.documentElement.removeAttribute('data-detail');\n  progPollCheck(checkJob, myId);")
P.write_text(t, encoding="utf-8")

NEW = {
    "ru": {"ui_sw_simple": "Просто", "ui_sw_expert": "Подробно", "sv_more": "Подробнее",
           "sv_ai_t": "Скорее всего, текст написан ИИ", "sv_ai_a": "Это не доказательство. Спросите автора, как он писал текст, и попросите показать черновики.",
           "sv_unc_t": "Трудно сказать", "sv_unc_a": "Часть текста похожа на написанный ИИ. Посмотрите выделенные предложения и сравните со стилем автора.",
           "sv_hum_t": "Скорее всего, текст написан человеком", "sv_hum_a": "Явных признаков ИИ не найдено. Но детектор может ошибаться, особенно на коротких текстах.",
           "sv_short": "Текст короткий ({n} слов): оценка менее надёжна.",
           "tour_step": "Шаг {n} из {total}", "tour_1_t": "Вставьте текст", "tour_1_b": "Вставьте текст в это поле или перетащите сюда файл Word, PDF или TXT.",
           "tour_2_t": "Нажмите «Проверить текст»", "tour_2_b": "Проверка занимает несколько секунд и идёт на вашем компьютере: тексты никуда не отправляются.",
           "tour_3_t": "Прочитайте результат", "tour_3_b": "Здесь появится вывод. Ниже подсветка покажет, какие предложения вызвали подозрение. Цвета означают:",
           "tour_l_ai": "Похоже на ИИ", "tour_l_unc": "Трудно сказать", "tour_l_hum": "Похоже на человека",
           "tour_next": "Далее", "tour_back": "Назад", "tour_skip": "Пропустить", "tour_done": "Готово", "tour_again": "Показать подсказки снова"},
    "pl": {"ui_sw_simple": "Prosty", "ui_sw_expert": "Szczegółowy", "sv_more": "Więcej szczegółów",
           "sv_ai_t": "Najpewniej tekst napisała sztuczna inteligencja", "sv_ai_a": "To nie jest dowód. Zapytaj autora, jak pisał tekst, i poproś o szkice.",
           "sv_unc_t": "Trudno powiedzieć", "sv_unc_a": "Część tekstu przypomina tekst AI. Zobacz zaznaczone zdania i porównaj ze stylem autora.",
           "sv_hum_t": "Najpewniej tekst napisał człowiek", "sv_hum_a": "Nie znaleziono wyraźnych śladów AI. Detektor może się jednak mylić, zwłaszcza przy krótkich tekstach.",
           "sv_short": "Tekst jest krótki ({n} słów): ocena jest mniej wiarygodna.",
           "tour_step": "Krok {n} z {total}", "tour_1_t": "Wklej tekst", "tour_1_b": "Wklej tekst w to pole lub przeciągnij tu plik Word, PDF albo TXT.",
           "tour_2_t": "Kliknij „Sprawdź tekst”", "tour_2_b": "Sprawdzanie trwa kilka sekund i odbywa się na Twoim komputerze: teksty nigdzie nie są wysyłane.",
           "tour_3_t": "Przeczytaj wynik", "tour_3_b": "Tutaj pojawi się wniosek. Podświetlenie poniżej pokaże, które zdania wzbudziły podejrzenia. Kolory oznaczają:",
           "tour_l_ai": "Wygląda na AI", "tour_l_unc": "Trudno powiedzieć", "tour_l_hum": "Wygląda na człowieka",
           "tour_next": "Dalej", "tour_back": "Wstecz", "tour_skip": "Pomiń", "tour_done": "Gotowe", "tour_again": "Pokaż wskazówki ponownie"},
    "en": {"ui_sw_simple": "Simple", "ui_sw_expert": "Detailed", "sv_more": "More details",
           "sv_ai_t": "The text was most likely written by AI", "sv_ai_a": "This is not proof. Ask the author how they wrote it and ask to see drafts.",
           "sv_unc_t": "Hard to say", "sv_unc_a": "Part of the text looks AI-written. Look at the highlighted sentences and compare with the author's style.",
           "sv_hum_t": "The text was most likely written by a person", "sv_hum_a": "No clear signs of AI were found. The detector can still be wrong, especially on short texts.",
           "sv_short": "The text is short ({n} words): the estimate is less reliable.",
           "tour_step": "Step {n} of {total}", "tour_1_t": "Paste your text", "tour_1_b": "Paste the text into this box or drop a Word, PDF or TXT file here.",
           "tour_2_t": "Press “Check text”", "tour_2_b": "A check takes a few seconds and runs on your computer: your texts are never sent anywhere.",
           "tour_3_t": "Read the result", "tour_3_b": "The conclusion appears here. The highlighting below shows which sentences raised suspicion. The colours mean:",
           "tour_l_ai": "Looks like AI", "tour_l_unc": "Hard to say", "tour_l_hum": "Looks human",
           "tour_next": "Next", "tour_back": "Back", "tour_skip": "Skip", "tour_done": "Done", "tour_again": "Show the tips again"},
}
for lang, kv in NEW.items():
    f = ROOT / "web" / "i18n" / f"{lang}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d.update(kv)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

# настройки на сервере
E = ROOT / "linda_desktop" / "engine.py"
s = E.read_text(encoding="utf-8")
if '"ui_mode"' not in s:
    s = s.replace('    "language": "ru",\n}', '    "language": "ru", "ui_mode": "simple", "tour_done": False,\n}', 1)
    E.write_text(s, encoding="utf-8")
A = ROOT / "linda_desktop" / "app.py"
s = A.read_text(encoding="utf-8")
if 'ui_mode' not in s:
    old = '        if body.get("language") in UI_LANGUAGES:\n            cur["language"] = body["language"]\n'
    assert old in s
    s = s.replace(old, old + '        if body.get("ui_mode") in ("simple", "expert"):\n            cur["ui_mode"] = body["ui_mode"]\n        if isinstance(body.get("tour_done"), bool):\n            cur["tour_done"] = body["tour_done"]\n', 1)
    A.write_text(s, encoding="utf-8")
print("patched")
