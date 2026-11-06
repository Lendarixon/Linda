"""Point every page at the single linda.css and generate theme-aware article diagrams.

Idempotent: run again after editing linda.css / suite.js to refresh cache-busting hashes.
  python tools/apply_linda_css.py
"""
import hashlib, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OLD_SHEETS = ('site.css', 'suite.css', 'catalogue.css', 'sales.css', 'results.css', 'metro.css', 'linda.css')
FIGURE_STYLE = re.compile(r'\s*<style>\s*\.prose \.article-figure\{.*?</style>', re.S)


def short_hash(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:10]


# ---------- theme variants of the article diagrams ----------
PALETTES = {
    # source colour -> (light, dark); values come from the linda.css colour system
    'probe': {
        '#f1f6fa': ('#ffffff', '#191c20'), '#b8cbdc': ('#d7dbe1', '#31363c'), '#fff': ('#f3f5f7', '#202429'),
        '#233c56': ('#161a1f', '#eceff2'), '#518b8f': ('#00787a', '#5ecbcb'), '#477e85': ('#006c6e', '#5ecbcb'),
        '#e6f1f2': ('#e2f1f1', '#14302f'), '#e4edf6': ('#ebeef2', '#202429'), '#8a929b': ('#8a929b', '#6c747d'),
    },
    'detector': {
        '#f1f6fa': ('#ffffff', '#191c20'), '#b8cbdc': ('#d7dbe1', '#31363c'), '#fff': ('#f3f5f7', '#202429'),
        '#233c56': ('#161a1f', '#eceff2'), '#518b8f': ('#1364b0', '#88bcf6'), '#477e85': ('#0e599d', '#88bcf6'),
        '#e6f1f2': ('#e5eef8', '#16283c'), '#e4edf6': ('#ebeef2', '#202429'),
    },
}
FONT = 'Segoe UI Variable Text, Segoe UI, system-ui, sans-serif'


def equalise_columns(svg):
    """Two-column comparison cards: give side-by-side boxes the height of the taller one."""
    rects = list(re.finditer(r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"', svg))
    by_y = {}
    for m in rects:
        x, y, w, h = map(int, m.groups())
        if w < 300:
            by_y.setdefault(y, []).append((m, h))
    for y, items in by_y.items():
        if len(items) < 2:
            continue
        top = max(h for _, h in items)
        for m, h in sorted(items, key=lambda t: -t[0].start()):
            if h != top:
                s = m.group(0).replace(f'height="{h}"', f'height="{top}"')
                svg = svg[:m.start()] + s + svg[m.end():]
    return svg


def themed_svgs():
    made = []
    for src in sorted((ROOT / 'assets').glob('*-art-*.svg')):
        if src.stem.endswith(('-light', '-dark')):
            continue
        base = src.read_text(encoding='utf-8')
        pal = PALETTES['detector' if src.name.startswith('detector') else 'probe']
        base = re.sub(r'rx="\d+"', 'rx="0"', base)
        base = re.sub(r'font-family="[^"]*"', f'font-family="{FONT}"', base)
        base = equalise_columns(base)
        if '-vs-' in src.name:
            # comparison cards: only the Linda column carries the product colour, the other tool stays neutral
            base = re.sub(r'(<path d="M40 \d+ H\d+" stroke=")#518b8f', r'\1#8a929b', base, count=1)
        for idx, suffix in ((0, 'light'), (1, 'dark')):
            out = base
            # replace longest keys first so #fff does not eat #ffffff etc.
            for key in sorted(pal, key=len, reverse=True):
                out = re.sub(re.escape(key) + r'(?![0-9a-fA-F])', '@@' + pal[key][idx][1:], out)
            out = out.replace('@@', '#')
            (src.parent / f'{src.stem}-{suffix}.svg').write_text(out, encoding='utf-8')
        made.append(src.name)
    return made


IMG_SVG = re.compile(r'<img src="assets/((?:probe|detector)-art-[a-z0-9-]+?)\.svg"([^>]*)>')


def theme_imgs(html):
    def rep(m):
        stem, rest = m.group(1), m.group(2)
        if stem.endswith(('-light', '-dark')):
            return m.group(0)
        rest = re.sub(r'\sclass="[^"]*"', '', rest)
        return (f'<img class="art-light" src="assets/{stem}-light.svg"{rest}>'
                f'<img class="art-dark" src="assets/{stem}-dark.svg"{rest}>')
    # already converted pages: leave as is
    if 'class="art-light"' in html:
        return html
    return IMG_SVG.sub(rep, html)


LOGO_IMG = re.compile(r'<img class="(app-logo|brand-mark)" src="assets/(detector|probe)-logo\.png" alt="" width="(\d+)" height="(\d+)">')


def app_tiles(html):
    """App icons become identity-coloured Metro tiles with a transparent glyph (no baked-in light-blue square)."""
    def rep(m):
        cls, app = m.group(1), m.group(2)
        return (f'<span class="{cls} app-tile is-{app}" aria-hidden="true">'
                f'<img src="assets/{app}-glyph.svg" alt="" width="20" height="16"></span>')
    return LOGO_IMG.sub(rep, html)


def main():
    themed = themed_svgs()
    css_v = short_hash(ROOT / 'linda.css')
    js_v = short_hash(ROOT / 'suite.js')
    link = f'<link rel="stylesheet" href="linda.css?v={css_v}">'
    changed = 0
    skip = {name for a in sys.argv[1:] if a.startswith('--skip=') for name in a[7:].split(',')}
    for page in sorted(ROOT.glob('*.html')):
        if skip and page.name in skip:
            continue
        raw = page.read_bytes().decode('utf-8')
        if 'suite-header' not in raw:
            continue  # demo.html, benchmark-brief.html, verification file
        html = raw
        html = re.sub(r'<link rel="stylesheet" href="(?:%s)(?:\?v=[^"]*)?">' % '|'.join(map(re.escape, OLD_SHEETS)), '', html)
        html = html.replace('</head>', link + '</head>', 1)
        html = re.sub(r'src="suite\.js(?:\?v=[^"]*)?"', f'src="suite.js?v={js_v}"', html)
        html = FIGURE_STYLE.sub('', html)
        html = theme_imgs(html)
        html = app_tiles(html)
        # product pages carry their identity colour on the hero (eyebrow + window bar)
        family = re.sub(r'(-ru|-pl)?\.html$', '', page.name)
        if family in ('detector', 'probe', 'humanizer', 'authorship'):
            html = re.sub(r'<section class="hero product-hero(?: [a-z]+)?"', f'<section class="hero product-hero {family}"', html, count=1)
        # layout belongs to linda.css: drop one-off inline sizing on button rows
        html = re.sub(r'(<div class="btns(?: [^"]*)?")\s+style="[^"]*"', r'\1', html)
        if html != raw:
            page.write_bytes(html.encode('utf-8'))
            changed += 1
    print(f'linda.css v={css_v}, suite.js v={js_v}; pages changed: {changed}; themed diagrams: {len(themed)}')


if __name__ == '__main__':
    main()
