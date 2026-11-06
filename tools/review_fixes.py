"""Structural fixes from the November 2026 buyer reviews (5 personas).

Idempotent: every step checks whether it already ran. Touches markup only; wording of
existing copy is kept, new strings are given per language below.
  python tools/review_fixes.py
"""
import glob, os, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFX = {'en': '', 'ru': '-ru', 'pl': '-pl'}
L = {
    'en': dict(biz='For business', prices='Prices & licences', rules='Trial and promo rules', date='30 October 2026',
               dl='Download for Windows', notes='Release notes', store='Microsoft Store', kicker='Linda Detector · ',
               demo='Try it in the online demo'),
    'ru': dict(biz='Для бизнеса', prices='Цены и лицензии', rules='Правила пробного периода и промокодов', date='30 октября 2026',
               dl='Скачать для Windows', notes='Что нового', store='Microsoft Store', kicker='Linda Detector · ',
               demo='Попробовать в онлайн-демо'),
    'pl': dict(biz='Dla firm', prices='Ceny i licencje', rules='Zasady okresu próbnego i promocji', date='30 października 2026',
               dl='Pobierz na Windows', notes='Informacje o wydaniu', store='Microsoft Store', kicker='Linda Detector · ',
               demo='Wypróbuj w demo online'),
}
PROBE_STORE = 'https://apps.microsoft.com/detail/9PGM1V68193X'
DETECTOR_EXE = 'https://github.com/Lendarixon/Linda/releases/latest/download/Linda-Setup.exe'

ICON = {  # 32px Metro line glyphs, 1.7 stroke like the existing tile glyphs
    'batch': '<path d="M11 8h11l6 6v16H11Zm11 0v6h6M7 4h11M7 4v22M15 19h9m-9 5h9"/>',
    'compare': '<path d="M3 5h11v22H3Zm15 0h11v22H18ZM6 10h5m-5 4h5m-5 4h5m10-8h5m-5 4h5m-5 4h5"/>',
    'org': '<path d="M5 29V4h14v25m0-15h8v15M3 29h26M9 9h2m3 0h2M9 14h2m3 0h2M9 19h2m3 0h2M9 24h2m3 0h2m7-5h1m-1 5h1"/>',
    'team': '<circle cx="12" cy="9" r="5"/><path d="M3 29v-6a9 9 0 0 1 18 0v6m1-25a5 5 0 0 1 0 10m2 5a7 7 0 0 1 5 7v3"/>',
    'plug': '<path d="M11 3v7m10-7v7M7 10h18v5a9 9 0 0 1-18 0Zm9 14v6"/>',
    'pen': '<path d="m5 25 3-9L22 2l8 8-14 14-11 1Zm3-9 8 8M3 30h26"/>',
    'trace': '<path d="M6 5h8v8H6zM20 19h8v8h-8zM10 13v10h10M24 19V9H14"/>',
    'loupe': '<circle cx="13" cy="13" r="9"/><path d="m20 20 9 9"/>',
    'layers': '<path d="m16 3 13 7-13 7-13-7Z"/><path d="m3 16 13 7 13-7M3 22l13 7 13-7"/>',
    'both': '<path d="M4 11h22l-5-5M28 21H6l5 5"/>',
    'warning': '<path d="M16 3 30 28H2Z"/><path d="M16 12v8m0 3v2"/>',
    'history': '<circle cx="16" cy="16" r="13"/><path d="M16 8v8l6 4"/>',
    'globe': '<circle cx="16" cy="16" r="13"/><path d="M3 16h26M16 3c-4 4-6 8-6 13s2 9 6 13c4-4 6-8 6-13s-2-9-6-13"/>',
    'gpu': '<path d="M3 9h26v14H3zM7 23v4m6-4v4m6-4v4m6-4v4"/><circle cx="11" cy="16" r="3"/><circle cx="21" cy="16" r="3"/>',
    'cpu': '<path d="M9 9h14v14H9zm4 4h6v6h-6zM13 3v6m6-6v6m-6 14v6m6-6v6M3 13h6m-6 6h6m14-6h6m-6 6h6"/>',
}
# One glyph per meaning: replace repeated generic glyphs by position (structure is identical in EN/RU/PL).
GLYPH_SWAPS = {
    'detector-results': (10, {2: 'warning', 4: 'history', 5: 'globe', 7: 'gpu', 8: 'cpu', 9: 'cpu'}),
    'versions': (4, {1: 'loupe', 2: 'layers', 3: 'both'}),
}


def swap_glyphs(s, total, swaps):
    main = s.find('<main')
    if main < 0 or 'data-g="' in s[main:]:
        return s
    found = list(re.finditer(r'(<svg[^>]*stroke-width="1.7"[^>]*)>(.*?)</svg>', s[main:], re.S))
    if len(found) != total:
        print('  skip glyphs: expected', total, 'got', len(found))
        return s
    for idx in sorted(swaps, reverse=True):
        m = found[idx]
        a, b = main + m.start(), main + m.end()
        s = s[:a] + f'{m.group(1)} data-g="{swaps[idx]}">{ICON[swaps[idx]]}</svg>' + s[b:]
    return s


def svg(name, cls='tile-glyph', box=32):
    return (f'<svg class="{cls}" viewBox="0 0 {box} {box}" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'aria-hidden="true">{ICON[name]}</svg>')


def lang_of(s):
    m = re.search(r'<html[^>]*\blang="([a-z]{2})', s)
    return m.group(1) if m and m.group(1) in SFX else 'en'


def balanced(s, start, tag):
    """End index (exclusive) of the element whose start tag begins at `start`."""
    depth, i = 0, start
    pat = re.compile(rf'<(/?){tag}\b[^>]*>')
    for m in pat.finditer(s, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    raise ValueError('unbalanced ' + tag)


def cut(s, marker, tag):
    i = s.find(marker)
    if i < 0:
        return s, ''
    i = s.rfind('<' + tag, 0, i + 1)
    j = balanced(s, i, tag)
    return s[:i] + s[j:], s[i:j]


def nav_business(s, lang):
    m = re.search(r'<nav id="(?:main|suite)-nav"[^>]*>.*?</nav>', s, re.S)
    if not m or 'href="business' in m.group(0):
        return s
    nav = re.sub(r'(<a href="pricing[^"]*"[^>]*>.*?</a>)', rf'\1<a href="business{SFX[lang]}.html">{L[lang]["biz"]}</a>',
                 m.group(0), count=1)
    return s[:m.start()] + nav + s[m.end():]


def home(s, lang):
    if 'task-choice-grid' not in s and 'purchase-offers' not in s:
        return s
    s, _ = cut(s, 'class="purchase-offers', 'section')
    s, _ = cut(s, 'class="task-choice-grid', 'div')
    s, guide = cut(s, 'class="task-demo-guide', 'details')
    s, _ = cut(s, 'class="catalogue-filters', 'div')
    s = re.sub(r'<p class="catalogue-count"[^>]*>.*?</p>', '', s, flags=re.S)
    i = s.find('class="catalogue-grid')
    i = s.rfind('<div', 0, i)
    j = balanced(s, i, 'div')
    s = s[:j] + guide + s[j:]
    # Humanizer and Trace covers get their own glyphs instead of the Detector logo
    covers = list(re.finditer(r'<div class="catalogue-cover">.*?</div>', s, re.S))
    for m, name in reversed(list(zip(covers[2:4], ['pen', 'trace']))):
        new = re.sub(r'<span class="app-logo[^"]*"[^>]*>.*?</span>', svg(name, 'cover-glyph', 34), m.group(0), count=1, flags=re.S)
        s = s[:m.start()] + new + s[m.end():]
    return s


def team_card(lang):
    p = (ROOT / f'pricing{SFX[lang]}.html').read_text(encoding='utf-8')
    k = p.find('Detector · Team')
    a = p[p.rfind('<article', 0, k):p.find('</article>', k)]
    fit = re.search(r'class="plan-fit">([^<]*)<', a).group(1)
    price = re.search(r'<div class="price">([^<]*)<small>([^<]*)</small>', a)
    seats = re.search(r'</div><p>([^<]*)</p>', a).group(1)
    return fit, price.group(1), price.group(2), seats


def business(s, lang):
    if 'business-plans' in s:
        return s
    grid_i = s.find('<div class="grid g2 business-features">')
    if grid_i < 0:
        return s
    grid_j = balanced(s, grid_i, 'div')
    grid = s[grid_i:grid_j]
    panels = {}
    for key in ['feature-batch', 'plan-org', 'feature-comparison', 'feature-privacy']:
        i = grid.find(f'class="panel') ; i = grid.find(key)
        i = grid.rfind('<div', 0, i)
        panels[key] = grid[i:balanced(grid, i, 'div')]
    rest = s[grid_j:]
    bm = re.match(r'\s*(<div class="btns">.*?</div>)', rest, re.S)
    btns = bm.group(1)
    rest = rest[bm.end():]

    def glyph(panel, name):
        return re.sub(r'<svg class="tile-glyph".*?</svg>', svg(name), panel, count=1, flags=re.S)

    batch = glyph(panels['feature-batch'], 'batch')
    comp = glyph(panels['feature-comparison'], 'compare')
    priv = panels['feature-privacy']
    org = glyph(panels['plan-org'], 'org')
    org = org[:-len('</div>')] + btns + '</div>'
    org_h3 = re.search(r'<h3>(.*?)</h3>', org).group(1)
    fit, price, once, seats = team_card(lang)
    team_h3 = org_h3.replace('label-org">Organization<', 'label-team">Team<')
    team = (f'<div class="panel plan-org plan-team tone-2">{svg("team")}<h3>{team_h3}</h3>'
            f'<div class="price">{price.strip()} <small>{once}</small></div><p>{fit}: {seats}.</p>'
            f'<div class="btns"><a class="btn sec" href="pricing{SFX[lang]}.html?app=detector">{L[lang]["prices"]}</a></div></div>')
    new = (f'<div class="grid g3 business-features">{batch}{comp}{priv}</div>'
           f'<div class="grid g2 business-plans">{org}{team}</div>')
    rest = rest.replace('class="panel neutral feature-business tone-1" style="margin-top:8px"',
                        'class="panel neutral feature-business tone-1"', 1)
    rest = re.sub(r'(class="panel neutral feature-business tone-1">)<svg class="tile-glyph".*?</svg>',
                  lambda m: m.group(1) + svg('plug'), rest, count=1, flags=re.S)
    return s[:grid_i] + new + rest


def downloads(s, lang):
    if 'download-actions' in s:
        return s
    t = L[lang]

    def fix(card, exe, store, notes_href):
        btn = re.search(r'<a class="button primary" href="[^"]*">.*?</a>', card, re.S)
        acts = (f'<div class="download-actions"><a class="button primary" href="{exe}">{t["dl"]}<span aria-hidden="true">↓</span></a>'
                f'<a class="button" href="{store}">{t["store"]}<span aria-hidden="true">↗</span></a></div>'
                f'<a class="text-link" href="{notes_href}">{t["notes"]}<span aria-hidden="true">↗</span></a>')
        card = card[:btn.start()] + acts + card[btn.end():]
        card = re.sub(r'<a class="text-link" href="https://apps\.microsoft\.com/[^"]*">.*?</a>', '', card, flags=re.S)
        return card

    for cls, exe, store, notes in [('detector', DETECTOR_EXE, 'https://apps.microsoft.com/detail/9NP66G69BQPN', 'https://github.com/Lendarixon/Linda/releases/latest'),
                                   ('probe', 'https://github.com/Lendarixon/Linda-Probe/releases/latest', PROBE_STORE, 'https://github.com/Lendarixon/Linda-Probe/releases/latest')]:
        i = s.find(f'<article class="download-card {cls}"')
        j = balanced(s, i, 'article')
        s = s[:i] + fix(s[i:j], exe, store, notes) + s[j:]
    return s


def pricing(s, lang):
    if 'trial-rules' in s:
        return s
    i = s.find('<div class="trial-plan"')
    if i < 0:
        return s
    j = balanced(s, i, 'div')
    block = s[i:j]
    ps = list(re.finditer(r'<p>(?:(?!</p>).)*</p>', block, re.S))
    long_p = max(ps, key=lambda m: len(m.group(0)))
    block = (block[:long_p.start()] + f'<details class="trial-rules"><summary>{L[lang]["rules"]}</summary>{long_p.group(0)}</details>'
             + block[long_p.end():])
    block = block.replace('<small>30 October 2026</small>', f'<small>{L[lang]["date"]}</small>')
    return s[:i] + block + s[j:]


def drop_duplicate_captions(s):
    """A diagram caption that only repeats the words printed inside the diagram is noise (reviewer C)."""
    import html as H

    def one(m):
        fig = m.group(0)
        alt = re.search(r'alt="([^"]*)"', fig)
        cap = re.search(r'\s*<figcaption>(.*?)</figcaption>', fig, re.S)
        if not alt or not cap:
            return fig
        text = H.unescape(re.sub('<[^>]+>', '', cap.group(1))).strip()
        sents = [x.strip() for x in re.split(r'(?<=\.)\s', text) if x.strip()]
        if sents and all(x in H.unescape(alt.group(1)) for x in sents):
            return fig.replace(cap.group(0), '')
        return fig

    return re.sub(r'<figure class="article-figure article-diagram">.*?</figure>', one, s, flags=re.S)


def main():
    changed = []
    for path in sorted(glob.glob(str(ROOT / '*.html'))):
        name = os.path.basename(path)
        if name == 'demo.html':
            continue
        s0 = s = open(path, encoding='utf-8', newline='').read()
        lang = lang_of(s)
        s = nav_business(s, lang)
        if name in ('index.html', 'ru.html', 'pl.html'):
            s = home(s, lang)
        if re.fullmatch(r'business(-ru|-pl)?\.html', name):
            s = business(s, lang)
        if re.fullmatch(r'humanizer(-ru|-pl)?\.html', name) and 'class="text-link hero-demo"' not in s:
            s = re.sub(r'(<div class="hero-actions">.*?#detector">.*?</a>)',
                       lambda m: m.group(1) + f'<a class="text-link hero-demo" href="demo.html?lang={lang}">{L[lang]["demo"]}<span aria-hidden="true">↗</span></a>',
                       s, count=1, flags=re.S)
        if re.fullmatch(r'downloads(-ru|-pl)?\.html', name):
            s = downloads(s, lang)
        if re.fullmatch(r'pricing(-ru|-pl)?\.html', name):
            s = pricing(s, lang)
        if re.fullmatch(r'updates(-ru|-pl)?\.html', name) and L[lang]['kicker'] not in s:
            s = re.sub(r'(<span class="release-kicker">)', r'\1' + L[lang]['kicker'], s, count=1)
        base = re.sub(r'(-ru|-pl)?\.html$', '', name)
        if base in GLYPH_SWAPS:
            s = swap_glyphs(s, *GLYPH_SWAPS[base])
        s = s.replace('(W&I;)', '(W&amp;I)')
        s = drop_duplicate_captions(s)
        if s != s0:
            open(path, 'w', encoding='utf-8', newline='').write(s)
            changed.append(name)
    print(len(changed), 'files:', ' '.join(changed))


if __name__ == '__main__':
    main()
