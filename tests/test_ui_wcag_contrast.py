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


def test_action_button_uses_the_on_primary_pair_in_every_theme():
    """C-02: the CTA is a flat --primary fill, so its label must be --on-primary, not black.

    Client bug 7 measured black on the contrast-theme blue at 3.33:1; the gradient it replaced
    ended on #82bcfc at 1.99:1 with white text.
    """
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    # 1. no gradient fill anywhere on the action button
    for block in re.findall(r"\.btn-analyze\s*\{([^}]*)\}", idx):
        assert "gradient" not in block, "the action button must not use a gradient"
    # 2. the contrast theme must not paint it black
    assert not re.search(r'html\[data-theme="contrast"\][^{]*\.btn-analyze[^{]*\{[^}]*color:#000', idx)
    assert re.search(r'html\[data-theme="contrast"\] \.btn-analyze[^{]*\{[^}]*color:var\(--on-primary', idx)
    # 3. and the pair itself passes in every theme
    for theme in ("dark", "light", "contrast"):
        tok = tokens_for(theme, "cobalt")
        assert ratio(tok["--on-primary"], tok["--primary"]) >= MIN_RATIO, (theme, tok["--primary"])


def test_deep_verdict_inks_are_not_painted_black_in_the_contrast_theme():
    """Client bug 7: --human-deep #00692f and --uncertain-deep #8f5f00 with black ink failed AA.

    The contrast theme keeps bright status fills and gives them black ink through
    --verdict-ink; index.html reads it as var(--verdict-ink,#000), so either an explicit
    declaration or the #000 fallback satisfies the contract.
    """
    shell = (WEB / "desktop-shell.css").read_text(encoding="utf-8")
    contrast = shell[shell.index('html[data-theme="contrast"]'):]
    contrast = contrast[:contrast.index("\n}") + 2]
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    declares = "--verdict-ink:#000" in contrast or "--verdict-ink: #000" in contrast
    falls_back = "var(--verdict-ink,#000)" in idx or "var(--verdict-ink, #000)" in idx
    assert declares or falls_back, "the contrast theme needs a black-ink token for status fills"
    # the blanket rule must not target the CTA or the cabinet actions any more
    blanket = [m for m in re.findall(r'html\[data-theme="contrast"\][^{]*\{color:#000!important\}', idx)]
    for rule in blanket:
        assert ".btn-analyze" not in rule, "the contrast blanket still paints the CTA black"
    # bright status fills with black ink stay far above AA
    for fill in ("#7bff9e", "#ffb020", "#ff8080"):
        assert ratio("#000000", fill) >= MIN_RATIO, fill


def test_control_heights_are_only_44_and_36():
    """C-07: controls take their height from one of two tokens, 44px or 36px.

    Only chrome tiers may hard-code a height: tabs (38px), the status-bar chips (22px)
    and the 36px retry/language buttons. Everything else must resolve through
    --ld-control / --ld-control-sm, so a new ad-hoc min-height fails this guard.
    """
    shell = (WEB / "desktop-shell.css").read_text(encoding="utf-8")
    assert "--ld-control:44px" in shell
    assert "--ld-control-sm:36px" in shell
    # the two tokens are actually wired to the control tiers
    wired = [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^}]*)\}", shell)
             if "min-height:var(--ld-control" in b]
    assert any("button" in s and "min-height:var(--ld-control)" in b for s, b in wired)
    assert any("btn-upload" in s and "var(--ld-control-sm)" in b for s, b in wired), wired
    # no other control selector may invent a height outside the documented chrome tiers
    body = re.sub(r"/\*.*?\*/", "", shell, flags=re.S)
    literals = set()
    for sel, block in re.findall(r"([^{}]+)\{([^}]*)\}", body):
        flat = " ".join(sel.split())
        if not re.search(r"button|input|select|textarea", flat):
            continue
        for h in re.findall(r"min-height:(\d+)px", block):
            literals.add((flat[:70], int(h)))
    allowed = {
        (".ld-desktop .tab", 38),
        (".ld-desktop .lp-input", 40),
        (".ld-desktop .ld-statusbar button", 22),
        ('.ld-desktop #statusIndicator[data-error="true"] .ld-retry', 36),
        (".ld-desktop .ld-language", 36),
        # superseded by the generic 44px rule (higher specificity); kept as the pre-shell fallback
        (".ld-desktop .btn-analyze", 42),
    }
    unexpected = sorted(literals - allowed)
    assert not unexpected, unexpected


def test_corners_are_square_everywhere():
    """C-06: Modern Metro — no radius token, no pill leftovers, no !important hacks."""
    for name in ("index.html", "desktop-shell.css", "cabinet.html"):
        text = (WEB / name).read_text(encoding="utf-8")
        leftovers = [v for v in re.findall(r"border-radius:\s*([^;}]+)", text)
                    if v.strip() not in ("0", "50%", "0!important", "50%!important")]
        assert not leftovers, (name, leftovers[:5])
        assert "var(--radius)!important" not in text, name


def test_no_token_resolves_to_itself():
    """A `--x: var(--x)` declaration is a cycle: the property becomes invalid at computed-value
    time, so `background: var(--primary-hover)` on the CTA hover painted nothing at all.
    """
    for name in ("index.html", "desktop-shell.css"):
        text = (WEB / name).read_text(encoding="utf-8")
        cycles = [t for t in re.findall(r"(--[a-z0-9-]+)\s*:\s*var\(\1\)", text)]
        assert not cycles, (name, cycles)


def test_action_button_hover_has_a_real_colour():
    """C-01 regression guard: the hover fill must be a literal or a different token."""
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    decl = re.search(r"--primary-hover:\s*([^;]+);", idx)
    assert decl, "index.html lost --primary-hover"
    value = decl.group(1).strip()
    assert value != "var(--primary-hover)", "--primary-hover is self-referential"
    assert re.fullmatch(r"#[0-9a-fA-F]{3,8}", value), value


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


# --- M2 (Neon markup audit 2026-11-20): solid AI badges need a white-ink fill ------------

BADGE_RULES = (
    ("index.html", r"(?m)^\.sent-tag\.ai\s*\{([^}]*)\}"),
    ("index.html", r"html:not\(\[data-theme=\"contrast\"\]\)\s*\.verdict-badge\.ai\{([^}]*)\}"),
    ("cabinet.html", r"(?m)^\.cab-badge\.ai\s*\{([^}]*)\}"),
    ("cabinet.html", r"\.v-pill\.ai\s*\{([^}]*)\}"),
)
# The contrast theme paints .sent-tag.ai with its own darker fill (index.html), so it is
# checked against that literal rather than --ai-deep.
CONTRAST_BADGE_FILL = "#8a0010"


def _badge_fill(name, pattern):
    text = (WEB / name).read_text(encoding="utf-8")
    blocks = re.findall(pattern, text)
    assert blocks, f"{name}: rule {pattern!r} is gone"
    block = blocks[-1]
    m = re.search(r"background(?:-color)?:\s*([^;]+)", block)
    assert m, (name, pattern, block)
    return m.group(1).strip()


def test_ai_badges_use_the_deep_fill_not_the_pale_accent():
    """White 900-weight 0.6rem text on --ai #e8635a was 3.30:1 in the dark theme (M2)."""
    for name, pattern in BADGE_RULES:
        fill = _badge_fill(name, pattern)
        assert "var(--ai-deep" in fill, f"{name}: badge still fills with the pale accent ({fill})"


def test_ai_badge_white_ink_meets_aa_in_every_theme():
    expected = {"dark": 4.5, "light": 4.5, "contrast": 4.5}
    for theme, floor in expected.items():
        tok = tokens_for(theme, "cobalt")
        for name, pattern in BADGE_RULES:
            fill = _badge_fill(name, pattern)
            if theme == "contrast":
                # the contrast theme keeps its own dark red for the sentence tag
                colour = CONTRAST_BADGE_FILL if "sent-tag" in pattern else tok["--ai-deep"]
            else:
                colour = tok["--ai-deep"]
            r = ratio("#ffffff", colour)
            assert r >= floor, f"{theme} {name} {pattern}: white on {colour} = {r:.2f}"
            assert r >= expected[theme] - 1e-9


def test_sentence_tag_white_text_is_above_aa_including_the_dark_theme():
    """Regression pin on the measured pair: dark must never fall back to the 3.30:1 accent."""
    dark = tokens_for("dark", "cobalt")
    assert ratio("#ffffff", dark["--ai"]) < MIN_RATIO  # the value that shipped the bug
    assert ratio("#ffffff", dark["--ai-deep"]) >= MIN_RATIO
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    assert ratio("#ffffff", CONTRAST_BADGE_FILL) >= CONTRAST_THEME_MIN
    assert f'background:{CONTRAST_BADGE_FILL}!important' in idx


def test_heatmap_card_follows_the_theme_surface_not_a_hardcoded_dark_tile():
    """L1: the inline skin pinned .heatmap-card to #191c20, ignoring --bg-card in contrast."""
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    pinned = re.findall(r"\.heatmap-card\{background:#191c20", idx)
    assert not pinned, "the heatmap card is hard-coded to the dark tile again"
    assert ".heatmap-card{background:var(--bg-card" in idx

def test_dark_theme_accent_picker_resolves_every_accent():
    """Fixer C (2026-11-21): dark-theme [data-accent] presets must beat the base block, so
    --cobalt differs per accent in the dark theme."""
    shell = (WEB / "desktop-shell.css").read_text(encoding="utf-8")
    for accent in ACCENTS[1:]:   # cobalt is the default base value
        pat = f'html:not([data-theme="contrast"])[data-accent="{accent}"]:not([data-theme="light"])'
        assert pat in shell, f"dark preset missing for {accent}"
    # and the base block must not out-specify them: it carries two :not() guards only
    assert 'html:not([data-theme="light"]):not([data-theme="contrast"]) {' in shell


def test_pause_button_is_wired_during_model_download():
    """Fixer C (2026-11-21): lpSetupCancel visible while busy, calls /api/models/cancel."""
    idx = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="lpSetupCancel" style="display:none"' not in idx, "Pause is hard-hidden again"
    assert "lpSetupCancel').style.display = busy ? '' : 'none'" in idx
    assert "post('/api/models/cancel')" in idx

