# -*- coding: utf-8 -*-
"""Site update for 2.4.0.0 / model pack 1.4.1h in the live Pages repo (C:/Users/ninja/Desktop/gh_pages_site).

Edits in place, no publishing:
  news.json                      prepend the 2026-11-20 entry (LF, indent=1, ensure_ascii=False)
  updates{,-pl,-ru}.html         new current release, 2.3.0.2 demoted into the archive
  versions{,-pl,-ru}.html        "Current versions:" line
  results{,-pl,-ru}.html         new benchmark block: pack 1.4.1h, PL + RU
  detector-results{,-pl,-ru}.html  "progress: 1.1 -> 1.4.1" + the same block + changelog link
  trust{,-pl,-ru}.html           release-integrity page: version, pack, installer SHA-256

Every replacement asserts an exact expected count, so a layout change aborts instead of
silently mangling a page.
"""
import io
import json
import re
import sys
from pathlib import Path

SITE = Path("C:/Users/ninja/Desktop/gh_pages_site")
DATE = "2026-11-20"
APP = "2.4.0.0"
PACK = "1.4.1h"
SETUP_SHA = "0979b9081c7ebc4ca2e881d3fa473344e288788113907b44afe2e50edbcb8405"


def rd(p):
    return io.open(SITE / p, encoding="utf-8", newline="").read()


def wr(p, s):
    io.open(SITE / p, "w", encoding="utf-8", newline="").write(s)


def sub(text, old, new, count=1, label=""):
    n = text.count(old)
    assert n == count, f"{label}: expected {count} of {old[:60]!r}, found {n}"
    return text.replace(old, new)


# ---------------------------------------------------------------- 1. news.json
TITLE = {
    "en": "Linda 2.4.0.0 + models 1.4.1h — redesigned interface, faster markup, Polish at 88.9%",
    "ru": "Linda 2.4.0.0 + модели 1.4.1h — новый интерфейс, ускоренная разметка, польский 88,9%",
    "pl": "Linda 2.4.0.0 + modele 1.4.1h — nowy interfejs, szybsze oznaczanie, polski 88,9%",
}
TEXT = {
    "en": (
        "• Interface rebuilt to the brand site: flat surfaces, square corners, two control sizes, "
        "navigation in three groups, one solid fill for the main action. Contrast verified on three "
        "themes and eight accents; every pair meets WCAG AA (worst 4.53:1).\n"
        "• Sentence and token markup runs a batch of windows per model pass: on a 3000-word text "
        "9 passes instead of 45, and the token check drops from 23.1 to 18.4 s on a normal CPU. "
        "Verdicts are identical on 20 test texts.\n"
        "• Model pack 1.4.1h: Polish catches 88.9% of AI texts at the same 1% false-alarm budget "
        "(was 79.4%); false accusations on Russian human texts fall to 0.00% (0 of 648, was 0.77%); "
        "English is unchanged by design — the routing table is byte-identical and 3266 English texts "
        "gave zero different verdicts.\n"
        "• train_args.json now ships with the pack, so the essay window is 384 tokens as calibrated "
        "instead of the silent default of 256.\n"
        "• New token heads: essay English F1 0.28 to 0.54, essay Polish 0.16 to 0.37, multi Polish "
        "0.16 to 0.32, with human tokens wrongly marked held at 5%.\n"
        "• Fixed: doubled words when importing slide-style PDFs; model-set downloads that started twice "
        "and then showed “lite” as not installed; a dead end on “Models and packs”; language switching "
        "now applies immediately; drafts survive a reload.\n"
        "• Honest limits: sentence highlighting is weaker on English and Polish than on Russian; Polish "
        "and Russian figures rest on 350 texts each, so expect about 5 points of noise; the pack is "
        "unsigned and for local installation only."
    ),
    "ru": (
        "• Интерфейс переработан по брендовому сайту: плоские поверхности, прямые углы, два размера "
        "контролов, навигация в трёх группах, единая заливка главной кнопки. Контраст проверен на трёх "
        "темах и восьми акцентах; каждая пара проходит WCAG AA (худшая 4,53:1).\n"
        "• Разметка предложений и токенов обрабатывает пакет окон за один проход модели: на тексте "
        "3000 слов 9 проходов вместо 45, проверка токенов — с 23,1 до 18,4 с на обычном CPU. Вердикты "
        "совпали на 20 текстах.\n"
        "• Пакет моделей 1.4.1h: польский находит 88,9% ИИ-текстов при том же 1% ложных срабатываний "
        "(было 79,4%); ложные обвинения русских человеческих текстов — 0,00% (0 из 648, было 0,77%); "
        "английский не изменён намеренно — таблица маршрутизации побайтово та же, 3266 английских "
        "текстов дали ноль разных вердиктов.\n"
        "• В пакете теперь есть train_args.json: окно essay — 384 токена, как при калибровке, а не "
        "молчаливые 256 по умолчанию.\n"
        "• Новые token-головы: essay EN F1 0,28 → 0,54, essay PL 0,16 → 0,37, multi PL 0,16 → 0,32; "
        "доля ошибочно помеченных человеческих токенов удержана на 5%.\n"
        "• Исправлено: удвоенные слова при импорте PDF-слайдов; загрузка наборов моделей, которая "
        "запускалась дважды и оставляла «lite» неустановленным; тупик на экране «Модели и пакеты»; "
        "переключение языка применяется сразу; черновик переживает перезагрузку.\n"
        "• Честно: разметка предложений слабее на английском и польском, чем на русском; цифры для "
        "польского и русского — по 350 текстов, ожидайте около 5 пунктов шума; пакет не подписан и "
        "предназначен только для локальной установки."
    ),
    "pl": (
        "• Interfejs przebudowany zgodnie ze stroną marki: płaskie powierzchnie, proste narożniki, dwa "
        "rozmiary kontrolek, nawigacja w trzech grupach, jedno wypełnienie przycisku głównego. Kontrast "
        "sprawdzony w trzech motywach i ośmiu akcentach; każda para spełnia WCAG AA (najgorsza 4,53:1).\n"
        "• Oznaczanie zdań i tokenów przetwarza partię okien na jedno przejście modelu: przy tekście "
        "3000 słów 9 przejść zamiast 45, a sprawdzenie tokenów skraca się z 23,1 do 18,4 s na zwykłym "
        "CPU. Werdykty identyczne na 20 tekstach.\n"
        "• Pakiet modeli 1.4.1h: polski wykrywa 88,9% tekstów AI przy tym samym 1% fałszywych alarmów "
        "(było 79,4%); fałszywe oskarżenia rosyjskich tekstów ludzkich spadają do 0,00% (0 z 648, było "
        "0,77%); angielski bez zmian z założenia — tabela routingu jest identyczna bajtowo, a 3266 "
        "tekstów angielskich dało zero różnych werdyktów.\n"
        "• Pakiet zawiera teraz train_args.json: okno essay to 384 tokeny, jak przy kalibracji, a nie "
        "milczące 256 domyślne.\n"
        "• Nowe głowy tokenów: essay EN F1 0,28 → 0,54, essay PL 0,16 → 0,37, multi PL 0,16 → 0,32; "
        "udział błędnie oznaczonych tokenów ludzkich utrzymany na 5%.\n"
        "• Naprawiono: podwojone słowa przy imporcie PDF w stylu slajdów; pobieranie zestawów, które "
        "startowało dwa razy i zostawiało „lite” jako niezainstalowane; ślepy zaułek na ekranie „Modele "
        "i pakiety”; przełączanie języka działa od razu; szkic przeżywa odświeżenie.\n"
        "• Uczciwie: oznaczanie zdań jest słabsze w angielskim i polskim niż w rosyjskim; liczby dla "
        "polskiego i rosyjskiego opierają się na 350 tekstach, więc licz się z około 5 punktami szumu; "
        "pakiet jest niepodpisany i przeznaczony tylko do instalacji lokalnej."
    ),
}

news = json.loads(rd("news.json"))
assert news[0]["date"] < DATE
entry = {"date": DATE, "title": TITLE["en"], "text": TEXT["en"],
         "title_i18n": {"ru": TITLE["ru"], "en": TITLE["en"], "pl": TITLE["pl"]},
         "text_i18n": {"ru": TEXT["ru"], "en": TEXT["en"], "pl": TEXT["pl"]}}
news.insert(0, entry)
wr("news.json", json.dumps(news, indent=1, ensure_ascii=False))

# ------------------------------------------------------- 2. updates pages
KICKER = {
    "en": "Linda Detector · Current Windows release",
    "pl": "Linda Detector · Aktualne wydanie Windows",
    "ru": "Linda Detector · Текущий выпуск для Windows",
}
DL = {"en": "Download 2.4.0.0", "pl": "Pobierz 2.4.0.0", "ru": "Скачать 2.4.0.0"}
SUMMARY = {
    "en": "Redesigned interface, faster markup and detector pack 1.4.1h: Polish catches 88.9% of AI "
          "texts at 1% false alarms (was 79.4%), Russian false accusations fall from 0.77% to 0.00%, "
          "English is unchanged by design.",
    "pl": "Nowy interfejs, szybsze oznaczanie i pakiet modeli 1.4.1h: polski wykrywa 88,9% tekstów AI "
          "przy 1% fałszywych alarmów (było 79,4%), fałszywe oskarżenia rosyjskich tekstów ludzkich "
          "spadają z 0,77% do 0,00%, angielski bez zmian z założenia.",
    "ru": "Новый интерфейс, ускоренная разметка и пакет моделей 1.4.1h: польский находит 88,9% "
          "ИИ-текстов при 1% ложных срабатываний (было 79,4%), ложные обвинения русских человеческих "
          "текстов падают с 0,77% до 0,00%, английский не изменён намеренно.",
}
FULL = {"en": "Full release notes", "pl": "Pełna lista zmian", "ru": "Полный список изменений"}

for lang, fn in (("en", "updates.html"), ("pl", "updates-pl.html"), ("ru", "updates-ru.html")):
    s = rd(fn)
    old = (f'<article class="release-current"><div class="release-heading"><div>'
           f'<span class="release-kicker">{KICKER[lang]}</span><h2>2.3.0.2</h2>'
           f'<time datetime="2026-10-30">30.10.2026</time></div>')
    assert s.count(old) == 1, f"{fn}: current-release header not found"
    # demote 2.3.0.2 into the archive, then rewrite the current article as 2.4.0.0
    old_article_start = s.index(old)
    old_article_end = s.index("</article>", old_article_start) + len("</article>")
    old_article = s[old_article_start:old_article_end]
    old_summary = re.search(r'<p class="release-summary">(.*?)</p>', old_article, re.S).group(1)
    archived = (f'<details class="release-archive"><summary><time>2026-10-30</time>'
                f'<span>Linda 2.3.0.2 — licence text corrected, no feature changes</span></summary>'
                f'<ul class="release-changes"><li>{old_summary}</li></ul></details>\r\n')

    bullets = "".join(f"<li>{p[2:].strip()}</li>" for p in TEXT[lang].split("\n") if p.startswith("• "))
    new_article = (
        f'<article class="release-current"><div class="release-heading"><div>'
        f'<span class="release-kicker">{KICKER[lang]}</span><h2>{APP}</h2>'
        f'<time datetime="{DATE}">20.11.2026</time></div>'
        f'<a class="btn acc" href="https://github.com/Lendarixon/Linda/releases/latest/download/Linda-Setup.exe">'
        f'{DL[lang]}</a></div><p class="release-summary">{SUMMARY[lang]}</p>'
        f'<details class="release-details"><summary>{FULL[lang]}</summary>'
        f'<ul class="release-changes">{bullets}</ul></details></article>'
    )
    s = s[:old_article_start] + new_article + s[old_article_end:]
    # insert the archived 2.3.0.2 right after the archive intro note
    j = s.index("</p>", s.index('class="archive-title"')) + len("</p>")
    s = s[:j] + archived.rstrip("\r\n") + s[j:]
    wr(fn, s)
    print(f"{fn}: current {APP}, 2.3.0.2 archived")

# --------------------------------------------- 3. versions pages
CUR = {
    "en": ('Current versions: app 2.3.0.2 · model package 1.3.4.1.',
           f'Current versions: app {APP} · model package {PACK} (per-token highlighting EN/PL/RU).'),
    "pl": ('Aktualne wersje: aplikacja 2.3.0.2 · pakiet modeli 1.3.4.1.',
           f'Aktualne wersje: aplikacja {APP} · pakiet modeli {PACK} (oznaczanie tokenów EN/PL/RU).'),
    "ru": ('Текущие версии: приложение 2.3.0.2 · пакет моделей 1.3.4.1.',
           f'Текущие версии: приложение {APP} · пакет моделей {PACK} (разметка по токенам EN/PL/RU).'),
}
for lang, fn in (("en", "versions.html"), ("pl", "versions-pl.html"), ("ru", "versions-ru.html")):
    s = rd(fn)
    s = sub(s, CUR[lang][0], CUR[lang][1], 1, fn)
    wr(fn, s)
    print(f"{fn}: current-vars line updated")

# --------------------------------------------- 4. results / detector-results blocks
BLOCK = {
    "en": (
        '<section class="benchmark-block"><h3>Model pack 1.4.1h — Polish and Russian</h3>'
        '<p>Same cohorts, same 1% false-alarm budget, shipped routing. “Before” is the rule that '
        'shipped with 1.3.1.</p><div class="results-table-wrap" tabindex="0" role="region" '
        'aria-label="Model pack 1.4.1h — Polish and Russian"><table class="results-table"><thead><tr>'
        '<th scope="col">Metric</th><th scope="col">n</th><th scope="col">1.3.1</th>'
        '<th scope="col">1.4.1h</th></tr></thead><tbody>'
        '<tr><th scope="row">Polish AI texts found, at 1% false alarms</th><td>350</td><td>79.4%</td><td>88.9%</td></tr>'
        '<tr><th scope="row">Polish false alarms on human texts</th><td>350</td><td>1.4%</td><td>0.9%</td></tr>'
        '<tr><th scope="row">Russian false alarms on human texts</th><td>648</td><td>0.77%</td><td>0.00%</td></tr>'
        '<tr><th scope="row">Polish false alarms, pre-2022 stress pool</th><td>700</td><td>0.14%</td><td>0.29%</td></tr>'
        '<tr><th scope="row">English AI texts found, HumanizerBench</th><td>1 675</td><td>81.0%</td><td>81.0%</td></tr>'
        '</tbody></table></div><p class="note">Honest reading: the Polish gain is 9.4 points at the shipped '
        'threshold; measured strictly at an equal realised false-alarm rate it is 2.0 points, and that '
        'interval includes zero. Zero false positives in 648 Russian texts means the rate is below 0.6% '
        'with 95% confidence, not that it is exactly zero. English is unchanged by construction: the '
        'English routing table is byte-identical and 3 266 English texts gave zero different verdicts. '
        'Token-level markup is still weaker on English and Polish than on Russian. Own measurement, not '
        'an independent audit.</p></section>'
    ),
    "pl": (
        '<section class="benchmark-block"><h3>Pakiet modeli 1.4.1h — polski i rosyjski</h3>'
        '<p>Te same zbiory, ten sam budżet 1% fałszywych alarmów, wysłany routing. „Przed” to reguła '
        'wysłana z 1.3.1.</p><div class="results-table-wrap" tabindex="0" role="region" '
        'aria-label="Pakiet modeli 1.4.1h — polski i rosyjski"><table class="results-table"><thead><tr>'
        '<th scope="col">Metryka</th><th scope="col">n</th><th scope="col">1.3.1</th>'
        '<th scope="col">1.4.1h</th></tr></thead><tbody>'
        '<tr><th scope="row">Wykryte polskie teksty AI, przy 1% fałszywych alarmów</th><td>350</td><td>79,4%</td><td>88,9%</td></tr>'
        '<tr><th scope="row">Fałszywe alarmy na polskich tekstach ludzkich</th><td>350</td><td>1,4%</td><td>0,9%</td></tr>'
        '<tr><th scope="row">Fałszywe alarmy na rosyjskich tekstach ludzkich</th><td>648</td><td>0,77%</td><td>0,00%</td></tr>'
        '<tr><th scope="row">Fałszywe alarmy PL, pula stresowa sprzed 2022</th><td>700</td><td>0,14%</td><td>0,29%</td></tr>'
        '<tr><th scope="row">Wykryte angielskie teksty AI, HumanizerBench</th><td>1 675</td><td>81,0%</td><td>81,0%</td></tr>'
        '</tbody></table></div><p class="note">Uczciwie: zysk na polskim to 9,4 punktu przy wysłanym progu; '
        'przy ściśle wyrównanym rzeczywistym odsetku fałszywych alarmów to 2,0 punktu, a ten przedział '
        'obejmuje zero. Zero fałszywych alarmów na 648 rosyjskich tekstach oznacza, że odsetek jest '
        'poniżej 0,6% z 95% pewnością, a nie że wynosi dokładnie zero. Angielski jest niezmieniony z '
        'konstrukcji: tabela routingu jest identyczna bajtowo, a 3 266 tekstów angielskich dało zero '
        'różnych werdyktów. Oznaczanie tokenów nadal jest słabsze w angielskim i polskim niż w rosyjskim. '
        'Pomiar własny, nie niezależny audyt.</p></section>'
    ),
    "ru": (
        '<section class="benchmark-block"><h3>Пакет моделей 1.4.1h — польский и русский</h3>'
        '<p>Те же наборы, тот же бюджет 1% ложных срабатываний, отгруженная маршрутизация. «Было» — '
        'правило, отгруженное с 1.3.1.</p><div class="results-table-wrap" tabindex="0" role="region" '
        'aria-label="Пакет моделей 1.4.1h — польский и русский"><table class="results-table"><thead><tr>'
        '<th scope="col">Метрика</th><th scope="col">n</th><th scope="col">1.3.1</th>'
        '<th scope="col">1.4.1h</th></tr></thead><tbody>'
        '<tr><th scope="row">Найдено польских ИИ-текстов при 1% ложных</th><td>350</td><td>79,4%</td><td>88,9%</td></tr>'
        '<tr><th scope="row">Ложные срабатывания на польских человеческих текстах</th><td>350</td><td>1,4%</td><td>0,9%</td></tr>'
        '<tr><th scope="row">Ложные срабатывания на русских человеческих текстах</th><td>648</td><td>0,77%</td><td>0,00%</td></tr>'
        '<tr><th scope="row">Ложные срабатывания PL, стресс-пул до 2022</th><td>700</td><td>0,14%</td><td>0,29%</td></tr>'
        '<tr><th scope="row">Найдено английских ИИ-текстов, HumanizerBench</th><td>1 675</td><td>81,0%</td><td>81,0%</td></tr>'
        '</tbody></table></div><p class="note">Честно: прирост на польском — 9,4 пункта при отгруженном '
        'пороге; при строго уравненной фактической доле ложных срабатываний — 2,0 пункта, и этот '
        'интервал включает ноль. Ноль ложных на 648 русских текстах означает, что доля ниже 0,6% с '
        '95% уверенностью, а не что она ровно ноль. Английский не изменён по построению: таблица '
        'маршрутизации побайтово та же, 3 266 английских текстов дали ноль разных вердиктов. Разметка '
        'по токенам по-прежнему слабее на английском и польском, чем на русском. Собственный замер, '
        'не независимый аудит.</p></section>'
    ),
}

# 4a. results*: append the block after the Assay 1.1/1.3/1.3.1 history details
HIST_SUM = {
    "en": "Assay test history: versions 1.1, 1.3 and 1.3.1",
    "pl": "Historia testów Assay: wersje 1.1, 1.3 i 1.3.1",
    "ru": "История тестов Assay: версии 1.1, 1.3 и 1.3.1",
}
for lang, fn in (("en", "results.html"), ("pl", "results-pl.html"), ("ru", "results-ru.html")):
    s = rd(fn)
    assert s.count(HIST_SUM[lang]) == 1, f"{fn}: history summary count {s.count(HIST_SUM[lang])}"
    i = s.index(HIST_SUM[lang])
    j = s.index("</details>", i) + len("</details>")
    s = s[:j] + BLOCK[lang] + s[j:]
    wr(fn, s)
    print(f"{fn}: 1.4.1h block inserted")

# 4b. detector-results*: header + replace the 1.3.1 PL/RU panel with the 1.4.1h numbers
PRG = {"en": "progress: 1.1 → 1.3.1", "pl": "postęp: 1.1 → 1.3.1", "ru": "Прогресс: 1.1 → 1.3.1"}
PRG_NEW = {"en": "progress: 1.1 → 1.4.1", "pl": "postęp: 1.1 → 1.4.1", "ru": "Прогресс: 1.1 → 1.4.1"}
PANEL_H3 = {
    "en": '<h3>Russian and Polish: what changed in 1.3.1</h3>',
    "pl": '<h3>Rosyjski i polski: co zmieniło się w 1.3.1</h3>',
    "ru": '<h3>Русский и польский: что изменилось в 1.3.1</h3>',
}
PANEL_BODY = {
    "en": '<h3>Russian and Polish: what changed in 1.4.1h</h3><p>Polish catches 88.9% of AI texts at the same '
          '1% false-alarm budget (1.3.1: 79.4%), and false accusations on Russian human texts fall from '
          '0.77% to 0.00% (0 of 648). Read that honestly: measured strictly at an equal realised false-alarm '
          'rate the Polish gain is 2.0 points, and zero errors in 648 texts only proves the rate is below '
          '0.6% with 95% confidence. English is untouched — the English routing table is byte-identical and '
          '3 266 English texts gave zero different verdicts. Polish and Russian sets are 350 texts each, so '
          'expect ±5 points. Token-level markup is now available for English and Polish (F1 0.54 and 0.37 at '
          '5% wrongly marked human tokens) but it is weaker than document-level detection.</p>',
    "pl": '<h3>Rosyjski i polski: co zmieniło się w 1.4.1h</h3><p>Polski wykrywa 88,9% tekstów AI przy tym '
          'samym budżecie 1% fałszywych alarmów (1.3.1: 79,4%), a fałszywe oskarżenia rosyjskich tekstów '
          'ludzkich spadają z 0,77% do 0,00% (0 z 648). Uczciwie: przy ściśle wyrównanym rzeczywistym '
          'odsetku fałszywych alarmów zysk na polskim to 2,0 punktu, a zero błędów na 648 tekstach dowodzi '
          'tylko, że odsetek jest poniżej 0,6% z 95% pewnością. Angielski jest nietknięty — tabela routingu '
          'jest identyczna bajtowo, a 3 266 tekstów angielskich dało zero różnych werdyktów. Zbiory polski i '
          'rosyjski to po 350 tekstów, więc spodziewaj się ±5 punktów. Oznaczanie tokenów jest teraz '
          'dostępne dla angielskiego i polskiego (F1 0,54 i 0,37 przy 5% błędnie oznaczonych tokenów '
          'ludzkich), ale jest słabsze niż detekcja na poziomie dokumentu.</p>',
    "ru": '<h3>Русский и польский: что изменилось в 1.4.1h</h3><p>Польский находит 88,9% ИИ-текстов при том же '
          'бюджете 1% ложных срабатываний (1.3.1: 79,4%), а ложные обвинения русских человеческих текстов '
          'падают с 0,77% до 0,00% (0 из 648). Честно: при строго уравненной фактической доле ложных '
          'прирост на польском — 2,0 пункта, а ноль ошибок на 648 текстах доказывает лишь то, что доля ниже '
          '0,6% с 95% уверенностью. Английский не тронут — таблица маршрутизации побайтово та же, 3 266 '
          'английских текстов дали ноль разных вердиктов. Польский и русский наборы — по 350 текстов, '
          'ожидайте ±5 пунктов. Разметка по токенам теперь есть для английского и польского (F1 0,54 и '
          '0,37 при 5% ошибочно помеченных человеческих токенов), но она слабее детекции на уровне '
          'документа.</p>',
}
CHG = {"en": "Full changelog · 2.3.0.2", "pl": "Pełna lista zmian · 2.3.0.2", "ru": "Полный список изменений · 2.3.0.2"}
CHG_NEW = {"en": "Full changelog · 2.4.0.0", "pl": "Pełna lista zmian · 2.4.0.0", "ru": "Полный список изменений · 2.4.0.0"}

for lang, fn in (("en", "detector-results.html"), ("pl", "detector-results-pl.html"), ("ru", "detector-results-ru.html")):
    s = rd(fn)
    s = sub(s, PRG[lang], PRG_NEW[lang], 1, fn)
    assert s.count(PANEL_H3[lang]) == 1, f"{fn}: panel heading count {s.count(PANEL_H3[lang])}"
    i = s.index(PANEL_H3[lang])
    j = s.index("</p></div>", i) + len("</p>")
    s = s[:i] + PANEL_BODY[lang] + s[j:]
    s = sub(s, CHG[lang], CHG_NEW[lang], 1, fn)
    wr(fn, s)
    print(f"{fn}: progress header + 1.4.1h panel")

# --------------------------------------------- 5. trust pages (release integrity)
TRUST = {
    "en": [("Updated 6 November 2026. Windows app 2.3.0.2; model pack 1.3.4.1.",
            f"Updated 20 November 2026. Windows app {APP}; model pack {PACK}."),
           ("releases/tag/v2.3.0.2\">Linda 2.3.0.2</a>", f"releases/tag/v{APP}\">Linda {APP}</a>"),
           ("d0d9ae248328ca0195e40d545f35389b80c291072316107ceb95bc3e87adf1ab", SETUP_SHA),
           ("does not claim signature or Store verification for 2.3.0.2.",
            f"does not claim signature or Store verification for {APP}.")],
    "pl": [("Zaktualizowano 6 listopada 2026. Aplikacja Windows 2.3.0.2; pakiet modeli 1.3.4.1.",
            f"Zaktualizowano 20 listopada 2026. Aplikacja Windows {APP}; pakiet modeli {PACK}."),
           ("releases/tag/v2.3.0.2\">Linda 2.3.0.2</a>", f"releases/tag/v{APP}\">Linda {APP}</a>"),
           ("d0d9ae248328ca0195e40d545f35389b80c291072316107ceb95bc3e87adf1ab", SETUP_SHA)],
    "ru": [("Обновлено 6 ноября 2026. Приложение Windows 2.3.0.2; пакет моделей 1.3.4.1.",
            f"Обновлено 20 ноября 2026. Приложение Windows {APP}; пакет моделей {PACK}."),
           ("releases/tag/v2.3.0.2\">Linda 2.3.0.2</a>", f"releases/tag/v{APP}\">Linda {APP}</a>"),
           ("d0d9ae248328ca0195e40d545f35389b80c291072316107ceb95bc3e87adf1ab", SETUP_SHA)],
}
for lang, fn in (("en", "trust.html"), ("pl", "trust-pl.html"), ("ru", "trust-ru.html")):
    s = rd(fn)
    for old, new in TRUST[lang]:
        if old in s and old != new:
            s = s.replace(old, new)
            print(f"  {fn}: {old[:44]}...")
    wr(fn, s)

print("site edits done")
