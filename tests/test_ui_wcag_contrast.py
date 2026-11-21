"""WCAG 2.1 AA for every theme x accent combination the UI can render (P0-1, P0-2).

CSS-variable parsing: both web/index.html (its :root, style#metro and the personalisation
block) and web/desktop-shell.css define tokens. The backend appends desktop-shell.css last
(linda_desktop/app.py), so it wins on equal specificity; the check therefore resolves each
token by walking every declaration in document order and keeping the last one that applies,
and it reads the meta style#metro first, exactly like the browser does.

Run this file directly for the contrast table used in P0_FIX_REPORT.md:
    python tests/test_ui_wcag_contrast.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

THEMES = ("dark", "light", "contrast")
ACCENTS = ("cobalt", "teal", "green", "orange", "amber", "purple", "rose", "graphite")

# Surfaces text can sit on, per theme (--bg, --bg-card, --bg-elevated).
SURFACES = {"dark": ("#111418", "#191c20", "#202429"),
            "light": ("#f3f5f7", "#ffffff", "#ebeef2"),
            "contrast": ("#000000", "#000000", "#111111")}

# Tokens that must be readable as body text (>= 4.5:1) on every surface.
TEXT_TOKENS = ("--text", "--text-muted", "--accent", "--ai", "--human", "--uncertain")
# Tokens used as a solid fill with white text on top (>= 4.5:1 against #fff).
WHITE_ON = ("--cobalt", "--primary", "--ai-deep", "--human-deep", "--uncertain-deep")


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexstr):
    h = hexstr.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# --- CSS parsing ------------------------------------------------------------

DECL = re.compile(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})")


def _blocks(css):
    """Yield (selector, declarations) for every rule, in source order."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        yield m.group(1).strip(), dict(DECL.findall(m.group(2)))


def _selector_matches(selector, theme, accent):
    """Only the theme/accent blocks are modelled; :root/body-level defaults always apply."""
    sels = [s.strip() for s in selector.split(",")]
    matched = {}
    for sel in sels:
        hit = True
        for cond, value in re.findall(r'\[data-(theme|accent)="([^"]+)"\]', sel):
            if (cond == "theme" and value != theme) or (cond == "accent" and value != accent):
                hit = False
        for neg in re.findall(r':not\(\[data-theme="([^"]+)"\]\)', sel):
            if neg == theme:
                hit = False
        if hit:
            matched[sel] = True
            break
    return bool(matched)


def tokens_for(theme, accent):
    """Resolve every custom property for one (theme, accent) pair, in cascade order."""
    sheets = []
    html = (WEB / "index.html").read_text(encoding="utf-8")
    # Empty selector == :root-level defaults of a style block; keep document order.
    for style in re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.S):
        sheets.append(style)
    sheets.append((WEB / "desktop-shell.css").read_text(encoding="utf-8"))  # appended last by app.py
    tokens = {}
    for css in sheets:
        for selector, decls in _blocks(css):
            if selector.startswith(":root") or selector == "" or _selector_matches(selector, theme, accent):
                tokens.update(decls)
    return tokens


def rows():
    out = []
    for theme in THEMES:
        for accent in ACCENTS:
            t = tokens_for(theme, accent)
            for tok in TEXT_TOKENS:
                if tok not in t:
                    continue
                for surface in SURFACES[theme]:
                    out.append((theme, accent, tok, t[tok], surface, ratio(t[tok], surface)))
            if theme != "contrast":
                for tok in WHITE_ON:
                    if tok not in t:
                        continue
                    out.append((theme, accent, tok + " (white text)", "#ffffff", t[tok],
                                ratio("#ffffff", t[tok])))
    return out


MIN_RATIO = 4.5
CONTRAST_THEME_MIN = 7.0


def test_every_text_token_is_readable_in_every_theme_and_accent():
    failures = []
    for theme, accent, tok, fg, bg, r in rows():
        floor = CONTRAST_THEME_MIN if theme == "contrast" else MIN_RATIO
        if r < floor - 1e-9:
            failures.append(f"{theme}/{accent} {tok} {fg} on {bg} = {r:.2f} (need {floor})")
    assert not failures, "\n".join(failures)


def test_light_theme_accent_presets_override_the_dark_ones():
    """P0-1 regression guard: the light preset must not keep a dark-theme (pale) accent."""
    pale = {"--accent": ("#4fd1d4", "#4ade80", "#f59e0b", "#f472b6", "#94a3b8", "#5ecbcb", "#88ca95", "#eca47f")}
    for accent in ACCENTS:
        light = tokens_for("light", accent)
        assert light["--accent"].lower() not in [c.lower() for c in pale["--accent"]], \
            f"light/{accent} still uses the dark preset {light['--accent']}"
        assert ratio(light["--accent"], "#ffffff") >= MIN_RATIO, f"light/{accent} {light['--accent']}"


def test_semantic_colours_follow_the_audit_targets():
    """P0-2: light = cabinet.html values, dark --ai lightened to #e8635a."""
    assert tokens_for("dark", "cobalt")["--ai"].lower() == "#e8635a"
    assert tokens_for("dark", "cobalt")["--ai-deep"].lower() == "#b03a30"
    light = tokens_for("light", "cobalt")
    assert light["--ai"].lower() == "#c4302b"
    assert light["--human"].lower() == "#0d7a3e"
    # #9a6700 (audit proposal) is only 4.18:1 on --bg-elevated, so the shipped value is darker.
    assert ratio("#9a6700", "#ebeef2") < MIN_RATIO
    assert light["--uncertain"].lower() == "#8f5f00"
    assert ratio(light["--uncertain"], "#ebeef2") >= MIN_RATIO


def test_accent_is_reachable_for_every_theme():
    """Both stylesheets used in the app must carry the light-accent overrides."""
    shell = (WEB / "desktop-shell.css").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for accent in ("teal", "green", "amber", "rose", "graphite", "orange", "purple"):
        assert f'html[data-theme="light"][data-accent="{accent}"]' in shell, accent
        assert f'html[data-theme="light"][data-accent="{accent}"]' in html, accent


if __name__ == "__main__":
    print(f"{'theme':9s} {'accent':9s} {'token':26s} {'fg':9s} {'bg':9s} ratio")
    worst = None
    for theme, accent, tok, fg, bg, r in rows():
        flag = "FAIL" if r < (CONTRAST_THEME_MIN if theme == "contrast" else MIN_RATIO) else "ok"
        print(f"{theme:9s} {accent:9s} {tok:26s} {fg:9s} {bg:9s} {r:5.2f} {flag}")
        if worst is None or r < worst[-1]:
            worst = (theme, accent, tok, fg, bg, r)
    print("\nlowest ratio:", worst[:5], f"{worst[-1]:.2f}:1")
    sys.exit(0)
