# -*- coding: utf-8 -*-
"""Home page v3: one clear sentence, two product tiles, everything else below the fold.

Idempotent: rewrites <section class="task-first"> and drops the heavy
catalogue card block, keeping the demo guide, help, evidence, privacy and FAQ.
"""
import re, sys, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

T = {
    'en': dict(
        file='index.html', s='',
        eyebrow='Linda · Windows apps for text and files',
        h1='Check a text for AI. Find a file by its words.',
        lead='Two apps that run on your own computer. Detector estimates whether a text looks AI-written; Probe finds documents by the words inside them.',
        badge='Free for personal use · no account',
        d_name='Linda Detector', d_desc='Does this text look AI-written?',
        p_name='Linda Probe', p_desc='Where is that document?',
        quiet='Inside Detector: <a href="humanizer{s}.html">Humanizer</a> rewrites stiff phrasing and <a href="authorship{s}.html">Trace</a> compares writing styles. <a href="https://lendarixon.github.io/Linda/demo.html">Try the detector online<span aria-hidden="true">↗</span></a>',
        quiet2='Inside Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> adds meaning-based search, OCR for scans and search by photo.',
        cta1='Download for Windows', cta2='Try the detector online',
        audience='For teachers, editors, translators, students and offices.',
    ),
    'ru': dict(
        file='ru.html', s='-ru',
        eyebrow='Linda · программы для Windows',
        h1='Проверить текст на ИИ. Найти файл по словам внутри.',
        lead='Две программы, которые работают на вашем компьютере. Detector оценивает, похож ли текст на написанный ИИ; Probe ищет документы по словам внутри.',
        badge='Бесплатно для личного использования · без аккаунта',
        d_name='Linda Detector', d_desc='Похож ли этот текст на ИИ?',
        p_name='Linda Probe', p_desc='Где этот документ?',
        quiet='Внутри Detector: <a href="humanizer{s}.html">Гуманайзер</a> убирает канцелярит, <a href="authorship{s}.html">Trace</a> сравнивает стиль текстов. <a href="https://lendarixon.github.io/Linda/demo.html">Проверить текст в демо<span aria-hidden="true">↗</span></a>',
        quiet2='Внутри Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> ищет по смыслу, распознаёт сканы и находит файлы по фото.',
        cta1='Скачать для Windows', cta2='Проверить текст в демо',
        audience='Для учителей, редакторов, переводчиков, студентов и офисов.',
    ),
    'pl': dict(
        file='pl.html', s='-pl',
        eyebrow='Linda · aplikacje dla Windows',
        h1='Sprawdź tekst pod kątem AI. Znajdź plik po słowach w środku.',
        lead='Dwie aplikacje, które działają na Twoim komputerze. Detector ocenia, czy tekst wygląda na napisany przez AI; Probe szuka dokumentów po słowach w środku.',
        badge='Bezpłatnie do użytku osobistego · bez konta',
        d_name='Linda Detector', d_desc='Czy ten tekst wygląda na AI?',
        p_name='Linda Probe', p_desc='Gdzie jest ten dokument?',
        quiet='W Detectorze: <a href="humanizer{s}.html">Humanizer</a> poprawia sztywny styl, <a href="authorship{s}.html">Trace</a> porównuje styl tekstów. <a href="https://lendarixon.github.io/Linda/demo.html">Sprawdź tekst w demo<span aria-hidden="true">↗</span></a>',
        quiet2='W Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> dodaje wyszukiwanie po sensie, OCR skanów i szukanie po zdjęciu.',
        cta1='Pobierz dla Windows', cta2='Sprawdź tekst w demo',
        audience='Dla nauczycieli, redaktorów, tłumaczy, studentów i biur.',
    ),
}

HERO = '''<section class="task-first" id="products"><div class="start-head"><div class="start-copy"><p class="eyebrow">{eyebrow}</p><h1>{h1}</h1><p class="lead">{lead}</p><span class="badge">{badge}</span></div></div><nav class="start-wall" aria-label="Linda apps">
<a class="live-tile wide detector" href="detector{s}.html" style="--d:0s"><span class="faces">
<span class="face"><img class="tile-glyph-img" src="assets/detector-glyph.svg" alt="" width="92" height="67"></span>
<span class="face specimen"><span class="tile-cap">Example</span><span class="spec-text"><mark>This passage needs a closer look.</mark></span><span class="spec-meter"><span>AI signals</span><i><b></b></i></span></span>
</span><span class="tile-label"><span class="tile-name">{d_name}</span><span class="tile-desc">{d_desc}</span></span><span class="tile-go" aria-hidden="true">↗</span></a>
<a class="live-tile wide probe" href="probe{s}.html" style="--d:1.3s"><span class="faces">
<span class="face"><img class="tile-glyph-img" src="assets/probe-glyph.svg" alt="" width="64" height="58"></span>
<span class="face search"><span class="search-q">budget presentation, spring</span><ul><li><b>PPT</b>Spring budget.pptx</li><li><b>DOC</b>Project notes.docx</li><li><b>PDF</b>Annual report.pdf</li></ul></span>
</span><span class="tile-label"><span class="tile-name">{p_name}</span><span class="tile-desc">{p_desc}</span></span><span class="tile-go" aria-hidden="true">↗</span></a>
</nav><div class="home-actions"><a class="button primary" href="downloads{s}.html">{cta1}<span aria-hidden="true">↗</span></a></div><div class="quiet-row"><p class="quiet-line">{quiet}</p><p class="quiet-line">{quiet2}</p></div><p class="audience-line">{audience}</p></section>'''


def section_span(s, start_marker):
    i = s.find(start_marker)
    if i < 0:
        return None
    j = s.find('</section>', i)
    return i, j + len('</section>')


def main():
    for lang, d in T.items():
        path = os.path.join(ROOT, d['file'])
        s = io.open(path, encoding='utf-8', newline='').read()
        orig = s

        # keep the demo guide (collapsed details) out of the block we drop
        guide = ''
        m = re.search(r'<details class="task-demo-guide">.*?</details>', s, re.S)
        if m:
            guide = m.group(0)

        span = section_span(s, '<section class="task-first"')
        if not span:
            print('  ! no task-first in', d['file'])
            continue
        i, j = span
        vals = {k: v for k, v in d.items() if k != 'file'}
        vals['quiet'] = d['quiet'].replace('{s}', d['s'])
        vals['quiet2'] = d['quiet2'].replace('{s}', d['s'])
        hero = HERO.format(**vals)
        s = s[:i] + hero + s[j:]

        span = section_span(s, '<section class="catalogue-section" id="products"')
        if span:
            i, j = span
            s = s[:i] + (guide + '\n' if guide else '') + s[j:]

        # "Not sure where to start?" is answered by the tiles now — drop just that block
        s = re.sub(r'<div><h2>Not sure where to start\?</h2>.*?</div>', '', s, flags=re.S)
        s = re.sub(r'<div><h2>Не знаете, с чего начать\?</h2>.*?</div>', '', s, flags=re.S)
        s = re.sub(r'<div><h2>Nie wiesz, od czego zacząć\?</h2>.*?</div>', '', s, flags=re.S)

        if s != orig:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  home ->', d['file'])
        else:
            print('  unchanged', d['file'])


if __name__ == '__main__':
    main()
