# -*- coding: utf-8 -*-
"""Светлая тема: поверхности Metro-оформления были жёстко тёмными (#171a22 !important), текст же брался из светлой палитры — выходил нечитаемым."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "web" / "index.html"
t = P.read_text(encoding="utf-8")
MARK = "/* СВЕТЛАЯ ТЕМА: поверхности */"
if MARK in t:
    raise SystemExit("already patched")
CSS = MARK + """
html[data-theme="light"] .input-box,html[data-theme="light"] .heatmap-card,html[data-theme="light"] .verdict-box,html[data-theme="light"] .voters-card{background:var(--bg-card)!important}
html[data-theme="light"] textarea{color:var(--text)!important}
html[data-theme="light"] .stat-pill,html[data-theme="light"] .model-card:not(.active){background:var(--bg-elevated)!important;color:var(--text)}
html[data-theme="light"] .model-card:not(.active) .tag{color:var(--text)!important;background:rgba(20,24,33,.1)!important}
html[data-theme="light"] .lp-link,html[data-theme="light"] .lp-link:hover{color:#0b5aa6}
html[data-theme="light"] .sv-warn,html[data-theme="light"] .dev-warn{color:#a04a00}
html[data-theme="light"] .sv-why q span{color:#c4202f}
html[data-theme="light"] .lp-lic-note,html[data-theme="light"] .lp-lic-note *{color:#4a5262!important}
html[data-theme="light"] ::-webkit-scrollbar-track{background:#dfe5ef}html[data-theme="light"] ::-webkit-scrollbar-thumb{background:#aab4c6}
html[data-theme="light"] .tour-card{background:#fff}
"""
t = t.replace("</style>\n</head>", CSS + "</style>\n</head>", 1)
P.write_text(t, encoding="utf-8")
print("ok")
# (дополнение: блок «ТЕМЫ: доп. контраст» добавлен отдельным шагом прямо в index.html)
