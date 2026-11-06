# -*- coding: utf-8 -*-
"""Business pages: the Organization card sends the visitor to the pricing page
instead of jumping into a Polar checkout for one app.

The card describes a licence for the whole company, but the old link opened the
Detector Organization checkout directly, so a buyer could not see that Probe Pro
is a separate licence. Both licence cards now lead to the pricing page, where the
Detector / Probe Pro tabs make the choice explicit. Idempotent.
"""
import re, io, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

L = {
    'en': dict(file='business.html', label='Choose a licence', href='pricing.html?app=detector'),
    'ru': dict(file='business-ru.html', label='Выбрать лицензию', href='pricing-ru.html?app=detector'),
    'pl': dict(file='business-pl.html', label='Wybierz licencję', href='pricing-pl.html?app=detector'),
}

POLAR_ORG = 'https://buy.polar.sh/polar_cl_UznG2OPeM5diDZ1nCtxwRD1HW1pO3OZIu55DN07bCQe'


def main():
    for lang, d in L.items():
        path = os.path.join(ROOT, d['file'])
        s = io.open(path, encoding='utf-8', newline='').read()
        orig = s

        # the Organization purchase button: same destination as the Team card
        s = re.sub(
            r'<a class="btn plan-org" href="[^"]*">[^<]*</a>',
            '<a class="btn plan-org" href="' + d['href'] + '">' + d['label'] + '</a>',
            s, count=1)

        if s != orig:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  business ->', d['file'])
        else:
            print('  unchanged', d['file'])


if __name__ == '__main__':
    main()
