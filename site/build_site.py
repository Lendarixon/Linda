# -*- coding: utf-8 -*-
"""Builds the static product site (GitHub Pages) into ./public. Nothing is published by this script.
   Localized: index.html (en), ru.html, pl.html + localized terms/privacy/refund/licensing.
    python build_site.py"""
import json
import os
from html import escape
from html.parser import HTMLParser
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public"
STATIC_ARTIFACTS = ("benchmark-brief.html", "pilot-en.pdf", "pilot-pl.pdf", "Linda_pilot_documents_EN_PL.zip")
BUY_PT = "https://buy.polar.sh/polar_cl_xbgd3gaCH2ZQIzNHmRAjyJiIUTNAHuRmE51zi1P8ywI"
BUY_ORG = "https://buy.polar.sh/polar_cl_UznG2OPeM5diDZ1nCtxwRD1HW1pO3OZIu55DN07bCQe"
DOWNLOAD = "https://github.com/Lendarixon/Linda/releases/latest"
LITE = os.environ.get("LINDA_LITE") == "1"  # Linda Loupe pages and sections: built only for a preview or at the Lite release
# the listing exists (9NP66G69BQPN) but holds an old 1.x build: switch it on with LINDA_MS_STORE=https://apps.microsoft.com/detail/9NP66G69BQPN once a current build is certified
MS_STORE_URL = os.environ.get("LINDA_MS_STORE", "https://get.microsoft.com/installer/download/9NP66G69BQPN?referrer=appbadge").strip()  # Microsoft Store listing; empty = the GitHub installer is the main download
PRIMARY_DL = MS_STORE_URL or DOWNLOAD
# measured numbers shown on the site (sensitive mode, one calibration rule for both; Lite = packaged ONNX model on the CPU)
NUMS = {"pro": {"hb": "81.0", "oct": "84.0", "unseen": "95.5", "pl": "79.4", "ru": "80.3", "toefl": "5.5", "mage_h": "2.0", "chi_h": "0.2", "fp_pl": "1.4", "fp_ru": "0.6"},
        "lite": {"hb": "68.7", "oct": "75.2", "unseen": "82.2", "pl": "70.9", "ru": "73.4", "toefl": "2.2", "mage_h": "0.3", "chi_h": "0.1", "fp_pl": "1.2", "fp_ru": "1.5"}}
_nf = ROOT / "content" / "benchmark_numbers.json"
if _nf.exists():  # one numbers file for the site, the READMEs and the model card
    _n = json.loads(_nf.read_text(encoding="utf-8"))
    NUMS = {"pro": _n["pro"], "lite": _n["lite"]}
MAIL = "lindapro.support@proton.me"
DOI = "10.5281/zenodo.23261670"
DOI_URL = f"https://doi.org/{DOI}"
SITE = "https://lendarixon.github.io/Linda"
DEMO_URL = "https://ninjagovlad--linda-pro-demo-web.modal.run/"
LANGS = ("en", "ru", "pl")
OG_LOCALE = {"en": "en_US", "ru": "ru_RU", "pl": "pl_PL"}
FILES = {
    "trust": {"en": "trust.html", "ru": "trust-ru.html", "pl": "trust-pl.html"},
    "updates": {"en": "updates.html", "ru": "updates-ru.html", "pl": "updates-pl.html"},
    "index": {"en": "index.html", "ru": "ru.html", "pl": "pl.html"},
    "results": {"en": "results.html", "ru": "results-ru.html", "pl": "results-pl.html"},
    "business": {"en": "business.html", "ru": "business-ru.html", "pl": "business-pl.html"},
    "faq": {"en": "faq.html", "ru": "faq-ru.html", "pl": "faq-pl.html"},
    "developers": {"en": "developers.html", "ru": "developers-ru.html", "pl": "developers-pl.html"},
    "memo": {"en": "memo.html", "ru": "memo-ru.html", "pl": "memo-pl.html"},
    "terms": {"en": "terms.html", "ru": "terms-ru.html", "pl": "terms-pl.html"},
    "privacy": {"en": "privacy.html", "ru": "privacy-ru.html", "pl": "privacy-pl.html"},
    "refund": {"en": "refund.html", "ru": "refund-ru.html", "pl": "refund-pl.html"},
    "licensing": {"en": "licensing.html", "ru": "licensing-ru.html", "pl": "licensing-pl.html"},
}
if LITE:
    FILES["versions"] = {"en": "versions.html", "ru": "versions-ru.html", "pl": "versions-pl.html"}
LIC_MD = {"en": "LICENSING.md", "ru": "LICENSING.ru.md", "pl": "LICENSING.pl.md"}


def load_i18n():
    t = {}
    for lang in LANGS:
        t[lang] = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
    base = set(t["en"])
    bad = False
    for lang in ("ru", "pl"):
        if set(t[lang]) != base:
            print(f"i18n mismatch {lang}: missing={sorted(base - set(t[lang]))} extra={sorted(set(t[lang]) - base)}")
            bad = True
    if bad:
        sys.exit("i18n key check failed")
    return t


def S(t, key: str) -> str:
    return (t[key].replace("__MAIL_LINK__", f'<a href="mailto:{MAIL}">{MAIL}</a>')
             .replace("__DOI_URL__", DOI_URL).replace("__MAIL__", MAIL)
             .replace("__VERSIONS__", FILES["versions"][I18N_LANG] if "versions" in FILES else "#"))


import hashlib as _hl
CSS = """
:root,html[data-theme="dark"]{color-scheme:dark;--bg:#0d0f15;--surface:#171a22;--surface-raised:#1f232d;--fg:#ffffff;--mut:#c3c8d2;--app-fg:#ffffff;--app-mut:#c3c8d2;--line:#2e323d;--c-loupe:#008183;--c-assay:#2f6fe6;--c-free:#4a5162;--c-personal:#6d3fc0;--c-team:#a36600;--c-org:#087db9;--c-download:#00802b;--c-privacy:#5b2bb5;--c-results:#a3195b;--c-business:#b8410a;--c-learn:#006b8f;--c-report:#087d6f;--c-performance:#3f6274}
html[data-theme="light"]{color-scheme:light;--bg:#eef1f6;--surface:#ffffff;--surface-raised:#e6ebf3;--fg:#141821;--mut:#4a5262;--app-fg:#141821;--app-mut:#4a5262;--line:#cfd6e3}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:88px}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 "Segoe UI","Segoe UI Variable",system-ui,sans-serif;-webkit-font-smoothing:antialiased;overflow-wrap:break-word}
a{color:var(--fg);text-decoration:none}a:hover{text-decoration:underline;text-underline-offset:4px}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}main{min-width:0}
header.top{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;align-items:center;gap:14px;min-height:76px}
.brand{display:flex;align-items:center;flex:none}.brand img{display:block;height:42px;width:auto}
nav.main{margin-left:auto;display:flex;align-items:center;gap:2px;white-space:nowrap}
nav.main a,.more summary{font-size:14px;color:var(--mut);padding:8px;letter-spacing:0;text-transform:none}
nav.main a:hover,nav.main a[aria-current=page]{color:var(--fg);background:var(--surface-raised);text-decoration:none;border-radius:0}
nav.main a.dl{background:var(--fg);color:var(--bg);font-weight:600;border-radius:0;padding:9px 12px;margin-left:6px}
nav.main a.dl:hover{background:var(--fg);text-decoration:underline}
.more{position:relative}.more>details{background:none;border:0;padding:0;margin:0}.more summary{list-style:none;cursor:pointer}.more summary::-webkit-details-marker{display:none}
.more-menu{position:absolute;right:0;top:calc(100% + 12px);display:flex;flex-direction:column;min-width:230px;background:var(--surface-raised);border:1px solid var(--line);border-radius:0;padding:8px}
.more-menu a{white-space:normal;padding:10px 12px!important}
.burger{display:none;margin-left:auto;background:var(--surface);border:1px solid var(--line);border-radius:0;color:var(--fg);font-size:20px;padding:6px 10px;cursor:pointer}
.langbox{display:flex;gap:6px;align-items:center;white-space:nowrap;flex:none}.langbox label{font-size:14px;color:var(--mut)}
.langsel{background:var(--surface);color:var(--fg);border:1px solid var(--line);border-radius:0;font:inherit;font-size:14px;padding:6px;max-width:64px;cursor:pointer}.langsel option{background:var(--surface);color:var(--fg)}
.hero{padding-top:72px;padding-bottom:72px;display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:48px;align-items:center}
.hero>div{min-width:0}.hero h1{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:clamp(2.5rem,4.1vw,3.6rem);font-weight:300;line-height:1.14;letter-spacing:-.035em;margin:0 0 24px;text-wrap:balance}.hero h1 em{font-style:normal;color:inherit}
.hero .lead{font-size:20px;line-height:1.55;color:var(--mut);margin:0 0 28px;max-width:540px}.hero .trust{font-size:14px;color:var(--mut);margin:18px 0 0}
.hero-shot{margin:0;border:1px solid var(--line);border-radius:0;padding:8px;background:var(--surface)}.hero-shot img{display:block;width:100%;height:auto;border-radius:0}.hero-shot a{display:block}
section{padding:64px 0 16px}h1,h2,h3{color:var(--fg)}h2{font-size:clamp(2rem,3.4vw,2.8rem);font-weight:300;line-height:1.2;letter-spacing:-.025em;margin:0 0 18px}h3{font-weight:600;line-height:1.3}
.sub{font-size:18px;line-height:1.6;color:var(--mut);max-width:780px;margin:0 0 28px}.note{font-size:14px!important;color:var(--mut);font-weight:400;opacity:1!important;line-height:1.65}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;max-width:100%;padding:12px 18px;background:var(--surface-raised);color:var(--fg)!important;border:1px solid var(--line);border-radius:0;font:inherit;font-size:16px;font-weight:600;text-transform:none;letter-spacing:0;text-align:center;text-decoration:none!important;cursor:pointer;line-height:1.4}
.btn:hover{border-color:var(--mut);background:var(--surface)}.btn.acc{background:var(--fg);color:var(--bg)!important;border-color:var(--fg)}.btn.acc:hover{text-decoration:underline!important;text-underline-offset:4px;background:var(--fg)}.btn.sec{background:transparent}
.btn.demo-cta{border:2px solid var(--c-report);font-weight:700}.btn.demo-cta:hover{background:var(--c-report);color:#fff!important;border-color:var(--c-report)}
.btns{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}.btns .btn{flex:0 1 auto}.hero .btns{flex-direction:column;align-items:flex-start}.hero .btn{min-width:240px}.btn-col{display:flex;flex-direction:column;gap:10px;margin-top:20px}.btn-col .btn{width:100%}
.grid,.tiles{display:grid;gap:8px;align-items:stretch;grid-auto-rows:minmax(240px,1fr)}.g2{grid-template-columns:repeat(2,minmax(0,1fr))}.g3,.tiles,.tiles.spd{grid-template-columns:repeat(3,minmax(0,1fr))}.g4{grid-template-columns:repeat(4,minmax(0,1fr))}.version-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.version-grid .version-both{grid-column:span 2}
.tile,.panel{min-width:0;background:var(--surface);color:var(--fg);border:1px solid var(--line);border-radius:0;padding:28px;overflow-wrap:break-word}
.tile{display:flex;flex-direction:column;justify-content:flex-start;gap:12px;text-decoration:none!important}.tile:hover{border-color:var(--mut)}.tile .big,.panel .big{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:clamp(2.5rem,4vw,3.5rem);font-weight:300;line-height:1.15;letter-spacing:-.03em}.tile .lbl{font-size:16px;color:var(--mut)}.tile .cap{font-size:14px;color:var(--mut);letter-spacing:.08em;text-transform:uppercase}.memo-num{font-size:14px;color:var(--mut)}
.w2,.w4{grid-column:auto}.h2{grid-row:auto}.panel p{margin:12px 0;color:var(--mut);font-weight:400;font-size:16px}.panel h3{margin:0 0 14px;font-size:24px;letter-spacing:-.02em}.panel .num{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:40px;font-weight:300;line-height:1.2;color:var(--mut);margin-bottom:16px}.panel .price{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:48px;font-weight:300;line-height:1.2;letter-spacing:-.035em}.panel .price small{font-size:16px;font-weight:400;letter-spacing:0;color:var(--mut)}
.panel ul{padding-left:20px;margin:20px 0;color:var(--mut)}.panel li{padding:4px 0;font-weight:400}.panel.recommended{border-color:var(--line)}.recommended-label{display:inline-block;font-size:14px;font-weight:600;margin:0 0 16px;color:var(--fg)}
.version-loupe{--tile-colour:var(--c-loupe)}.version-both{--tile-colour:var(--surface-raised)}
h1::first-letter,h2::first-letter,h3::first-letter{text-transform:uppercase}.version-assay{--tile-colour:var(--c-assay)}
.tbl-wrap{max-width:100%;overflow-x:auto}.tbl{width:100%;min-width:560px;border-collapse:collapse;font-size:16px}.tbl th{font-size:14px;font-weight:600;color:var(--mut);text-align:left;padding:12px;border-bottom:1px solid var(--line)}.tbl td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}.tbl td.n,.tbl th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.tbl td.txt{white-space:normal;text-align:left;min-width:180px}.tbl tr.grp td{font-size:14px;font-weight:600;color:var(--mut);padding-top:24px}.tbl td.new{font-weight:700}.chg{display:inline-block;min-width:64px;text-align:center;padding:2px 8px;font-weight:600;font-size:14px;background:var(--surface-raised);color:var(--fg);border:1px solid var(--line);border-radius:0}
.bars{display:grid;grid-template-columns:160px minmax(0,1fr) 64px;gap:12px 18px;align-items:center;font-size:16px}.bars .bar{height:14px;background:var(--surface-raised);position:relative;border-radius:0;overflow:hidden}.bars .bar i{position:absolute;left:0;top:0;bottom:0;background:var(--mut)}.bars .bar.us i{background:var(--c-assay)}.bars .us{font-weight:600}.bars .v{text-align:right;font-variant-numeric:tabular-nums}
details{border:1px solid var(--line);border-radius:0;background:var(--surface);padding:16px 20px;margin:12px 0}summary{cursor:pointer;font-weight:600;font-size:18px;line-height:1.5}details p{margin:12px 0 2px;color:var(--mut)}details details summary{font-size:16px}.faq-a-in{min-width:0}
.priv{padding:24px;border:1px solid var(--line);border-radius:0;background:var(--surface);max-width:780px;margin:24px 0}.priv b{font-weight:600}.priv p{margin:8px 0 0;color:var(--mut)}.priv .lock{display:none}
.shots{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:28px;align-items:start}.shot{margin:0;border:1px solid var(--line);border-radius:0;background:var(--surface);overflow:hidden}.shot a{display:block;cursor:zoom-in}.shot img{display:block;width:100%;height:auto}.shot figcaption{padding:14px 18px;font-size:14px;color:var(--mut);border-top:1px solid var(--line)}
.quiz .btns{flex-direction:column;align-items:stretch}.quiz .btn{justify-content:flex-start;text-align:left}.quiz-out{margin-top:20px;padding:20px;background:var(--surface-raised);border:1px solid var(--line);border-radius:0}.quiz-out p{margin:0}
.news{display:grid;grid-template-columns:120px minmax(0,1fr);gap:24px;padding:20px 0;border-bottom:1px solid var(--line)}.news time{font-size:14px;color:var(--mut)}.news h3{margin:0 0 8px;font-size:24px}.news p{white-space:pre-line;margin:0;color:var(--mut)}
footer{margin-top:80px;border-top:1px solid var(--line);background:var(--bg);color:var(--mut);padding:36px 0 48px;font-size:14px}footer a{display:inline-block;margin-right:18px;margin-bottom:8px}
.prose{max-width:1180px;padding-top:56px}.prose h1,.release-page h1{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:clamp(2.5rem,4vw,3.5rem);font-weight:300;line-height:1.2;letter-spacing:-.03em;margin:0 0 24px}.prose>:is(p,ul,ol){max-width:880px}.prose h2{font-size:28px;margin-top:36px}.prose h3{font-size:24px;margin:28px 0 10px}.prose p,.prose li{color:var(--mut);font-weight:400}.prose table{border-collapse:collapse;width:100%;font-size:16px;margin:20px 0}.prose th,.prose td{font-size:14px;padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.prose th{font-weight:600;color:var(--mut)}.prose code{background:var(--surface-raised);padding:2px 6px;color:var(--fg)}
.release-strip{margin-top:24px;display:flex;gap:28px;justify-content:space-between;align-items:center;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding-top:24px;padding-bottom:24px}.release-kicker{display:block;color:var(--mut);font-size:14px;margin-bottom:8px}.release-strip strong{font-size:24px;font-weight:600}.release-strip p{margin:8px 0 0;color:var(--mut);max-width:720px}.release-link{flex:none}.release-page{padding-top:56px}.release-current{background:var(--surface);border:1px solid var(--line);border-radius:0;padding:28px;max-width:960px}.release-heading{display:flex;align-items:center;justify-content:space-between;gap:24px}.release-heading h2{margin:0 0 8px}.release-heading time{font-size:14px;color:var(--mut)}.release-summary{font-size:18px;color:var(--mut);max-width:780px;margin:24px 0}.release-details{border:0;border-top:1px solid var(--line);background:transparent;padding:20px 0 0}.release-details summary{font-size:16px}.release-changes{padding-left:22px}.release-changes li{margin-bottom:16px;color:var(--mut)}.archive-title{margin-top:56px}.release-archive{max-width:960px;border:0;border-top:1px solid var(--line);border-radius:0;background:transparent;padding:20px 0;margin:0}.release-archive summary{display:list-item;font-size:16px}.release-archive summary time{font-size:14px;color:var(--mut);margin-right:20px}.release-archive p{max-width:800px}
.skip-link{position:fixed;left:16px;top:-100px;z-index:100;background:var(--fg);color:var(--bg);padding:12px 18px;font-weight:600}.skip-link:focus{top:12px}:focus-visible{outline:3px solid var(--fg);outline-offset:4px}.shot a:focus-visible{outline-offset:-4px}
#lb{position:fixed;inset:0;z-index:1000;background:color-mix(in srgb,var(--bg) 96%,transparent);display:none;align-items:center;justify-content:center;padding:64px 12px 12px}#lb.on{display:flex}#lb img{max-width:100%;max-height:100%;object-fit:contain}#lb button{position:absolute;top:12px;right:12px;width:48px;height:48px;border:1px solid var(--line);border-radius:0;background:var(--fg);color:var(--bg);font-size:26px;cursor:pointer}
@media(max-width:1100px){nav.main{display:none}.burger{display:block}header.top.open nav.main{display:flex;position:absolute;top:76px;left:0;right:0;flex-direction:column;align-items:stretch;white-space:normal;background:var(--surface);border-bottom:1px solid var(--line);padding:12px}header.top.open nav.main a{padding:12px}header.top.open .more-menu{position:static;min-width:0;background:transparent;border:0}nav.main a.dl{margin-left:0}.hero{gap:28px}}
@media(max-width:900px){.hero{grid-template-columns:minmax(0,1fr);padding-top:48px;padding-bottom:48px}.hero .lead{max-width:680px}.hero .btns{flex-direction:row}.hero .btn{min-width:0}.hero-shot{max-width:760px;width:100%}.g3,.g4,.tiles,.tiles.spd{grid-template-columns:repeat(2,minmax(0,1fr))}.release-strip,.release-heading{flex-direction:column;align-items:flex-start}.shots{grid-template-columns:minmax(0,1fr)}}
@media(max-width:600px){.wrap{padding-left:20px;padding-right:20px}.g2,.g3,.g4,.tiles,.tiles.spd{grid-template-columns:minmax(0,1fr)}.tile,.panel{padding:24px}.hero h1{font-size:32px}.hero .lead{font-size:18px}.hero .btns{flex-direction:column;align-items:stretch}.hero .btn{width:100%}.bars{grid-template-columns:110px minmax(0,1fr) 56px;gap:12px 8px;font-size:14px}.news{grid-template-columns:1fr}.release-current{padding:22px}.release-archive summary time{display:block;margin-bottom:8px}section{padding-top:48px}}
@media(max-width:400px){.brand img{height:32px}.langbox label{display:none}header.top .wrap{gap:10px}.btns .btn{width:100%}}

/* Semantic colour tokens are reserved for their named roles. */
.label-loupe{--label-colour:var(--c-loupe)}.label-assay{--label-colour:var(--c-assay)}
.label-free,.plan-free{--label-colour:var(--c-free)}.label-personal,.plan-personal{--label-colour:var(--c-personal)}.label-team,.plan-team{--label-colour:var(--c-team)}.label-org,.plan-org{--label-colour:var(--c-org)}
/* Colours belong to complete meaning tiles, never decorative markers. */
.semantic-label::before{display:none}
.plan-free{--tile-colour:var(--c-free)}.plan-personal{--tile-colour:var(--c-personal)}.plan-team{--tile-colour:var(--c-team)}.plan-org{--tile-colour:var(--c-org)}
:is(.panel,.tile,.btn,.quiz-out):is(.version-loupe,.version-assay,.plan-free,.plan-personal,.plan-team,.plan-org){background:var(--tile-colour);border:0;color:#fff;--fg:#fff;--mut:#fff}
:is(.panel,.tile,.quiz-out):is(.version-loupe,.version-assay,.plan-free,.plan-personal,.plan-team,.plan-org) :is(h3,p,li,ul,.price,small,.note,.semantic-label,a){color:#fff}
:is(.panel,.tile):is(.version-loupe,.version-assay,.plan-free,.plan-personal,.plan-team,.plan-org) .btn{background:transparent;border:1px solid #fff;color:#fff!important}
.btn:is(.version-loupe,.version-assay,.plan-free,.plan-personal,.plan-team,.plan-org){color:#fff!important}
.panel{display:flex;flex-direction:column}.panel .btn-col{margin-top:auto;padding-top:20px}
/* The single brand motif, derived from the three text bars of the logo. */
.highlight-rule{display:block;position:relative;width:48px;height:20px;flex:none;border-top:4px solid var(--mut);border-bottom:4px solid var(--mut)}.highlight-rule::after{content:"";position:absolute;left:0;right:0;top:4px;height:4px;background:var(--mut)}
.home-rule{max-width:1180px;margin:48px auto 0;padding:0 28px}.benefit .cap{display:flex;align-items:center;gap:12px}
.hero-visual{display:grid;grid-template-columns:minmax(0,1fr) 120px;gap:8px;align-items:end;min-width:0}
.highlight-text{position:relative;width:120px;aspect-ratio:1;padding:22px 14px;border:0;background:var(--surface-raised);overflow:hidden;pointer-events:none}
.highlight-text i{display:block;position:relative;height:7px;margin-bottom:6px;width:94%;background:var(--mut)}
.highlight-text i:nth-child(2){width:76%}.highlight-text i:nth-child(3){width:88%}.highlight-text i:nth-child(4){width:66%}.highlight-text i:nth-child(5){width:92%}.highlight-text i:nth-child(6){width:58%}
.highlight-text i::after{content:"";position:absolute;inset:0;background:var(--fg);transform:scaleX(0);transform-origin:left;animation:highlight-sweep 1.8s ease-in-out both;animation-delay:calc(var(--row)*.12s)}
.highlight-text i:nth-child(1){--row:0}.highlight-text i:nth-child(2){--row:1}.highlight-text i:nth-child(3){--row:2}.highlight-text i:nth-child(4){--row:3}.highlight-text i:nth-child(5){--row:4}.highlight-text i:nth-child(6){--row:5}
.highlight-text i:nth-child(2)::after{left:28%;right:34%;transform:scaleX(1);animation-name:highlight-settle}.highlight-text i:nth-child(5)::after{left:54%;right:16%;transform:scaleX(1);animation-name:highlight-settle}
@keyframes highlight-sweep{0%{transform:scaleX(0)}45%{transform:scaleX(1)}100%{transform:scaleX(0)}}
@keyframes highlight-settle{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@media(max-width:600px){.home-rule{padding:0 20px}}
.tiles.stats{grid-template-columns:repeat(3,minmax(0,1fr));align-items:stretch;grid-auto-rows:minmax(200px,1fr)}
.stats .tile{gap:12px}.stats .lbl{font-size:16px;line-height:1.4}
.business-features{align-items:stretch}.business-features .panel{display:flex;flex-direction:column;justify-content:flex-start}.business-features p{margin-bottom:0}
section>.wrap>h1{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:clamp(2.5rem,4vw,3.5rem);font-weight:300;line-height:1.2;letter-spacing:-.03em;margin:0 0 24px}
@media(max-width:900px){.version-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-visual{grid-template-columns:minmax(0,1fr) 120px}}
@media(max-width:600px){.version-grid{grid-template-columns:minmax(0,1fr)}.version-grid .version-both{grid-column:auto}.hero-visual{grid-template-columns:minmax(0,1fr)}.highlight-text{justify-self:end}.tiles.stats{gap:8px;grid-auto-rows:minmax(150px,1fr)}.stats .tile{padding:14px 10px}.stats .big{font-size:clamp(24px,6.2vw,32px)}.stats .lbl{font-size:14px}}
.stats .tile.on{animation:metro-slide .45s ease-out both}
@keyframes metro-slide{from{transform:translateY(8px)}to{transform:translateY(0)}}

@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}}

/* App surfaces and feature colours, identical across languages and themes. */
body{position:relative;background:var(--bg)}
header.top,footer{background:var(--bg)}
h2{font-family:"Segoe UI Light","Segoe UI",sans-serif;font-size:28px;font-weight:300;border:0}
.home-rule{display:none}
.feature-batch{--tile-colour:var(--c-learn)}.feature-comparison{--tile-colour:var(--c-results)}.feature-privacy{--tile-colour:var(--c-privacy)}.feature-highlighting{--tile-colour:var(--c-download)}.feature-report{--tile-colour:var(--c-report)}.feature-business{--tile-colour:var(--c-business)}.feature-performance{--tile-colour:var(--c-performance)}
.plan-free{--tile-colour:var(--c-free)}.plan-personal{--tile-colour:var(--c-personal)}.plan-team{--tile-colour:var(--c-team)}.plan-org{--tile-colour:var(--c-org)}.version-assay{--tile-colour:var(--c-assay)}.version-loupe{--tile-colour:var(--c-loupe)}
.version-both{--tile-colour:var(--surface-raised)}
.panel,.tile{position:relative;display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line)}
.tone-1{background:var(--surface)}.tone-2{background:var(--surface-raised)}.tone-3{background:var(--bg)}
:is(.panel,.tile):is([class*="feature-"],[class*="plan-"],.version-assay,.version-loupe){background:var(--tile-colour);border-color:transparent;--mut:#fff;--fg:#fff;color:#fff}
.panel{padding:24px;gap:0}.tile{padding:20px;gap:12px}
.tile .lbl{margin-top:auto}.tile-glyph{width:40px;height:40px;color:var(--fg);flex:none;margin-bottom:16px}
.tile .tile-glyph{margin-bottom:0}.panel h3{font-weight:400;font-size:22px}
.grid,.tiles{gap:8px;grid-auto-rows:1fr}
.grid.g4:not(.pricing){grid-auto-rows:minmax(273px,auto)}
.tiles.stats{grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:auto}
.tiles.spd{grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:auto}.tiles.spd .tile{min-height:273px}
.g2>:last-child:nth-child(odd),.g3>:last-child:nth-child(3n+1),.g4>:last-child:nth-child(4n+1){grid-column:1/-1}
.evidence-grid{grid-template-columns:repeat(6,minmax(0,1fr))}.evidence-grid>.panel{grid-column:span 2}.evidence-grid>.panel:nth-last-child(-n+2){grid-column:span 3}
.stats .tile{min-height:200px}.stats .big{font-size:46px}
.highlight-text{background:var(--c-download)}.highlight-text i{background:#b0dfbf}.highlight-text i::after{background:#fff}
.pricing .panel{padding:48px 18px 20px}.pricing h3{min-height:58px;margin-bottom:8px}.pricing .price{min-height:78px;font-size:42px}
.pricing .btn-col{margin-top:auto;padding-top:24px}.pricing .btn{font-size:14px;padding:12px 6px;white-space:nowrap}
.recommended-label{position:absolute;top:0;right:0;margin:0;padding:5px 10px;background:#fff;color:#141821;font-size:12px;line-height:1.5}
.pricing-notes{margin:16px 0;display:flex;flex-wrap:wrap;gap:8px 24px}.pricing-notes p{margin:0}
.btns{gap:8px;align-items:stretch;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));grid-auto-rows:1fr}
.btns .btn{width:100%;min-height:52px}.hero .btns{display:grid;grid-template-columns:1fr}.hero .btn{min-width:0}
.btns:has(>.btn:nth-child(3)):not(:has(>.btn:nth-child(4))){grid-template-columns:repeat(3,minmax(0,1fr))}
.shots{align-items:stretch}.shot{display:flex;flex-direction:column}.shot a{flex:1;display:flex;align-items:center;background:var(--surface)}.shot figcaption{margin-top:auto;background:var(--surface);color:var(--mut);border-top:1px solid var(--line)}
.btn-col{gap:8px}.btn-col .btn{min-height:72px}.panel>.btn{margin-top:auto}
.btn,.btn.sec{background:var(--surface-raised);border:2px solid var(--line);color:var(--fg)!important;transition:background-color .15s,color .15s,transform .1s;white-space:normal}
.btn:is([class*="plan-"],.version-assay,.version-loupe){--fg:var(--app-fg);--mut:var(--app-mut)}
.btn.acc{background:var(--fg);color:var(--bg)!important;border-color:var(--fg)}
.panel .btn{background:transparent;border:2px solid var(--fg);color:var(--fg)!important}
:is(.btn,.btn.acc):hover{background:var(--fg);color:var(--bg)!important;border-color:var(--fg);text-decoration:none!important}
:is(.panel,.tile):is([class*="feature-"],[class*="plan-"],.version-assay,.version-loupe) .btn:hover{background:#fff;color:#141821!important;border-color:#fff}
a.tile:hover{outline:2px solid var(--fg);outline-offset:-4px}
:is(button,.btn,a.tile,nav a,summary):active{transform:scale(.97)}
:is(button,.btn,a.tile,nav a,summary):focus-visible{outline:3px solid var(--fg);outline-offset:4px}
nav.main a:hover,.more summary:hover,.burger:hover{background:var(--surface-raised);color:var(--fg)}.more-menu{background:var(--surface-raised)}
.theme-toggle{display:inline-flex;align-items:center;justify-content:center;flex:none;width:40px;height:40px;padding:8px;background:var(--surface);color:var(--fg);border:1px solid var(--line);cursor:pointer}
.theme-toggle:hover{background:var(--surface-raised)}.theme-toggle svg{width:22px;height:22px}.theme-toggle .moon{display:none}html[data-theme="light"] .theme-toggle .sun{display:none}html[data-theme="light"] .theme-toggle .moon{display:block}
@media(max-width:900px){.pricing{grid-template-columns:repeat(2,minmax(0,1fr))}.tiles.spd{grid-template-columns:repeat(2,minmax(0,1fr))}.evidence-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.evidence-grid>.panel{grid-column:auto}.evidence-grid>.panel:nth-last-child(2){grid-column:auto}.evidence-grid>.panel:last-child{grid-column:1/-1}.g3>:last-child:nth-child(odd),.g4>:last-child:nth-child(odd){grid-column:1/-1}.version-grid .version-both{grid-column:1/-1}}
@media(max-width:600px){.pricing{grid-template-columns:1fr}.pricing h3,.pricing .price{min-height:0}.pricing .panel{min-height:480px}.tiles.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.stats .tile{min-height:180px}.stats .tile:last-child{grid-column:1/-1}.stats .big{font-size:32px}.stats .tile-glyph{width:32px;height:32px}.grid.g4:not(.pricing){grid-auto-rows:auto}.btns,.btns:has(>.btn:nth-child(3)):not(:has(>.btn:nth-child(4))){grid-template-columns:1fr}.tile-glyph{width:36px;height:36px}.tiles.spd{grid-template-columns:1fr}.tiles.spd .tile{min-height:180px;padding:20px;gap:8px}.tiles.spd .tile-glyph{width:28px;height:28px}.tiles.spd .cap{font-size:12px}.tiles.spd .lbl{font-size:14px!important;line-height:1.5}.evidence-grid{grid-template-columns:1fr}.evidence-grid>.panel:nth-last-child(-n+2){grid-column:auto}.hero-visual{grid-template-columns:minmax(0,1fr) 80px;align-items:end}.highlight-text{width:80px;padding:14px 10px}.hero-shot{padding:4px}}

"""
CSS_V = _hl.md5(CSS.encode("utf-8")).hexdigest()[:8]

LANG_JS = """<script>
(function(){
var FILES=_FILES_JSON_;
var slug='_SLUG_', lang='_LANG_';
var sel=document.getElementById('langsel');
function navLang(){var l=(navigator.language||navigator.userLanguage||'en').toLowerCase();return l.indexOf('ru')===0?'ru':(l.indexOf('pl')===0?'pl':'en');}
try{
  var stored=null;try{stored=localStorage.getItem('linda-lang');}catch(e){}
  sel.value=lang;
  if(!stored&&slug==='index'&&lang==='en'&&navLang()!=='en'){
    try{localStorage.setItem('linda-lang',navLang());}catch(e){}
    location.replace(FILES[slug][navLang()]);
  }
}catch(e){sel.value=lang;}
sel.addEventListener('change',function(){
  try{localStorage.setItem('linda-lang',sel.value);}catch(e){}
  location.href=FILES[slug][sel.value];
});
})();
</script>"""

def _news_js(t):
    """Новости встроены в страницу (работает и при открытии с диска, без fetch); версию модели подтягивает сеть."""
    lang = I18N_LANG
    items = [dict(n, title=(n.get('title_i18n') or {}).get(lang, n['title']), text=(n.get('text_i18n') or {}).get(lang, n['text'])) for n in NEWS]
    data = json.dumps(items, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
    return (NEWS_JS.replace("fetch('news.json').then(r=>r.json())", "Promise.resolve(%s)" % data)
            .replace("_FAIL_", S(t, "news_fail")).replace("_CUR_", S(t, "news_cur")))


NEWS_JS = """<script>
fetch('news.json').then(r=>r.json()).then(items=>{
  const box=document.getElementById('newsList');box.innerHTML='';
  items.forEach(n=>{const d=document.createElement('div');d.className='news';
    d.innerHTML='<time></time><div><h3></h3><p></p></div>';d.querySelector('time').textContent=n.date;d.querySelector('h3').textContent=n.title;d.querySelector('p').textContent=n.text;box.appendChild(d);});
}).catch(()=>{document.getElementById('newsList').innerHTML='<p class="note">_FAIL_</p>';});
fetch('https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/latest.json').then(r=>r.json()).then(m=>{
  document.getElementById('curVer').textContent='_CUR_'+m.version+' ('+m.released+')';
}).catch(()=>{});
</script>"""


REVEAL_JS = """<script>
(function(){
try{
  var lb=document.createElement("div");lb.id="lb";lb.innerHTML='<button type="button" aria-label="Close">&times;</button>';document.body.appendChild(lb);
  function lbClose(back){if(!lb.classList.contains("on"))return;lb.classList.remove("on");if(back!==true&&history.state&&history.state.lb){history.back();}}
  document.querySelectorAll(".shot a, .hero-shot a").forEach(function(a){a.addEventListener("click",function(e){e.preventDefault();var img=lb.querySelector("img")||document.createElement("img");img.src=a.getAttribute("href");img.alt=a.querySelector("img").alt;lb.appendChild(img);lb.classList.add("on");try{history.pushState({lb:1},"");}catch(x){}});});
  lb.addEventListener("click",function(){lbClose();});
  document.addEventListener("keydown",function(e){if(e.key==="Escape")lbClose();});
  window.addEventListener("popstate",function(){lbClose(true);});
}catch(e){}
try{
  var els=document.querySelectorAll('section .wrap, .hero>div, .tile, .panel, .news, .shot, .priv');
  els.forEach(function(el){el.classList.add('rv');});
  var reduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduced||!('IntersectionObserver' in window)){els.forEach(function(el){el.classList.add('on');});}
  else{var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('on');io.unobserve(e.target);}});},{threshold:.08});
  els.forEach(function(el){io.observe(el);});}
  var nums=document.querySelectorAll('[data-count]');
  function anim(el){
    var target=parseFloat(el.getAttribute('data-count')),dec=parseInt(el.getAttribute('data-dec')||'0',10),suf=el.getAttribute('data-suffix')||'';
    if(reduced||!(target>0)){return;}
    var t0=null,dur=900;
    function fr(ts){if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/dur);el.textContent=(target*(0.2+0.8*p)).toFixed(dec)+suf;if(p<1)requestAnimationFrame(fr);else el.textContent=target.toFixed(dec)+suf;}
    requestAnimationFrame(fr);
  }
  if('IntersectionObserver' in window&&!reduced){var io2=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){anim(e.target);io2.unobserve(e.target);}});},{threshold:.4});nums.forEach(function(el){io2.observe(el);});}
}catch(e){}
})();
</script>"""


def hreflang(slug: str) -> str:
    f = FILES[slug]
    return (f'<link rel="canonical" href="{SITE}/{f[I18N_LANG]}">\n'
            + "\n".join(f'<link rel="alternate" hreflang="{l}" href="{SITE}/{fn}">' for l, fn in f.items())
            + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}/{f["en"]}">')



def semantic_html(markup: str, t) -> str:
    """Mark visible labels while preserving source copy, attributes and scripts."""
    labels = {"Linda Loupe": "loupe", "Linda Assay": "assay", "Personal": "personal",
              "Team": "team", "Organization / University": "org", "Organization": "org", t["free_h"]: "free"}
    pattern = re.compile(r"(?<![\w])(" + "|".join(re.escape(k) for k in sorted(labels, key=len, reverse=True)) + r")(?![\w])")
    class MarkLabels(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out, self.stack = [], []
        def handle_starttag(self, tag, attrs):
            self.out.append(self.get_starttag_text())
            if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
                classes = dict(attrs).get("class", "").split()
                protected = tag in ("script", "style", "code", "pre", "button") or "semantic-label" in classes or "btn" in classes
                self.stack.append((tag, protected))
        def handle_startendtag(self, tag, attrs):
            self.out.append(self.get_starttag_text())
        def handle_endtag(self, tag):
            self.out.append(f"</{tag}>")
            if self.stack and self.stack[-1][0] == tag:
                self.stack.pop()
        def handle_data(self, data):
            self.out.append(data if any(p for _, p in self.stack) else pattern.sub(lambda m: '<span class="semantic-label label-' + labels[m[0]] + '">' + m[0] + '</span>', data))
        def reference(self, prefix, name):
            line, column = self.getpos()
            offset = sum(len(part) for part in markup.splitlines(keepends=True)[:line - 1]) + column
            raw = prefix + name
            self.out.append(raw + (";" if markup[offset + len(raw):].startswith(";") else ""))
        def handle_entityref(self, name):
            self.reference("&", name)
        def handle_charref(self, name):
            self.reference("&#", name)
        def handle_comment(self, data):
            self.out.append("<!--" + data + "-->")
    parser = MarkLabels()
    parser.feed(markup)
    return "".join(parser.out)


GLYPHS = {
    "download": '<path d="M16 3v18m-7-7 7 7 7-7M5 23v6h22v-6"/>',
    "lock": '<rect x="6" y="14" width="20" height="15"/><path d="M10 14V9a6 6 0 0 1 12 0v5m-6 6v4"/>',
    "chart": '<path d="M4 3v26h25M9 24v-8m7 8V9m7 15V4"/>',
    "people": '<circle cx="12" cy="9" r="5"/><path d="M3 29v-6a9 9 0 0 1 18 0v6m1-25a5 5 0 0 1 0 10m2 5a7 7 0 0 1 5 7v3"/>',
    "document": '<path d="M7 2h12l7 7v21H7Zm12 0v8h7M11 16h11m-11 5h11m-11 5h7"/>',
    "question": '<circle cx="16" cy="16" r="13"/><path d="M11 11a5 5 0 0 1 10 0c0 4-5 4-5 8m0 4v2"/>',
    "store": '<path d="M5 10h22l2 20H3ZM11 11V8a5 5 0 0 1 10 0v3"/>',
    "code": '<path d="m10 7-8 9 8 9m12-18 8 9-8 9M19 3l-6 26"/>',
}


def org_button(t):
    return {"en": "Buy Organization", "ru": "Купить Organization", "pl": "Kup Organization"}[I18N_LANG]


def metro_html(markup: str, slug: str) -> str:
    """Add icons and neutral surface variants; feature classes are explicit in templates."""
    class Metro(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out, self.stack = [], []

        def handle_starttag(self, tag, attrs):
            data = dict(attrs)
            classes = data.get("class", "").split()
            role = next((c[8:] for c in classes if c.startswith("feature-")), "neutral")
            card = "tile" in classes or "panel" in classes
            if card:
                parent = self.stack[-1] if self.stack else None
                if parent:
                    parent[3] += 1
                classes.append("tone-" + str(((parent[3] if parent else 1) - 1) % 3 + 1))
                data["class"] = " ".join(classes)
            if "grid" in classes and self.stack and self.stack[-1][2] == "pricing":
                data["class"] = " ".join(classes) + " pricing plans"
            raw = self.get_starttag_text()
            if data.get("class") != dict(attrs).get("class"):
                raw = re.sub(r'class="[^"]*"', 'class="' + data["class"] + '"', raw, count=1)
            self.out.append(raw)
            if card:
                glyph = {"privacy": "lock", "comparison": "document", "batch": "document",
                         "business": "people", "report": "chart", "highlighting": "chart",
                         "performance": "chart", "neutral": "document"}[role]
                if "quiz" in classes or "version-both" in classes:
                    glyph = "question"
                elif "plan-free" in classes:
                    glyph = "store"
                elif self.stack and self.stack[-1][2] == "dev":
                    glyph = "code"
                self.out.append('<svg class="tile-glyph" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">' + GLYPHS[glyph] + '</svg>')
            if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
                self.stack.append([tag, role, data.get("id", self.stack[-1][2] if self.stack else ""), 0])

        def handle_endtag(self, tag):
            self.out.append('</' + tag + '>')
            if self.stack and self.stack[-1][0] == tag:
                self.stack.pop()

        def handle_startendtag(self, tag, attrs):
            self.out.append(self.get_starttag_text())

        def handle_data(self, data):
            self.out.append(data)

        def handle_entityref(self, name):
            self.out.append('&' + name + ';')

        def handle_charref(self, name):
            self.out.append('&#' + name + ';')

        def handle_comment(self, data):
            self.out.append('<!--' + data + '-->')

    parser = Metro()
    parser.feed(markup)
    return ''.join(parser.out)


THEME_HEAD = """<script>(function(){var t;try{t=localStorage.getItem('linda-theme');}catch(e){}if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=t;})();</script>"""
THEME_JS = """<script>(function(){var h=document.documentElement,b=document.getElementById('theme-toggle'),m=matchMedia('(prefers-color-scheme: dark)'),chosen=false;try{chosen=/^(light|dark)$/.test(localStorage.getItem('linda-theme'));}catch(e){}function sync(){b.setAttribute('aria-pressed',h.dataset.theme==='dark'?'true':'false');}sync();b.addEventListener('click',function(){h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';chosen=true;try{localStorage.setItem('linda-theme',h.dataset.theme);}catch(e){}sync();});m.addEventListener('change',function(e){if(!chosen){h.dataset.theme=e.matches?'dark':'light';sync();}});})();</script>"""



def page(lang: str, slug: str, title: str, desc: str, body: str) -> str:
    t = I18N[lang]
    if slug not in ("terms", "privacy", "refund", "licensing"):
        if "<h1" not in body:
            body = re.sub(r"<h2>(.*?)</h2>", r"<h1>\1</h1>", body, count=1, flags=re.S)
        body = re.sub(r"(<h1\b[^>]*>)([^<]+)", lambda m: m[1] + m[2][:1].upper() + m[2][1:], body)
        if slug == "faq" and lang == "en":
            body = body.replace("<h1>Faq</h1>", "<h1>FAQ</h1>")
    body = metro_html(semantic_html(body, t), slug)
    idx = FILES["index"][lang]
    pre = "" if slug == "index" else idx
    f = FILES
    main_nav = (
        f'<a href="{pre}#how">{S(t, "nav_how")}</a>'
        f'<a href="{pre}#pricing">{S(t, "nav_pricing")}</a>'
        f'<a href="{f["business"][lang]}">{S(t, "nav_business")}</a>'
        f'<a href="{f["faq"][lang]}">{S(t, "nav_faq")}</a>'
        f'<a class="demo-nav" href="{DEMO_URL}" target="_blank" rel="noopener noreferrer">{S(t, "nav_demo")}</a>'
        f'<a class="dl" href="{PRIMARY_DL}">{S(t, "nav_download")}</a>')
    if LITE:
        main_nav = main_nav.replace(f'<a href="{f["business"][lang]}">', f'<a href="{f["versions"][lang]}">{S(t, "nav_versions")}</a><a href="{f["business"][lang]}">', 1)
    more_nav = "".join(
        f'<a href="{href}">{label}</a>' for href, label in (
            (f["results"][lang], S(t, "nav_results")),
            (f["developers"][lang], S(t, "nav_dev")),
            (f["memo"][lang], S(t, "nav_memo")),
            (f["licensing"][lang], S(t, "nav_lic")),
            (f["updates"][lang], S(t, "nav_updates")),
        ))
    for name,files in FILES.items():
        if name==slug and slug!="index":
            main_nav=main_nav.replace(f'href="{files[lang]}"',f'href="{files[lang]}" aria-current="page"')
            more_nav=more_nav.replace(f'href="{files[lang]}"',f'href="{files[lang]}" aria-current="page"')
    other = " ".join(f'<a href="{FILES[slug][l]}">{l.upper()}</a>' for l in LANGS if l != lang)
    langjs = LANG_JS.replace("_FILES_JSON_", json.dumps(FILES)).replace("_SLUG_", slug).replace("_LANG_", lang)
    jld = json.dumps({"@context": "https://schema.org", "@type": "SoftwareApplication",
                      "name": "Linda", "operatingSystem": "Windows 10/11",
                      "applicationCategory": "UtilitiesApplication", "inLanguage": lang,
                      "description": desc,
                      "offers": [{"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                                 {"@type": "Offer", "price": "10", "priceCurrency": "USD"}]},
                     ensure_ascii=False)
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{THEME_HEAD}
<title>{title}</title><meta name="description" content="{desc}">
{hreflang(slug)}
<meta property="og:type" content="website"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}/{FILES[slug][lang]}"><meta property="og:image" content="{SITE}/assets/og_image.png"><meta property="og:locale" content="{OG_LOCALE[lang]}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}">
<script type="application/ld+json">{jld}</script>
<link rel="icon" href="assets/linda.png"><link rel="stylesheet" href="site.css?v={CSS_V}"></head><body>
<a class="skip-link" href="#main-content">{S(t,"skip_main")}</a>
<header class="top" id="topbar"><div class="wrap"><a class="brand" href="{idx}"><img src="assets/logo_wordmark.png" alt="Linda" height="42"></a>
<button class="burger" id="burger" aria-label="{S(t, "burger_label")}" aria-expanded="false" aria-controls="main-nav">&#9776;</button>
<nav class="main" id="main-nav" aria-label="Main">{main_nav}<span class="more"><details><summary>{S(t, "nav_more")} &#9662;</summary><span class="more-menu">{more_nav}</span></details></span></nav><button type="button" class="theme-toggle" id="theme-toggle" aria-label="{S(t, "theme_label")}"><svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 1v3m0 16v3M1 12h3m16 0h3M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2"/></svg><svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z"/></svg></button><span class="langbox"><label for="langsel">{S(t, "lang_label")}</label><select class="langsel" id="langsel" aria-label="Language"><option value="en">EN</option><option value="ru">RU</option><option value="pl">PL</option></select><noscript>{other}</noscript></span></div></header>
<main id="main-content" tabindex="-1">{body}</main>
<footer><div class="wrap"><p>{S(t, "foot_op")}</p>
<p><a href="{FILES["updates"][lang]}">{S(t,"nav_updates")}</a><a href="{FILES["results"][lang]}">{S(t, "nav_results")}</a><a href="{FILES["business"][lang]}">{S(t, "nav_business")}</a><a href="{FILES["faq"][lang]}">{S(t, "nav_faq")}</a><a href="{FILES["developers"][lang]}">{S(t, "nav_dev")}</a><a href="{FILES["memo"][lang]}">{S(t, "nav_memo")}</a></p>
<p><a href="{FILES["trust"][lang]}">{S(t,"trust_title")}</a><a href="{FILES["licensing"][lang]}">{S(t, "foot_lic")}</a><a href="{FILES["terms"][lang]}">{S(t, "foot_terms")}</a><a href="{FILES["privacy"][lang]}">{S(t, "foot_priv")}</a><a href="{FILES["refund"][lang]}">{S(t, "foot_ref")}</a><a href="https://github.com/Lendarixon/Linda">GitHub</a><a href="https://huggingface.co/Lindarixon/Linda-Pro">Hugging Face</a><a href="{DOI_URL}">Technical report</a><a href="mailto:{MAIL}">{MAIL}</a></p></div></footer>{THEME_JS}{langjs}<script>
(function(){{var b=document.getElementById('burger'),h=document.getElementById('topbar');if(b&&h){{function close(){{h.classList.remove('open');b.setAttribute('aria-expanded','false');}}b.addEventListener('click',function(){{var o=h.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false');}});h.querySelectorAll('nav a').forEach(function(a){{a.addEventListener('click',close);}});window.addEventListener('resize',function(){{if(window.innerWidth>1000)close();}});document.addEventListener('keydown',function(e){{if(e.key==='Escape'){{var mobile=h.classList.contains('open'),expanded=h.querySelector('details[open]');close();if(expanded){{expanded.open=false;if(!mobile)expanded.querySelector('summary').focus();}}if(mobile)b.focus();}}}});document.addEventListener('click',function(e){{if(!h.contains(e.target)){{close();h.querySelectorAll('details[open]').forEach(function(d){{d.open=false;}});}}}});}}}})();
</script></body></html>"""


def prose(inner: str) -> str:
    return '<div class="wrap prose">' + inner + "</div>"


def index_body(t) -> str:
    rows = (("res_r1", "69.9", "81.0", "up", "+11.1"), ("res_r2", "81.8", "84.0", "up", "+2.2"),
            ("res_r3", "93.0", "95.5", "up", "+2.5"), ("res_r4", "99.7", "99.8", "eq", "+0.1"),
            ("res_r5", "82.9", "88.0", "up", "+5.1"), ("res_r6", "44.5", "46.6", "up", "+2.1"))
    hurows = (("res_r7", "4.4", "5.5", "dn", "+1.1"), ("res_r8", "0.2", "0.2", "eq", "0.0"),
              ("res_r9", "1.1", "0.4", "eq", "&minus;0.7"), ("res_r10", "0.7", "0.4", "eq", "&minus;0.3"),
              ("res_r11", "1.8", "0.4", "up", "&minus;1.4"), ("res_r12", "1.1", "2.0", "dn", "+0.9"))

    def trow(key, a, b, cls, ch):
        return (f'<tr><td>{S(t, key)}</td><td class="n">{a}</td><td class="n new">{b}</td>'
                f'<td class="n"><span class="chg {cls}">{ch}</span></td></tr>')

    tbl = ("".join(trow(*r) for r in rows)
           + f'<tr class="grp"><td colspan="4">{S(t, "res_grp_hu")}</td></tr>'
           + "".join(trow(*r) for r in hurows))
    faq = "".join(f"<details><summary>{S(t, f'qa{i}_q')}</summary><div class=\"faq-a\"><div class=\"faq-a-in\"><p>{S(t, f'qa{i}_a')}</p></div></div></details>" for i in (13, 1, 2, 3, 4, 6))
    newsjs = _news_js(t)
    w = S(t, "spd_words")
    return f"""
<div class="wrap hero"><div>
<h1>{S(t, "hero_h1a")[0].upper() + S(t, "hero_h1a")[1:].rstrip(".")} {S(t, "hero_h1b")}</h1>
<p class="lead">{S(t, "hero_lead").split(". ", 1)[0]}.</p>
<div class="btns">{dl_buttons(t, compact=True)}<a class="btn demo-cta" href="{DEMO_URL}" target="_blank" rel="noopener noreferrer">{S(t, "demo_cta")}</a></div>
<p class="note demo-note">{S(t, "demo_note")}</p>
</div>
<div class="hero-visual"><figure class="hero-shot"><a href="assets/shot-app-{I18N_LANG}.png" aria-label="{S(t, "shot_open")}: {S(t, "shot1_cap")}"><img src="assets/shot-app-{I18N_LANG}.png" alt="{S(t, "shot1_cap")}" fetchpriority="high"></a></figure><div class="highlight-text" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div></div>
</div>
<section id="overview"><div class="wrap"><h2>{ {"en": "Texts and models stay on your PC", "ru": "Тексты и модели остаются на вашем ПК", "pl": "Teksty i modele zostają na Twoim komputerze"}[I18N_LANG] }</h2>
<p class="sub">{S(t, "hero_priv_p")}</p>
<p>{S(t, "hero_free")}</p>
<p class="note">{S(t, "dl_store_note")}</p>
<div class="btns" style="margin:24px 0"><a class="btn sec" href="#pricing">{S(t, "hero_pricing")}</a><a class="btn sec" href="{FILES["business"][I18N_LANG]}">{S(t, "nav_business")}</a><a class="btn sec" href="{DOI_URL}">{S(t, "hero_report")}</a></div>
<div class="tiles stats">
<div class="tile neutral benefit version-assay"><span class="big">81%</span><span class="lbl">{ {"en": "Humanizer texts", "ru": "Гуманизаторы", "pl": "Teksty humanizerów"}[I18N_LANG] }</span></div>
<div class="tile neutral benefit feature-performance"><span class="big">0.8 s</span><span class="lbl">{S(t, "tile2_cap")}<br>{ {"en": "on CPU", "ru": "на CPU", "pl": "na CPU"}[I18N_LANG] }</span></div>
<div class="tile neutral benefit feature-privacy"><span class="big">{ {"en": "0 bytes", "ru": "0 байт", "pl": "0 bajtów"}[I18N_LANG] }</span><span class="lbl">{S(t, "tile3_lbl")}</span></div>
</div>
<p class="note" style="margin-top:16px">81% {S(t, "tile1_lbl").split(". ", 1)[0]}. <a href="{FILES["results"][I18N_LANG]}">{S(t, "strip_more")}</a></p>
</div></section>

{release_strip(t)}
<div class="home-rule" aria-hidden="true"><span class="highlight-rule"></span></div>
{versions_strip(t)}
<section id="numbers"><div class="wrap"><h2>{S(t, "nums_h")}</h2>
<div class="grid g4">
<div class="panel neutral"><div class="big">{S(t, "nums1_big")}</div><h3>{S(t, "nums1_lbl")}</h3><p>{S(t, "nums1_p")}</p></div>
<div class="panel neutral"><div class="big">{S(t, "nums2_big")}</div><h3>{S(t, "nums2_lbl")}</h3><p>{S(t, "nums2_p")}</p></div>
<div class="panel neutral"><div class="big">{S(t, "nums3_big")}</div><h3>{S(t, "nums3_lbl")}</h3><p>{S(t, "nums3_p")}</p></div>
<div class="panel neutral"><div class="big">{S(t, "nums4_big")}</div><h3>{S(t, "nums4_lbl")}</h3><p>{S(t, "nums4_p")}</p></div>
</div>
<p class="note" style="margin-top:10px">{S(t, "nums_note")} <a href="{FILES["results"][I18N_LANG]}">{S(t, "strip_more")}</a></p>
</div></section>
<div class="home-rule" aria-hidden="true"><span class="highlight-rule"></span></div>
<section id="how"><div class="wrap"><h2>{S(t, "how_h")}</h2><p class="sub">{S(t, "how_sub")}</p>
<div class="grid g3">
<div class="panel neutral"><h3>{S(t, "how1h")}</h3><p>{S(t, "how1p")}</p></div>
<div class="panel neutral feature-highlighting"><h3>{S(t, "how2h")}</h3><p>{S(t, "how2p")}</p></div>
<div class="panel neutral"><h3>{S(t, "how3h")}</h3><p>{S(t, "how3p")}</p></div>
</div>
<div class="btns" style="margin-top:22px;max-width:520px"><a class="btn sec" href="{FILES["results"][I18N_LANG]}">{S(t, "learn_more")}</a></div>
</div></section>

<section id="results"><div class="wrap"><h2>{S(t, "res_h")}</h2>
<p class="sub" style="margin-bottom:14px">{S(t, "res_vs_sub")}</p>
<div class="bars">
<span class="us">Linda Assay 1.3.1</span><div class="bar us"><i style="width:81.0%"></i></div><span class="v us">81.0%</span>
<span class="us note">Linda Assay 1.3</span><div class="bar us"><i style="width:80.8%"></i></div><span class="v us note">80.8%</span>
<span class="us note">Linda Assay 1.1</span><div class="bar us"><i style="width:69.9%"></i></div><span class="v us note">69.9%</span>
<span>GPTZero</span><div class="bar"><i style="width:47.7%"></i></div><span class="v">47.7%</span>
<span>Originality.ai</span><div class="bar"><i style="width:47.2%"></i></div><span class="v">47.2%</span></div>
<p class="note" style="margin-top:8px">{S(t, "res_vs_note")}</p>
<div class="btns" style="margin-top:22px;max-width:520px"><a class="btn sec" href="{FILES["results"][I18N_LANG]}">{S(t, "learn_more")}</a></div>
</div></section>



<div class="home-rule" aria-hidden="true"><span class="highlight-rule"></span></div>
<section id="pricing"><div class="wrap"><h2>{S(t, "pr_h")}</h2>
<p class="sub">{S(t, "pr_sub")}</p>
<div class="grid g4">
<div class="panel plan-free"><h3>{S(t, "free_h")}</h3><div class="price">{S(t, "free_price")}</div><ul><li>{S(t, "free_li1")}</li><li>{S(t, "free_li2")}</li><li>{S(t, "free_li3")}</li></ul><div class="btn-col"><a class="btn" href="{PRIMARY_DL}">{S(t, "free_dl")}</a></div></div>
<div class="panel recommended plan-personal"><span class="recommended-label">{ {"en": "Recommended", "ru": "Рекомендуем", "pl": "Polecany"}[I18N_LANG] }</span><h3>{S(t, "per_h")}</h3><div class="price">{S(t, "per_price")}</div><ul><li>{S(t, "per_li1")}</li><li>{S(t, "per_li2")}</li><li>{S(t, "per_li3")}</li></ul><div class="btn-col"><a class="btn" href="{BUY_PT}">{S(t, "per_buy")}</a></div></div>
<div class="panel plan-team"><h3>{S(t, "team_h")}</h3><div class="price">{S(t, "team_price")}</div><ul><li>{S(t, "team_li1")}</li><li>{S(t, "team_li2")}</li><li>{S(t, "team_li3")}</li></ul><div class="btn-col"><a class="btn" href="{BUY_PT}">{S(t, "team_buy")}</a></div></div>
<div class="panel plan-org"><h3>{S(t, "org_h")}</h3><div class="price">{S(t, "org_price")}</div><ul><li>{S(t, "org_li1")}</li><li>{S(t, "org_li2")}</li><li>{S(t, "org_li3")}</li></ul><div class="btn-col"><a class="btn" href="{BUY_ORG}">{org_button(t)}</a></div></div>
</div>
<div class="pricing-notes"><p class="note">{S(t, "free_buy_rule_q")} <a href="{FILES["licensing"][I18N_LANG]}" style="text-decoration:underline">{S(t, "free_buy_rule_a")}</a>.</p><p class="note">{S(t, "team_note")}</p></div>
<div class="panel neutral feature-business" style="margin-top:8px"><h3>{S(t, "oem_h")}</h3><p>{S(t, "oem_p")}</p></div>
<div style="margin-top:14px">
<div class="btns" style="margin-top:0"><a class="btn" href="{PRIMARY_DL}">{S(t, "cta_dl")}</a>{alt_dl(t)}<a class="btn sec plan-personal" href="{BUY_PT}">{S(t, "cta_buy")}</a><a class="btn sec" href="mailto:{MAIL}">{S(t, "cta_mail")}</a></div></div>
</div></section>

<section id="faq"><div class="wrap"><h2>{S(t, "faq_h")}</h2>
{faq}
<div class="btns" style="margin-top:22px;max-width:520px"><a class="btn sec" href="{FILES["faq"][I18N_LANG]}">{S(t, "learn_more")}</a></div>
</div></section>

{REVEAL_JS}
"""




def alt_dl(t) -> str:
    """The GitHub installer next to a main button that leads to the Store."""
    return f'<a class="btn sec" href="{DOWNLOAD}">{S(t, "dl_github")}</a>' if MS_STORE_URL else ""


def dl_buttons(t, compact=False) -> str:
    """Main download: Microsoft Store when its link is set (the familiar way, like other apps), the GitHub installer as the alternative."""
    if compact:
        return (f'<a class="btn acc" href="{PRIMARY_DL}">{S(t, "dl_store" if MS_STORE_URL else "hero_dl")}</a>' + alt_dl(t))
    if MS_STORE_URL:
        return (f'<a class="btn acc" style="grid-column:1/-1" href="{MS_STORE_URL}">{S(t, "dl_store")}</a>'
                f'<a class="btn sec" style="grid-column:1/-1" href="{DOWNLOAD}">{S(t, "dl_github")}</a>'
                f'<p class="note" style="grid-column:1/-1;flex:1 1 100%;margin:4px 0 0;font-size:14px">{S(t, "dl_store_note")}</p>')
    return f'<a class="btn acc" href="{PRIMARY_DL}">{S(t, "hero_dl")}</a>'


def versions_strip(t) -> str:
    if not LITE:
        return ""
    return f"""<section id="versions"><div class="wrap"><h2>{S(t, "ver_h")}</h2><p class="sub">{S(t, "ver_sub")}</p><p class="note">{S(t, "ver_current")}</p>
<div class="grid version-grid">
<div class="panel version-loupe"><h3>{S(t, "ver_lite_h")}</h3><p>{S(t, "ver_lite_p")}</p><ul><li>{S(t, "ver_lite_li1")}</li><li>{S(t, "ver_lite_li2")}</li><li>{S(t, "ver_lite_li3")}</li></ul></div>
<div class="panel version-assay"><h3>{S(t, "ver_pro_h")}</h3><p>{S(t, "ver_pro_p")}</p><ul><li>{S(t, "ver_pro_li1")}</li><li>{S(t, "ver_pro_li2")}</li><li>{S(t, "ver_pro_li3")}</li></ul></div>
<div class="panel version-both"><h3>{S(t, "ver_both_h")}</h3><p>{S(t, "ver_both_p")}</p><div class="btn-col"><a class="btn" href="{FILES["versions"][I18N_LANG]}">{S(t, "ver_choose")}</a></div></div>
</div></div></section>"""


def versions_body(t) -> str:
    n = NUMS
    rows = (("cmp_hb", n["pro"]["hb"] + "%", n["lite"]["hb"] + "%"), ("cmp_oct", n["pro"]["oct"] + "%", n["lite"]["oct"] + "%"), ("cmp_unseen", n["pro"]["unseen"] + "%", n["lite"]["unseen"] + "%"),
            ("cmp_pl", n["pro"]["pl"] + "%", n["lite"]["pl"] + "%"), ("cmp_ru", n["pro"]["ru"] + "%", n["lite"]["ru"] + "%"),
            ("cmp_toefl", n["pro"]["toefl"] + "%", n["lite"]["toefl"] + "%"), ("cmp_mage", n["pro"]["mage_h"] + "%", n["lite"]["mage_h"] + "%"),
            ("cmp_speed", S(t, "cmp_speed_pro"), S(t, "cmp_speed_lite")), ("cmp_size", S(t, "cmp_size_pro"), S(t, "cmp_size_lite")), ("cmp_gpu", S(t, "cmp_gpu_pro"), S(t, "cmp_gpu_lite")), ("cmp_offline", S(t, "cmp_yes"), S(t, "cmp_yes")))
    cl = lambda v: "n" if str(v).endswith("%") else "n txt"  # длинный текст (скорость, размер) переносится, иначе таблица уезжает вправо
    cmp_rows = "".join(f'<tr><td>{S(t, k)}</td><td class="{cl(a)}">{a}</td><td class="{cl(b)} new">{b}</td></tr>' for k, a, b in rows)
    hw = (("hw_os", "Windows 10 / 11, 64-bit", "Windows 10 / 11, 64-bit"), ("hw_cpu", S(t, "hw_cpu_lite"), S(t, "hw_cpu_pro")), ("hw_ram", S(t, "hw_ram_lite"), S(t, "hw_ram_pro")),
          ("hw_gpu", S(t, "hw_gpu_lite"), S(t, "hw_gpu_pro")), ("hw_disk", S(t, "hw_disk_lite"), S(t, "hw_disk_pro")), ("hw_net_l", S(t, "hw_net"), S(t, "hw_net")))
    hw_rows = "".join(f'<tr><td>{S(t, k)}</td><td>{a}</td><td>{b}</td></tr>' for k, a, b in hw)
    quiz = f"""<div class="panel neutral quiz" id="quiz"><h3>{S(t, "quiz_h")}</h3>
<div class="btns" style="max-width:720px">
<button class="btn sec" data-r="lite">{S(t, "quiz_a1")}</button><button class="btn sec" data-r="pro">{S(t, "quiz_a2")}</button><button class="btn sec" data-r="idk">{S(t, "quiz_a3")}</button></div>
<div id="quizOut" class="quiz-out" style="display:none"></div></div>
<script>(function(){{var T={{lite:{json.dumps(semantic_html(S(t, "quiz_r_lite"), t), ensure_ascii=False)},pro:{json.dumps(semantic_html(S(t, "quiz_r_pro"), t), ensure_ascii=False)},idk:{json.dumps(semantic_html(S(t, "quiz_r_idk"), t), ensure_ascii=False)}}};
var o=document.getElementById('quizOut');document.querySelectorAll('#quiz button').forEach(function(b){{b.addEventListener('click',function(){{o.style.display='block';o.className='quiz-out version-'+(b.dataset.r==='pro'?'assay':(b.dataset.r==='idk'?'both':'loupe'));o.innerHTML='<p>'+T[b.dataset.r]+'</p>';}});}});}})();</script>"""
    return f"""
<section id="which"><div class="wrap"><h1 style="font-weight:300;letter-spacing:-.04em">{S(t, "ver_page_h")}</h1><p class="sub">{S(t, "ver_page_sub")}</p><p class="note">{S(t, "ver_current")}</p>
{quiz}
<div class="grid version-grid" style="margin-top:18px">
<div class="panel version-loupe"><h3>{S(t, "ver_lite_h")}</h3><p>{S(t, "ver_lite_long")}</p></div>
<div class="panel version-assay"><h3>{S(t, "ver_pro_h")}</h3><p>{S(t, "ver_pro_long")}</p></div>
<div class="panel version-both"><h3>{S(t, "ver_both_h")}</h3><p>{S(t, "ver_both_long")}</p></div></div></div></section>
<section id="compare"><div class="wrap"><h2>{S(t, "cmp_h")}</h2><p class="sub">{S(t, "cmp_sub")}</p>
<div class="tbl-wrap"><table class="tbl"><tr><th>{S(t, "cmp_th")}</th><th class="n">Linda Assay</th><th class="n">Linda Loupe</th></tr>{cmp_rows}</table></div>
<p class="note" style="margin-top:8px">{S(t, "cmp_note")}</p></div></section>
<section id="hardware"><div class="wrap"><h2>{S(t, "hw_h")}</h2><p class="sub">{S(t, "hw_sub")}</p>
<div class="tbl-wrap"><table class="tbl"><tr><th></th><th>Linda Loupe</th><th>Linda Assay</th></tr>{hw_rows}</table></div>
<p class="note" style="margin-top:8px">{S(t, "hw_note")}</p></div></section>
<section id="getit"><div class="wrap"><h2>{S(t, "get_h")}</h2><p class="sub">{S(t, "get_sub")}</p>
<div class="btns version-downloads" style="max-width:640px">{dl_buttons(t)}</div>
<p class="note" style="margin-top:12px">{S(t, "get_note")}</p></div></section>
{REVEAL_JS}"""


def lite_results(t) -> str:
    if not LITE:
        return ""
    n = NUMS
    rows = (("res_r1", n["pro"]["hb"], n["lite"]["hb"]), ("res_r2", n["pro"]["oct"], n["lite"]["oct"]), ("res_r3", n["pro"]["unseen"], n["lite"]["unseen"]), ("cmp_pl", n["pro"]["pl"], n["lite"]["pl"]), ("cmp_ru", n["pro"]["ru"], n["lite"]["ru"]))
    hrows = (("res_r7", n["pro"]["toefl"], n["lite"]["toefl"]), ("res_r12", n["pro"]["mage_h"], n["lite"]["mage_h"]), ("res_r8", n["pro"]["chi_h"], n["lite"]["chi_h"]))
    tr = "".join(f'<tr><td>{S(t, k)}</td><td class="n">{a}</td><td class="n new">{b}</td></tr>' for k, a, b in rows) + f'<tr class="grp"><td colspan="3">{S(t, "res_grp_hu")}</td></tr>' + "".join(f'<tr><td>{S(t, k)}</td><td class="n">{a}</td><td class="n new">{b}</td></tr>' for k, a, b in hrows)
    return (f'<h3 style="font-weight:300;font-size:1.8rem;letter-spacing:-.03em;margin:44px 0 6px">{S(t, "lite_res_h")}</h3><p class="sub" style="margin-bottom:14px">{S(t, "lite_res_sub")}</p>'
            f'<div class="tbl-wrap"><table class="tbl"><tr><th>{S(t, "res_th_test")}</th><th class="n">Linda Assay</th><th class="n">Linda Loupe</th></tr>{tr}</table></div><p class="note" style="margin-top:8px">{S(t, "lite_res_note")}</p>')


def results_body(t) -> str:
    rows = (('res_r1', '69.9', '80.8', '81.0', 'up', '+0.2'), ('res_r2', '81.8', '81.3', '84.0', 'up', '+2.7'), ('res_r3', '93.0', '94.6', '95.5', 'up', '+0.9'), ('res_r4', '99.7', '99.8', '99.8', 'eq', '0.0'), ('res_r5', '82.9', '86.6', '88.0', 'up', '+1.4'), ('res_r6', '44.5', '45.9', '46.6', 'up', '+0.7'))
    hurows = (('res_r7', '4.4', '6.6', '5.5', 'up', '&minus;1.1'), ('res_r8', '0.2', '0.1', '0.2', 'eq', '+0.1'), ('res_r9', '1.1', '0.5', '0.4', 'eq', '&minus;0.1'), ('res_r10', '0.7', '0.4', '0.4', 'eq', '0.0'), ('res_r11', '1.8', '0.4', '0.4', 'eq', '0.0'), ('res_r12', '1.1', '0.9', '2.0', 'dn', '+1.1'))

    def trow(key, a, m, b, cls, ch):
        return (f'<tr><td>{S(t, key)}</td><td class="n">{a}</td><td class="n">{m}</td><td class="n new">{b}</td>'
                f'<td class="n"><span class="chg {cls}">{ch}</span></td></tr>')

    tbl = ("".join(trow(*r) for r in rows)
           + f'<tr class="grp"><td colspan="5">{S(t, "res_grp_hu")}</td></tr>'
           + "".join(trow(*r) for r in hurows))
    newsjs = _news_js(t)
    w = S(t, "spd_words")
    return f"""
<section id="trust"><div class="wrap"><h2>{S(t, "trust_h")}</h2><p class="sub">{S(t, "trust_sub")}</p>
<div class="grid evidence-grid">
<div class="panel neutral feature-privacy"><h3>{S(t, "tr1h")}</h3><p>{S(t, "tr1p")}</p></div>
<div class="panel neutral feature-report"><h3>{S(t, "tr2h")}</h3><p>{S(t, "tr2p")}</p></div>
<div class="panel neutral"><h3>{S(t, "tr3h")}</h3><p>{S(t, "tr3p")}</p></div>
<div class="panel neutral feature-business"><h3>{S(t, "tr5h")}</h3><p>{S(t, "tr5p")}</p></div>
<div class="panel neutral feature-privacy"><h3>{S(t, "tr6h")}</h3><p>{S(t, "tr6p")}</p></div>
</div></div></section>

<section id="results"><div class="wrap"><h2>{S(t, "res_h")}</h2>
<p class="sub">{S(t, "res_sub")}</p>
<div class="tbl-wrap"><table class="tbl"><tr><th>{S(t, "res_th_test")}</th><th class="n semantic-label label-assay">{S(t, "res_th_10")}</th><th class="n semantic-label label-assay">{S(t, "res_th_13")}</th><th class="n semantic-label label-assay">{S(t, "res_th_11")}</th><th class="n">{S(t, "res_th_ch")}</th></tr>
<tr class="grp"><td colspan="5">{S(t, "res_grp_ai")}</td></tr>
{tbl}</table></div>

<h3 style="font-weight:300;font-size:1.8rem;letter-spacing:-.03em;margin:44px 0 6px">{S(t, "res_vs_h")}</h3>
<p class="sub" style="margin-bottom:14px">{S(t, "res_vs_sub")}</p>
<div class="bars">
<span class="us">Linda Assay 1.3.1</span><div class="bar us"><i style="width:81.0%"></i></div><span class="v us">81.0%</span>
<span class="us note">Linda Assay 1.3</span><div class="bar us"><i style="width:80.8%"></i></div><span class="v us note">80.8%</span>
<span class="us note">Linda Assay 1.1</span><div class="bar us"><i style="width:69.9%"></i></div><span class="v us note">69.9%</span>
<span>GPTZero</span><div class="bar"><i style="width:47.7%"></i></div><span class="v">47.7%</span>
<span>Originality.ai</span><div class="bar"><i style="width:47.2%"></i></div><span class="v">47.2%</span>
<span>Copyleaks</span><div class="bar"><i style="width:39.2%"></i></div><span class="v">39.2%</span>
<span>Winston</span><div class="bar"><i style="width:34.8%"></i></div><span class="v">34.8%</span>
<span class="note">Linda Assay 1.0</span><div class="bar us"><i style="width:31.4%"></i></div><span class="v note">31.4%</span>
<span>ZeroGPT</span><div class="bar"><i style="width:19.3%"></i></div><span class="v">19.3%</span></div>
<p class="note" style="margin-top:8px">{S(t, "res_vs_note")}</p>

<div class="tbl-wrap"><table class="tbl" style="margin-top:34px"><tr><th>{S(t, "res_chi_th")}</th><th class="n">{S(t, "res_chi_plain")}</th><th class="n">{S(t, "res_chi_stealth")}</th></tr>
<tr><td>Pangram</td><td class="n">99.9</td><td class="n new" >98.1</td></tr>
<tr><td><b>Linda Assay 1.3.1</b></td><td class="n new">99.8</td><td class="n new">88.0</td></tr>
<tr><td>Linda Assay 1.3</td><td class="n">99.8</td><td class="n">86.6</td></tr>
<tr><td>Linda Assay 1.1</td><td class="n">99.7</td><td class="n">82.9</td></tr>
<tr><td>GPTZero</td><td class="n">98.6</td><td class="n">44.3</td></tr>
<tr><td>Originality.ai</td><td class="n">94.2</td><td class="n">29.1</td></tr></table></div>
<p class="note" style="margin-top:8px">{S(t, "res_chi_note")}</p>

<div class="panel neutral" style="margin-top:26px"><h3>{S(t, "res_lang_h")}</h3><p>{S(t, "res_lang_p")}</p></div>
{lite_results(t)}

<h3 style="font-weight:300;font-size:1.8rem;letter-spacing:-.03em;margin:44px 0 6px">{S(t, "res_spd_h")}</h3>
<p class="sub" style="margin-bottom:14px">{S(t, "res_spd_sub")}</p>
<div class="tiles spd">
<div class="tile neutral"><span class="cap">{S(t, "res_spd_len_cap")}</span><span class="lbl">300 {w}<br>1,000 {w}<br>3,000 {w}</span></div>
<div class="tile neutral"><span class="cap">{S(t, "res_spd_gpu_cap")}</span><span class="lbl" style="font-size:1.25rem;font-weight:300">0.08 s<br>0.25 s<br>0.76 s</span></div>
<div class="tile neutral"><span class="cap">{S(t, "res_spd_cpuw_cap")}</span><span class="lbl" style="font-size:1.25rem;font-weight:300">0.8 s<br>2.7 s<br>8.4 s</span></div>
<div class="tile neutral"><span class="cap">{S(t, "res_spd_cpus_cap")}</span><span class="lbl" style="font-size:1.25rem;font-weight:300">2.1 s<br>5.7 s<br>20 s</span></div></div>
<p class="note" style="margin-top:8px">{S(t, "res_spd_note")}</p>
<div class="btns" style="margin-top:22px;max-width:640px"><a class="btn acc" href="{PRIMARY_DL}">{S(t, "cta_dl")}</a>{alt_dl(t)}<a class="btn sec" href="{FILES["index"][I18N_LANG]}#pricing">{S(t, "hero_pricing")}</a></div>
</div></section>

<section id="news"><div class="wrap"><h2>{S(t, "news_h")}</h2><p class="sub">{S(t, "news_sub")}</p>
<p class="sub">{S(t,"updates_summary")}</p><a class="btn sec" href="{FILES["updates"][I18N_LANG]}">{S(t,"updates_full")} · 2.0.6.2</a></div></section>
{REVEAL_JS}
"""


def business_body(t) -> str:
    return f"""
<section id="business"><div class="wrap"><h1>{S(t, "biz_h")[:1].upper() + S(t, "biz_h")[1:]}</h1><p class="sub">{S(t, "biz_sub")}</p>
<div class="grid g2 business-features">
<div class="panel neutral feature-batch"><h3>{S(t, "biz_b1h")}</h3><p>{S(t, "biz_b1p")}</p></div>
<div class="panel plan-org"><h3>{S(t, "biz_b4h")}</h3><div class="price">{S(t, "org_price")}</div><p>{S(t, "biz_b4p")}</p></div>
<div class="panel neutral feature-comparison"><h3>{S(t, "biz_b2h")}</h3><p>{S(t, "biz_b2p")}</p></div>
<div class="panel neutral feature-privacy"><h3>{S(t, "biz_b3h")}</h3><p>{S(t, "biz_b3p")}</p></div>
</div>
<div class="btns" style="margin:20px 0"><a class="btn plan-org" href="{BUY_ORG}">{org_button(t)}</a><a class="btn sec" href="mailto:{MAIL}">{S(t, "biz_cta_mail")}</a></div>
<div class="panel neutral feature-business" style="margin-top:8px"><h3>{S(t, "oem_h")}</h3><p>{S(t, "oem_p")}</p></div>
<div class="shots">
<figure class="shot" style="margin:0"><a href="assets/shot-app-{I18N_LANG}.png" aria-label="{S(t,"shot_open")}: {S(t,"shot1_cap")}"><img src="assets/shot-app-{I18N_LANG}.png" alt="{S(t, "shot1_cap")}" loading="lazy"></a><figcaption>{S(t, "shot1_cap")}</figcaption></figure>
<figure class="shot" style="margin:0"><a href="assets/shot-report-{I18N_LANG}.png" aria-label="{S(t,"shot_open")}: {S(t,"shot2_cap")}"><img src="assets/shot-report-{I18N_LANG}.png" alt="{S(t, "shot2_cap")}" loading="lazy"></a><figcaption>{S(t, "shot2_cap")}</figcaption></figure>
</div>
<div class="btns" style="margin-top:22px;max-width:640px"><a class="btn acc" href="{PRIMARY_DL}">{S(t, "cta_dl")}</a>{alt_dl(t)}<a class="btn sec" href="{FILES["index"][I18N_LANG]}#pricing">{S(t, "hero_pricing")}</a></div>
</div></section>
{REVEAL_JS}
"""


def faq_body(t) -> str:
    faq = "".join(f"<details><summary>{S(t, f'qa{i}_q')}</summary><div class=\"faq-a\"><div class=\"faq-a-in\"><p>{S(t, f'qa{i}_a')}</p></div></div></details>" for i in range(1, 17 if LITE else 14))
    return f"""
<section id="faq"><div class="wrap"><h2>{S(t, "faq_h")}</h2>
{faq}
<div class="btns" style="margin-top:22px;max-width:640px"><a class="btn sec" href="{FILES["memo"][I18N_LANG]}">{S(t, "nav_memo")}</a><a class="btn sec" href="{FILES["results"][I18N_LANG]}">{S(t, "nav_results")}</a></div>
</div></section>
{REVEAL_JS}
"""


def developers_body(t) -> str:
    return f"""
<section id="licensing"><div class="wrap"><h2>{S(t, "lic_h")}</h2>
<p class="sub">{S(t, "lic_sub")}</p>
<div class="grid g2">
<div class="panel neutral"><h3>{S(t, "lic_free_h")}</h3><p>{S(t, "lic_free_p")}</p>
<div class="btn-col"><a class="btn" href="{PRIMARY_DL}">{S(t, "lic_btn_app")}</a><a class="btn sec" href="https://huggingface.co/Lindarixon/Linda-Pro">{S(t, "lic_btn_models")}</a></div></div>
<div class="panel neutral"><h3>{S(t, "lic_com_h")}</h3><p>{S(t, "lic_com_p")}</p>
<div class="btn-col"><a class="btn" href="{FILES["index"][I18N_LANG]}#pricing">{S(t, "lic_btn_prices")}</a><a class="btn sec" href="{FILES["licensing"][I18N_LANG]}">{S(t, "lic_btn_full")}</a></div></div>
</div></div></section>

<section id="dev"><div class="wrap"><h2>{S(t, "dev_h")}</h2><p class="sub">{S(t, "dev_sub")}</p>
<div class="panel neutral"><p>{S(t, "dev_p")}</p>
<div class="btn-col" style="max-width:520px"><a class="btn" href="https://github.com/Lendarixon/Linda">{S(t, "dev_btn_gh")}</a><a class="btn sec" href="https://huggingface.co/Lindarixon/Linda-Pro">{S(t, "dev_btn_hf")}</a></div></div>
</div></section>

<section id="req"><div class="wrap"><div class="panel neutral"><h3>{S(t, "qa5_q")}</h3><p>{S(t, "qa5_a")}</p></div>
</div></section>
{REVEAL_JS}
"""


def memo_body(t) -> str:
    return f"""
<section id="memo"><div class="wrap"><h2>{S(t, "memo_h")}</h2><p class="sub">{S(t, "memo_sub")}</p>
<div class="grid g4">
<div class="panel neutral"><h3>{S(t, "memo_s1h")}</h3><p>{S(t, "memo_s1p")}</p></div>
<div class="panel neutral"><h3>{S(t, "memo_s2h")}</h3><p>{S(t, "memo_s2p")}</p></div>
<div class="panel neutral feature-comparison"><h3>{S(t, "memo_s3h")}</h3><p>{S(t, "memo_s3p")}</p></div>
<div class="panel neutral feature-report"><h3>{S(t, "memo_s4h")}</h3><p>{S(t, "memo_s4p")}</p></div>
</div>
<div class="btns" style="margin-top:22px;max-width:640px"><a class="btn sec" href="{FILES["faq"][I18N_LANG]}">{S(t, "learn_more")}</a><a class="btn sec" href="{FILES["results"][I18N_LANG]}">{S(t, "nav_results")}</a></div>
</div></section>
{REVEAL_JS}
"""


def terms_body(t) -> str:
    secs = "".join(f"<h3>{S(t, f't{i}h')}</h3><p>{S(t, f't{i}p')}</p>" for i in range(1, 8))
    prev = f'<p class="note">{S(t, "legal_prevails")}</p>' if t["legal_prevails"] else ""
    lic = FILES["licensing"][I18N_LANG]
    upd = S(t, "terms_updated").replace("licensing overview",
                                        f'<a href="{lic}">licensing overview</a>').replace(
        "одностраничный обзор лицензии", f'<a href="{lic}">одностраничный обзор лицензии</a>').replace(
        "jednostronicowy przegląd licencji", f'<a href="{lic}">jednostronicowy przegląd licencji</a>')
    return prose(f"<h1>{S(t, 'terms_h')}</h1>{prev}<p class=\"note\">{upd}</p>{secs}")


def privacy_body(t) -> str:
    prev = f'<p class="note">{S(t, "legal_prevails")}</p>' if t["legal_prevails"] else ""
    return prose(f"<h1>{S(t, 'priv_h')}</h1>{prev}<h3>{S(t, 'pb1h')}</h3><p>{S(t, 'pb1p')}</p>"
                 f"<h3>{S(t, 'pb2h')}</h3>{S(t, 'pb2p')}"
                 f"<h3>{S(t, 'pb3h')}</h3><p>{S(t, 'pb3p')}</p>"
                 f"<h3>{S(t, 'pb4h')}</h3><p>{S(t, 'pb4p')}</p>")


def refund_body(t) -> str:
    prev = f'<p class="note">{S(t, "legal_prevails")}</p>' if t["legal_prevails"] else ""
    secs = "".join(f"<h3>{S(t, f'rb{i}h')}</h3><p>{S(t, f'rb{i}p')}</p>" for i in range(1, 4))
    return prose(f"<h1>{S(t, 'ref_h')}</h1>{prev}<p class=\"note\">{S(t, 'ref_updated')}</p>"
                 f"<p>{S(t, 'ref_intro')}</p>{secs}")


def md_inline(s: str) -> str:
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md2html(md: str) -> str:
    out, para, i = [], [], 0
    lines = md.split("\n")
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|\s*$", lines[i + 1]):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out.append('<div class="tbl-wrap"><table><tr>' + "".join(f"<th>{md_inline(c)}</th>" for c in cells) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</table></div>")
            continue
        if line.startswith("### "):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
            out.append(f"<h3>{md_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
            out.append(f"<h2>{md_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
            out.append(f"<h1>{md_inline(line[2:])}</h1>")
        elif line.startswith("* "):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
            items = []
            while i < len(lines) and lines[i].strip().startswith("* "):
                items.append("<li>" + md_inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif not line.strip():
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para = []
        else:
            para.append(line.strip())
        i += 1
    if para:
        out.append("<p>" + md_inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def trust_body(t, lang):
    text = (ROOT / "content" / ("TRUST." + lang + ".md")).read_text(encoding="utf-8")
    return prose(md2html(text))


def licensing_body(t, lang: str) -> str:
    md = (ROOT / "content" / LIC_MD[lang]).read_text(encoding="utf-8")
    if lang != "en":
        md = (md.replace("](privacy.html)", f"](privacy-{lang}.html)")
                .replace("](terms.html)", f"](terms-{lang}.html)"))
    prev = f'<p class="note">{S(t, "lic_prevails")}</p>' if lang != "en" else ""
    html = md2html(md)
    html = html.replace("<h2>1. ", '<h2 class="semantic-label label-free">1. ', 1)
    return prose(prev + html)


NEWS = [
    {
        'date': '2026-10-17',
        'title': 'Linda 2.0.6.2 — Clearer checks and safer file handling',
        'text': '• A pre-check guide recommends at least 300 words of continuous prose. Very short texts and lists, rules, formulas, forms and slide-like material may not be assessed reliably. A recommendation is not a quality guarantee, and “no signs found” does not prove human authorship.\n• PPT/PPTX files are unsupported. Exporting slides to PDF does not make slide content suitable for analysis; text PDFs are supported.\n• File replacement, model-folder moves and cancellation are safer and clearer. Diagnostic archives redact local profile paths.\n• Models remain version 1.3.4. No detection-accuracy improvement is claimed.',
        'title_i18n': {
            'en': 'Linda 2.0.6.2 — Clearer checks and safer file handling',
            'ru': 'Linda 2.0.6.2 — Понятнее проверка и безопаснее работа с файлами',
            'pl': 'Linda 2.0.6.2 — Czytelniejsze wskazówki i bezpieczniejsza obsługa plików',
        },
        'text_i18n': {
            'en': '• A pre-check guide recommends at least 300 words of continuous prose. Very short texts and lists, rules, formulas, forms and slide-like material may not be assessed reliably. This is a recommendation, not a quality guarantee; “no signs found” does not prove human authorship.\n• PPT/PPTX files are unsupported. Exporting slides to PDF does not make slide content suitable for analysis; text PDFs are supported.\n• File replacement, model-folder moves and cancellation are safer and clearer. Diagnostic archives redact local profile paths.\n• Microsoft Store package 2.0.6002.0 is prepared for submission and will become available after submission and review; the GitHub installer release is 2.0.6.2. Models remain version 1.3.4; no detection-accuracy improvement is claimed.',
            'ru': '• Перед проверкой программа подсказывает: лучше использовать не менее 300 слов связного текста. Короткие тексты, списки, правила, формулы, бланки и слайды могут оцениваться ненадёжно. Это рекомендация, а не гарантия качества; отсутствие найденных признаков не доказывает, что текст написал человек.\n• Файлы PPT/PPTX не поддерживаются. Экспорт слайдов в PDF не делает их содержимое подходящим для анализа; текстовые PDF поддерживаются.\n• Безопаснее заменять текст и переносить папку моделей; анализ можно отменить. Локальные пути профиля скрываются в диагностических архивах.\n• Пакет Microsoft Store 2.0.6002.0 подготовлен к отправке и станет доступен после подачи и проверки; версия установщика GitHub — 2.0.6.2. Модели остаются версии 1.3.4; улучшение точности детекции не заявляется.',
            'pl': '• Przed analizą program zaleca co najmniej 300 słów spójnego tekstu. Krótkie teksty, listy, regulaminy, wzory, formularze i treść slajdów mogą być oceniane nierzetelnie. To zalecenie, nie gwarancja jakości; brak wykrytych oznak nie dowodzi, że tekst napisał człowiek.\n• Pliki PPT/PPTX nie są obsługiwane. Eksport slajdów do PDF nie sprawia, że ich treść nadaje się do analizy; tekstowe pliki PDF są obsługiwane.\n• Bezpieczniej zastępować tekst i przenosić folder modeli; analizę można anulować. Archiwa diagnostyczne ukrywają lokalne ścieżki profilu.\n• Pakiet Microsoft Store 2.0.6002.0 jest przygotowany do przesłania i będzie dostępny po zgłoszeniu oraz weryfikacji; wydanie instalatora GitHub to 2.0.6.2. Modele pozostają w wersji 1.3.4; nie deklarujemy poprawy dokładności detekcji.',
        },
    },
    {'date': '2026-10-11', 'title': 'Linda 2.0.6.0 — Consistent GPU inference and local highlighting', 'text': '• Assay uses FP32 stable DirectML on Windows to reduce CPU/GPU score drift; Loupe remains on CPU. GPU memory use is higher than FP16; 4 GB compatibility is not certified.\n• Assay samples the same context anchors on CPU/GPU.\n• Model identity, independent Essay/Multi evidence, Unicode offsets and document extraction are corrected.\n• Selected highlighting, counters, word shares and exports stay synchronized. Document confidence and local coverage are separate.\n• Weights remain 1.3.4. Short AI inserts and edited texts may still be missed; these fixes do not certify detection accuracy.', 'title_i18n': {'en': 'Linda 2.0.6.0 — Consistent GPU inference and local highlighting', 'ru': 'Linda 2.0.6.0 — Согласованные GPU-оценки и локальная разметка', 'pl': 'Linda 2.0.6.0 — Spójne oceny GPU i lokalne oznaczenia'}, 'text_i18n': {'en': '• Assay uses FP32 stable DirectML on Windows to reduce CPU/GPU score drift; Loupe remains on CPU. GPU memory use is higher than FP16; 4 GB compatibility is not certified.\n• Assay samples the same context anchors on CPU/GPU.\n• Model identity, independent Essay/Multi evidence, Unicode offsets and document extraction are corrected.\n• Selected highlighting, counters, word shares and exports stay synchronized. Document confidence and local coverage are separate.\n• Weights remain 1.3.4. Short AI inserts and edited texts may still be missed; these fixes do not certify detection accuracy.', 'ru': '• Assay использует стабильный FP32 DirectML в Windows для уменьшения расхождений CPU/GPU; Loupe работает на CPU. Расход видеопамяти выше FP16; совместимость с 4 ГБ не сертифицирована.\n• Assay использует одинаковые опорные контексты на CPU/GPU.\n• Исправлены имя модели, независимые данные Essay/Multi, Unicode-смещения и извлечение документов.\n• Выбранная подсветка, счётчики, доли слов и экспорт синхронизированы. Оценка документа и локальное покрытие — разные показатели.\n• Веса остаются 1.3.4. Короткие ИИ-вставки и редактированные тексты могут быть пропущены; эти исправления не сертифицируют точность детекции.', 'pl': '• Assay używa stabilnego FP32 DirectML w Windows, aby ograniczyć różnice CPU/GPU; Loupe pozostaje na CPU. Zużycie VRAM jest wyższe niż FP16; zgodność z 4 GB nie została potwierdzona.\n• Assay wybiera te same konteksty na CPU/GPU.\n• Poprawiono identyfikację modelu, niezależne dane Essay/Multi, przesunięcia Unicode i odczyt dokumentów.\n• Podświetlenie, liczniki, udziały słów i eksport są zsynchronizowane. Ocena dokumentu i lokalne pokrycie to oddzielne wskaźniki.\n• Wagi pozostają 1.3.4. Krótkie wstawki AI i edytowane teksty mogą pozostać niewykryte; poprawki nie certyfikują dokładności.'}},
    {'date': '2026-10-10', 'title': 'Linda 2.0.5.3 — Fixes after the rename', 'text': '• First-run tips now use the interface language (they were always in Russian).\n• Reports (PDF and HTML) show the Linda mark in the header; the short PDF report no longer prints the old name.\n• The installer shows the correct Linda Loupe size, about 0.3 GB.\n• Models, verdicts and licence keys are unchanged.', 'title_i18n': {'ru': 'Linda 2.0.5.3 — Исправления после переименования', 'en': 'Linda 2.0.5.3 — Fixes after the rename', 'pl': 'Linda 2.0.5.3 — Poprawki po zmianie nazwy'}, 'text_i18n': {'ru': '• Подсказки при первом запуске показываются на языке интерфейса (раньше всегда по-русски).\n• В заголовке отчётов (PDF и HTML) появился значок Linda; краткий PDF-отчёт больше не пишет старое название.\n• Установщик показывает правильный размер Linda Loupe — около 0,3 ГБ.\n• Модели, вердикты и ключи лицензий не изменились.', 'en': '• First-run tips now use the interface language (they were always in Russian).\n• Reports (PDF and HTML) show the Linda mark in the header; the short PDF report no longer prints the old name.\n• The installer shows the correct Linda Loupe size, about 0.3 GB.\n• Models, verdicts and licence keys are unchanged.', 'pl': '• Wskazówki przy pierwszym uruchomieniu są w języku interfejsu (wcześniej zawsze po rosyjsku).\n• Raporty (PDF i HTML) mają znak Linda w nagłówku; krótki raport PDF nie pokazuje już starej nazwy.\n• Instalator pokazuje poprawny rozmiar Linda Loupe — ok. 0,3 GB.\n• Modele, werdykty i klucze licencyjne bez zmian.'}},
    {'date': '2026-10-10', 'title': 'Linda 2.0.5.2 — Linda: new names and logo', 'text': '• Linda is now the name of the product. The full ensemble is now called Linda Assay, the fast version is Linda Loupe.\n• Models, verdicts, settings and licence keys are unchanged; keys work as before.\n• New Metro-style logo: a tile with three lines of text, part of the middle one highlighted, just like the AI marking in the app. New icon for the app, the installer and the Start menu.\n• The logo in the app header follows the light/dark theme.', 'title_i18n': {'ru': 'Linda 2.0.5.2 — Linda: новые названия и логотип', 'en': 'Linda 2.0.5.2 — Linda: new names and logo', 'pl': 'Linda 2.0.5.2 — Linda: nowe nazwy i logo'}, 'text_i18n': {'ru': '• Linda — теперь общее имя продукта. Полный ансамбль называется Linda Assay, быстрая версия — Linda Loupe.\n• Модели, вердикты, настройки и ключи лицензий не изменились, ключи работают как прежде.\n• Новый логотип в стиле Metro: плитка с тремя строками текста, кусок средней подсвечен — как разметка ИИ в самом приложении. Новая иконка приложения, установщика и меню «Пуск».\n• Логотип в шапке приложения подстраивается под светлую и тёмную тему.', 'en': '• Linda is now the name of the product. The full ensemble is now called Linda Assay, the fast version is Linda Loupe.\n• Models, verdicts, settings and licence keys are unchanged; keys work as before.\n• New Metro-style logo: a tile with three lines of text, part of the middle one highlighted, just like the AI marking in the app. New icon for the app, the installer and the Start menu.\n• The logo in the app header follows the light/dark theme.', 'pl': '• Linda to teraz nazwa produktu. Pełny zespół nazywa się teraz Linda Assay, szybka wersja — Linda Loupe.\n• Modele, werdykty, ustawienia i klucze licencyjne bez zmian; klucze działają jak dotąd.\n• Nowe logo w stylu Metro: kafelek z trzema wierszami tekstu, fragment środkowego podświetlony — tak jak oznaczanie AI w aplikacji. Nowa ikona aplikacji, instalatora i menu Start.\n• Logo w nagłówku aplikacji dopasowuje się do jasnego/ciemnego motywu.'}},
    {'date': '2026-10-10', 'title': 'Linda-Pro 2.0.5.1 — Linda-Pro Lite: highlighting twice as fast', 'text': '• Linda-Pro Lite takes the token scores for highlighting from the same model passes that compute the verdict and reads only the rest of the text: highlighting is about 2x faster (our measurement: 2.1 -> 1.0 s per 1,000 words on 4 threads) with no loss of highlighting accuracy (85% of words labelled correctly on mixed texts, false AI mark on 3% of human words).\n• Verdicts are unchanged.', 'title_i18n': {'ru': 'Linda-Pro 2.0.5.1 — Linda-Pro Lite: разметка вдвое быстрее', 'en': 'Linda-Pro 2.0.5.1 — Linda-Pro Lite: highlighting twice as fast', 'pl': 'Linda-Pro 2.0.5.1 — Linda-Pro Lite: podświetlanie dwa razy szybsze'}, 'text_i18n': {'ru': '• Linda-Pro Lite берёт оценки токенов для разметки из тех же проходов модели, что считают вердикт, и дочитывает только остальной текст: разметка примерно в 2 раза быстрее (наш замер: 2,1 → 1,0 с на 1 000 слов на 4 потоках), точность разметки не ниже прежней (на смешанных текстах 85% верных меток слов, ложная метка «ИИ» у 3% человеческих слов).\n• Вердикты не изменились.', 'en': '• Linda-Pro Lite takes the token scores for highlighting from the same model passes that compute the verdict and reads only the rest of the text: highlighting is about 2x faster (our measurement: 2.1 -> 1.0 s per 1,000 words on 4 threads) with no loss of highlighting accuracy (85% of words labelled correctly on mixed texts, false AI mark on 3% of human words).\n• Verdicts are unchanged.', 'pl': '• Linda-Pro Lite bierze oceny tokenów do podświetlania z tych samych przebiegów modelu, które liczą werdykt, i doczytuje tylko resztę tekstu: podświetlanie ok. 2 razy szybsze (nasz pomiar: 2,1 -> 1,0 s na 1000 słów przy 4 wątkach) bez utraty dokładności (85% poprawnych etykiet słów na tekstach mieszanych, fałszywe AI u 3% słów ludzkich).\n• Werdykty bez zmian.'}},
    {'date': '2026-10-10', 'title': 'Linda-Pro 2.0.5.0 — Version 2.5: token-level highlighting, more accurate at the same speed', 'text': '• Sentence highlighting is now computed from tokens in the same model pass as the verdict instead of repeated passes over pieces of the text. Linda-Pro Lite highlights a 3,800-word text in about 4-6 s on a modern processor, without the huge uniform blocks of 2.0.4.x.\n• Highlighting accuracy on mixed human + AI texts with a known boundary (our measurement, EN/RU/PL): Linda-Pro labels 90% of words correctly (2.0.4.x: 90% at the cost of many repeated passes), Linda-Pro Lite 88% (2.0.4.x: 67%); about 3% of human words get a false "AI" mark.\n• The verdict and its accuracy are unchanged: same models, same thresholds.\n• If the document as a whole is "unclear" but AI is marked in almost all of the text, the Authorship box says "AI"; if nothing is marked it says "unclear" instead of "mixed".\n• Text scrolling no longer stops working after the model set is changed.\n• History and document comparison open faster.', 'title_i18n': {'ru': 'Linda-Pro 2.0.5.0 — Версия 2.5: разметка по токенам — точнее при той же скорости', 'en': 'Linda-Pro 2.0.5.0 — Version 2.5: token-level highlighting, more accurate at the same speed', 'pl': 'Linda-Pro 2.0.5.0 — Wersja 2.5: podświetlanie na poziomie tokenów, dokładniejsze przy tej samej szybkości'}, 'text_i18n': {'ru': '• Разметка предложений теперь строится по токенам за тот же проход модели, что и вердикт, а не повторными прогонами по кускам текста. Linda-Pro Lite размечает текст в 3 800 слов примерно за 4–6 с на современном процессоре вместо огромных однородных кусков в 2.0.4.x.\n• Точность разметки на смешанных текстах «человек + ИИ» с известной границей (наш замер, EN/RU/PL): Linda-Pro — верная метка у 90% слов (2.0.4.x: 90% ценой многих повторных прогонов), Linda-Pro Lite — 88% (2.0.4.x: 67%); у человеческих слов ложная метка «ИИ» около 3%.\n• Вердикт и его точность не изменились: модели те же, пороги те же.\n• Если документ в целом «неясно», а ИИ отмечен почти во всём тексте, в блоке «Авторство» пишется «ИИ»; если не отмечено ничего — «неясно», а не «смешанное».\n• Прокрутка текста больше не пропадает после смены набора моделей.\n• Быстрее открываются история и сравнение документов.', 'en': '• Sentence highlighting is now computed from tokens in the same model pass as the verdict instead of repeated passes over pieces of the text. Linda-Pro Lite highlights a 3,800-word text in about 4-6 s on a modern processor, without the huge uniform blocks of 2.0.4.x.\n• Highlighting accuracy on mixed human + AI texts with a known boundary (our measurement, EN/RU/PL): Linda-Pro labels 90% of words correctly (2.0.4.x: 90% at the cost of many repeated passes), Linda-Pro Lite 88% (2.0.4.x: 67%); about 3% of human words get a false "AI" mark.\n• The verdict and its accuracy are unchanged: same models, same thresholds.\n• If the document as a whole is "unclear" but AI is marked in almost all of the text, the Authorship box says "AI"; if nothing is marked it says "unclear" instead of "mixed".\n• Text scrolling no longer stops working after the model set is changed.\n• History and document comparison open faster.', 'pl': '• Podświetlanie zdań liczone jest teraz z tokenów w tym samym przebiegu modelu co werdykt, zamiast wielokrotnych przebiegów po fragmentach tekstu. Linda-Pro Lite podświetla tekst 3800 słów w ok. 4-6 s na nowoczesnym procesorze, bez ogromnych jednolitych bloków z 2.0.4.x.\n• Dokładność podświetlania na tekstach mieszanych człowiek + AI ze znaną granicą (nasz pomiar, EN/RU/PL): Linda-Pro - poprawna etykieta 90% słów (2.0.4.x: 90% kosztem wielu przebiegów), Linda-Pro Lite - 88% (2.0.4.x: 67%); ok. 3% słów ludzkich dostaje fałszywe oznaczenie „AI”.\n• Werdykt i jego dokładność bez zmian: te same modele, te same progi.\n• Gdy dokument jako całość jest „niejasny”, a AI zaznaczono prawie w całym tekście, blok „Autorstwo” pokazuje „AI”; gdy nic nie zaznaczono - „niejasne” zamiast „mieszane”.\n• Przewijanie tekstu nie przestaje działać po zmianie zestawu modeli.\n• Historia i porównanie dokumentów otwierają się szybciej.'}},
    {'date': '2026-10-10', 'title': 'Linda-Pro 2.0.4.2 — A more honest verdict and sentence highlighting', 'text': '• Linda-Pro Lite: sentence highlighting is fixed. Before, almost the whole text was coloured "possibly AI" for human and AI texts alike, and no sentence was ever marked "AI". Now about 9 in 10 words of AI texts are marked "AI", and 0-3% of words in human texts.\n• The verdict no longer contradicts the highlighting: if the app says "written by a human" while a noticeable part of the text (a quarter of the words or more) is marked AI, the verdict becomes "unclear".\n• Linda-Pro Lite is more careful: when the Lite model sees AI above its own threshold but the combined score is lower, the verdict is "unclear" instead of "human" (an AI text edited by hand is no longer passed off as human). In the "Both sets" mode this also applies to the Lite verdict.\n• The "possibly AI" band of Lite highlighting is wider and starts where the "unclear" zone of the verdict starts.', 'title_i18n': {'ru': 'Linda-Pro 2.0.4.2 — Честнее вердикт и разметка предложений', 'en': 'Linda-Pro 2.0.4.2 — A more honest verdict and sentence highlighting', 'pl': 'Linda-Pro 2.0.4.2 — Uczciwszy werdykt i podświetlanie zdań'}, 'text_i18n': {'ru': '• Linda-Pro Lite: исправлена разметка предложений. Раньше почти весь текст окрашивался как «возможно ИИ» — и у людей, и у ИИ-текстов, — а предложений «ИИ» не было вовсе. Теперь в ИИ-текстах около 9 из 10 слов отмечены «ИИ», у людей — 0–3%.\n• Вердикт больше не спорит с разметкой: если программа говорит «написан человеком», а заметная часть текста (от четверти слов) отмечена как ИИ, вердикт становится «неясно».\n• Linda-Pro Lite осторожнее: если модель Lite видит признаки ИИ выше своего порога, а общий балл ниже, вердикт «неясно», а не «человек» (так ИИ-текст с ручной правкой больше не выдаётся за человеческий). В режиме «Оба набора» это действует и на вердикт Lite.\n• Зона «возможно ИИ» в разметке Lite стала шире и начинается там же, где зона «неясно» у вердикта.', 'en': '• Linda-Pro Lite: sentence highlighting is fixed. Before, almost the whole text was coloured "possibly AI" for human and AI texts alike, and no sentence was ever marked "AI". Now about 9 in 10 words of AI texts are marked "AI", and 0-3% of words in human texts.\n• The verdict no longer contradicts the highlighting: if the app says "written by a human" while a noticeable part of the text (a quarter of the words or more) is marked AI, the verdict becomes "unclear".\n• Linda-Pro Lite is more careful: when the Lite model sees AI above its own threshold but the combined score is lower, the verdict is "unclear" instead of "human" (an AI text edited by hand is no longer passed off as human). In the "Both sets" mode this also applies to the Lite verdict.\n• The "possibly AI" band of Lite highlighting is wider and starts where the "unclear" zone of the verdict starts.', 'pl': '• Linda-Pro Lite: poprawione podświetlanie zdań. Wcześniej prawie cały tekst był oznaczany jako „możliwe AI” — zarówno u ludzi, jak i w tekstach AI — a żadne zdanie nie dostawało oznaczenia „AI”. Teraz w tekstach AI około 9 na 10 słów jest oznaczonych „AI”, u ludzi 0–3%.\n• Werdykt nie przeczy już podświetleniu: jeśli program mówi „napisany przez człowieka”, a znaczna część tekstu (co najmniej ćwierć słów) jest oznaczona jako AI, werdykt zmienia się na „niejasne”.\n• Linda-Pro Lite jest ostrożniejsza: gdy model Lite widzi AI powyżej własnego progu, a łączny wynik jest niższy, werdykt brzmi „niejasne”, a nie „człowiek” (tekst AI poprawiony ręcznie nie uchodzi już za ludzki). W trybie „Oba zestawy” dotyczy to też werdyktu Lite.\n• Pasmo „możliwe AI” w podświetleniu Lite jest szersze i zaczyna się tam, gdzie strefa „niejasne” werdyktu.'}},
    {'date': '2026-10-09', 'title': 'Linda-Pro 2.0.4.1 — Fixes: closing, restarting and updating', 'text': '• Closing the window no longer leaves the program hanging in the Task Manager; a new launch ends an old hung copy by itself and no longer opens its old interface.\n• Loading the models into memory at start no longer blocks the restart for an update ("finish the check" with no check running) or the applying of new models.\n• Error messages of the update buttons stay on screen longer.', 'title_i18n': {'ru': 'Linda-Pro 2.0.4.1 — Исправления: закрытие, перезапуск и обновление', 'en': 'Linda-Pro 2.0.4.1 — Fixes: closing, restarting and updating', 'pl': 'Linda-Pro 2.0.4.1 — Poprawki: zamykanie, restart i aktualizacja'}, 'text_i18n': {'ru': '• Закрытое окно больше не оставляет программу висеть в диспетчере задач; новый запуск сам завершает старую зависшую копию и не открывает её старый интерфейс.\n• Загрузка моделей в память при запуске больше не мешает перезапуску для обновления («Завершите проверку» без всякой проверки) и применению новых моделей.\n• Сообщения об ошибках кнопки обновления остаются на экране дольше.', 'en': '• Closing the window no longer leaves the program hanging in the Task Manager; a new launch ends an old hung copy by itself and no longer opens its old interface.\n• Loading the models into memory at start no longer blocks the restart for an update ("finish the check" with no check running) or the applying of new models.\n• Error messages of the update buttons stay on screen longer.', 'pl': '• Zamknięcie okna nie zostawia już programu wiszącego w Menedżerze zadań; nowe uruchomienie samo kończy starą zawieszoną kopię i nie otwiera jej starego interfejsu.\n• Ładowanie modeli do pamięci przy starcie nie blokuje już restartu do aktualizacji („zakończ sprawdzanie”, choć nic nie jest sprawdzane) ani zastosowania nowych modeli.\n• Komunikaty o błędach przycisków aktualizacji pozostają na ekranie dłużej.'}},
    {'date': '2026-10-09', 'title': 'Linda-Pro 2.0.4.0 — Version 2.4: Linda-Pro Lite, two sets and two verdicts', 'text': '• New, improved Linda-Pro Lite (about 0.3 GB): retrained on texts rewritten by stealth humanizers, without Llama; it finds disguised AI text better and runs on any processor.\n• New "Both sets" mode (Settings > Models): next to the Linda-Pro verdict the app shows the Lite verdict for comparison.\n• With only Linda-Pro Lite installed, the interface shows only it: no rows or buttons for the Essay and Multi models; model names in reports (PDF, Markdown) match the installed set.\n• Choice of set in the installer and in Settings; the graphics-card choice is kept.', 'title_i18n': {'ru': 'Linda-Pro 2.0.4.0 — Версия 2.4: Linda-Pro Lite, два набора и два вердикта', 'en': 'Linda-Pro 2.0.4.0 — Version 2.4: Linda-Pro Lite, two sets and two verdicts', 'pl': 'Linda-Pro 2.0.4.0 — Wersja 2.4: Linda-Pro Lite, dwa zestawy i dwa werdykty'}, 'text_i18n': {'ru': '• Новый, улучшенный Linda-Pro Lite (около 0,3 ГБ): модель дообучена на текстах, переписанных «стелс»-гуманайзерами, без Llama; лучше находит замаскированный ИИ-текст, работает на любом процессоре.\n• Новый режим «Оба набора» (Настройки → Модели): рядом с вердиктом Linda-Pro показывается вердикт Lite для сравнения.\n• Если установлен только Linda-Pro Lite, интерфейс показывает только его: без строк и кнопок моделей Essay и Multi; в отчётах (PDF, Markdown) названия моделей совпадают с установленным набором.\n• Выбор набора при установке и в настройках, выбор видеокарты сохранён.', 'en': '• New, improved Linda-Pro Lite (about 0.3 GB): retrained on texts rewritten by stealth humanizers, without Llama; it finds disguised AI text better and runs on any processor.\n• New "Both sets" mode (Settings > Models): next to the Linda-Pro verdict the app shows the Lite verdict for comparison.\n• With only Linda-Pro Lite installed, the interface shows only it: no rows or buttons for the Essay and Multi models; model names in reports (PDF, Markdown) match the installed set.\n• Choice of set in the installer and in Settings; the graphics-card choice is kept.', 'pl': '• Nowy, ulepszony Linda-Pro Lite (około 0,3 GB): douczony na tekstach przepisanych przez „stealth” humanizery, bez Llama; lepiej wykrywa zamaskowany tekst AI i działa na każdym procesorze.\n• Nowy tryb „Oba zestawy” (Ustawienia > Modele): obok werdyktu Linda-Pro aplikacja pokazuje werdykt Lite dla porównania.\n• Gdy zainstalowany jest tylko Linda-Pro Lite, interfejs pokazuje tylko jego: bez wierszy i przycisków modeli Essay i Multi; nazwy modeli w raportach (PDF, Markdown) odpowiadają zainstalowanemu zestawowi.\n• Wybór zestawu w instalatorze i w ustawieniach; wybór karty graficznej zachowany.'}},
    {'date': '2026-10-09', 'title': 'Linda-Pro 2.0.3.7 — Linda-Pro Lite: a light set for any computer', 'text': '• Two model sets: Linda-Pro (the most accurate, best with a graphics card) and Linda-Pro Lite (about 0.3 GB, runs on any processor, a 3,800-word text in seconds). Choose either one or both during installation and later in Settings ("Models").\n• Lite finds noticeably fewer AI texts after "humanizers" than Linda-Pro (10-14 points lower in our measurements, much lower on deliberately disguised texts); use Linda-Pro for an important text.\n• On a computer without a graphics card the app uses Lite by itself. Models download automatically.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.7 — Linda-Pro Lite: лёгкий набор для любых компьютеров', 'en': 'Linda-Pro 2.0.3.7 — Linda-Pro Lite: a light set for any computer', 'pl': 'Linda-Pro 2.0.3.7 — Linda-Pro Lite: lekki zestaw dla każdego komputera'}, 'text_i18n': {'ru': '• Два набора моделей: Linda-Pro (самая точная, лучше с видеокартой) и Linda-Pro Lite (около 0,3 ГБ, работает на любом процессоре, текст на 3 800 слов за секунды). При установке и позже в настройках («Модели») можно выбрать любой из них или оба.\n• Lite находит заметно меньше ИИ-текстов после «гуманизаторов», чем Linda-Pro (на 10–14 пунктов в наших замерах, на текстах с маскировкой — сильно меньше); для важного текста берите Linda-Pro.\n• Если на компьютере нет видеокарты, приложение само использует Lite. Модели скачиваются автоматически.', 'en': '• Two model sets: Linda-Pro (the most accurate, best with a graphics card) and Linda-Pro Lite (about 0.3 GB, runs on any processor, a 3,800-word text in seconds). Choose either one or both during installation and later in Settings ("Models").\n• Lite finds noticeably fewer AI texts after "humanizers" than Linda-Pro (10-14 points lower in our measurements, much lower on deliberately disguised texts); use Linda-Pro for an important text.\n• On a computer without a graphics card the app uses Lite by itself. Models download automatically.', 'pl': '• Dwa zestawy modeli: Linda-Pro (najdokładniejszy, najlepiej z kartą graficzną) i Linda-Pro Lite (około 0,3 GB, działa na każdym procesorze, tekst 3800 słów w kilka sekund). Podczas instalacji i później w ustawieniach („Modele”) można wybrać jeden z nich lub oba.\n• Lite znajduje wyraźnie mniej tekstów AI po „humanizerach” niż Linda-Pro (o 10–14 punktów w naszych pomiarach, przy celowo zamaskowanych tekstach znacznie mniej); do ważnego tekstu użyj Linda-Pro.\n• Na komputerze bez karty graficznej aplikacja sama używa Lite. Modele pobierają się automatycznie.'}},
    {'date': '2026-10-08', 'title': 'Linda-Pro 2.0.3.6 — Clearer and more convenient', 'text': '• After new models are downloaded the app now offers “Restart” instead of showing the “Update models” button again.\n• An old failed-install message (“Installer exit code 5”) is no longer shown at every start once that version is installed.\n• Rows of the batch table no longer flicker while several files are being checked.\n• Short text (under 150 words): a clear warning above the result that the estimate may be inaccurate.\n• The results panel can be widened or narrowed by dragging the divider between the text and the results (double-click resets it).\n• The built-in downloads flyout no longer covers the buttons at the top right.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.6 — Понятнее и удобнее', 'en': 'Linda-Pro 2.0.3.6 — Clearer and more convenient', 'pl': 'Linda-Pro 2.0.3.6 — Czytelniej i wygodniej'}, 'text_i18n': {'ru': '• После загрузки новых моделей программа предлагает «Перезапустить» вместо повторной кнопки «Обновить модели».\n• Старое сообщение о неудачной установке («Installer exit code 5») больше не показывается при каждом запуске, если эта версия уже установлена.\n• При проверке нескольких файлов строки таблицы больше не мигают.\n• Короткий текст (меньше 150 слов): над результатом заметное предупреждение, что оценка может быть неточной.\n• Правую панель результатов можно растянуть или сузить за разделитель между текстом и результатом (двойной щелчок — вернуть).\n• Окно загрузок встроенного браузера больше не закрывает кнопки сверху справа.', 'en': '• After new models are downloaded the app now offers “Restart” instead of showing the “Update models” button again.\n• An old failed-install message (“Installer exit code 5”) is no longer shown at every start once that version is installed.\n• Rows of the batch table no longer flicker while several files are being checked.\n• Short text (under 150 words): a clear warning above the result that the estimate may be inaccurate.\n• The results panel can be widened or narrowed by dragging the divider between the text and the results (double-click resets it).\n• The built-in downloads flyout no longer covers the buttons at the top right.', 'pl': '• Po pobraniu nowych modeli program proponuje „Uruchom ponownie” zamiast ponownie pokazywać przycisk aktualizacji modeli.\n• Stary komunikat o nieudanej instalacji („Installer exit code 5”) nie jest już pokazywany przy każdym uruchomieniu, gdy ta wersja jest już zainstalowana.\n• Wiersze tabeli nie migają już podczas sprawdzania kilku plików.\n• Krótki tekst (poniżej 150 słów): wyraźne ostrzeżenie nad wynikiem, że ocena może być niedokładna.\n• Panel wyników można poszerzyć lub zwęzić przeciągając separator między tekstem a wynikami (podwójne kliknięcie przywraca).\n• Okno pobierania wbudowanej przeglądarki nie zasłania już przycisków w prawym górnym rogu.'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.3.4 — More reliable updates', 'text': '• Updates no longer fail if you open the app during installation: it shows a message and opens by itself when the update is done.\n• Launching the app again while its window is open brings that window to the front instead of opening a browser.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.4 — Надёжное обновление', 'en': 'Linda-Pro 2.0.3.4 — More reliable updates', 'pl': 'Linda-Pro 2.0.3.4 — Pewniejsze aktualizacje'}, 'text_i18n': {'ru': '• Обновление больше не срывается, если открыть программу во время установки: она покажет сообщение и откроется сама после обновления.\n• Повторный запуск при уже открытом окне выводит окно на передний план и не открывает браузер.', 'en': '• Updates no longer fail if you open the app during installation: it shows a message and opens by itself when the update is done.\n• Launching the app again while its window is open brings that window to the front instead of opening a browser.', 'pl': '• Aktualizacja nie przerywa się już, gdy uruchomisz program w trakcie instalacji: pokaże komunikat i otworzy się sam po aktualizacji.\n• Ponowne uruchomienie przy otwartym oknie wysuwa to okno na wierzch i nie otwiera przeglądarki.'}},
    {'date': '2026-10-08', 'title': 'Models 1.3.1 — trained without Llama-generated texts', 'text': '• Model weights 1.3.1 (the app updates them automatically, no new installer): the training data no longer contains texts generated by Llama models; instead we added permissively licensed human learner essays (ASAP 2.0, IELTS sets) and rewrites from open models.\n• English: HumanizerBench 81.0% (was 80.8%), Oct 2026 cycle 84.0% (81.3%), three unseen generators 95.5% (94.6%), Chicago after StealthGPT 88.0% (86.6%). False flags: TOEFL 5.5% (6.6%), W&I 0.4%, ELLIPSE 0.4%.\n• Russian: 80% of AI texts at 0.6% false flags (was 78%); Gemini-rewritten 59% (50%). Polish: 79% at 1.4% false flags (was 80% at 0.9%); Gemini-rewritten 56% (48%).\n• Honest limits: false flags on MAGE human texts rose from 0.9% to 2.0%, and on the Polish set from 0.9% to 1.4% (5 of 350 texts instead of 3).\nTechnical report: https://doi.org/10.5281/zenodo.23242014', 'title_i18n': {'en': 'Models 1.3.1 — trained without Llama-generated texts', 'ru': 'Модели 1.3.1 — обучение без текстов, сгенерированных Llama', 'pl': 'Modele 1.3.1 — trening bez tekstów wygenerowanych przez Llama'}, 'text_i18n': {'en': '• Model weights 1.3.1 (the app updates them automatically, no new installer): the training data no longer contains texts generated by Llama models; instead we added permissively licensed human learner essays (ASAP 2.0, IELTS sets) and rewrites from open models.\n• English: HumanizerBench 81.0% (was 80.8%), Oct 2026 cycle 84.0% (81.3%), three unseen generators 95.5% (94.6%), Chicago after StealthGPT 88.0% (86.6%). False flags: TOEFL 5.5% (6.6%), W&I 0.4%, ELLIPSE 0.4%.\n• Russian: 80% of AI texts at 0.6% false flags (was 78%); Gemini-rewritten 59% (50%). Polish: 79% at 1.4% false flags (was 80% at 0.9%); Gemini-rewritten 56% (48%).\n• Honest limits: false flags on MAGE human texts rose from 0.9% to 2.0%, and on the Polish set from 0.9% to 1.4% (5 of 350 texts instead of 3).\nTechnical report: https://doi.org/10.5281/zenodo.23242014', 'ru': '• Веса моделей 1.3.1 (приложение обновит их само, новый установщик не нужен): в обучающих данных больше нет текстов, сгенерированных моделями Llama; добавлены эссе изучающих язык людей с разрешающей лицензией (ASAP 2.0, наборы IELTS) и переписывания открытыми моделями.\n• Английский: HumanizerBench 81,0% (было 80,8%), цикл октября 2026 84,0% (81,3%), три невиданных генератора 95,5% (94,6%), Chicago после StealthGPT 88,0% (86,6%). Ложные: TOEFL 5,5% (6,6%), W&I 0,4%, ELLIPSE 0,4%.\n• Русский: 80% ИИ-текстов при 0,6% ложных (было 78%); переписанные Gemini 59% (50%). Польский: 79% при 1,4% ложных (было 80% при 0,9%); переписанные Gemini 56% (48%).\n• Честно: ложные срабатывания на человеческих текстах MAGE выросли с 0,9% до 2,0%, на польском наборе — с 0,9% до 1,4% (5 текстов из 350 вместо 3).\nТехнический отчёт: https://doi.org/10.5281/zenodo.23242014', 'pl': '• Wagi modeli 1.3.1 (program zaktualizuje je sam, nowy instalator nie jest potrzebny): w danych treningowych nie ma już tekstów wygenerowanych przez modele Llama; dodaliśmy eseje uczących się języka z licencją zezwalającą (ASAP 2.0, zbiory IELTS) oraz przepisania przez otwarte modele.\n• Angielski: HumanizerBench 81,0% (było 80,8%), cykl października 2026 84,0% (81,3%), trzy niewidziane generatory 95,5% (94,6%), Chicago po StealthGPT 88,0% (86,6%). Fałszywe alarmy: TOEFL 5,5% (6,6%), W&I 0,4%, ELLIPSE 0,4%.\n• Rosyjski: 80% tekstów AI przy 0,6% fałszywych alarmów (było 78%); przepisane przez Gemini 59% (50%). Polski: 79% przy 1,4% (było 80% przy 0,9%); przepisane przez Gemini 56% (48%).\n• Uczciwie: fałszywe alarmy na ludzkich tekstach MAGE wzrosły z 0,9% do 2,0%, a na polskim zbiorze z 0,9% do 1,4% (5 z 350 tekstów zamiast 3).\nRaport techniczny: https://doi.org/10.5281/zenodo.23242014'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.3.3 — Tabs for several texts', 'text': '• Tabs: keep several texts side by side (up to 8, the + button or Ctrl+T). Each tab has its own text, file and result, and switching loses nothing.\n• A check belongs to its own tab: while it runs you can type in another one, and when it finishes the tab shows a green dot. One check runs at a time.\n• A file from Explorer (“Check in Linda-Pro”) opens in a new tab and does not overwrite the current text.\n• Closing a tab whose check is running cancels that check.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.3 — Вкладки для нескольких текстов', 'en': 'Linda-Pro 2.0.3.3 — Tabs for several texts', 'pl': 'Linda-Pro 2.0.3.3 — Karty dla kilku tekstów'}, 'text_i18n': {'ru': '• Вкладки: можно держать несколько текстов рядом (до 8, кнопка «+» или Ctrl+T). У каждой вкладки свой текст, файл и результат, переключение ничего не теряет.\n• Проверка привязана к своей вкладке: пока она идёт, можно печатать в другой, а когда закончится, у вкладки загорится зелёная точка. Одновременно идёт одна проверка.\n• Файл из проводника («Проверить в Linda-Pro») открывается в новой вкладке и не затирает текущий текст.\n• Закрытие вкладки с идущей проверкой её отменяет.', 'en': '• Tabs: keep several texts side by side (up to 8, the + button or Ctrl+T). Each tab has its own text, file and result, and switching loses nothing.\n• A check belongs to its own tab: while it runs you can type in another one, and when it finishes the tab shows a green dot. One check runs at a time.\n• A file from Explorer (“Check in Linda-Pro”) opens in a new tab and does not overwrite the current text.\n• Closing a tab whose check is running cancels that check.', 'pl': '• Karty: kilka tekstów obok siebie (do 8, przycisk + lub Ctrl+T). Każda karta ma własny tekst, plik i wynik, a przełączanie niczego nie gubi.\n• Sprawdzanie należy do swojej karty: gdy trwa, można pisać w innej, a po zakończeniu karta pokazuje zieloną kropkę. Naraz trwa jedno sprawdzanie.\n• Plik z Eksploratora („Sprawdź w Linda-Pro”) otwiera się w nowej karcie i nie nadpisuje bieżącego tekstu.\n• Zamknięcie karty z trwającym sprawdzaniem anuluje je.'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.3.2 — Automatic model updates, protection against silly input, a short summary', 'text': '• Automatic model updates: when a release brings new models they download in the background, are verified and replace the old ones (old files and caches are removed). On by default, can be turned off in Settings.\n• Protection against wrong input: texts in unsupported languages (Arabic, Chinese, Greek and others) get a clear message instead of a false verdict; a binary file renamed .txt is rejected; file errors are explained in plain words; Windows-1251 and UTF-16 files are read correctly; German and Ukrainian texts show a warning.\n• A one-page PDF summary for a teacher or editor: the verdict, what it means, the figures, the most suspicious sentences and a note that it is not proof.\n• 70 “silly” scenarios were tested (empty and huge texts, odd files, wrong paths, rapid clicks) with no failures.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.2 — Автообновление моделей, защита от «дурака», краткая справка', 'en': 'Linda-Pro 2.0.3.2 — Automatic model updates, protection against silly input, a short summary', 'pl': 'Linda-Pro 2.0.3.2 — Automatyczna aktualizacja modeli, ochrona przed błędnymi danymi, krótkie zaświadczenie'}, 'text_i18n': {'ru': '• Автообновление моделей: когда выходит релиз с новыми моделями, они скачиваются в фоне, проверяются и заменяют старые (старые файлы и кэш удаляются). Включено по умолчанию, выключается в настройках.\n• Защита от неверных данных: тексты на неподдерживаемых языках (арабский, китайский, греческий и др.) получают понятное сообщение вместо ложного вердикта; двоичный файл под видом .txt отклоняется; ошибки файлов объясняются понятными словами; кодировки Windows-1251 и UTF-16 читаются верно; для немецкого и украинского текста показывается предупреждение.\n• Краткая справка на одну страницу (PDF) для преподавателя или редактора: вердикт, что он значит, цифры, самые подозрительные предложения и оговорка, что это не доказательство.\n• Проверено 70 «глупых» сценариев (пустые и огромные тексты, странные файлы, неверные пути, быстрые клики) — без сбоев.', 'en': '• Automatic model updates: when a release brings new models they download in the background, are verified and replace the old ones (old files and caches are removed). On by default, can be turned off in Settings.\n• Protection against wrong input: texts in unsupported languages (Arabic, Chinese, Greek and others) get a clear message instead of a false verdict; a binary file renamed .txt is rejected; file errors are explained in plain words; Windows-1251 and UTF-16 files are read correctly; German and Ukrainian texts show a warning.\n• A one-page PDF summary for a teacher or editor: the verdict, what it means, the figures, the most suspicious sentences and a note that it is not proof.\n• 70 “silly” scenarios were tested (empty and huge texts, odd files, wrong paths, rapid clicks) with no failures.', 'pl': '• Automatyczna aktualizacja modeli: gdy wydanie przynosi nowe modele, są pobierane w tle, weryfikowane i zastępują stare (stare pliki i pamięć podręczna są usuwane). Domyślnie włączona, można wyłączyć w ustawieniach.\n• Ochrona przed błędnymi danymi: teksty w nieobsługiwanych językach (arabski, chiński, grecki i inne) dostają jasny komunikat zamiast fałszywego werdyktu; plik binarny z rozszerzeniem .txt jest odrzucany; błędy plików są wyjaśniane prostymi słowami; kodowania Windows-1251 i UTF-16 są czytane poprawnie; dla tekstu niemieckiego i ukraińskiego pokazywane jest ostrzeżenie.\n• Jednostronicowe zaświadczenie PDF dla nauczyciela lub redaktora: werdykt, jego znaczenie, liczby, najbardziej podejrzane zdania i zastrzeżenie, że to nie dowód.\n• Przetestowano 70 „głupich” scenariuszy (puste i ogromne teksty, dziwne pliki, błędne ścieżki, szybkie kliknięcia) bez awarii.'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.3.1 — Simple mode, a tour for beginners, models folder choice and “Check in Linda-Pro”', 'text': '• Simple mode by default: one screen, a verdict in plain words, warnings for unreliable cases (short text, mixed languages, many numbers) and “Most similar to AI”; the Detailed button brings all panels back.\n• A 3-step tour on first start (skippable; “Show the tips again” is in Settings).\n• Models folder: choose it in the installer, on first start and in Settings, with moving of the models already downloaded. Free space is checked before a download and a time estimate is shown.\n• The first check no longer waits: models are prepared in the background right after start; the header shows what computes; Settings has Check speed.\n• “Check in Linda-Pro” in the Explorer menu for .docx, .pdf, .txt, .md files (a checkbox in the installer), a Check clipboard button, and files can be dropped anywhere in the window.\n• Save diagnostics for a support e-mail: versions, graphics cards, logs, no checked texts.\n• 150% font, hints for terms, fixed light and high-contrast themes, the arrow of the Advanced block.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.1 — Простой режим, тур для новичков, выбор папки для моделей и «Проверить в Linda-Pro»', 'en': 'Linda-Pro 2.0.3.1 — Simple mode, a tour for beginners, models folder choice and “Check in Linda-Pro”', 'pl': 'Linda-Pro 2.0.3.1 — Tryb prosty, wprowadzenie dla początkujących, wybór folderu modeli i „Sprawdź w Linda-Pro”'}, 'text_i18n': {'ru': '• Простой режим по умолчанию: один экран, вердикт простыми словами, предупреждения о ненадёжных случаях (короткий текст, смесь языков, много цифр) и «Больше всего похожи на ИИ»; кнопка «Подробно» возвращает все панели.\n• Тур на 3 шага при первом запуске (можно пропустить; «Показать подсказки снова» — в настройках).\n• Папка для моделей: выбор в установщике, при первом запуске и в настройках, с переносом уже скачанных моделей. Перед скачиванием проверяется место на диске, показывается оценка времени.\n• Первая проверка больше не ждёт: модели готовятся в фоне сразу после запуска; в шапке видно, на чём считается; в настройках есть «Проверить скорость».\n• «Проверить в Linda-Pro» в меню проводника для файлов .docx, .pdf, .txt, .md (отметка в установщике), кнопка «Проверить буфер», файл можно перетащить в любое место окна.\n• «Сохранить диагностику» для письма в поддержку: версии, видеокарты, логи, без текстов проверок.\n• Шрифт 150%, подсказки к терминам, исправлены светлая и контрастная темы, стрелка у блока «Для опытных».', 'en': '• Simple mode by default: one screen, a verdict in plain words, warnings for unreliable cases (short text, mixed languages, many numbers) and “Most similar to AI”; the Detailed button brings all panels back.\n• A 3-step tour on first start (skippable; “Show the tips again” is in Settings).\n• Models folder: choose it in the installer, on first start and in Settings, with moving of the models already downloaded. Free space is checked before a download and a time estimate is shown.\n• The first check no longer waits: models are prepared in the background right after start; the header shows what computes; Settings has Check speed.\n• “Check in Linda-Pro” in the Explorer menu for .docx, .pdf, .txt, .md files (a checkbox in the installer), a Check clipboard button, and files can be dropped anywhere in the window.\n• Save diagnostics for a support e-mail: versions, graphics cards, logs, no checked texts.\n• 150% font, hints for terms, fixed light and high-contrast themes, the arrow of the Advanced block.', 'pl': '• Tryb prosty domyślnie: jeden ekran, werdykt prostymi słowami, ostrzeżenia o niepewnych przypadkach (krótki tekst, mieszane języki, dużo cyfr) i „Najbardziej przypominają AI”; przycisk Szczegółowy przywraca wszystkie panele.\n• Wprowadzenie w 3 krokach przy pierwszym uruchomieniu (można pominąć; „Pokaż wskazówki ponownie” w ustawieniach).\n• Folder modeli: wybór w instalatorze, przy pierwszym uruchomieniu i w ustawieniach, z przeniesieniem już pobranych modeli. Przed pobraniem sprawdzane jest miejsce na dysku i pokazywany szacowany czas.\n• Pierwsze sprawdzenie nie czeka: modele przygotowują się w tle zaraz po starcie; nagłówek pokazuje, na czym liczy program; w ustawieniach jest „Sprawdź szybkość”.\n• „Sprawdź w Linda-Pro” w menu Eksploratora dla plików .docx, .pdf, .txt, .md (pole wyboru w instalatorze), przycisk „Sprawdź schowek”, plik można upuścić w dowolnym miejscu okna.\n• „Zapisz diagnostykę” do wiadomości dla wsparcia: wersje, karty graficzne, logi, bez tekstów sprawdzeń.\n• Czcionka 150%, podpowiedzi do pojęć, poprawione motywy jasny i kontrastowy, strzałka bloku „Zaawansowane”.'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.3.0 — Simpler and clearer: progress bars, quick settings, automatic GPU choice', 'text': '• The settings window no longer hides under the top bar.\n• Automatic graphics-card choice is more reliable: a discrete card is recognised by its video memory and the most powerful one comes first.\n• Progress bars for file upload and reading, analysis, batch checks and document comparison.\n• The interface language switches with RU / PL / EN buttons in the header; settings got a gear icon; theme, font size and device choice moved to the left panel.\n• Analysis mode and model choice moved into a collapsible Advanced block, so the default screen is simpler.\n• The in-app change list shows only version numbers and titles with a link to the full list.\n• The Check for updates button moved to the updates section.', 'title_i18n': {'ru': 'Linda-Pro 2.0.3.0 — Проще и нагляднее: полосы прогресса, быстрые настройки, автовыбор видеокарты', 'en': 'Linda-Pro 2.0.3.0 — Simpler and clearer: progress bars, quick settings, automatic GPU choice', 'pl': 'Linda-Pro 2.0.3.0 — Prościej i czytelniej: paski postępu, szybkie ustawienia, automatyczny wybór karty'}, 'text_i18n': {'ru': '• Окно настроек больше не скрывается под верхней панелью.\n• Видеокарта выбирается автоматически надёжнее: дискретная карта определяется по объёму видеопамяти, самая мощная идёт первой.\n• Полосы прогресса при загрузке и чтении файла, анализе, пакетной проверке и сравнении документов.\n• Язык интерфейса переключается кнопками RU / PL / EN в шапке; у настроек появилась иконка шестерёнки; тема, размер шрифта и выбор устройства вынесены в левую панель.\n• Выбор режима и моделей убран в сворачиваемый блок «Для опытных»: по умолчанию экран проще.\n• Список изменений в программе показывает только номера и названия обновлений со ссылкой на полный список.\n• Кнопка «Проверить обновления» перенесена в раздел обновлений.', 'en': '• The settings window no longer hides under the top bar.\n• Automatic graphics-card choice is more reliable: a discrete card is recognised by its video memory and the most powerful one comes first.\n• Progress bars for file upload and reading, analysis, batch checks and document comparison.\n• The interface language switches with RU / PL / EN buttons in the header; settings got a gear icon; theme, font size and device choice moved to the left panel.\n• Analysis mode and model choice moved into a collapsible Advanced block, so the default screen is simpler.\n• The in-app change list shows only version numbers and titles with a link to the full list.\n• The Check for updates button moved to the updates section.', 'pl': '• Okno ustawień nie chowa się już pod górnym paskiem.\n• Automatyczny wybór karty graficznej jest pewniejszy: karta dyskretna jest rozpoznawana po pamięci wideo, najmocniejsza jest pierwsza.\n• Paski postępu przy wczytywaniu i odczycie pliku, analizie, sprawdzaniu wsadowym i porównywaniu dokumentów.\n• Język interfejsu przełączają przyciski RU / PL / EN w nagłówku; ustawienia mają ikonę koła zębatego; motyw, rozmiar czcionki i wybór urządzenia przeniesiono do lewego panelu.\n• Wybór trybu i modeli przeniesiono do zwijanego bloku „Zaawansowane”: domyślny ekran jest prostszy.\n• Lista zmian w programie pokazuje tylko numery i tytuły aktualizacji z linkiem do pełnej listy.\n• Przycisk „Sprawdź aktualizacje” przeniesiono do sekcji aktualizacji.'}},
    {'date': '2026-10-06', 'title': 'Linda-Pro 2.0.2.21 — New model ensemble 1.3: Russian, Polish and English', 'text': '• New 1.3 models (Essay and Multi, each merged from three trained variants) for all three languages. English now uses the same routed path as Russian and Polish, on shared models: switching language no longer reloads them.\n• Polish: on the main test set detection of AI text rose from 39% to 80% at 0.9% false flags (was 0.3%); Russian: 57% to 78% at the same 0.6% false flags; English: recent-model and humanized texts are caught noticeably more often (HumanizerBench 70% to 81%).\n• Honest limits: in English, false flags rose slightly on non-native writing (TOEFL exam essays: 4.4% to 6.6% on 91 texts) and on lightly edited human text. In Precise mode the same TOEFL essays give 1.1% false flags (1 of 91), at the cost of catching fewer English AI texts (HumanizerBench 69%). Use it for schools and universities.\n• The model package is about 4 GB; peak GPU memory is about 1.6 GB. The update does not delete old model folders.\nThe verdict threshold was frozen on development data; the website test sets were not used for selection.', 'title_i18n': {'ru': 'Linda-Pro 2.0.2.21 — Новый ансамбль моделей 1.3: русский, польский и английский', 'en': 'Linda-Pro 2.0.2.21 — New model ensemble 1.3: Russian, Polish and English', 'pl': 'Linda-Pro 2.0.2.21 — Nowy zespół modeli 1.3: rosyjski, polski i angielski'}, 'text_i18n': {'ru': '• Новые модели 1.3 (Essay и Multi, объединённые из трёх обученных вариантов) для всех трёх языков. Английский теперь идёт тем же путём, что русский и польский, на общих моделях: при смене языка они не перезагружаются.\n• Польский: на тестовом наборе обнаружение ИИ выросло с 39% до 80% при ложных 0,9% (было 0,3%); русский: с 57% до 78% при тех же 0,6% ложных; английский: свежие модели и «очеловеченные» тексты ловятся заметно чаще (HumanizerBench 70% → 81%).\n• Честно: на английском чуть выросли ложные срабатывания на текстах не носителей языка (экзаменационные эссе TOEFL: 4,4% → 6,6% на 91 тексте) и на «правленых людях». В режиме «Точный» те же эссе TOEFL дают 1,1% ложных (1 из 91), но английский ИИ ловится реже (HumanizerBench 69%). Для школ и вузов используйте его.\n• Пакет моделей около 4 ГБ; пик видеопамяти около 1,6 ГБ. Обновление не удаляет старые папки моделей.\nПорог вердикта заморожен по dev-данным; наборы сайта в подборе не участвовали.', 'en': '• New 1.3 models (Essay and Multi, each merged from three trained variants) for all three languages. English now uses the same routed path as Russian and Polish, on shared models: switching language no longer reloads them.\n• Polish: on the main test set detection of AI text rose from 39% to 80% at 0.9% false flags (was 0.3%); Russian: 57% to 78% at the same 0.6% false flags; English: recent-model and humanized texts are caught noticeably more often (HumanizerBench 70% to 81%).\n• Honest limits: in English, false flags rose slightly on non-native writing (TOEFL exam essays: 4.4% to 6.6% on 91 texts) and on lightly edited human text. In Precise mode the same TOEFL essays give 1.1% false flags (1 of 91), at the cost of catching fewer English AI texts (HumanizerBench 69%). Use it for schools and universities.\n• The model package is about 4 GB; peak GPU memory is about 1.6 GB. The update does not delete old model folders.\nThe verdict threshold was frozen on development data; the website test sets were not used for selection.', 'pl': '• Nowe modele 1.3 (Essay i Multi, każdy scalony z trzech wytrenowanych wariantów) dla wszystkich trzech języków. Angielski idzie teraz tą samą ścieżką co rosyjski i polski, na wspólnych modelach: zmiana języka nie przeładowuje ich.\n• Polski: na głównym zestawie testowym wykrywanie tekstu AI wzrosło z 39% do 80% przy 0,9% fałszywych alarmów (było 0,3%); rosyjski: z 57% do 78% przy tych samych 0,6%; angielski: teksty nowych modeli i „uczłowieczone” są wykrywane wyraźnie częściej (HumanizerBench 70% do 81%).\n• Uczciwie: w angielskim nieco wzrosły fałszywe alarmy na tekstach osób niebędących native speakerami (eseje TOEFL: 4,4% do 6,6% na 91 tekstach) i na lekko redagowanych tekstach ludzi. W trybie Dokładnym te same eseje TOEFL dają 1,1% fałszywych alarmów (1 z 91), ale angielski tekst AI jest wykrywany rzadziej (HumanizerBench 69%). Użyj go w szkołach i na uczelniach.\n• Pakiet modeli ma około 4 GB; szczyt pamięci GPU około 1,6 GB. Aktualizacja nie usuwa starych folderów modeli.\nPróg werdyktu zamrożono na danych deweloperskich; zestawy ze strony nie brały udziału w doborze.'}},
    {'date': '2026-10-04', 'title': 'Linda-Pro 2.0.2.20 — Data protection, PDF reports and blank-window fix', 'text': '• PDF reports now use the bundled renderer without Edge, Chrome or Brave. One A4 layout includes vector charts, structure map, metrics, annotated text and Unicode for English, Russian and Polish. Silent switching to the old exporter has been removed.\n• PDF/DOCX parsing runs in a separate Windows LPAC process with restricted file and network access. Limits remain: 20 seconds, 512 MiB, 20 MB input, 4 MB output and 500 PDF pages; DOCX entry count and expansion are bounded.\n• Current-user Windows DPAPI encrypts history. Existing records migrate into protected storage; writes are atomic and deletion respects retention policy.\n• Restart and page-refresh drafts also use DPAPI. New text is no longer stored in plaintext sessionStorage; legacy drafts migrate while preserving text.\n• The audit ledger uses an HMAC chain, independent checkpoint and recovery of interrupted writes. Manual clearing is disabled; organization retention policy controls storage.\n• Fixed the blank WebView2 window after minimizing: the surface repaints without reloading the page or losing input. The dark window background is retained.\n• An explicit PerMonitorV2 DPI manifest is included, with Windows long-path support for the temporary document worker.\n• DirectML checks the actual execution provider. Switching CPU/GPU releases previous sessions and refreshes device status.\n• Fixed isolated document-worker preparation and error handling: damaged documents do not block subsequent work or expose internal paths to users.\n• Background update download, hidden installation, automatic relaunch and unsaved-text recovery remain supported. The stable channel serves the normal Windows installer separately from Dev.\nModel weights, calibrations and commercial terms are unchanged.', 'title_i18n': {'ru': 'Linda-Pro 2.0.2.20 — Защита данных, PDF-отчёты и исправление белого окна', 'en': 'Linda-Pro 2.0.2.20 — Data protection, PDF reports and blank-window fix', 'pl': 'Linda-Pro 2.0.2.20 — Ochrona danych, raporty PDF i naprawa białego okna'}, 'text_i18n': {'ru': '• PDF-отчёты теперь строятся встроенной библиотекой без Edge, Chrome или Brave. Единая вёрстка A4 включает векторные диаграммы, карту структуры, метрики, отмеченный текст и Unicode для русского, английского и польского. Молчаливое переключение на старый экспортёр устранено.\n• PDF/DOCX разбираются отдельным процессом Windows LPAC с ограничениями доступа к файлам и сети. Сохраняются лимиты: 20 секунд, 512 МиБ, вход 20 МБ, результат 4 МБ, PDF до 500 страниц; для DOCX ограничены число элементов и распаковка.\n• История шифруется DPAPI текущего пользователя Windows. Существующие записи мигрируют в защищённое хранилище; запись выполняется атомарно, очистка учитывает политику хранения.\n• Черновики перезапуска и обновления страницы также защищены DPAPI. Новый текст не сохраняется открыто в sessionStorage; прежние черновики переносятся с сохранением текста.\n• Журнал аудита защищён цепочкой HMAC, отдельной контрольной точкой и восстановлением незавершённой записи. Ручная очистка отключена; журнал хранится согласно политике организации.\n• Исправлено белое окно WebView2 после сворачивания: поверхность перерисовывается без перезагрузки страницы и потери введённого текста. Сохранён тёмный фон окна.\n• Добавлен явный PerMonitorV2 DPI-манифест, сохранена поддержка длинных путей Windows для временного обработчика документов.\n• DirectML проверяет фактически используемый провайдер. При смене CPU/GPU освобождаются прежние сессии и обновляется статус устройства.\n• Исправлены подготовка изолированного обработчика документов и обработка его ошибок: повреждённые документы не блокируют последующую работу и не показывают внутренние пути пользователю.\n• Сохранены фоновое скачивание обновления, скрытая установка, повторное открытие программы и восстановление несохранённого текста. Основной канал предлагает обычный Windows-установщик, отдельно от Dev.\nВеса моделей, калибровки и коммерческие условия не менялись.', 'en': '• PDF reports now use the bundled renderer without Edge, Chrome or Brave. One A4 layout includes vector charts, structure map, metrics, annotated text and Unicode for English, Russian and Polish. Silent switching to the old exporter has been removed.\n• PDF/DOCX parsing runs in a separate Windows LPAC process with restricted file and network access. Limits remain: 20 seconds, 512 MiB, 20 MB input, 4 MB output and 500 PDF pages; DOCX entry count and expansion are bounded.\n• Current-user Windows DPAPI encrypts history. Existing records migrate into protected storage; writes are atomic and deletion respects retention policy.\n• Restart and page-refresh drafts also use DPAPI. New text is no longer stored in plaintext sessionStorage; legacy drafts migrate while preserving text.\n• The audit ledger uses an HMAC chain, independent checkpoint and recovery of interrupted writes. Manual clearing is disabled; organization retention policy controls storage.\n• Fixed the blank WebView2 window after minimizing: the surface repaints without reloading the page or losing input. The dark window background is retained.\n• An explicit PerMonitorV2 DPI manifest is included, with Windows long-path support for the temporary document worker.\n• DirectML checks the actual execution provider. Switching CPU/GPU releases previous sessions and refreshes device status.\n• Fixed isolated document-worker preparation and error handling: damaged documents do not block subsequent work or expose internal paths to users.\n• Background update download, hidden installation, automatic relaunch and unsaved-text recovery remain supported. The stable channel serves the normal Windows installer separately from Dev.\nModel weights, calibrations and commercial terms are unchanged.', 'pl': '• Raporty PDF używają teraz wbudowanego renderera bez Edge, Chrome ani Brave. Jeden układ A4 zawiera wykresy wektorowe, mapę struktury, metryki, oznaczony tekst i Unicode dla polskiego, angielskiego i rosyjskiego. Usunięto ciche przełączanie na stary eksport.\n• PDF/DOCX są odczytywane w osobnym procesie Windows LPAC z ograniczonym dostępem do plików i sieci. Limity: 20 sekund, 512 MiB, wejście 20 MB, wynik 4 MB, PDF do 500 stron; DOCX ma limity liczby elementów i rozpakowania.\n• DPAPI bieżącego użytkownika Windows szyfruje historię. Istniejące rekordy są migrowane do chronionego magazynu; zapis jest atomowy, a usuwanie uwzględnia retencję.\n• Szkice po restarcie i odświeżeniu strony również używają DPAPI. Nowy tekst nie jest zapisywany jawnie w sessionStorage; stare szkice są migrowane z zachowaniem tekstu.\n• Dziennik audytu używa łańcucha HMAC, osobnego punktu kontrolnego i odtwarzania przerwanych zapisów. Ręczne czyszczenie jest wyłączone; obowiązuje retencja organizacji.\n• Naprawiono białe okno WebView2 po minimalizacji: powierzchnia jest odrysowywana bez przeładowania strony i utraty tekstu. Zachowano ciemne tło okna.\n• Dodano jawny manifest PerMonitorV2 DPI oraz obsługę długich ścieżek Windows dla tymczasowego procesu dokumentów.\n• DirectML sprawdza rzeczywistego dostawcę wykonania. Zmiana CPU/GPU zwalnia poprzednie sesje i odświeża stan urządzenia.\n• Poprawiono przygotowanie izolowanego procesu dokumentów i błędy: uszkodzone dokumenty nie blokują dalszej pracy ani nie ujawniają wewnętrznych ścieżek.\n• Zachowano pobieranie aktualizacji w tle, ukrytą instalację, ponowne otwarcie aplikacji i odtwarzanie tekstu. Kanał stabilny udostępnia zwykły instalator Windows oddzielnie od Dev.\nWagi modeli, kalibracje i warunki komercyjne pozostają bez zmian.'}},
    {'date': '2026-10-04', 'title': 'Linda-Pro 2.0.2.17 — complete hotfix list', 'text': '• Background update download, hidden installation and automatic app relaunch; fixed the helper waiting indefinitely after a successful install.\n• Installer failure reopens the previous app, records the error and allows retry; failed packages are not automatically relaunched.\n• Unsaved text is restored after updating; temporary drafts are acknowledged and removed, respecting storage policies.\n• Duplicate update clicks are blocked, notes match the offered version, and restart is blocked during analysis, queued work or document parsing.\n• Package signature, size, version and checksum are verified. Failed model updates roll back changed, added and deleted files with the manifest; fixed open-file handling on Windows.\n• Cancellation belongs to a job and tab, covering early cancellation, page reload and disconnect. Cancelled results are not stored in history.\n• PDF/DOCX use a separate process: 20-second timeout, 512 MiB memory cap, 20 MB input, 4 MB output, PDF up to 500 pages; DOCX entry and expansion limits. Parsing keeps HTTP responsive.\n• Late uploads cannot overwrite newer input; damaged documents fail without blocking subsequent work.\n• Legacy single mode executes only the selected model. CPU voters load on demand, with optional preload.\n• Single verdict/probability agree with history and JSON/CSV/HTML exports, including model and analysis scope.\n• Stylo without sentence evidence no longer displays NaN, fabricated authorship shares or a human-authorship claim. Missing scores and text analytics without labels are handled correctly.\n• Uncertain sentences are not exported as explicit AI signals. Missing highlighting does not establish human authorship.\n• Precise mode requires the full ensemble; UI resets incompatible choices and API rejects them before model loading. Routed calibration supports the full ensemble.\n• Editing text, mode or model invalidates stale results. Fixed human-verdict confidence, zero scores, history percentages and opening history records.\n• Atomic settings; Origin/Host and iframe protections; CSV formula escaping; storage/export/folder/licence policies respected.\n• Metro UI: flat colours, square corners, keyboard focus and reduced motion. History / Batch / Compare centred on the window, using a separate row on narrow windows.\n• Status polling has a timeout; translations no longer redraw continually; update errors avoid blocking dialogs.\n• Website mobile menu closes on Escape, navigation and outside clicks; full release notes added.\nWeights and calibrations are unchanged.', 'title_i18n': {'ru': 'Linda-Pro 2.0.2.17 — Обновления, документы, одиночные модели и Metro UI', 'en': 'Linda-Pro 2.0.2.17 — Updates, documents, single models and Metro UI', 'pl': 'Linda-Pro 2.0.2.17 — Aktualizacje, dokumenty, pojedyncze modele i Metro UI'}, 'text_i18n': {'ru': '• Скачивание обновления в фоне, скрытая установка и автоматическое повторное открытие программы; исправлено зависание помощника после успешной установки.\n• После отказа установщика открывается предыдущая версия, сохраняется ошибка и доступна повторная попытка; отказный пакет не запускается снова автоматически.\n• Несохранённый текст восстанавливается после обновления; временный черновик удаляется после подтверждения, учитываются запреты хранения.\n• Повторные клики обновления блокируются; заметки относятся к предлагаемой версии. Перезапуск запрещён при анализе, очереди и разборе документа.\n• Проверяются подпись, размер, версия и хеш пакета. При ошибке обновления моделей откатываются изменённые, добавленные и удалённые файлы вместе с манифестом; исправлены открытые файлы Windows.\n• Отмена привязана к заданию и вкладке, включая раннюю отмену, перезагрузку страницы и разрыв связи. Отменённый результат не сохраняется в историю.\n• PDF/DOCX разбираются в отдельном процессе: 20 секунд, 512 МиБ, вход 20 МБ, результат 4 МБ, PDF до 500 страниц; ограничены число файлов и распаковка DOCX. Интерфейс остаётся доступен при разборе.\n• Поздний ответ загрузки не подменяет новый ввод; повреждённые документы дают ошибку и позволяют продолжить работу.\n• Одиночный legacy-режим запускает только выбранную модель. CPU загружает голоса по требованию; предварительная загрузка остаётся отдельной настройкой.\n• Одиночный вердикт и вероятность согласованы с историей и JSON/CSV/HTML-отчётами; экспорт указывает выбранную модель и область анализа.\n• Stylo без подсветки не показывает NaN, выдуманные доли или ложное утверждение о человеческом авторстве. Исправлены пустые scores и текстовая аналитика без меток.\n• Неопределённые предложения не экспортируются как явные ИИ-сигналы. Отсутствие подсветки не подтверждает человеческое авторство.\n• Точный режим доступен только с полным ансамблем; интерфейс сбрасывает несовместимый выбор, API отклоняет его до загрузки моделей. Routed поддерживает полный ансамбль.\n• Старый результат сбрасывается после изменения текста, режима или модели. Исправлены уверенность вердикта «человек», нулевой score, проценты и открытие истории.\n• Настройки сохраняются атомарно; усилены проверки Origin/Host и защита от iframe. CSV защищён от формул; соблюдаются политики истории, экспорта, папок и лицензии.\n• Metro UI: плоские цвета, прямые углы, клавиатурный фокус, reduced-motion. История / Пакет / Сравнение расположены по центру окна, на узком окне — отдельной строкой.\n• Опрос состояния имеет таймаут, переводы не перерисовываются постоянно, ошибки обновления показаны без блокирующего окна.\n• На сайте мобильное меню закрывается по Escape, выбору раздела и клику снаружи; добавлен полный список изменений.\nВеса и калибровки не менялись.', 'en': '• Background update download, hidden installation and automatic app relaunch; fixed the helper waiting indefinitely after a successful install.\n• Installer failure reopens the previous app, records the error and allows retry; failed packages are not automatically relaunched.\n• Unsaved text is restored after updating; temporary drafts are acknowledged and removed, respecting storage policies.\n• Duplicate update clicks are blocked, notes match the offered version, and restart is blocked during analysis, queued work or document parsing.\n• Package signature, size, version and checksum are verified. Failed model updates roll back changed, added and deleted files with the manifest; fixed open-file handling on Windows.\n• Cancellation belongs to a job and tab, covering early cancellation, page reload and disconnect. Cancelled results are not stored in history.\n• PDF/DOCX use a separate process: 20-second timeout, 512 MiB memory cap, 20 MB input, 4 MB output, PDF up to 500 pages; DOCX entry and expansion limits. Parsing keeps HTTP responsive.\n• Late uploads cannot overwrite newer input; damaged documents fail without blocking subsequent work.\n• Legacy single mode executes only the selected model. CPU voters load on demand, with optional preload.\n• Single verdict/probability agree with history and JSON/CSV/HTML exports, including model and analysis scope.\n• Stylo without sentence evidence no longer displays NaN, fabricated authorship shares or a human-authorship claim. Missing scores and text analytics without labels are handled correctly.\n• Uncertain sentences are not exported as explicit AI signals. Missing highlighting does not establish human authorship.\n• Precise mode requires the full ensemble; UI resets incompatible choices and API rejects them before model loading. Routed calibration supports the full ensemble.\n• Editing text, mode or model invalidates stale results. Fixed human-verdict confidence, zero scores, history percentages and opening history records.\n• Atomic settings; Origin/Host and iframe protections; CSV formula escaping; storage/export/folder/licence policies respected.\n• Metro UI: flat colours, square corners, keyboard focus and reduced motion. History / Batch / Compare centred on the window, using a separate row on narrow windows.\n• Status polling has a timeout; translations no longer redraw continually; update errors avoid blocking dialogs.\n• Website mobile menu closes on Escape, navigation and outside clicks; full release notes added.\nWeights and calibrations are unchanged.', 'pl': '• Pobieranie aktualizacji w tle, ukryta instalacja i ponowne otwarcie aplikacji; usunięto zawieszanie pomocnika po instalacji.\n• Błąd instalatora przywraca poprzednią aplikację, zapisuje komunikat i pozwala ponowić próbę; błędny pakiet nie uruchamia się automatycznie.\n• Przywracanie niezapisanego tekstu po aktualizacji; tymczasowy szkic jest usuwany po potwierdzeniu, z uwzględnieniem zasad przechowywania.\n• Blokada powtórnych kliknięć, informacje dla oferowanej wersji oraz blokada restartu podczas analizy, kolejki i odczytu dokumentu.\n• Weryfikacja podpisu, rozmiaru, wersji i sumy pakietu. Nieudana aktualizacja modeli cofa zmienione, dodane i usunięte pliki wraz z manifestem; poprawiono otwarte pliki Windows.\n• Anulowanie przypisane do zadania i karty, także przed rejestracją, przy odświeżeniu i utracie połączenia. Anulowany wynik nie trafia do historii.\n• PDF/DOCX w osobnym procesie: 20 sekund, 512 MiB, wejście 20 MB, wynik 4 MB, PDF do 500 stron; limity liczby plików i rozpakowania DOCX. Serwer pozostaje dostępny.\n• Spóźniony wynik wczytania nie zastępuje nowego tekstu; uszkodzony dokument nie blokuje dalszej pracy.\n• Tryb pojedynczy legacy uruchamia wybrany model. Modele CPU ładowane na żądanie; opcjonalne ładowanie wstępne pozostaje dostępne.\n• Wynik i prawdopodobieństwo pojedynczego modelu zgodne z historią oraz JSON/CSV/HTML; eksport zawiera model i zakres analizy.\n• Stylo bez podświetlenia nie pokazuje NaN, wymyślonych udziałów ani twierdzenia o ludzkim autorstwie. Poprawiono brakujące wyniki i analizę zdań bez etykiet.\n• Niepewne zdania nie są eksportowane jako wyraźne sygnały AI; brak podświetlenia nie potwierdza ludzkiego autorstwa.\n• Tryb precyzyjny wymaga wszystkich modeli; interfejs resetuje niezgodny wybór, API odrzuca go przed ładowaniem. Routed obsługuje pełny zespół.\n• Zmiana tekstu, trybu lub modelu usuwa nieaktualny wynik; poprawiono pewność wyniku ludzkiego, zera, procenty i otwieranie historii.\n• Atomowy zapis ustawień, ochrona Origin/Host i iframe, zabezpieczenie CSV przed formułami oraz zasady historii, eksportu, katalogów i licencji.\n• Metro UI: płaskie kolory, prostokątne elementy, fokus klawiatury i ograniczony ruch. Historia / Pakiet / Porównanie na środku okna, w osobnym wierszu przy małej szerokości.\n• Limit czasu odpytywania stanu, brak ciągłego odrysowywania tłumaczeń, błędy aktualizacji bez blokującego okna.\n• Menu mobilne strony zamyka się klawiszem Escape, wyborem sekcji i kliknięciem poza nim; pełna lista zmian na stronie.\nWagi i kalibracje bez zmian.'}},
    {"date": "2026-10-03", "title": "Windows app 2.0.2: one-click update and working report export (2.0.0 and 2.0.1 need a manual install)",
     "text": "2.0.1 fixed the export buttons (PDF, HTML, CSV, JSON, Markdown), which did nothing in the app window; 2.0.2 fixes the in-app update: after the download a Restart and update button appears and the app installs the new version by itself. "
             "If you have 2.0.0 or 2.0.1, the update button in those versions cannot install anything: please download Linda-Setup.exe from the latest GitHub release once and run it over your current copy (history, settings and models are kept). From 2.0.2 on, updates work from inside the app."},
    {"date": "2026-10-03", "title": "Windows app 2.0: PDF reports, updates without reinstalling, Russian and Polish interface",
     "text": "What is new: a PDF report with charts (probability along the text, authorship shares, where the text sits against human and AI samples, structure map), "
             "plus HTML, CSV and JSON exports; updates download in the background and apply after a restart, with rollback if something goes wrong; "
             "the interface in Russian, Polish and English; appearance settings (theme, accent, density, font size, corners); "
             "for organizations: batch check of a whole folder, an audit log and policies in enterprise.json. The word and character counter is fixed. "
             "The models are unchanged (version 1.1). Version 1.x updates itself from inside the app."},
    {"date": "2026-10-03", "title": "Windows app 1.2.1: the colour map now agrees with the verdict",
     "text": "Fix for version 1.2: on polished AI texts the verdict said AI while the sentences were all coloured as human, because one sentence is too short for the models on its own. "
             "Now every sentence is scored alone and in its context (about 120 words around it) and the higher score counts, so a whole AI text is shown as AI and a lone strongly-AI sentence still stands out. "
             "On our test texts 64-78% of the sentences of AI texts are marked AI and another 18-23% possibly AI, against 0% AI and 2% possibly-AI for human texts. The thresholds for AI and possibly-AI now come from the program itself, "
             "so the main window and the full reader always show the same colours. The models are unchanged. Versions 1.1.x and 1.2.0 update themselves from inside the app."},
    {"date": "2026-10-02", "title": "Windows app 1.2: history with folders, batch check, document comparison, text structure",
     "text": "What is new: "
             "(1) History kept only on your computer: every check is saved with its text and result; folders (drag a row onto a folder), search, sorting, bulk delete, automatic clean-up after 30, 90 or 365 days, switch it off any time. "
             "(2) Batch check: drop any number of PDF, DOCX, TXT or MD files and they are checked one after another, with CSV export. "
             "(3) Document comparison: two versions side by side with the passages they share (8+ identical words) and how the AI colouring changed; or an overlap matrix across many documents. "
             "(4) Full reader: open any saved check or compared document in the full analysis view and go back to the list. "
             "(5) Authorship verdict: human, mixed or AI, with shares of AI, possibly-AI and human text. "
             "(6) Text analytics and structure: sentence rhythm, lexical diversity, stock phrases, repeated phrases, an AI-probability strip along the text, a paragraph map and a violin plot of sentence scores against human and AI references. "
             "(7) Every sentence is scored on its own again (single AI sentences among human ones are visible), the possibly-AI band starts lower, and flat Metro animations. "
             "Everything still runs on your PC; nothing is uploaded. Limits: sentence-level detection is about 70-75% accurate, weaker than whole-text detection, and the structure view describes a text but is not part of the verdict. Version 1.1.x installs update themselves from inside the app."},
    {"date": "2026-10-01", "title": "Windows app 1.1.2: GPU acceleration for AMD, NVIDIA and Intel graphics cards",
     "text": "The app now runs the models on any DirectX 12 graphics card through DirectML, with no CUDA or ROCm installation: 8-12 times faster than the CPU on our test PC (AMD Radeon RX 9070 XT: 0.3 s for 1,000 words instead of 3.5 s), identical verdicts. "
             "Automatic mode uses a discrete card; the first start prepares the GPU models once (about a minute). Choosing GPU on a PC without a usable card no longer breaks the app: it falls back to the CPU."},
    {"date": "2026-10-01", "title": "Windows app 1.1.1: sharper colour map, faster start, licence keys",
     "text": "The colour map now follows sliding windows of about 300 words, so the boundary between human and AI-written passages is accurate to roughly 100 words, and the Multi view no longer stays green. "
             "The models can load right at start-up (Settings; turn it off and you get a warning that the first analysis will be slower). New Metro-style look for the app and the online demo. "
             "Licence keys are tied to the computer they are activated on and can be moved with Remove key; complimentary keys work offline. Version 1.1.0 installs update themselves from inside the app."},
    {"date": "2026-10-01", "title": "Linda-Pro 1.1: retrained against AI humanizers",
     "text": "The three detectors were retrained on real outputs of AI humanizer tools. On the public HumanizerBench set (not used for training) the share of humanized texts flagged as AI rose from 31% to 70%; false flags on TOEFL exam essays fell from 8.8% to 4.4%. The technical report (DOI 10.5281/zenodo.23261670) lists the data, tests and caveats."},
    {"date": "2026-10-01", "title": "Technical report for version 1.1 published",
     "text": "Data, evaluation and limitations of Linda-Pro 1.1 are described in an open technical report on Zenodo."},
]


def release_strip(t):
    return f'<aside class="wrap release-strip"><div><span class="release-kicker">{S(t,"updates_current")} · 17.10.2026</span><strong>Linda 2.0.6.2</strong><p>{S(t,"updates_summary")}</p></div><a class="release-link" href="{FILES["updates"][I18N_LANG]}">{S(t,"updates_full")} <span aria-hidden="true">→</span></a></aside>'

def notes_content(text):
    lines=text.splitlines()
    bullets=[line[2:] for line in lines if line.startswith('• ')]
    other=[line for line in lines if line and not line.startswith('• ')]
    if bullets:
        return '<ul class="release-changes">'+''.join('<li>'+escape(line)+'</li>' for line in bullets)+'</ul>'+''.join('<p>'+escape(line)+'</p>' for line in other)
    return '<p>'+escape(text)+'</p>'

def updates_body(t):
    current=NEWS[0]
    latest=(current.get('text_i18n') or {}).get(I18N_LANG,current['text'])
    archive=''.join('<details class="release-archive"><summary><time>'+escape(n['date'])+'</time><span>'+escape((n.get('title_i18n') or {}).get(I18N_LANG,n['title']))+'</span></summary>'+notes_content((n.get('text_i18n') or {}).get(I18N_LANG,n['text']))+'</details>' for n in NEWS[1:])
    return f'<section class="release-page"><div class="wrap"><h1>{S(t,"updates_title")}</h1><p class="sub">{S(t,"updates_intro")}</p><article class="release-current"><div class="release-heading"><div><span class="release-kicker">{S(t,"updates_current")}</span><h2>2.0.6.2</h2><time datetime="2026-10-17">17.10.2026</time></div><a class="btn acc" href="https://github.com/Lendarixon/Linda/releases/latest/download/Linda-Setup.exe">{S(t,"updates_download")}</a></div><p class="release-summary">{S(t,"updates_summary")}</p><details class="release-details"><summary>{S(t,"updates_full")}</summary>{notes_content(latest)}</details></article><h2 class="archive-title">{S(t,"updates_archive")}</h2><p class="note">{S(t,"news_en_note")}</p>{archive}</div></section>'


I18N = {}
I18N_LANG = "en"

if __name__ == "__main__":
    I18N.update(load_i18n())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "site.css").write_text(CSS, encoding="utf-8")
    built = []
    for lang in LANGS:
        I18N_LANG = lang
        t = I18N[lang]
        pages = (("trust", S(t,"trust_title"), S(t,"trust_title"), trust_body(t, lang)),
                 ("updates", S(t,"updates_title"), S(t,"updates_intro"), updates_body(t)),
                 ("index", S(t, "meta_title"), S(t, "meta_desc"), index_body(t)),
                 ("results", S(t, "page_results_title"), S(t, "meta_desc"), results_body(t)),
                 ("business", S(t, "page_business_title"), S(t, "meta_desc"), business_body(t)),
                 ("faq", S(t, "page_faq_title"), S(t, "meta_desc"), faq_body(t)),
                 ("developers", S(t, "page_dev_title"), S(t, "meta_desc"), developers_body(t)),
                 ("memo", S(t, "page_memo_title"), S(t, "meta_desc"), memo_body(t)),
                 ("terms", S(t, "terms_title"), S(t, "terms_title"), terms_body(t)),
                 ("privacy", S(t, "priv_title"), S(t, "priv_title"), privacy_body(t)),
                 ("refund", S(t, "ref_title"), S(t, "ref_title"), refund_body(t)),
                 ("licensing", S(t, "licpage_title"), S(t, "licpage_title"), licensing_body(t, lang))) + ((("versions", S(t, "ver_page_h"), S(t, "ver_page_sub"), versions_body(t)),) if LITE else ())
        for slug, title, desc, body in pages:
            (OUT / FILES[slug][lang]).write_text(page(lang, slug, title, desc, body), encoding="utf-8")
            built.append(FILES[slug][lang])
    for name in ("LICENSING.md", "LICENSING.ru.md", "LICENSING.pl.md"):
        (OUT / name).write_text((ROOT / "content" / name).read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "news.json").write_text(json.dumps(NEWS, indent=1, ensure_ascii=False), encoding="utf-8")
    urls = sorted({f"{SITE}/{fn}" for d in FILES.values() for fn in d.values()})
    sm = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    (OUT / "sitemap.xml").write_text(sm, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    for n in ["linda.png", "logo_wordmark.png", "logo_square.png", "og_image.png"] + [f"shot-{k}-{l}.png" for k in ("app", "report") for l in ("en", "ru", "pl")]:
        shutil.copy2(ROOT / "assets" / n, OUT / "assets" / n)
    for n in STATIC_ARTIFACTS:
        shutil.copy2(ROOT / "static" / n, OUT / n)
    print("site built:", OUT, f"({len(built)} pages: " + ", ".join(built) + ")")
