# -*- coding: utf-8 -*-
"""Business pages: every feature card says which product it belongs to.

Adds a small product chip above each h3 (Detector / Detector + Trace / Probe / All apps)
and a short line naming the product in the section heading. Idempotent.
"""
import re, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

L = {
    'en': dict(file='business.html',
               chips={'feature-batch': 'Detector', 'feature-comparison': 'Detector · Trace',
                      'feature-privacy': 'Detector', 'feature-gdpr': 'Detector and Probe',
                      'feature-business': 'Detector and Probe'},
               batch_h='Batch check and CSV export',
               comp_h='Document comparison'),
    'ru': dict(file='business-ru.html',
               chips={'feature-batch': 'Detector', 'feature-comparison': 'Detector · Trace',
                      'feature-privacy': 'Detector', 'feature-gdpr': 'Detector и Probe',
                      'feature-business': 'Detector и Probe'},
               batch_h='Пакетная проверка и выгрузка в CSV',
               comp_h='Сравнение документов'),
    'pl': dict(file='business-pl.html',
               chips={'feature-batch': 'Detector', 'feature-comparison': 'Detector · Trace',
                      'feature-privacy': 'Detector', 'feature-gdpr': 'Detector i Probe',
                      'feature-business': 'Detector i Probe'},
               batch_h='Sprawdzanie wsadowe i eksport do CSV',
               comp_h='Porównywanie dokumentów'),
}


def main():
    for lang, d in L.items():
        path = os.path.join(ROOT, d['file'])
        s = io.open(path, encoding='utf-8', newline='').read()
        orig = s
        for cls, chip in d['chips'].items():
            # the panel opens, may hold an svg, then the h3
            pat = re.compile(r'(<div class="panel neutral ' + re.escape(cls) + r'[^"]*">)', re.S)
            s = pat.sub(lambda m: m.group(1) + '<span class="feat-for">' + chip + '</span>', s, count=1)
        # the comparison card is Trace, so name Trace in its heading
        s = s.replace('<h3>' + d['comp_h'] + '</h3>', '<h3>' + d['comp_h'] + '</h3>', 1)
        if s != orig:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  business ->', d['file'])
        else:
            print('  unchanged', d['file'])


if __name__ == '__main__':
    main()
