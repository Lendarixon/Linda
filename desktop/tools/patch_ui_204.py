# -*- coding: utf-8 -*-
"""Пачка улучшений 2.0.3.1: индикатор устройства + «Проверить скорость», предупреждения о ненадёжных случаях, «Почему такой вердикт»,
шрифт 150%, подсказки на трёх языках, перетаскивание файла в любое место окна, «Проверить буфер», оценка времени и места при скачивании."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "web" / "index.html"
t = P.read_text(encoding="utf-8")
if 'id="btnPaste"' in t:
    raise SystemExit("already patched")


def sub(old, new, count=1):
    global t
    if old not in t:
        raise SystemExit("not found: " + old[:90])
    t = t.replace(old, new, count)


sub("</style>\n</head>", """.sv-warn{white-space:pre-line}.sv-why{margin-top:12px;font-size:.88rem}.sv-why b{display:block;margin-bottom:4px}
.sv-why q{display:block;color:var(--text-muted);margin:3px 0;quotes:none}.sv-why q span{color:var(--ai);font-weight:600}
.dev-warn{color:#fa6800}
</style>
</head>""")

# ---- 1. индикатор устройства в шапке
sub("    const eng = s.engine.phase, dev = s.engine.device === 'cpu' ? T('dev_cpu') : T('dev_gpu');",
    """    const eng = s.engine.phase;
    const gI = s.engine.gpu || {}, gName = ((gI.names && gI.names[(s.settings || {}).gpu_index || 0]) || '').replace(/^(AMD|NVIDIA|Intel\\(R\\)) |\\(TM\\)|\\(R\\)/g, '').trim();
    const dev = s.engine.device === 'cpu' ? T('dev_cpu') : (gName || T('dev_gpu'));
    const slowWarn = s.engine.device === 'cpu' && gI.available && gI.discrete;  // есть дискретная карта, а считает процессор""")
sub("""$('devInfo').textContent = !s.models_ready ? '' : eng === 'loading' ? (s.engine.note || T('dev_loading'))""",
    """$('devInfo').classList.toggle('dev-warn', !!slowWarn && s.models_ready);
    $('devInfo').title = slowWarn ? T('dev_slow_tip') : '';
    $('devInfo').textContent = !s.models_ready ? '' : eng === 'loading' ? (s.engine.note === 'prepare_models' ? T('dev_prepare') : (s.engine.note || T('dev_loading')))""")

# ---- 2. «Проверить скорость» в настройках
sub('<p class="lp-hint lp-full" data-i18n="set_dev_note">',
    '<div class="lp-upd-row lp-full"><button class="lp-btn sec small" id="lpBench" data-i18n="bench_btn">Check speed</button><span class="note" id="lpBenchOut"></span></div>\n  <p class="lp-hint lp-full" data-i18n="set_dev_note">')

JS = r"""
  // ПРОВЕРИТЬ СКОРОСТЬ
  $('lpBench').onclick = async () => {
    const b = $('lpBench'), o = $('lpBenchOut'); b.disabled = true; o.textContent = T('bench_run');
    try {
      const r = await post('/api/benchmark');
      const g = r.gpu || {}, slow = r.device === 'cpu' && g.available && g.discrete;
      o.textContent = T('bench_res', { s: r.seconds, w: r.words, d: r.device === 'cpu' ? T('dev_cpu') : T('dev_gpu') }) + (slow ? ' ' + T('bench_cpu_hint') : '');
    } catch (e) { o.textContent = e.message; } finally { b.disabled = false; }
  };
  // ОЦЕНКА ВРЕМЕНИ СКАЧИВАНИЯ
  window.LINDA_eta = d => { if (!d || !d.speed || !d.total || d.done >= d.total) return ''; const m = Math.max(1, Math.round((d.total - d.done) / d.speed / 60)); return ' · ' + T('setup_eta', { m }); };
"""
sub("  // ЯЗЫК В ШАПКЕ И БЫСТРЫЕ НАСТРОЙКИ", JS + "  // ЯЗЫК В ШАПКЕ И БЫСТРЫЕ НАСТРОЙКИ")
sub("(d.speed ? T('setup_speed', { x: (d.speed / 1e6).toFixed(1) }) : '')", "(d.speed ? T('setup_speed', { x: (d.speed / 1e6).toFixed(1) }) : '') + window.LINDA_eta(d)")

# ---- 3. предупреждения о ненадёжных случаях и «почему»
sub("""    $('svWarn').textContent = words && words < 150 ? T('sv_short', { n: words }) : '';""",
    """    const warn = [], txt0 = r._text || '', letters = (txt0.match(/\\p{L}/gu) || []), cyr = (txt0.match(/[\\u0400-\\u04FF]/g) || []).length, lat = (txt0.match(/[A-Za-z\\u00C0-\\u017F]/g) || []).length;
    const other = letters.length - cyr - lat;
    if (words && words < 150) warn.push(T('sv_short', { n: words }));
    if (letters.length > 80 && cyr / letters.length > 0.12 && lat / letters.length > 0.12) warn.push(T('sv_mixed'));
    if (letters.length > 80 && other / letters.length > 0.3) warn.push(T('sv_lang'));
    if (txt0.length > 200 && letters.length / txt0.length < 0.6) warn.push(T('sv_symbols'));
    if (v !== 'human') warn.push(T('sv_esl'));
    $('svWarn').textContent = warn.join('\\n');
    const why = $('svWhy'), top = (r.sentences || []).filter(s => s.p_ai >= 0.5).sort((a, b) => b.p_ai - a.p_ai).slice(0, 3);
    why.innerHTML = '';
    if (v !== 'human' && top.length) {
      const h = document.createElement('b'); h.textContent = T('sv_why'); why.appendChild(h);
      top.forEach(s => { const q = document.createElement('q'); const sp = document.createElement('span'); sp.textContent = Math.round(s.p_ai * 100) + '% '; q.appendChild(sp); q.appendChild(document.createTextNode('\\u201c' + (s.text.length > 150 ? s.text.slice(0, 147) + '\\u2026' : s.text) + '\\u201d')); why.appendChild(q); });
    }""")
sub('<div class="sv-warn" id="svWarn"></div>', '<div class="sv-warn" id="svWarn"></div><div class="sv-why" id="svWhy"></div>')

# ---- 4. шрифт 150%
sub('<select class="lp-input" id="lpFont"><option value="90">90%</option><option value="100">100%</option><option value="110">110%</option><option value="125">125%</option></select>',
    '<select class="lp-input" id="lpFont"><option value="90">90%</option><option value="100">100%</option><option value="110">110%</option><option value="125">125%</option><option value="150">150%</option></select>')
sub('<select class="lp-input" id="qFont"><option value="90">90%</option><option value="100">100%</option><option value="110">110%</option><option value="125">125%</option></select>',
    '<select class="lp-input" id="qFont"><option value="90">90%</option><option value="100">100%</option><option value="110">110%</option><option value="125">125%</option><option value="150" data-i18n="font_xl">150% (large)</option></select>')

# ---- 5. подсказки
sub('<button class="active" data-sens="sensitive" data-i18n="ui_sensitive">', '<button class="active" data-sens="sensitive" data-i18n-title="tip_sensitive" data-i18n="ui_sensitive">')
sub('<button data-sens="precise" data-i18n="ui_precise">', '<button data-sens="precise" data-i18n-title="tip_precise" data-i18n="ui_precise">')
sub('<div class="verdict-pct" id="verdictPct">', '<div class="verdict-pct" id="verdictPct" data-i18n-title="tip_pct">')
sub('<div class="metric-label" data-i18n="ui_z">', '<div class="metric-label" data-i18n-title="tip_score" data-i18n="ui_z">')

# ---- 6. перетаскивание в любое место + проверка буфера
sub('<button class="btn-upload" id="btnUploadTrigger" type="button">',
    '<button class="btn-upload" id="btnPaste" type="button" data-i18n="ui_paste">Check clipboard</button>\n        <button class="btn-upload" id="btnUploadTrigger" type="button">')
JS2 = r"""
// ПЕРЕТАСКИВАНИЕ ФАЙЛА В ЛЮБОЕ МЕСТО ОКНА и «ПРОВЕРИТЬ БУФЕР»
['dragover', 'drop'].forEach(n => window.addEventListener(n, e => {
  if (!e.dataTransfer || ![...(e.dataTransfer.types || [])].includes('Files')) return;
  if (e.target.closest && e.target.closest('#bDrop,.cab-drop,#dropzoneBox')) return;  // у этих зон своя обработка
  e.preventDefault();
  if (n === 'drop' && e.dataTransfer.files && e.dataTransfer.files.length) { if (typeof showMainPane === 'function') { try { showMainPane(); } catch (x) { } } handleFileUpload(e.dataTransfer.files[0]); }
}));
document.getElementById('btnPaste').addEventListener('click', async () => {
  try {
    const txt = await navigator.clipboard.readText();
    if (!txt || !txt.trim()) { statusIndicator.textContent = window.LINDA_T('paste_empty'); return; }
    cancelCheck(); textInput.value = txt; textInput.dispatchEvent(new Event('input')); runAnalysis();
  } catch (e) { statusIndicator.textContent = window.LINDA_T('paste_fail'); textInput.focus(); }
});
"""
sub("// ПРОГРЕСС ОБРАБОТКИ:", JS2 + "// ПРОГРЕСС ОБРАБОТКИ:")
P.write_text(t, encoding="utf-8")

NEW = {
    "ru": {"dev_prepare": "Подготовка моделей (один раз, до минуты)…", "dev_slow_tip": "Есть видеокарта, но считает процессор. Откройте Настройки → «Чем считать» и выберите «Авто».",
           "bench_btn": "Проверить скорость", "bench_run": "Проверяю…", "bench_res": "{w} слов проверены за {s} с ({d}).",
           "bench_cpu_hint": "Есть видеокарта, но считает процессор: выберите «Авто» в списке выше.",
           "setup_eta": "осталось около {m} мин",
           "sv_why": "Больше всего похожи на ИИ:", "sv_mixed": "В тексте смешаны языки: оценка менее надёжна.",
           "sv_lang": "Похоже, язык текста не поддерживается (русский, польский, английский): оценка ненадёжна.",
           "sv_symbols": "В тексте много цифр, кода или таблиц: оценка менее надёжна.",
           "sv_esl": "Тексты людей, для которых язык не родной, иногда ошибочно принимаются за ИИ.",
           "font_xl": "150% (крупно)", "ui_paste": "Проверить буфер", "paste_empty": "В буфере обмена нет текста.", "paste_fail": "Не удалось прочитать буфер: вставьте текст сочетанием Ctrl+V.",
           "tip_sensitive": "Ловит больше текстов, написанных ИИ, но чаще ошибочно подозревает людей. Для личного использования.",
           "tip_precise": "Реже ошибочно подозревает людей, но пропускает больше текстов ИИ. Для школ и вузов.",
           "tip_pct": "Насколько программа уверена в выводе. Это не доказательство авторства.",
           "tip_score": "Общая оценка трёх моделей: чем выше, тем больше текст похож на написанный ИИ.",
           "err_no_space": "На диске с моделями мало места: нужно около %.1f ГБ, свободно %.1f ГБ. Выберите другую папку в настройках."},
    "pl": {"dev_prepare": "Przygotowanie modeli (jednorazowo, do minuty)…", "dev_slow_tip": "Jest karta graficzna, ale liczy procesor. Ustawienia → „Czym liczyć” → „Auto”.",
           "bench_btn": "Sprawdź szybkość", "bench_run": "Sprawdzam…", "bench_res": "{w} słów sprawdzono w {s} s ({d}).",
           "bench_cpu_hint": "Jest karta graficzna, ale liczy procesor: wybierz „Auto” na liście powyżej.",
           "setup_eta": "zostało około {m} min",
           "sv_why": "Najbardziej przypominają AI:", "sv_mixed": "W tekście zmieszano języki: ocena jest mniej wiarygodna.",
           "sv_lang": "Wygląda na to, że język tekstu nie jest obsługiwany (rosyjski, polski, angielski): ocena jest niewiarygodna.",
           "sv_symbols": "W tekście jest dużo cyfr, kodu lub tabel: ocena jest mniej wiarygodna.",
           "sv_esl": "Teksty osób, dla których język nie jest ojczysty, bywają błędnie uznawane za AI.",
           "font_xl": "150% (duża)", "ui_paste": "Sprawdź schowek", "paste_empty": "W schowku nie ma tekstu.", "paste_fail": "Nie udało się odczytać schowka: wklej tekst skrótem Ctrl+V.",
           "tip_sensitive": "Wykrywa więcej tekstów AI, ale częściej błędnie podejrzewa ludzi. Do użytku osobistego.",
           "tip_precise": "Rzadziej błędnie podejrzewa ludzi, ale pomija więcej tekstów AI. Dla szkół i uczelni.",
           "tip_pct": "Na ile program jest pewny wniosku. To nie jest dowód autorstwa.",
           "tip_score": "Łączna ocena trzech modeli: im wyższa, tym bardziej tekst przypomina tekst AI.",
           "err_no_space": "Na dysku z modelami jest za mało miejsca: potrzeba około %.1f GB, wolne %.1f GB. Wybierz inny folder w ustawieniach."},
    "en": {"dev_prepare": "Preparing the models (one time, up to a minute)…", "dev_slow_tip": "A graphics card is present but the processor is used. Settings → Run on → Automatic.",
           "bench_btn": "Check speed", "bench_run": "Checking…", "bench_res": "{w} words checked in {s} s ({d}).",
           "bench_cpu_hint": "A graphics card is present but the processor is used: choose Automatic in the list above.",
           "setup_eta": "about {m} min left",
           "sv_why": "Most similar to AI:", "sv_mixed": "The text mixes languages: the estimate is less reliable.",
           "sv_lang": "The language of the text does not look supported (Russian, Polish, English): the estimate is unreliable.",
           "sv_symbols": "The text has many numbers, code or tables: the estimate is less reliable.",
           "sv_esl": "Texts by people writing in a non-native language are sometimes mistaken for AI.",
           "font_xl": "150% (large)", "ui_paste": "Check clipboard", "paste_empty": "The clipboard has no text.", "paste_fail": "Could not read the clipboard: paste the text with Ctrl+V.",
           "tip_sensitive": "Catches more AI-written texts but more often wrongly suspects people. For personal use.",
           "tip_precise": "Wrongly suspects people less often but misses more AI texts. For schools and universities.",
           "tip_pct": "How sure the program is of its conclusion. It is not proof of authorship.",
           "tip_score": "Combined score of the three models: the higher, the more the text looks AI-written.",
           "err_no_space": "Not enough space on the models disk: about %.1f GB needed, %.1f GB free. Choose another folder in Settings."},
}
for lang, kv in NEW.items():
    f = ROOT / "web" / "i18n" / f"{lang}.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d.update(kv)
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

# сервер: шрифт 150, проверка места перед скачиванием
E = ROOT / "linda_desktop" / "engine.py"
s = E.read_text(encoding="utf-8")
s = s.replace("UI_FONT_SCALES = (90, 100, 110, 125)", "UI_FONT_SCALES = (90, 100, 110, 125, 150)")
E.write_text(s, encoding="utf-8")
A = ROOT / "linda_desktop" / "app.py"
s = A.read_text(encoding="utf-8")
old = '        if not core.job.start(core.manifest, core.manifest_raw):'
new = '''        need = float((core.update or {}).get("bytes_to_download") or 0)
        free = models_location.free_gb(Path(config.models_root()))
        if need and free * 2**30 < need * 1.15 + 1.5 * 2**30:  # models + a safety margin + the ONNX cache
            return terr("err_no_space", 507, need * 1.15 / 2**30 + 1.5, free)
        if not core.job.start(core.manifest, core.manifest_raw):'''
assert old in s
if "err_no_space" not in s:
    s = s.replace(old, new, 1)
A.write_text(s, encoding="utf-8")
print("patched")
