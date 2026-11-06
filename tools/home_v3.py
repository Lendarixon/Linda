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
        d_name='Linda Detector', d_desc='Does this text look AI-written?', d_kind='Windows app', d_tag='AI signals', d_score='62%',
        d_before='This paragraph ', d_mark='needs a closer look', d_after=' before you rely on it.', f1='Spring budget.pptx', f2='Project notes.docx', f3='Annual report.pdf', p_query='budget, spring',
        p_name='Linda Probe', p_desc='Where is that document?', p_kind='Windows app',
        quiet='Inside Detector: <a href="humanizer{s}.html">Humanizer</a> rewrites stiff phrasing and <a href="authorship{s}.html">Trace</a> compares writing styles.',
        quiet2='Inside Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> adds meaning-based search, OCR for scans and search by photo.',
        cta1='Download for Windows', cta2='Detector demo online', d_cta='Download Detector', p_cta='Download Probe',
        audience='For teachers, editors, translators, students and offices.',
    ),
    'ru': dict(
        file='ru.html', s='-ru',
        eyebrow='Linda · программы для Windows',
        h1='Проверить текст на ИИ. Найти файл по словам внутри.',
        lead='Две программы, которые работают на вашем компьютере. Detector оценивает, похож ли текст на написанный ИИ; Probe ищет документы по словам внутри.',
        badge='Бесплатно для личного использования · без аккаунта',
        d_name='Linda Detector', d_desc='Похож ли этот текст на ИИ?', d_kind='Программа для Windows', d_tag='Признаки ИИ', d_score='62%',
        d_before='Этот абзац ', d_mark='стоит проверить', d_after=' внимательнее.', f1='Бюджет на весну.pptx', f2='Заметки по проекту.docx', f3='Годовой отчёт.pdf', p_query='бюджет, весна',
        p_name='Linda Probe', p_desc='Где этот документ?', p_kind='Программа для Windows',
        quiet='Внутри Detector: <a href="humanizer{s}.html">Гуманайзер</a> убирает канцелярит, <a href="authorship{s}.html">Trace</a> сравнивает стиль текстов.',
        quiet2='Внутри Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> ищет по смыслу, распознаёт сканы и находит файлы по фото.',
        cta1='Скачать для Windows', cta2='Демо детектора', d_cta='Скачать Detector', p_cta='Скачать Probe',
        audience='Для учителей, редакторов, переводчиков, студентов и офисов.',
    ),
    'pl': dict(
        file='pl.html', s='-pl',
        eyebrow='Linda · aplikacje dla Windows',
        h1='Sprawdź tekst pod kątem AI. Znajdź plik po słowach w środku.',
        lead='Dwie aplikacje, które działają na Twoim komputerze. Detector ocenia, czy tekst wygląda na napisany przez AI; Probe szuka dokumentów po słowach w środku.',
        badge='Bezpłatnie do użytku osobistego · bez konta',
        d_name='Linda Detector', d_desc='Czy ten tekst wygląda na AI?', d_kind='Aplikacja dla Windows', d_tag='Sygnały AI', d_score='62%',
        d_before='Ten akapit ', d_mark='warto sprawdzić', d_after=' dokładniej.', f1='Budżet na wiosnę.pptx', f2='Notatki projektowe.docx', f3='Raport roczny.pdf', p_query='budżet, wiosna',
        p_name='Linda Probe', p_desc='Gdzie jest ten dokument?', p_kind='Aplikacja dla Windows',
        quiet='W Detectorze: <a href="humanizer{s}.html">Humanizer</a> poprawia sztywny styl, <a href="authorship{s}.html">Trace</a> porównuje styl tekstów.',
        quiet2='W Probe: <a href="pricing{s}.html?app=probe">Probe Pro</a> dodaje wyszukiwanie po sensie, OCR skanów i szukanie po zdjęciu.',
        cta1='Pobierz dla Windows', cta2='Demo detektora', d_cta='Pobierz Detector', p_cta='Pobierz Probe',
        audience='Dla nauczycieli, redaktorów, tłumaczy, studentów i biur.',
    ),
}

HERO = '''<section class="task-first" id="products"><div class="start-copy"><p class="eyebrow">{eyebrow}</p><h1>{h1}</h1><p class="lead">{lead}</p><span class="badge">{badge}</span></div><nav class="start-wall" aria-label="Linda apps">
<a class="live-tile product-tile pe-detector" href="detector{s}.html"><span class="pt-head"><img class="pt-icon" src="assets/detector-glyph.svg" alt="" width="26" height="20"><span class="pt-kind">{d_kind}</span></span><span class="pt-preview"><span class="pp-text">{d_before}<mark>{d_mark}</mark>{d_after}</span><span class="pp-meter"><i style="--w:{d_score}"></i><b>{d_score}</b></span><span class="pp-tag">{d_tag}</span></span><span class="pt-foot"><span class="pt-name">{d_name}</span><span class="pt-desc">{d_desc}</span></span><span class="tile-go" aria-hidden="true">↗</span></a>
<a class="live-tile product-tile pe-probe" href="probe{s}.html"><span class="pt-head"><img class="pt-icon" src="assets/probe-glyph.svg" alt="" width="24" height="22"><span class="pt-kind">{p_kind}</span></span><span class="pt-preview"><span class="pp-q">{p_query}</span><span class="pp-files"><span class="pp-file"><b>PPT</b>{f1}</span><span class="pp-file"><b>DOC</b>{f2}</span><span class="pp-file"><b>PDF</b>{f3}</span></span></span><span class="pt-foot"><span class="pt-name">{p_name}</span><span class="pt-desc">{p_desc}</span></span><span class="tile-go" aria-hidden="true">↗</span></a>
</nav><div class="home-actions"><a class="button primary bt-detector" href="downloads{s}.html#detector">{d_cta}<span aria-hidden="true">↗</span></a><a class="button primary bt-probe" href="downloads{s}.html#probe">{p_cta}<span aria-hidden="true">↗</span></a></div><div class="quiet-row"><p class="quiet-line">{quiet}</p><p class="quiet-line">{quiet2}</p></div><p class="audience-line">{audience}</p></section>'''


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
        vals['quiet'] = d['quiet'].replace('{s}', d['s']).replace('{cta2}', d['cta2'])
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
