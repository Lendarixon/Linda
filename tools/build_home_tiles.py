"""Insert the Metro start-screen 'live tile' wall into the three home pages.

Idempotent (replaces <div class="start-head">...</div><!--/start-head-->). Content is illustrative and reuses the
translated sample strings of the product-page mock-ups. Run after editing the strings below:
  python tools/build_home_tiles.py
"""
import html, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent

T = {
    'en': dict(page='index.html', sfx='', example='Example',
               det='Linda Detector', det_txt='Good writing leaves room for a reader.', det_mark='This passage needs a closer look.',
               det_verdict='AI signals', langs='EN · PL · RU',
               probe='Linda Probe', probe_q='budget presentation, spring', files=[('PPT', 'Spring budget.pptx'), ('DOC', 'Project notes.docx'), ('PDF', 'Annual report.pdf')],
               hum='Humanizer', before='Before', after='After',
               hum_b='facilitates improvement', hum_a='improves',
               trace='Linda Trace', trace_cap='Style similarity',
               local='On your PC', local_txt='Texts and files are processed locally',
               price_cap='Licences', price='from $10', price_txt='one-time',
               aria='Linda apps'),
    'ru': dict(page='ru.html', sfx='-ru', example='Пример',
               det='Linda Detector', det_txt='Хороший текст оставляет место читателю.', det_mark='На этот фрагмент стоит взглянуть внимательнее.',
               det_verdict='Признаки ИИ', langs='EN · PL · RU',
               probe='Linda Probe', probe_q='презентация с бюджетом, весна', files=[('PPT', 'Бюджет на весну.pptx'), ('DOC', 'Заметки по проекту.docx'), ('PDF', 'Годовой отчёт.pdf')],
               hum='Гуманайзер', before='До', after='После',
               hum_b='способствует улучшению', hum_a='улучшает',
               trace='Linda Trace', trace_cap='Сходство стиля',
               local='На вашем ПК', local_txt='Тексты и файлы обрабатываются локально',
               price_cap='Лицензии', price='от $10', price_txt='один раз',
               aria='Программы Linda'),
    'pl': dict(page='pl.html', sfx='-pl', example='Przykład',
               det='Linda Detector', det_txt='Dobry tekst zostawia miejsce dla czytelnika.', det_mark='Temu fragmentowi warto przyjrzeć się bliżej.',
               det_verdict='Sygnały AI', langs='EN · PL · RU',
               probe='Linda Probe', probe_q='prezentacja budżetu, wiosna', files=[('PPT', 'Budżet na wiosnę.pptx'), ('DOC', 'Notatki projektowe.docx'), ('PDF', 'Raport roczny.pdf')],
               hum='Humanizer', before='Przed', after='Po',
               hum_b='przyczynia się do poprawy', hum_a='poprawia',
               trace='Linda Trace', trace_cap='Podobieństwo stylu',
               local='Na Twoim PC', local_txt='Teksty i pliki są przetwarzane lokalnie',
               price_cap='Licencje', price='od 10 USD', price_txt='jednorazowo',
               aria='Aplikacje Linda'),
}

LOCK = '<svg viewBox="0 0 34 34" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M9 15V10a8 8 0 0 1 16 0v5M6 15h22v15H6z"/><path d="M17 21v4"/></svg>'


def wall(t):
    e = {k: html.escape(v) if isinstance(v, str) else v for k, v in t.items()}
    s = e['sfx']
    files = ''.join(f'<li><b>{html.escape(k)}</b>{html.escape(n)}</li>' for k, n in t['files'])
    # Metro live tile: content faces peek upward, the app name stays fixed in the bottom-left corner.
    return f'''<nav class="start-wall" aria-label="{e['aria']}">
<a class="live-tile wide detector" href="detector{s}.html" style="--d:0s"><span class="faces">
<span class="face"><img class="tile-glyph-img" src="assets/detector-glyph.svg" alt="" width="92" height="67"></span>
<span class="face specimen"><span class="tile-cap">{e['example']}</span><span class="spec-text"><mark>{e['det_mark']}</mark></span><span class="spec-meter"><span>{e['det_verdict']}</span><i><b></b></i></span></span>
</span><span class="tile-name">{e['det']}</span></a>
<a class="live-tile wide probe" href="probe{s}.html" style="--d:1.3s"><span class="faces">
<span class="face"><img class="tile-glyph-img" src="assets/probe-glyph.svg" alt="" width="64" height="58"></span>
<span class="face search"><span class="search-q">{e['probe_q']}</span><ul>{files}</ul></span>
</span><span class="tile-name">{e['probe']}</span></a>
<a class="live-tile humanizer" href="humanizer{s}.html" style="--d:2.6s"><span class="faces">
<span class="face"><span class="tile-mark" aria-hidden="true">Aa</span></span>
<span class="face rewrite"><s>{e['hum_b']}</s><span class="rw-arrow" aria-hidden="true">↓</span><span class="rw-new">{e['hum_a']}</span></span>
</span><span class="tile-name">{e['hum']}</span></a>
<a class="live-tile authorship" href="authorship{s}.html" style="--d:3.9s"><span class="faces">
<span class="face"><span class="tile-mark" aria-hidden="true">A·B</span></span>
<span class="face ranking" title="{e['trace_cap']}"><span class="rank-row"><b>A</b><i style="--w:86%"></i></span><span class="rank-row"><b>B</b><i style="--w:54%"></i></span><span class="rank-row"><b>C</b><i style="--w:31%"></i></span></span>
</span><span class="tile-name">{e['trace']}</span></a>
</nav>'''


def main():
    for lang, t in T.items():
        p = ROOT / t['page']
        s = p.read_text(encoding='utf-8')
        new, n = re.subn(r'<nav class="start-wall".*?</nav>', wall(t).replace('\\', '\\\\'), s, flags=re.S)
        assert n == 1, (p.name, n)
        p.write_text(new, encoding='utf-8')
        print('tiles ->', p.name)

if __name__ == '__main__':
    main()
