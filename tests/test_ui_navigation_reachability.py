"""Every cabinet pane and every advertised screen must be reachable from the sidebar (P0-4).

All UI tests in this repo are static (playwright=False), so this parses the same artefacts the
browser gets: desktop-shell.js (the NAV array baked into nav.innerHTML, paneMap, activate) plus
cabinet.html (.cab-tab[data-pane]).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SHELL = (WEB / "desktop-shell.js").read_text(encoding="utf-8")
CABINET = (WEB / "cabinet.html").read_text(encoding="utf-8")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")

# Screens the shell renders itself (not cabinet panes) — no external element needed.
STANDALONE = {"check", "models", "help", "settings", "license", "about", "audit"}


def nav_routes():
    """Routes present in the rendered sidebar markup."""
    line = next(l for l in SHELL.splitlines() if "nav.innerHTML=" in l)
    return set(re.findall(r"""\.map\(navButton\)""", line)), \
        set(k for k in re.findall(r"'([a-z]+)'", line))


def nav_groups():
    """(group, routes) pairs from the nav.innerHTML template literal."""
    line = next(l for l in SHELL.splitlines() if "nav.innerHTML=" in l)
    groups = {}
    for group, body in re.findall(r'data-ld-text="(\w+)"></div>\'\+\[([^\]]*)\]', line):
        groups[group] = re.findall(r"'([a-z]+)'", body)
    return groups


def pane_map():
    m = re.search(r"const paneMap=\{([^}]*)\}", SHELL)
    assert m, "paneMap not found"
    return dict(re.findall(r"(\w+):'(\w+)'", m.group(1)))


def cabinet_panes():
    return set(re.findall(r'class="cab-tab[^"]*"\s+data-pane="(\w+)"', CABINET))


def test_audit_is_a_sidebar_entry_in_the_app_group():
    groups = nav_groups()
    assert "audit" in groups["app"], groups
    # the pane has to exist on the other side of the route
    assert pane_map()["audit"] == "audit"
    assert "audit" in cabinet_panes()


def test_about_is_a_sidebar_entry_in_the_app_group():
    groups = nav_groups()
    assert "about" in groups["app"], groups


def test_every_sidebar_route_is_handled_by_the_shell():
    """A nav button without a branch in activate()/navigate() is a dead link."""
    groups = nav_groups()
    routes = [r for rs in groups.values() for r in rs]
    assert len(routes) >= 11, routes
    # activate() renders standalone screens; navigate() opens the legacy dialogs (settings/licence).
    handler = SHELL[SHELL.index("function activate(next"):SHELL.index("nav.addEventListener('click'")]
    panes = pane_map()
    for route in routes:
        assert route in panes or re.search(r"'%s'" % route, handler), f"{route} has no activate/navigate branch"


def test_every_cabinet_pane_has_a_sidebar_route():
    """The 11 tabs used to live in .cab-top, which desktop-shell.css hides."""
    panes = pane_map()
    reachable = set(panes.values())
    missing = sorted(p for p in cabinet_panes() if p not in reachable)
    assert not missing, f"cabinet panes with no sidebar route: {missing}"
    # and the top bar really is hidden, which is why the sidebar has to carry them
    assert re.search(r"#cabView>\.cab-top\s*\{\s*display:none", SHELL + (WEB / "desktop-shell.css").read_text(encoding="utf-8"))


def test_about_screen_is_linked_from_settings_updates():
    """P0-4 also asked for about to be tied to Settings › Updates and about."""
    assert 'id="lpOpenAbout"' in INDEX
    assert re.search(r"lpOpenAbout'\)\)\$\('lpOpenAbout'\)\.onclick=\(\)=>navigate\('about'\)", SHELL)
    about = SHELL[SHELL.index("about.innerHTML="):SHELL.index("workspace.append(about);")]
    assert 'id="desktopAboutUpdates"' in about
    assert "desktopAboutUpdates').onclick" in SHELL


def test_nav_labels_are_translated_in_all_three_languages():
    shell_copy = SHELL[SHELL.index("const COPY = {"):SHELL.index("const LEGACY")]
    for key in ("audit", "audit_desc", "about", "about_desc"):
        hits = re.findall(r"\b%s:'" % key, shell_copy)
        assert len(hits) == 3, (key, len(hits))
