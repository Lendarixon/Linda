# -*- coding: utf-8 -*-
"""Home page v5: the page IS the detector demo.

Above the fold: one sentence, a paste field, a Check button.
Below it: the result, then the download block (Store + GitHub + price),
then Probe as a second product, then help / privacy / FAQ.

Idempotent: rewrites <section class="task-first"> and everything the old home
carried between it and the FAQ, keeping the FAQ itself.
"""
import re, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

T = {
    'en': dict(
        file='index.html', s='', lang='en',
        eyebrow='Linda Detector · AI text check for Windows',
        h1='Paste a text. See whether AI wrote it.',
        lead='Paste a text and get a verdict in a few seconds — no account, no limits on the desktop app.',
        placeholder='Paste an essay, an article or a work e-mail — at least 20 words.',
        check='Check the text',
        note='No account. The text is processed on a server for this check.',
        dl_h='Want it on your computer?',
        dl_p='The desktop app checks text offline, with no character limit, and adds the Humanizer and Trace.',
        dl_store='Get it from Microsoft Store',
        dl_gh='Installer from GitHub',
        dl_price='Licences from $10 · one-time',
        probe_h='Linda Probe — find a file by the words inside',
        probe_p='A second app, for documents rather than texts: it searches inside PDFs, Word files and scans on your own computer. Install it separately if you need it.',
        probe_cta='About Linda Probe',
        help_h='How do the paid tools work?',
        help_p='A Detector licence unlocks the Humanizer and Trace. Meaning-based search, OCR and photo search need a separate Probe Pro licence. You do not have to buy both.',
        help_cta='Prices and licences',
        sample='The implementation of the proposed methodology facilitates a substantial improvement in overall operational efficiency. Furthermore, it is important to note that the utilization of advanced analytical frameworks enables organizations to achieve enhanced outcomes across multiple dimensions of performance. It is therefore recommended that stakeholders consider the adoption of these practices in order to maximize the realization of potential benefits.',
        sample_btn='Try an example',
        faq_trace='No. Trace compares your texts and ranks how similar their style is. Genre, length, editing and shared sources all change the result, so it is a clue, not proof.',
    ),
    'ru': dict(
        file='ru.html', s='-ru', lang='ru',
        eyebrow='Linda Detector · проверка текста на ИИ для Windows',
        h1='Вставьте текст. Узнайте, писал ли его ИИ.',
        lead='Вставьте текст и получите вердикт за пару секунд — без аккаунта, а в приложении ещё и без лимитов.',
        placeholder='Вставьте эссе, статью или рабочее письмо — не меньше 20 слов.',
        check='Проверить текст',
        note='Без аккаунта. Для этой проверки текст обрабатывается на сервере.',
        dl_h='Нужно на своём компьютере?',
        dl_p='Приложение проверяет текст офлайн, без ограничения по символам, и добавляет Гуманайзер и Trace.',
        dl_store='Скачать из Microsoft Store',
        dl_gh='Установщик с GitHub',
        dl_price='Лицензии от $10 · разово',
        probe_h='Linda Probe — найти файл по словам внутри',
        probe_p='Вторая программа, для документов, а не текстов: ищет внутри PDF, файлов Word и сканов на вашем компьютере. Ставится отдельно, если нужна.',
        probe_cta='Подробнее о Linda Probe',
        help_h='Как устроены платные возможности?',
        help_p='Лицензия Detector открывает Гуманайзер и Trace. Для поиска по смыслу, OCR и поиска по фото нужна отдельная лицензия Probe Pro. Покупать обе необязательно.',
        help_cta='Цены и лицензии',
        sample='Внедрение предложенной методологии способствует существенному повышению общей операционной эффективности. Кроме того, важно отметить, что использование продвинутых аналитических инструментов позволяет организациям достигать улучшенных результатов по многим направлениям деятельности. Таким образом, заинтересованным сторонам рекомендуется рассмотреть внедрение указанных практик для максимальной реализации потенциальных выгод.',
        sample_btn='Попробовать на примере',
        faq_trace='Нет. Trace сравнивает ваши тексты и показывает, насколько похож их стиль. На результат влияют жанр, объём, редактирование и общие источники — это подсказка, а не доказательство.',
    ),
    'pl': dict(
        file='pl.html', s='-pl', lang='pl',
        eyebrow='Linda Detector · sprawdzanie tekstu pod kątem AI dla Windows',
        h1='Wklej tekst. Sprawdź, czy napisało go AI.',
        lead='Wklej tekst i dostań werdykt w kilka sekund — bez konta, a w aplikacji także bez limitów.',
        placeholder='Wklej esej, artykuł albo służbowy e-mail — co najmniej 20 słów.',
        check='Sprawdź tekst',
        note='Bez konta. Na potrzeby tego sprawdzenia tekst jest przetwarzany na serwerze.',
        dl_h='Chcesz mieć to na swoim komputerze?',
        dl_p='Aplikacja sprawdza tekst offline, bez limitu znaków, i dodaje Humanizera oraz Trace.',
        dl_store='Pobierz z Microsoft Store',
        dl_gh='Instalator z GitHuba',
        dl_price='Licencje od $10 · jednorazowo',
        probe_h='Linda Probe — znajdź plik po słowach w środku',
        probe_p='Druga aplikacja, do dokumentów, nie do tekstów: szuka wewnątrz PDF-ów, plików Word i skanów na Twoim komputerze. Instaluje się osobno, jeśli jest potrzebna.',
        probe_cta='Więcej o Linda Probe',
        help_h='Jak działają płatne funkcje?',
        help_p='Licencja Detector odblokowuje Humanizera i Trace. Wyszukiwanie po sensie, OCR i szukanie po zdjęciu wymagają osobnej licencji Probe Pro. Nie trzeba kupować obu.',
        help_cta='Ceny i licencje',
        sample='Wdrożenie proponowanej metodologii umożliwia istotną poprawę ogólnej efektywności operacyjnej. Ponadto należy zauważyć, że wykorzystanie zaawansowanych narzędzi analitycznych pozwala organizacjom osiągać lepsze wyniki w wielu obszarach działalności. Zaleca się zatem rozważenie wdrożenia tych praktyk w celu maksymalizacji potencjalnych korzyści.',
        sample_btn='Wypróbuj na przykładzie',
        faq_trace='Nie. Trace porównuje Twoje teksty i pokazuje, jak podobny jest ich styl. Na wynik wpływają gatunek, długość, redakcja i wspólne źródła — to podpowiedź, nie dowód.',
    ),
}

STORE_DETECTOR = 'https://apps.microsoft.com/detail/9NP66G69BQPN'
GH_DETECTOR = 'https://github.com/Lendarixon/Linda/releases/latest'

HERO = '''<section class="task-first" id="products"><div class="start-copy"><p class="eyebrow">{eyebrow}</p><h1>{h1}</h1><p class="lead">{lead}</p></div><div class="hd-card" data-hd data-state="idle" data-sample="{sample}"><label class="hd-label" for="hd-input">{placeholder}</label><textarea class="hd-input" id="hd-input" rows="6" spellcheck="false"></textarea><div class="hd-row"><button class="button primary hd-check" type="button">{check}</button><button class="text-link hd-sample" type="button">{sample_btn}</button><span class="hd-hint">{note}</span></div><p class="hd-error" hidden></p><div class="hd-result" hidden></div></div><section class="home-download" id="download"><div class="hd-dl-copy"><h2>{dl_h}</h2><p>{dl_p}</p></div><div class="hd-dl-actions"><a class="button primary" href="''' + STORE_DETECTOR + '''">{dl_store}<span aria-hidden="true">↗</span></a><a class="button" href="''' + GH_DETECTOR + '''">{dl_gh}<span aria-hidden="true">↗</span></a><a class="text-link" href="pricing{s}.html">{dl_price}<span aria-hidden="true">↗</span></a></div></section><section class="home-probe"><div><span class="eyebrow">Linda Probe</span><h2>{probe_h}</h2><p>{probe_p}</p></div><a class="button" href="probe{s}.html">{probe_cta}<span aria-hidden="true">↗</span></a></section><section class="catalogue-help"><div><h2>{help_h}</h2><p>{help_p}</p><a class="text-link" href="pricing{s}.html">{help_cta}<span aria-hidden="true">↗</span></a></div></section><aside class="privacy-strip">[LOCK]<div><h3>{privacy_h}</h3><p>{privacy_p}</p></div></aside>'''


def main():
    for lang, d in T.items():
        path = os.path.join(ROOT, d['file'])
        s = io.open(path, encoding='utf-8', newline='').read()
        orig = s

        # keep the FAQ section as it is
        m = re.search(r'<section><div class="section-heading reveal">.*?</section>', s, re.S)
        faq = m.group(0) if m else ''
        if faq:
            s = s.replace(faq, '<!--FAQ-->')

        i = s.find('<section class="task-first"')
        j = s.find('<!--FAQ-->')
        if i < 0 or j < 0:
            print('  ! anchors missing in', d['file'], i, j)
            continue

        lock = ''
        pm = re.search(r'<aside class="privacy-strip">(<svg.*?</svg>)', s, re.S)
        if pm:
            lock = pm.group(1)

        vals = dict(d)
        vals['privacy_h'] = {
            'en': 'Need to keep a text on your computer?',
            'ru': 'Нужно оставить текст на компьютере?',
            'pl': 'Chcesz zachować tekst na swoim komputerze?',
        }[lang]
        vals['privacy_p'] = {
            'en': 'Install the desktop app: it checks text locally. This page sends the text to a server for the online check, so do not paste confidential documents.',
            'ru': 'Установите приложение: там проверка идёт локально. Эта страница отправляет текст на сервер — не вставляйте сюда конфиденциальные документы.',
            'pl': 'Zainstaluj aplikację: tam sprawdzanie odbywa się lokalnie. Ta strona wysyła tekst na serwer — nie wklejaj tu poufnych dokumentów.',
        }[lang]

        hero = HERO.format(**vals).replace('[LOCK]', lock)
        s = s[:i] + hero + s[j:]
        s = s.replace('<!--FAQ-->', faq)

        # the Trace answer in the FAQ: plain words instead of "ранжирует сходство стиля"
        s = re.sub(r'(<details><summary>[^<]*Trace[^<]*<span[^>]*>\+</span></summary>)<p>.*?</p>',
                   lambda mm: mm.group(1) + '<p>' + d['faq_trace'] + '</p>', s, flags=re.S)

        # the home page now owns the demo, so the "how to use the demo" guide is gone
        s = re.sub(r'<details class="task-demo-guide">.*?</details>', '', s, flags=re.S)
        s = re.sub(r'<section class="catalogue-evidence">.*?</section>', '', s, flags=re.S)

        if s != orig:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  home ->', d['file'])
        else:
            print('  unchanged', d['file'])


if __name__ == '__main__':
    main()
