# -*- coding: utf-8 -*-
"""Builds the unlisted CV page: cv.html (EN, default), cv-ru.html, cv-pl.html.

The page reuses linda.css and suite.js, so it keeps the site's Metro look, but it has
no product navigation and is marked noindex: it is reachable by direct link only and
is never added to the sitemap or to any page's navigation.

    python tools/build_cv.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAIL = "v.manzyuk@student.uw.edu.pl"
MISES = "https://mises.org/profile/vladyslav-manzyuk"
GH = "https://github.com/Lendarixon"
LINDA = "https://github.com/Lendarixon/Linda"
PROBE = "https://github.com/Lendarixon/Linda-Probe"
FILES = {"en": "cv.html", "ru": "cv-ru.html", "pl": "cv-pl.html"}
CSS_V = "19eb33cd1d"
JS_V = "ffbea9073a"

CSS = """
/* ---------- CV page: same tokens as the site, no product navigation ---------- */
.cv-header .header-controls{margin-left:auto}
.cv-tag{font-size:.6875rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);padding-left:var(--s4);border-left:1px solid var(--line);white-space:nowrap}
.cv-main>section{margin:0 0 var(--s7)}
.cv-hero{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:var(--s7);align-items:start;padding:var(--s7) 0 0}
.cv-hero h1{font-family:var(--font-display);font-size:clamp(2.6rem,1.5rem + 3.6vw,4.6rem);font-weight:300;line-height:1.02;letter-spacing:-.04em;margin:0}
.cv-role{font-size:1.125rem;line-height:1.55;color:var(--muted);max-width:44ch;margin:var(--s4) 0 var(--s5)}
.cv-meta{display:flex;flex-wrap:wrap;gap:var(--s2) var(--s4);margin:0 0 var(--s5);font-size:.875rem;color:var(--muted)}
.cv-meta span{display:inline-flex;align-items:center;gap:6px}
.cv-meta a{color:var(--muted);text-decoration:underline;text-underline-offset:3px}
.cv-meta a:hover{color:var(--ink)}
.cv-actions{display:flex;flex-wrap:wrap;align-items:center;gap:var(--s3) var(--s4)}
.cv-focus{margin:var(--s5) 0 0;padding-top:var(--s4);border-top:1px solid var(--line);font-size:.8125rem;line-height:1.5;letter-spacing:.02em;color:var(--muted);max-width:46ch}
.cv-wall{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.cv-tile{position:relative;display:flex;flex-direction:column;gap:var(--s2);min-height:150px;padding:16px;background:var(--tone);color:#fff;overflow:hidden}
.cv-tile .k{font-size:.6875rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;opacity:.85}
.cv-tile .n{font-family:var(--font-display);font-size:clamp(1.9rem,1.4rem + 1.3vw,2.75rem);font-weight:300;line-height:1;letter-spacing:-.03em}
.cv-tile .t{margin-top:auto;font-size:.75rem;line-height:1.4;opacity:.92}
.cv-prose p{font-size:1.0625rem;line-height:1.7;color:var(--muted);max-width:var(--measure);margin:0 0 var(--s4)}
.cv-prose p:last-child{margin-bottom:0}
.cv-prose strong{color:var(--ink);font-weight:600}
.cv-panel{background:var(--surface);border:1px solid var(--line);padding:var(--s5);display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:var(--s6)}
.cv-panel h3{font-size:1.375rem;font-weight:400;margin:0 0 var(--s2)}
.cv-panel .sub{font-size:.9375rem;color:var(--muted);margin:0 0 var(--s4)}
.cv-panel .deg{font-size:1rem;line-height:1.55;margin:0 0 var(--s2)}
.cv-panel .gpa{font-size:.9375rem;color:var(--muted);margin:0}
.cv-areas{list-style:none;margin:0;padding:0}
.cv-areas li{font-size:.9375rem;line-height:1.5;color:var(--muted);padding:9px 0;border-bottom:1px solid var(--line)}
.cv-areas li:first-child{padding-top:0}
.cv-areas li:last-child{border-bottom:0;padding-bottom:0}
.cv-awards{border-top:1px solid var(--line);margin-top:var(--s2)}
.cv-award{display:grid;grid-template-columns:92px minmax(0,1fr);gap:var(--s5);padding:var(--s5) 0;border-bottom:1px solid var(--line)}
.cv-award .yr{font-family:var(--font-display);font-size:1.5rem;font-weight:300;line-height:1.1;color:var(--muted)}
.cv-award .place{display:block;font-size:.6875rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:0 0 var(--s2)}
.cv-award h3{font-size:1.25rem;font-weight:400;line-height:1.3;margin:0 0 var(--s2);max-width:52ch}
.cv-award .org{font-size:.9375rem;line-height:1.5;color:var(--muted);max-width:70ch}
.cv-award p{margin:var(--s2) 0 0;font-size:.9375rem;line-height:1.55;color:var(--muted);max-width:70ch}
.cv-award .pub{color:var(--ink)}
.cv-pubs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap)}
.cv-pub{position:relative;display:flex;flex-direction:column;gap:var(--s2);padding:var(--s5);background:var(--surface);border:1px solid var(--line);text-decoration:none;color:var(--ink);min-height:170px}
.cv-pub::before{content:"";position:absolute;left:-1px;right:-1px;top:-1px;height:3px;background:var(--id-blue)}
.cv-pub:hover{border-color:var(--line-strong);text-decoration:none}
.cv-pub .d{font-size:.75rem;color:var(--muted)}
.cv-pub .ti{font-family:var(--font-display);font-size:1.375rem;font-weight:300;line-height:1.25;letter-spacing:-.015em}
.cv-pub .src{margin-top:auto;font-size:.8125rem;color:var(--muted);display:flex;align-items:center;gap:var(--s2)}
.cv-pub .src::after{content:"\\2197"}
.cv-more{margin:var(--s4) 0 0;font-size:.9375rem}
.cv-journals{border-top:1px solid var(--line);margin-top:var(--s6)}
.cv-jrow{display:grid;grid-template-columns:88px minmax(0,1fr) 190px;gap:var(--s4);padding:var(--s4) 0;border-bottom:1px solid var(--line);font-size:.9375rem;line-height:1.5}
.cv-jrow .v{color:var(--muted)}
.cv-jrow .s{color:var(--muted);text-align:right}
.cv-projects{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap)}
.cv-project{position:relative;display:flex;flex-direction:column;gap:var(--s3);padding:var(--s5);background:var(--surface);border:1px solid var(--line);text-decoration:none;color:var(--ink);min-height:230px}
.cv-project::before{content:"";position:absolute;left:-1px;right:-1px;top:-1px;height:3px;background:var(--tone)}
.cv-project:hover{border-color:var(--line-strong);text-decoration:none}
.cv-project .head{display:flex;align-items:center;gap:var(--s3)}
.cv-project h3{font-size:1.25rem;font-weight:400;margin:0}
.cv-project p{margin:0;font-size:.9375rem;line-height:1.6;color:var(--muted)}
.cv-project .go{margin-top:auto;font-size:.8125rem;color:var(--muted);display:flex;align-items:center;gap:var(--s2)}
.cv-project .go::after{content:"\\2197"}
.cv-inside{margin:var(--gap) 0 0;padding:var(--s5);background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--id-violet)}
.cv-inside h3{font-size:1rem;font-weight:600;margin:0 0 var(--s2)}
.cv-inside p{margin:0;font-size:.9375rem;line-height:1.6;color:var(--muted);max-width:80ch}
.cv-inside a{color:var(--accent);text-decoration:none}
.cv-inside a:hover{text-decoration:underline;text-underline-offset:3px}
.cv-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--gap)}
.cv-list{list-style:none;margin:0;padding:0}
.cv-list li{display:flex;justify-content:space-between;gap:var(--s4);font-size:.9375rem;line-height:1.5;padding:10px 0;border-bottom:1px solid var(--line)}
.cv-list li:last-child{border-bottom:0;padding-bottom:0}
.cv-list .lv{color:var(--muted);text-align:right;flex:none}
.cv-note{margin:var(--gap) 0 0;padding:var(--s5);background:var(--surface);border:1px solid var(--line);font-size:.9375rem;line-height:1.6;color:var(--muted);max-width:90ch}
.cv-note b{color:var(--ink);font-weight:600}
.cv-footer .cv-foot-note{font-size:.75rem;color:var(--muted);max-width:52ch}
@media(max-width:1000px){
  .cv-hero{grid-template-columns:minmax(0,1fr);gap:var(--s6);padding-top:var(--s6)}
  .cv-wall{grid-template-columns:repeat(4,minmax(0,1fr))}
  .cv-tile{min-height:132px;padding:12px}
  .cv-panel{grid-template-columns:minmax(0,1fr);gap:var(--s5)}
}
@media(max-width:760px){
  .cv-wall{grid-template-columns:repeat(2,minmax(0,1fr))}
  .cv-pubs,.cv-projects,.cv-two{grid-template-columns:minmax(0,1fr)}
  .cv-award{grid-template-columns:64px minmax(0,1fr);gap:var(--s4)}
  .cv-award .yr{font-size:1.25rem}
  .cv-jrow{grid-template-columns:64px minmax(0,1fr);gap:var(--s2) var(--s4)}
  .cv-jrow .s{grid-column:2;text-align:left}
  .cv-tag{display:none}
}
@media(max-width:520px){
  .cv-tile .n{font-size:1.6rem}
  .cv-tile .t{font-size:.6875rem}
  .cv-tile{min-height:118px}
  .cv-actions .button{width:100%}
}
@media print{
  html,html[data-theme]{--bg:#fff;--surface:#fff;--raised:#f4f4f4;--ink:#111;--muted:#3d3d3d;--line:#c9c9c9;--line-strong:#555;--accent:#111}
  .suite-header,.suite-footer,.cv-actions,.cv-focus,.skip-link{display:none!important}
  body{background:#fff;color:#111;font-size:9.4pt;line-height:1.45}
  .cv-main{padding:0;max-width:none}
  .cv-hero{padding-top:0;grid-template-columns:minmax(0,1.5fr) minmax(0,.5fr);gap:18px}
  .cv-hero h1{font-size:26pt;line-height:1}
  .cv-role{font-size:10pt;margin:8px 0 10px}
  .cv-meta{font-size:8.4pt;margin-bottom:0}
  .cv-main>section{margin-bottom:13px}
  .section-heading{margin-bottom:8px}
  .section-heading h2{font-size:15pt}
  .eyebrow{font-size:7.4pt;margin-bottom:4px}
  .cv-prose p{font-size:9.4pt;line-height:1.45;margin-bottom:6px}
  .cv-award{padding:9px 0;grid-template-columns:70px minmax(0,1fr);gap:14px}
  .cv-award .yr{font-size:11pt}
  .cv-award h3{font-size:10.5pt}
  .cv-award .org,.cv-award p{font-size:8.8pt;line-height:1.4;margin-top:4px}
  .cv-pub{padding:10px;min-height:0}
  .cv-pub .ti{font-size:11pt}
  .cv-pub .d,.cv-pub .src{font-size:8pt}
  .cv-pubs{gap:8px}
  .cv-jrow{padding:6px 0;font-size:8.8pt}
  .cv-more{margin-top:6px;font-size:8.8pt}
  .cv-journals{margin-top:8px}
  .cv-project{padding:10px;min-height:0;gap:6px}
  .cv-project h3{font-size:11pt}
  .cv-project p{font-size:8.8pt;line-height:1.4}
  .cv-project .go{font-size:8pt}
  .cv-inside,.cv-note{padding:9px 11px;font-size:8.6pt;line-height:1.45;margin-top:8px}
  .cv-list li{font-size:8.8pt;padding:4px 0}
  .cv-panel{padding:11px;gap:16px}
  .cv-panel h3{font-size:11pt}
  .cv-panel .sub,.cv-panel .gpa{font-size:8.6pt}
  .cv-panel .deg{font-size:8.8pt}
  .cv-areas li{font-size:8.6pt;padding:3px 0}
  .cv-tile{background:#eee!important;color:#111!important;min-height:0;padding:8px;gap:2px}
  .cv-tile .k{font-size:6.6pt;opacity:1;color:#333}
  .cv-tile .n{font-size:15pt}
  .cv-tile .t{font-size:6.8pt;opacity:1;color:#333;line-height:1.3}
  .cv-wall{gap:5px}
  .cv-award,.cv-pub,.cv-project,.cv-note,.cv-inside,.cv-tile,.cv-jrow{break-inside:avoid}
  .cv-pubs,.cv-two{break-inside:avoid}
  .cv-hero{break-inside:avoid}
  /* projects keep two columns in print: side by side they are short enough to stay on one page */
  .cv-projects{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  .cv-project{padding:8px 10px;gap:3px}
  .cv-project .head{gap:8px}
  .cv-project .head .app-tile{width:22px;height:22px}
  .cv-project h3{font-size:10pt}
  .cv-pub,.cv-project,.cv-note,.cv-inside,.cv-panel,.cv-tile{border-color:#c9c9c9!important}
  .cv-pub::before,.cv-project::before{background:#111!important}
  .cv-prose p,.cv-award p,.cv-award .org,.cv-project p,.cv-list li{color:#333}
  a{color:#111}
  .cv-pub,.cv-project{text-decoration:none}
}
"""

T = {
    "en": dict(
        file="cv.html", lang="en",
        title="Vladyslav Manzyuk — CV",
        desc="Vladyslav Manzyuk — political science student at the University of Warsaw, essayist, author of Linda.",
        tag="Curriculum vitae",
        eyebrow="Curriculum vitae · Warsaw 2026",
        role="Political science · institutions · essays on regulation, knowledge and technology",
        place="Cegielnia, Poland",
        status="Ukrainian citizen · residence permit in Poland",
        mail_cta="Write an e-mail",
        print_cta="Print or save as PDF",
        mises_cta="Mises Wire profile",
        focus="Austrian economics · dispersed knowledge in social coordination · information theory · regulation of AI",
        tiles=[
            ("Independent Institute", "1st", "Student essay competition, 2026 — 57 entries from 13 countries"),
            ("UNIDROIT", "5th", "Essay competition, 2026 — 341 entries from 64 countries"),
            ("University of Warsaw", "4.56", "Grade point average, out of 5.00"),
            ("Mises Wire", "2", "Articles published in 2026"),
        ],
        profile_h="Profile", profile_h2="A political scientist who writes and builds.",
        profile=[
            "Third-year political science student at the University of Warsaw and a winner of international essay "
            "competitions on regulation, institutions and artificial intelligence. My essays are published in Poland "
            "and abroad; I work where economics, law and technology meet — dispersed knowledge, the information "
            "content of prices, and the rules autonomous agents will need.",
            "In my work I want to support research and analysis, monitoring of the Sejm's work, and the preparation "
            "of materials for legislative work.",
            "Alongside essays I build software: <strong>Linda</strong>, a local detector of AI-generated text, and "
            "<strong>Linda Probe</strong>, a local document search tool with OCR. Both run entirely on the user's "
            "computer.",
        ],
        edu_h="Education", edu_h2="University of Warsaw.",
        edu_univ="University of Warsaw",
        edu_fac="Faculty of Political Science and International Studies",
        edu_deg="BA in Political Science · October 2024 – June 2027 (expected)",
        edu_gpa="Grade point average 4.56 / 5.00",
        areas="Key areas",
        areas_list=["Methodology and social data analysis", "Political economy and political philosophy",
                    "Comparative political systems", "Constitutional law", "Public administration",
                    "Political communication"],
        aw_h="Awards", aw_h2="Four international competitions.",
        awards=[
            dict(yr="2026", place="1st place",
                 title="Dostoevsky, Hayek and knowledge that cannot be expressed",
                 org="Student Essay Competition, The Independent Institute",
                 detail="Chosen from 57 entries from 13 countries — the only entry from Poland.",
                 pub="Publication: The Independent Review, winter 2026/27."),
            dict(yr="2026", place="5th place",
                 title="Autonomous AI agents and the need for a UNIDROIT instrument",
                 org="UNIDROIT Essay Competition, centenary of the institute",
                 detail="341 entries from 64 countries.",
                 pub="Invited to publish in the Uniform Law Review."),
            dict(yr="2026", place="Winner",
                 title="Student Award Competition",
                 org="Center for International Relations, Washington",
                 detail="One of three winning texts, 14 countries — the only entry from Poland.",
                 pub="Publication: International Affairs Forum, 2026, no. 48."),
            dict(yr="2025", place="3rd place",
                 title="Geopolitics over Bureaucracy",
                 org="Centre of Excellence in Social Sciences and Centre of Migration Research, University of "
                     "Warsaw (Horizon Europe)",
                 detail="Essay on the European Union's neighbourhood and enlargement policy.",
                 pub=""),
        ],
        pub_h="Publications", pub_h2="Mises Wire and journals.",
        pub_kicker="Mises Wire · Mises Institute",
        arts=[
            ("Civilizations Are Transaction Costs", "6 June 2026",
             "https://mises.org/mises-wire/civilizations-are-transaction-costs"),
            ("Inflation, Communication, and Noise", "25 April 2026",
             "https://mises.org/mises-wire/inflation-communication-and-noise"),
        ],
        pub_src="Mises Wire · Mises Institute",
        mises_more="Author profile and all articles on Mises.org",
        journals=[
            ("2026/27", "Dostoevsky, Hayek and knowledge that cannot be expressed", "The Independent Review"),
            ("2026", "Winning essay, Student Award Competition", "International Affairs Forum · no. 48"),
            ("—", "Autonomous AI agents and the need for a UNIDROIT instrument", "Uniform Law Review · invited"),
        ],
        proj_h="Projects", proj_h2="Tools I build and ship.",
        proj=[
            ("Linda", "A local detector of AI-generated text for English, Russian and Polish. Transformer models "
                      "combined with stylometric features, packaged as a Windows application: the text never leaves "
                      "the machine.", LINDA, "github.com/Lendarixon/Linda", "detector", "detector-glyph.svg",
             "20", "16"),
            ("Linda Probe", "Local document search for Windows with OCR and semantic search. Documents are indexed "
                            "and searched only on the user's computer.", PROBE, "github.com/Lendarixon/Linda-Probe",
             "probe", "probe-glyph.svg", "20", "16"),
        ],
        inside_h="Also inside Linda Detector",
        inside_p='<a href="humanizer.html">Humanizer</a> rewrites stiff, templated sentences and shows every change '
                 'next to the original. <a href="authorship.html">Trace</a> compares writing styles and ranks how '
                 'similar texts are — a clue for review, not proof of authorship.',
        sk_h="Skills and languages", sk_h2="Research, sources, and five languages.",
        sk_sub="Research and tools",
        skills=["Research and analytical writing", "Work with primary sources", "Social data analysis", "Python"],
        lang_sub="Languages",
        langs=[("Ukrainian", "native"), ("Russian", "native"), ("Polish", "B2"),
               ("English", "B2, University of Warsaw certificate"), ("German", "A2")],
        rec_h="Recommendation",
        rec="A letter of recommendation from the Center for International Relations (Washington) is available on "
            "request. It was issued for another purpose — the University of Warsaw rector's scholarship.",
        consent="I consent to the processing of my personal data for the purposes necessary to carry out the "
                "recruitment process (GDPR).",
        foot_note="Unlisted page: it is not linked from the site navigation and is excluded from search engines.",
        foot_site="Linda",
        foot_links=[("Mises.org", MISES), ("GitHub", GH), ("E-mail", "mailto:" + MAIL)],
    ),
    "ru": dict(
        file="cv-ru.html", lang="ru",
        title="Владислав Манзюк — CV",
        desc="Владислав Манзюк — студент-политолог Варшавского университета, эссеист, автор Linda.",
        tag="Curriculum vitae",
        eyebrow="Curriculum vitae · Варшава, 2026",
        role="Политология · институты · эссе о регулировании, знании и технологиях",
        place="Цегельня, Польша",
        status="Гражданин Украины · карта побыту в Польше",
        mail_cta="Написать письмо",
        print_cta="Печать или PDF",
        mises_cta="Профиль на Mises Wire",
        focus="Австрийская экономика · рассеянное знание в социальной координации · теория информации · регулирование ИИ",
        tiles=[
            ("Independent Institute", "1-е", "Конкурс студенческих эссе, 2026 — 57 работ из 13 стран"),
            ("UNIDROIT", "5-е", "Конкурс эссе, 2026 — 341 работа из 64 стран"),
            ("Варшавский университет", "4,56", "Средний балл из 5,00"),
            ("Mises Wire", "2", "Статьи, опубликованные в 2026 году"),
        ],
        profile_h="Профиль", profile_h2="Политолог, который пишет и делает программы.",
        profile=[
            "Студент третьего курса политологии Варшавского университета, лауреат международных конкурсов эссе "
            "о регулировании, институтах и искусственном интеллекте. Эссе выходят в Польше и за рубежом; работаю "
            "на стыке экономики, права и технологий — рассеянное знание, информационное содержание цен и правила, "
            "которые понадобятся автономным агентам.",
            "В работе хочу заниматься исследованием и аналитикой, мониторингом работы Сейма и подготовкой "
            "материалов для законодательной работы.",
            "Помимо эссе я делаю программы: <strong>Linda</strong> — локальный детектор текста, написанного ИИ, и "
            "<strong>Linda Probe</strong> — локальный поиск по документам с OCR. Обе работают целиком на "
            "компьютере пользователя.",
        ],
        edu_h="Образование", edu_h2="Варшавский университет.",
        edu_univ="Варшавский университет",
        edu_fac="Факультет политических наук и международных исследований",
        edu_deg="Политология, бакалавриат · октябрь 2024 – июнь 2027 (план)",
        edu_gpa="Средний балл 4,56 / 5,00",
        areas="Ключевые области",
        areas_list=["Методология и анализ социальных данных", "Политическая экономия и политическая философия",
                    "Сравнительные политические системы", "Конституционное право", "Государственное управление",
                    "Политическая коммуникация"],
        aw_h="Награды", aw_h2="Четыре международных конкурса.",
        awards=[
            dict(yr="2026", place="1-е место",
                 title="Достоевский, Хайек и знание, которое нельзя выразить",
                 org="Конкурс студенческих эссе, The Independent Institute",
                 detail="Выбрано из 57 работ из 13 стран — единственная работа из Польши.",
                 pub="Публикация: The Independent Review, зима 2026/27."),
            dict(yr="2026", place="5-е место",
                 title="Автономные агенты ИИ и необходимость инструмента UNIDROIT",
                 org="Конкурс эссе UNIDROIT к 100-летию института",
                 detail="341 работа из 64 стран.",
                 pub="Приглашение к публикации в Uniform Law Review."),
            dict(yr="2026", place="Победитель",
                 title="Student Award Competition",
                 org="Center for International Relations, Вашингтон",
                 detail="Один из трёх победивших текстов, 14 стран — единственная работа из Польши.",
                 pub="Публикация: International Affairs Forum, 2026, № 48."),
            dict(yr="2025", place="3-е место",
                 title="«Геополитика поверх бюрократии»",
                 org="Centre of Excellence in Social Sciences и Centre of Migration Research Варшавского "
                     "университета (проект Horizon Europe)",
                 detail="Эссе о политике соседства и расширения Европейского союза.",
                 pub=""),
        ],
        pub_h="Публикации", pub_h2="Mises Wire и журналы.",
        pub_kicker="Mises Wire · Mises Institute",
        arts=[
            ("Civilizations Are Transaction Costs", "6 июня 2026",
             "https://mises.org/mises-wire/civilizations-are-transaction-costs"),
            ("Inflation, Communication, and Noise", "25 апреля 2026",
             "https://mises.org/mises-wire/inflation-communication-and-noise"),
        ],
        pub_src="Mises Wire · Mises Institute",
        mises_more="Профиль автора и все статьи на Mises.org",
        journals=[
            ("2026/27", "Достоевский, Хайек и знание, которое нельзя выразить", "The Independent Review"),
            ("2026", "Конкурсный текст Student Award Competition", "International Affairs Forum · № 48"),
            ("—", "Автономные агенты ИИ и необходимость инструмента UNIDROIT", "Uniform Law Review · приглашение"),
        ],
        proj_h="Проекты", proj_h2="Программы, которые я делаю.",
        proj=[
            ("Linda", "Локальный детектор текста, написанного ИИ, для английского, русского и польского. "
                      "Трансформерные модели вместе со стилометрическими признаками; приложение для Windows, "
                      "текст не покидает компьютер.", LINDA, "github.com/Lendarixon/Linda", "detector",
             "detector-glyph.svg", "20", "16"),
            ("Linda Probe", "Локальный поиск по документам для Windows с OCR и семантическим поиском. Индексация "
                            "и поиск идут только на компьютере пользователя.", PROBE,
             "github.com/Lendarixon/Linda-Probe", "probe", "probe-glyph.svg", "20", "16"),
        ],
        inside_h="Также внутри Linda Detector",
        inside_p='<a href="humanizer.html">Humanizer</a> переписывает шаблонные фразы и показывает каждое изменение '
                 'рядом с оригиналом. <a href="authorship.html">Trace</a> сравнивает стиль текстов и ранжирует, '
                 'насколько они похожи, — это подсказка для проверки, а не доказательство авторства.',
        sk_h="Навыки и языки", sk_h2="Research, источники и пять языков.",
        sk_sub="Research и инструменты",
        skills=["Research и аналитическое письмо", "Работа с источниками", "Анализ социальных данных", "Python"],
        lang_sub="Языки",
        langs=[("Украинский", "родной"), ("Русский", "родной"), ("Польский", "B2"),
               ("Английский", "B2, сертификат Варшавского университета"), ("Немецкий", "A2")],
        rec_h="Рекомендация",
        rec="Есть рекомендательное письмо от Center for International Relations (Вашингтон); оно выдавалось для "
            "другой цели — стипендии ректора Варшавского университета — и предоставляется по запросу.",
        consent="Согласен на обработку моих персональных данных в целях, необходимых для проведения процесса "
                "рекрутации (GDPR).",
        foot_note="Страница не в индексе: её нет в навигации сайта, поисковые системы её не видят.",
        foot_site="Linda",
        foot_links=[("Mises.org", MISES), ("GitHub", GH), ("Почта", "mailto:" + MAIL)],
    ),
    "pl": dict(
        file="cv-pl.html", lang="pl",
        title="Vladyslav Manzyuk — CV",
        desc="Vladyslav Manzyuk — student politologii na Uniwersytecie Warszawskim, eseista, autor Lindy.",
        tag="Curriculum vitae",
        eyebrow="Curriculum vitae · Warszawa 2026",
        role="Politologia · instytucje · eseje o regulacji, wiedzy i technologii",
        place="Cegielnia, Polska",
        status="Obywatel Ukrainy · karta pobytu w Polsce",
        mail_cta="Napisz e-mail",
        print_cta="Drukuj lub zapisz PDF",
        mises_cta="Profil na Mises Wire",
        focus="Ekonomia austriacka · wiedza rozproszona w koordynacji społecznej · teoria informacji · regulacja AI",
        tiles=[
            ("Independent Institute", "1.", "Konkurs esejów studenckich, 2026 — 57 prac z 13 krajów"),
            ("UNIDROIT", "5.", "Konkurs esejów, 2026 — 341 prac z 64 krajów"),
            ("Uniwersytet Warszawski", "4,56", "Średnia ocen na 5,00"),
            ("Mises Wire", "2", "Artykuły opublikowane w 2026 roku"),
        ],
        profile_h="Profil", profile_h2="Politolog, który pisze i tworzy programy.",
        profile=[
            "Student trzeciego roku politologii na Uniwersytecie Warszawskim, laureat międzynarodowych konkursów "
            "esejów o regulacji, instytucjach i sztucznej inteligencji. Eseje publikuję w Polsce i za granicą; "
            "pracuję na przecięciu ekonomii, prawa i technologii — wiedza rozproszona, informacyjna treść cen "
            "i reguły, których będą potrzebować autonomiczne agenty.",
            "W pracy chcę wspierać research i analizy, monitorowanie prac Sejmu oraz przygotowanie materiałów dla "
            "prac legislacyjnych.",
            "Obok esejów piszę programy: <strong>Linda</strong> — lokalny detektor tekstu generowanego przez AI — "
            "i <strong>Linda Probe</strong> — lokalną wyszukiwarkę dokumentów z OCR. Oba działają wyłącznie na "
            "komputerze użytkownika.",
        ],
        edu_h="Wykształcenie", edu_h2="Uniwersytet Warszawski.",
        edu_univ="Uniwersytet Warszawski",
        edu_fac="Wydział Nauk Politycznych i Studiów Międzynarodowych",
        edu_deg="Politologia, studia licencjackie · październik 2024 – czerwiec 2027 (planowane)",
        edu_gpa="Średnia ocen: 4,56 / 5,00",
        areas="Kluczowe obszary",
        areas_list=["Metodologia i analiza danych społecznych", "Ekonomia polityczna i filozofia polityki",
                    "Porównawcze systemy polityczne", "Prawo konstytucyjne", "Administracja publiczna",
                    "Komunikacja polityczna"],
        aw_h="Nagrody", aw_h2="Cztery międzynarodowe konkursy.",
        awards=[
            dict(yr="2026", place="I miejsce",
                 title="Dostojewski, Hayek i wiedza, której nie da się wyrazić",
                 org="Student Essay Competition, The Independent Institute",
                 detail="Wybrany spośród 57 prac z 13 krajów — jedyna praca z Polski.",
                 pub="Publikacja: The Independent Review, zima 2026/27."),
            dict(yr="2026", place="V miejsce",
                 title="Autonomiczne agenty AI i potrzeba instrumentu UNIDROIT",
                 org="UNIDROIT Essay Competition, stulecie instytutu",
                 detail="341 prac z 64 krajów.",
                 pub="Zaproszenie do publikacji w Uniform Law Review."),
            dict(yr="2026", place="Laureat",
                 title="Student Award Competition",
                 org="Center for International Relations, Waszyngton",
                 detail="Jeden z trzech zwycięskich tekstów, 14 krajów — jedyna praca z Polski.",
                 pub="Publikacja: International Affairs Forum, 2026, nr 48."),
            dict(yr="2025", place="III miejsce",
                 title="„Geopolityka ponad biurokracją”",
                 org="Centre of Excellence in Social Sciences i Centre of Migration Research UW "
                     "(projekt Horyzont Europa)",
                 detail="Praca o polityce sąsiedztwa i rozszerzenia Unii Europejskiej.",
                 pub=""),
        ],
        pub_h="Publikacje", pub_h2="Mises Wire i czasopisma.",
        pub_kicker="Mises Wire · Mises Institute",
        arts=[
            ("Civilizations Are Transaction Costs", "6 czerwca 2026",
             "https://mises.org/mises-wire/civilizations-are-transaction-costs"),
            ("Inflation, Communication, and Noise", "25 kwietnia 2026",
             "https://mises.org/mises-wire/inflation-communication-and-noise"),
        ],
        pub_src="Mises Wire · Mises Institute",
        mises_more="Profil autora i wszystkie artykuły na Mises.org",
        journals=[
            ("2026/27", "Dostojewski, Hayek i wiedza, której nie da się wyrazić", "The Independent Review"),
            ("2026", "Tekst konkursowy Student Award Competition", "International Affairs Forum · nr 48"),
            ("—", "Autonomiczne agenty AI i potrzeba instrumentu UNIDROIT", "Uniform Law Review · zaproszenie"),
        ],
        proj_h="Projekty", proj_h2="Programy, które tworzę.",
        proj=[
            ("Linda", "Autorski, lokalny detektor tekstu generowanego przez AI dla języka angielskiego, rosyjskiego "
                      "i polskiego. Modele transformerowe i cechy stylometryczne; aplikacja na Windows, tekst nie "
                      "opuszcza komputera.", LINDA, "github.com/Lendarixon/Linda", "detector", "detector-glyph.svg",
             "20", "16"),
            ("Linda Probe", "Lokalna wyszukiwarka dokumentów dla Windows z OCR i wyszukiwaniem semantycznym. "
                            "Indeksowanie i wyszukiwanie wyłącznie na komputerze użytkownika.", PROBE,
             "github.com/Lendarixon/Linda-Probe", "probe", "probe-glyph.svg", "20", "16"),
        ],
        inside_h="Także w Linda Detector",
        inside_p='<a href="humanizer.html">Humanizer</a> przepisuje sztywne, szablonowe zdania i pokazuje każdą '
                 'zmianę obok oryginału. <a href="authorship.html">Trace</a> porównuje styl tekstów i szereguje, '
                 'jak bardzo są podobne — to wskazówka do sprawdzenia, nie dowód autorstwa.',
        sk_h="Umiejętności i języki", sk_h2="Research, źródła i pięć języków.",
        sk_sub="Research i narzędzia",
        skills=["Research i pisanie analityczne", "Praca ze źródłami", "Analiza danych społecznych", "Python"],
        lang_sub="Języki",
        langs=[("Ukraiński", "ojczysty"), ("Rosyjski", "ojczysty"), ("Polski", "B2"),
               ("Angielski", "B2, certyfikat UW"), ("Niemiecki", "A2")],
        rec_h="Rekomendacja",
        rec="Dysponuję listem rekomendacyjnym od Center for International Relations (Waszyngton), wystawionym w "
            "innym celu (stypendium rektora UW); mogę go udostępnić na życzenie.",
        consent="Wyrażam zgodę na przetwarzanie moich danych osobowych dla potrzeb niezbędnych do realizacji "
                "procesu rekrutacji (zgodnie z RODO).",
        foot_note="Strona nieindeksowana: nie ma jej w nawigacji serwisu, wyszukiwarki jej nie widzą.",
        foot_site="Linda",
        foot_links=[("Mises.org", MISES), ("GitHub", GH), ("E-mail", "mailto:" + MAIL)],
    ),
}


def page(t):
    lang = t["lang"]
    tiles = "".join(
        f'<div class="cv-tile" style="--tone:var({tone})"><span class="k">{k}</span>'
        f'<span class="n">{n}</span><span class="t">{x}</span></div>'
        for (k, n, x), tone in zip(t["tiles"], ("--id-blue", "--id-violet", "--id-teal", "--id-green")))
    profile = "".join(f"<p>{p}</p>" for p in t["profile"])
    areas = "".join(f"<li>{a}</li>" for a in t["areas_list"])
    awards = "".join(
        f'<article class="cv-award"><div class="yr">{a["yr"]}</div><div>'
        f'<span class="place">{a["place"]}</span><h3>{a["title"]}</h3>'
        f'<div class="org">{a["org"]}</div><p>{a["detail"]}</p>'
        + (f'<p class="pub">{a["pub"]}</p>' if a["pub"] else "")
        + "</div></article>"
        for a in t["awards"])
    pubs = "".join(
        f'<a class="cv-pub" href="{u}"><span class="d">{d}</span><span class="ti">{ti}</span>'
        f'<span class="src">{t["pub_src"]}</span></a>'
        for ti, d, u in t["arts"])
    journals = "".join(
        f'<div class="cv-jrow"><span class="v">{v}</span><span class="w">{w}</span>'
        f'<span class="s">{s}</span></div>' for v, w, s in t["journals"])
    projects = "".join(
        f'<a class="cv-project" href="{url}" style="--tone:var(--id-{tone})">'
        f'<span class="head"><span class="app-tile is-{tone}" aria-hidden="true">'
        f'<img src="assets/{glyph}" alt="" width="{w}" height="{h}"></span><h3>{name}</h3></span>'
        f'<p>{desc}</p><span class="go">{link}</span></a>'
        for name, desc, url, link, tone, glyph, w, h in t["proj"])
    skills = "".join(f"<li><span>{s}</span></li>" for s in t["skills"])
    langs = "".join(f'<li><span>{n}</span><span class="lv">{lv}</span></li>' for n, lv in t["langs"])
    foot_links = "".join(f'<a href="{u}">{l}</a>' for l, u in t["foot_links"])
    lang_links = "".join(
        f'<a href="{FILES[l]}" lang="{l}" hreflang="{l}"'
        + (' aria-current="true"' if l == lang else "") + f'>{l.upper()}</a>'
        for l in ("en", "ru", "pl"))

    return f"""<!doctype html><html lang="{lang}" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script data-linda-theme-init>(function(){{var t='dark';try{{var s=localStorage.getItem('linda-site-theme');if(s!=='light'&&s!=='dark')s=localStorage.getItem('linda-theme');if(s==='light'||s==='dark')t=s;}}catch(e){{}}document.documentElement.dataset.theme=t;}})();</script>
<title>{t["title"]}</title><meta name="description" content="{t["desc"]}">
<meta name="robots" content="noindex,nofollow,noarchive">
<link rel="icon" href="assets/detector-logo.png">
<link rel="stylesheet" href="linda.css?v={CSS_V}">
<style>{CSS}</style></head><body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="suite-header cv-header"><div class="header-inner">
<a class="brand" href="index.html" aria-label="Linda"><span class="brand-mark app-tile is-detector" aria-hidden="true"><img src="assets/detector-glyph.svg" alt="" width="20" height="16"></span><span>linda</span></a>
<span class="cv-tag">{t["tag"]}</span>
<div class="header-controls"><button class="theme-toggle" type="button" aria-label="Change colour theme">◐</button>
<div class="language-switch" aria-label="Language">{lang_links}</div></div>
</div></header>
<main class="suite-main cv-main" id="main">

<section class="cv-hero">
<div class="cv-hero-copy">
<span class="eyebrow">{t["eyebrow"]}</span>
<h1>Vladyslav Manzyuk</h1>
<p class="cv-role">{t["role"]}</p>
<p class="cv-meta"><span>{t["place"]}</span><span>{t["status"]}</span><span><a href="mailto:{MAIL}">{MAIL}</a></span></p>
<div class="cv-actions">
<a class="button primary" href="mailto:{MAIL}">{t["mail_cta"]}<span aria-hidden="true">↗</span></a>
<button class="button" type="button" onclick="window.print()">{t["print_cta"]}<span aria-hidden="true">↗</span></button>
<a class="text-link" href="{MISES}">{t["mises_cta"]}<span aria-hidden="true">↗</span></a>
</div>
<p class="cv-focus">{t["focus"]}</p>
</div>
<div class="cv-wall">{tiles}</div>
</section>

<section id="profile">
<div class="section-heading"><span class="eyebrow">{t["profile_h"]}</span><h2>{t["profile_h2"]}</h2></div>
<div class="cv-prose">{profile}</div>
</section>

<section id="education">
<div class="section-heading"><span class="eyebrow">{t["edu_h"]}</span><h2>{t["edu_h2"]}</h2></div>
<div class="cv-panel">
<div><h3>{t["edu_univ"]}</h3><p class="sub">{t["edu_fac"]}</p>
<p class="deg">{t["edu_deg"]}</p><p class="gpa">{t["edu_gpa"]}</p></div>
<div><span class="eyebrow">{t["areas"]}</span><ul class="cv-areas">{areas}</ul></div>
</div>
</section>

<section id="awards">
<div class="section-heading"><span class="eyebrow">{t["aw_h"]}</span><h2>{t["aw_h2"]}</h2></div>
<div class="cv-awards">{awards}</div>
</section>

<section id="publications">
<div class="section-heading"><span class="eyebrow">{t["pub_h"]}</span><h2>{t["pub_h2"]}</h2></div>
<div class="cv-pubs">{pubs}</div>
<p class="cv-more"><a class="text-link" href="{MISES}">{t["mises_more"]}<span aria-hidden="true">↗</span></a></p>
<div class="cv-journals">{journals}</div>
</section>

<section id="projects">
<div class="section-heading"><span class="eyebrow">{t["proj_h"]}</span><h2>{t["proj_h2"]}</h2></div>
<div class="cv-projects">{projects}</div>
<div class="cv-inside"><h3>{t["inside_h"]}</h3><p>{t["inside_p"]}</p></div>
</section>

<section id="skills">
<div class="section-heading"><span class="eyebrow">{t["sk_h"]}</span><h2>{t["sk_h2"]}</h2></div>
<div class="cv-two">
<div class="cv-panel" style="grid-template-columns:minmax(0,1fr);display:block">
<span class="eyebrow">{t["sk_sub"]}</span><ul class="cv-list">{skills}</ul></div>
<div class="cv-panel" style="grid-template-columns:minmax(0,1fr);display:block">
<span class="eyebrow">{t["lang_sub"]}</span><ul class="cv-list">{langs}</ul></div>
</div>
<div class="cv-note"><b>{t["rec_h"]}.</b> {t["rec"]}</div>
<div class="cv-note">{t["consent"]}</div>
</section>

</main>
<footer class="suite-footer cv-footer"><div>
<a class="brand" href="index.html"><span class="app-logo app-tile is-detector" aria-hidden="true"><img src="assets/detector-glyph.svg" alt="" width="20" height="16"></span><span>linda</span></a>
<p class="cv-foot-note">{t["foot_note"]}</p>
<small>© 2026 Vladyslav Manzyuk</small></div>
<div class="footer-links">{foot_links}</div>
<div class="footer-links"><a href="index.html">{t["foot_site"]}</a></div>
</footer>
<script>(function(){{var root=document.documentElement;document.querySelectorAll('.cv-header .theme-toggle').forEach(function(b){{b.addEventListener('click',function(){{var v=root.dataset.theme==='light'?'dark':'light';root.dataset.theme=v;try{{localStorage.setItem('linda-site-theme',v)}}catch(e){{}}}})}});}})();</script>
</body></html>"""


if __name__ == "__main__":
    for key, t in T.items():
        path = os.path.join(ROOT, FILES[key])
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page(t))
        print("wrote", path)
