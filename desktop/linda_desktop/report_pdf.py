# -*- coding: utf-8 -*-
"""Печатный отчёт Linda-Pro: HTML с векторными графиками (SVG) и PDF из него.

Вёрстка — обычный HTML/CSS (А4, переносы страниц, колонтитул), графики рисуются SVG без внешних библиотек:
шкала вероятности, доли авторства, вероятность ИИ по ходу текста, скрипичный график (распределение вероятности ИИ
по предложениям у людей, у ИИ и у этого текста), карта структуры, диапазоны структурных признаков.
PDF строится встроенной fpdf2 без Edge/Chrome и без переключения на старую вёрстку. Текст отчёта на ru/pl/en; всё считается локально."""
from __future__ import annotations

import html
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

LANGS = ("ru", "pl", "en")

# Цвета: человек — зелёный, неопределённо — жёлтый, ИИ — красный (как в приложении)
C_HUM, C_UNC, C_AI, C_INK, C_MUTED, C_ACC = "#2e9e4f", "#e0a100", "#d6342c", "#1b1f2a", "#5d6575", "#2457d6"

T = {
    "ru": {
        "title": "Отчёт о проверке текста", "doc": "Документ", "file": "Файл", "date": "Дата", "num": "Проверка №", "mode": "Режим",
        "org": "Организация", "words": "слов", "sentences": "предложений", "ai_share": "доля ИИ в тексте",
        "v_ai": "Вероятно, ИИ", "v_human": "Вероятно, человек", "v_uncertain": "Неопределённо",
        "ai_prob": "Оценка вероятности ИИ", "origin_prob": "Оценка вероятности указанного происхождения", "summary": "Что это значит",
        "s_ai": "Детектор нашёл в тексте устойчивые признаки машинной генерации. Это сильный сигнал, но не доказательство: поговорите с автором, попросите показать черновики и объяснить ход мысли.",
        "s_human": "Явных признаков машинной генерации не найдено. Это не гарантия: хорошо отредактированный ИИ-текст бывает неотличим от человеческого.",
        "s_uncertain": "Сигналы противоречивы: часть текста похожа на машинную, часть на человеческую. Такой результат нельзя трактовать ни как «ИИ», ни как «человек».",
        "authorship": "Авторство (доли по словам)", "a_human": "человек", "a_mixed": "возможно ИИ / смешанное", "a_ai": "ИИ",
        "a_note": "Предложения распознаются хуже целого текста, поэтому доли — ориентир, а не точное разделение.",
        "timeline": "Вероятность ИИ по ходу текста", "tl_note": "Один столбик — фрагмент текста слева направо; высота — вероятность ИИ.",
        "tl_start": "начало", "tl_end": "конец", "violin": "Где этот текст относительно людей и ИИ",
        "vi_note": "Форма показывает, как распределена вероятность ИИ по предложениям: чем шире форма на уровне, тем больше предложений с такой вероятностью. Тёмная черта — медиана. Слева тексты людей, в центре тексты ИИ из эталонной выборки, справа проверяемый текст.",
        "vi_h": "люди (эталон)", "vi_a": "ИИ (эталон)", "vi_t": "этот текст", "vi_med": "медиана",
        "structure": "Карта структуры", "st_note": "Каждая строка — абзац (длина по числу слов); штрихи — предложения, цвет — оценка.",
        "par": "абзац", "kind_list": "список", "kind_heading": "заголовок",
        "features": "Что выделяется в структуре текста", "ft_note": "Серая зона — типичный диапазон у людей, красная — у ИИ, чёрная метка — этот текст. Показатель описывает стиль и не входит в вердикт.",
        "ft_none": "Все структурные показатели в пределах типичного для людей.",
        "metrics": "Метрики текста", "m_words": "Слов", "m_sent": "Предложений", "m_par": "Абзацев", "m_avg": "Слов в предложении (в среднем)",
        "m_burst": "Разброс длины предложений", "m_div": "Разнообразие лексики", "m_stock": "Штампы на 1000 слов",
        "stock": "Типичные «машинные» обороты", "rep": "Повторяющиеся фразы", "none": "не найдено",
        "models": "Оценки моделей", "models_note": "Чем больше число, тем увереннее модель в ИИ. Это внутренние оценки, а не проценты.",
        "flagged": "Фрагменты, на которые стоит обратить внимание", "fl_none": "Предложений с высокой вероятностью ИИ нет.",
        "marked": "Размеченный текст", "marked_note": "Красным отмечены предложения с высокой вероятностью ИИ, жёлтым — спорные.",
        "legend_ai": "ИИ", "legend_unc": "спорно", "legend_hum": "человек",
        "teacher": "Как пользоваться результатом",
        "t1": "Не используйте отчёт как единственное основание для оценки или наказания: детектор ошибается, особенно на коротких текстах, текстах на неродном для автора языке и сильно отредактированных текстах.",
        "t2": "Попросите автора устно пересказать работу и пояснить спорные фрагменты, покажите ему отмеченные места.",
        "t3": "Сравните с прежними работами этого автора и историей версий документа (Google Docs, Word).",
        "t4": "Для спорных случаев запустите проверку ещё раз на полной версии текста: длинные тексты оцениваются надёжнее коротких.",
        "method": "О методе и ограничениях",
        "me": "Linda-Pro оценивает текст ансамблем из нескольких моделей и анализом стиля; результат — вероятность, а не доказательство. Точность зависит от языка, длины и жанра: русский и польский поддерживаются хуже английского, а тексты новых ИИ-моделей и ИИ-тексты, пропущенные через «очеловечиватели», распознаются хуже. Текст обработан локально на этом компьютере и никуда не отправлялся.",
        "page": "Страница", "of": "из", "footer": "Linda-Pro — локальный детектор ИИ-текста",
        "sec_summary": "Итог", "sec_charts": "Графики", "sec_text": "Текст",
        "print": "Печать / сохранить PDF", "untitled": "без названия",
    },
    "pl": {
        "title": "Raport sprawdzenia tekstu", "doc": "Dokument", "file": "Plik", "date": "Data", "num": "Sprawdzenie nr", "mode": "Tryb",
        "org": "Organizacja", "words": "słów", "sentences": "zdań", "ai_share": "udział AI w tekście",
        "v_ai": "Prawdopodobnie AI", "v_human": "Prawdopodobnie człowiek", "v_uncertain": "Niejednoznacznie",
        "ai_prob": "Szacowane prawdopodobieństwo AI", "origin_prob": "Szacowane prawdopodobieństwo wskazanego pochodzenia", "summary": "Co to oznacza",
        "s_ai": "Detektor znalazł w tekście wyraźne cechy generowania maszynowego. To silny sygnał, ale nie dowód: porozmawiaj z autorem, poproś o szkice i wyjaśnienie toku myślenia.",
        "s_human": "Nie znaleziono wyraźnych cech generowania maszynowego. To nie gwarancja: dobrze zredagowany tekst AI bywa nie do odróżnienia od ludzkiego.",
        "s_uncertain": "Sygnały są sprzeczne: część tekstu przypomina maszynowy, część ludzki. Tego wyniku nie można uznać ani za „AI”, ani za „człowieka”.",
        "authorship": "Autorstwo (udziały wg słów)", "a_human": "człowiek", "a_mixed": "możliwe AI / mieszane", "a_ai": "AI",
        "a_note": "Zdania rozpoznawane są gorzej niż cały tekst, więc udziały są orientacyjne, a nie dokładnym podziałem.",
        "timeline": "Prawdopodobieństwo AI w toku tekstu", "tl_note": "Jeden słupek to fragment tekstu od lewej do prawej; wysokość to prawdopodobieństwo AI.",
        "tl_start": "początek", "tl_end": "koniec", "violin": "Gdzie ten tekst leży wobec ludzi i AI",
        "vi_note": "Kształt pokazuje rozkład prawdopodobieństwa AI w zdaniach. Po lewej teksty ludzi, w środku teksty AI z próbki wzorcowej, po prawej zdania sprawdzanego tekstu (punkty).",
        "vi_h": "ludzie (wzorzec)", "vi_a": "AI (wzorzec)", "vi_t": "ten tekst", "vi_med": "mediana",
        "structure": "Mapa struktury", "st_note": "Każdy wiersz to akapit (długość w słowach); kreski to zdania, kolor to ocena.",
        "par": "akapit", "kind_list": "lista", "kind_heading": "nagłówek",
        "features": "Co wyróżnia się w strukturze tekstu", "ft_note": "Szary pas to typowy zakres u ludzi, czerwony u AI, czarna kreska to ten tekst. Wskaźnik opisuje styl i nie wchodzi do werdyktu.",
        "ft_none": "Wszystkie wskaźniki struktury mieszczą się w typowym zakresie ludzi.",
        "metrics": "Metryki tekstu", "m_words": "Słów", "m_sent": "Zdań", "m_par": "Akapitów", "m_avg": "Słów w zdaniu (średnio)",
        "m_burst": "Zróżnicowanie długości zdań", "m_div": "Różnorodność słownictwa", "m_stock": "Szablony na 1000 słów",
        "stock": "Typowe „maszynowe” zwroty", "rep": "Powtarzające się frazy", "none": "nie znaleziono",
        "models": "Oceny modeli", "models_note": "Im większa liczba, tym pewniej model wskazuje AI. To oceny wewnętrzne, nie procenty.",
        "flagged": "Fragmenty warte uwagi", "fl_none": "Brak zdań z wysokim prawdopodobieństwem AI.",
        "marked": "Tekst z oznaczeniami", "marked_note": "Na czerwono zdania o wysokim prawdopodobieństwie AI, na żółto sporne.",
        "legend_ai": "AI", "legend_unc": "sporne", "legend_hum": "człowiek",
        "teacher": "Jak korzystać z wyniku",
        "t1": "Nie używaj raportu jako jedynej podstawy oceny lub kary: detektor się myli, zwłaszcza na krótkich tekstach, tekstach w obcym dla autora języku i mocno zredagowanych.",
        "t2": "Poproś autora o ustne streszczenie pracy i wyjaśnienie spornych fragmentów, pokaż mu zaznaczone miejsca.",
        "t3": "Porównaj z wcześniejszymi pracami autora i historią wersji dokumentu (Google Docs, Word).",
        "t4": "W spornych przypadkach uruchom sprawdzenie ponownie na pełnej wersji tekstu: długie teksty ocenia się pewniej niż krótkie.",
        "method": "O metodzie i ograniczeniach",
        "me": "Linda-Pro ocenia tekst zespołem modeli i analizą stylu; wynik to prawdopodobieństwo, a nie dowód. Trafność zależy od języka, długości i gatunku: rosyjski i polski są obsługiwane gorzej niż angielski, a teksty nowych modeli AI i teksty AI przepuszczone przez „humanizery” rozpoznawane są gorzej. Tekst przetworzono lokalnie na tym komputerze i nigdzie go nie wysłano.",
        "page": "Strona", "of": "z", "footer": "Linda-Pro — lokalny detektor tekstu AI",
        "sec_summary": "Podsumowanie", "sec_charts": "Wykresy", "sec_text": "Tekst",
        "print": "Drukuj / zapisz PDF", "untitled": "bez tytułu",
    },
    "en": {
        "title": "Text check report", "doc": "Document", "file": "File", "date": "Date", "num": "Check no.", "mode": "Mode",
        "org": "Organization", "words": "words", "sentences": "sentences", "ai_share": "AI share of the text",
        "v_ai": "Likely AI", "v_human": "Likely human", "v_uncertain": "Uncertain",
        "ai_prob": "Estimated AI probability", "origin_prob": "Estimated probability of this origin", "summary": "What this means",
        "s_ai": "The detector found consistent signs of machine generation. This is a strong signal but not proof: talk to the author, ask for drafts and an explanation of the reasoning.",
        "s_human": "No clear signs of machine generation were found. This is not a guarantee: a well-edited AI text can be indistinguishable from a human one.",
        "s_uncertain": "The signals conflict: part of the text looks machine-written, part human. This result should be read neither as \"AI\" nor as \"human\".",
        "authorship": "Authorship (shares by words)", "a_human": "human", "a_mixed": "possibly AI / mixed", "a_ai": "AI",
        "a_note": "Single sentences are recognized less reliably than a whole text, so the shares are a guide, not an exact split.",
        "timeline": "AI probability along the text", "tl_note": "One bar is a stretch of text from left to right; its height is the AI probability.",
        "tl_start": "start", "tl_end": "end", "violin": "Where this text sits against humans and AI",
        "vi_note": "The shape shows how AI probability is spread over sentences. Left: human texts, middle: AI texts from the reference sample, right: sentences of this text (dots).",
        "vi_h": "humans (reference)", "vi_a": "AI (reference)", "vi_t": "this text", "vi_med": "median",
        "structure": "Structure map", "st_note": "Each row is a paragraph (length in words); ticks are sentences, colour is the score.",
        "par": "paragraph", "kind_list": "list", "kind_heading": "heading",
        "features": "What stands out in the structure", "ft_note": "Grey band: typical range for humans, red: for AI, black mark: this text. This describes style and is not part of the verdict.",
        "ft_none": "All structure measures are within the typical human range.",
        "metrics": "Text metrics", "m_words": "Words", "m_sent": "Sentences", "m_par": "Paragraphs", "m_avg": "Words per sentence (average)",
        "m_burst": "Sentence length variation", "m_div": "Vocabulary diversity", "m_stock": "Stock phrases per 1000 words",
        "stock": "Typical \"machine\" phrases", "rep": "Repeated phrases", "none": "none found",
        "models": "Model scores", "models_note": "A larger number means the model is more confident in AI. These are internal scores, not percentages.",
        "flagged": "Passages worth a look", "fl_none": "No sentences with a high AI probability.",
        "marked": "Annotated text", "marked_note": "Red marks sentences with a high AI probability, yellow the disputed ones.",
        "legend_ai": "AI", "legend_unc": "disputed", "legend_hum": "human",
        "teacher": "How to use the result",
        "t1": "Do not use the report as the only basis for grading or punishment: the detector makes mistakes, especially on short texts, texts in a language foreign to the author, and heavily edited texts.",
        "t2": "Ask the author to retell the work orally and explain the disputed passages; show them the marked places.",
        "t3": "Compare with the author's earlier work and the document's version history (Google Docs, Word).",
        "t4": "For disputed cases run the check again on the full text: long texts are scored more reliably than short ones.",
        "method": "About the method and its limits",
        "me": "Linda-Pro scores a text with an ensemble of models and a style analysis; the result is a probability, not proof. Accuracy depends on language, length and genre: Russian and Polish are supported less well than English, and texts from new AI models and AI texts run through \"humanizers\" are recognized less well. The text was processed locally on this computer and was never sent anywhere.",
        "page": "Page", "of": "of", "footer": "Linda-Pro — local AI text detector",
        "sec_summary": "Summary", "sec_charts": "Charts", "sec_text": "Text",
        "print": "Print / save PDF", "untitled": "untitled",
    },
}


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _col(p: float) -> str:
    return C_AI if p >= 0.65 else (C_UNC if p >= 0.35 else C_HUM)


def _lab_col(label: str) -> str:
    return {"ai": C_AI, "uncertain": C_UNC}.get(label, C_HUM)


def _gauge(pct: float, color: str) -> str:
    """Полукруглая шкала 0–100 %: число по центру дуги."""
    r, cx, cy = 80, 100, 100
    circ = math.pi * r
    filled = circ * max(0.0, min(100.0, pct)) / 100.0
    arc = "M %d %d A %d %d 0 0 1 %d %d" % (cx - r, cy, r, r, cx + r, cy)
    return ('<svg viewBox="0 0 200 118" class="gauge"><path d="%s" fill="none" stroke="#e3e6ee" stroke-width="16" stroke-linecap="round"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="16" stroke-linecap="round" stroke-dasharray="%.1f %.1f"/>'
            '<text x="100" y="96" text-anchor="middle" font-size="34" font-weight="700" fill="%s">%d%%</text></svg>'
            % (arc, arc, color, filled, circ + 5, C_INK, round(pct)))


def _timeline(sents: list[dict], t: dict) -> str:
    """Столбики вероятности ИИ по ходу текста; длинные тексты усредняются в ≤ 70 столбиков."""
    if not sents:
        return ""
    w = [max(1, len(s["text"].split())) for s in sents]
    n_bins = min(70, len(sents))
    tot = sum(w)
    bins = [[0.0, 0] for _ in range(n_bins)]
    acc = 0
    for s, ww in zip(sents, w):
        b = min(n_bins - 1, int((acc + ww / 2) / tot * n_bins))
        bins[b][0] += s["p_ai"] * ww
        bins[b][1] += ww
        acc += ww
    W, H, L, B = 700, 105, 34, 20
    bw = (W - L) / n_bins
    out = ['<svg viewBox="0 0 %d %d" class="chart">' % (W, H + B)]
    for v in (0, 0.5, 1):
        y = H - v * (H - 8)
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#d5d9e3" stroke-dasharray="%s"/>'
                   '<text x="%d" y="%.1f" font-size="10" fill="%s" text-anchor="end">%d%%</text>'
                   % (L, y, W, y, "0" if v == 0 else "3 3", L - 6, y + 3.5, C_MUTED, int(v * 100)))
    for i, (sp, sw) in enumerate(bins):
        if not sw:
            continue
        p = sp / sw
        h = max(2.0, p * (H - 8))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.5" fill="%s"/>' % (L + i * bw + 0.6, H - h, max(1.0, bw - 1.2), h, _col(p)))
    out.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text><text x="%d" y="%d" font-size="10" fill="%s" text-anchor="end">%s</text></svg>'
               % (L, H + 15, C_MUTED, _e(t["tl_start"]), W, H + 15, C_MUTED, _e(t["tl_end"])))
    return "".join(out)


def _smooth(h: list[float], s: float = 1.1) -> list[float]:
    """То же сглаживание, что в приложении (кабинет): гауссово ядро по ±3 корзины."""
    o = [0.0] * len(h)
    for i, v in enumerate(h):
        for d in range(-3, 4):
            k = i + d
            if 0 <= k < len(h):
                o[i] += v * math.exp(-(d * d) / (2 * s * s))
    return o


def _hist_median(h: list[float]) -> float:
    tot = sum(h) or 1.0
    c = 0.0
    for i, v in enumerate(h):
        c += v
        if c >= tot / 2:
            return (i + 0.5) / len(h)
    return 0.5


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    q = sorted(xs)
    m = len(q) // 2
    return q[m] if len(q) % 2 else (q[m - 1] + q[m]) / 2


def _violin(rep: dict, t: dict) -> str:
    """Скрипичный график как в приложении: распределение вероятности ИИ по предложениям у людей и у ИИ (эталон) и у этого текста
    (те же корзины, то же сглаживание, линейный масштаб, медианы подписаны)."""
    ref = (rep.get("structure_reference") or {})
    hh, ha = ref.get("human_hist"), ref.get("ai_hist")
    ps = [float(s["p_ai"]) for s in rep.get("sentences") or []]
    if not hh or not ha or not ps:
        return ""
    N = len(hh)
    mine = [0.0] * N
    for p in ps:
        mine[min(N - 1, int(p * N))] += 1
    W, H, top, bot, left = 700, 270, 30, 34, 52
    ph = H - top - bot
    cw = (W - left - 10) / 3
    groups = [(hh, "#aab2c3", t["vi_h"], _hist_median(hh), .85), (ha, "#aab2c3", t["vi_a"], _hist_median(ha), .85), (mine, C_ACC, t["vi_t"], _median(ps), .9)]
    out = ['<svg viewBox="0 0 %d %d" class="chart">' % (W, H)]
    for v in (0, .25, .5, .75, 1):
        y = H - bot - v * ph
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#d5d9e3" stroke-dasharray="%s"/><text x="%d" y="%.1f" font-size="10" fill="%s" text-anchor="end">%.2f</text>'
                   % (left, y, W - 6, y, "4 3" if v == .5 else "0", left - 6, y + 3.5, C_MUTED, v))
    for gi, (hist, color, name, med, fill) in enumerate(groups):
        cx = left + cw * (gi + .5)
        sm = _smooth(hist)
        mx = max(sm) or 1.0
        half = cw * .42
        ys = lambda i: H - bot - (i + .5) / N * ph  # noqa: E731
        right = ["%.1f,%.1f" % (cx + sm[i] / mx * half, ys(i)) for i in range(N)]
        leftp = ["%.1f,%.1f" % (cx - sm[i] / mx * half, ys(i)) for i in range(N - 1, -1, -1)]
        out.append('<polygon points="%s" fill="%s" fill-opacity="%s" stroke="#fff" stroke-width="1"/>' % (" ".join(right + leftp), color, fill))
        my = H - bot - med * ph
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.2"/>' % (cx - half, my, cx + half, my, C_INK))
        out.append('<text x="%.1f" y="16" font-size="12" font-weight="700" text-anchor="middle" fill="%s">%.2f</text>' % (cx, C_ACC if gi == 2 else C_MUTED, med))
        out.append('<text x="%.1f" y="%d" font-size="12" font-weight="600" text-anchor="middle" fill="%s">%s</text>' % (cx, H - 10, C_INK, _e(name)))
    out.append("</svg>")
    return "".join(out)


def _structure_map(layout: list[dict], t: dict) -> str:
    rows = layout[:40]
    if not rows:
        return ""
    mx = max(r.get("words", 1) for r in rows) or 1
    out = ['<div class="smap">']
    for i, r in enumerate(rows, 1):
        wpct = max(6.0, r.get("words", 1) / mx * 100)
        kind = r.get("kind")
        tag = ' <i>%s</i>' % _e(t["kind_" + kind]) if kind in ("list", "heading") else ""
        ticks = "".join('<span style="flex:%d;background:%s"></span>' % (max(1, s.get("words", 1)), _col(float(s.get("p_ai", 0)))) for s in (r.get("sentences") or []))
        if not ticks:
            ticks = '<span style="flex:1;background:#c9ceda"></span>'
        out.append('<div class="smr"><b>%d</b><div class="smb" style="width:%.1f%%">%s</div><em>%d%s</em></div>' % (i, wpct, ticks, r.get("words", 0), tag))
    out.append("</div>")
    return "".join(out)


def _range_row(f: dict) -> str:
    """Мини-диаграмма диапазонов: серая зона — люди, красная — ИИ, чёрная метка — значение текста."""
    hr, ar, v = f.get("human_range"), f.get("ai_range"), float(f.get("value") or 0)
    if not hr or not ar:
        return ""
    lo = min(hr[0], ar[0], v)
    hi = max(hr[1], ar[1], v)
    span = (hi - lo) or 1.0
    pos = lambda x: 4 + (x - lo) / span * 192  # noqa: E731
    return ('<svg viewBox="0 0 200 18" class="rng"><rect x="4" y="6" width="192" height="6" rx="3" fill="#eef0f5"/>'
            '<rect x="%.1f" y="4" width="%.1f" height="10" rx="3" fill="#8b93a5" fill-opacity=".55"/>'
            '<rect x="%.1f" y="4" width="%.1f" height="10" rx="3" fill="%s" fill-opacity=".4"/>'
            '<rect x="%.1f" y="1" width="3" height="16" rx="1.5" fill="%s"/></svg>'
            % (pos(hr[0]), max(3.0, pos(hr[1]) - pos(hr[0])), pos(ar[0]), max(3.0, pos(ar[1]) - pos(ar[0])), C_AI, pos(v) - 1.5, C_INK))


FEAT = {
    "ru": {"par_per_100w": "абзацев на 100 слов", "par_len_mean": "средняя длина абзаца", "par_len_cv": "разброс длины абзацев", "first_par_share": "доля первого абзаца",
           "last_par_share": "доля последнего абзаца", "sent_per_par": "предложений в абзаце", "sent_len_mean": "средняя длина предложения", "sent_len_cv": "разброс длины предложений",
           "short_sent": "короткие предложения (до 6 слов)", "long_sent": "длинные предложения (от 30 слов)", "heading_lines": "строки-заголовки", "list_items": "пункты списков",
           "bold_marks": "выделения жирным", "colon": "двоеточия", "dash": "тире", "semicolon": "точки с запятой", "paren": "скобки", "question": "вопросительные предложения",
           "exclaim": "восклицательные предложения", "quotes": "кавычки", "digits": "числа", "first_person": "первое лицо (я, мы)", "second_person": "обращение на «вы»",
           "opener_div": "разнообразие начал предложений", "opener_rep": "самое частое начало предложения", "stock_opener": "штампованные вводные слова",
           "concl_last": "вывод в последнем абзаце", "comma_per_sent": "запятых на предложение", "triads": "перечисления из трёх", "contrast": "конструкции «не только… но и»",
           "mattr": "разнообразие лексики", "word_len": "средняя длина слова", "caps": "слова с заглавной", "ellipsis": "многоточия", "emoji": "эмодзи", "par_end_q": "абзацы-вопросы"},
    "pl": {"par_per_100w": "akapitów na 100 słów", "par_len_mean": "średnia długość akapitu", "par_len_cv": "zróżnicowanie długości akapitów", "first_par_share": "udział pierwszego akapitu",
           "last_par_share": "udział ostatniego akapitu", "sent_per_par": "zdań w akapicie", "sent_len_mean": "średnia długość zdania", "sent_len_cv": "zróżnicowanie długości zdań",
           "short_sent": "krótkie zdania (do 6 słów)", "long_sent": "długie zdania (od 30 słów)", "heading_lines": "linie-nagłówki", "list_items": "punkty list",
           "bold_marks": "wyróżnienia pogrubieniem", "colon": "dwukropki", "dash": "myślniki", "semicolon": "średniki", "paren": "nawiasy", "question": "zdania pytające",
           "exclaim": "zdania wykrzyknikowe", "quotes": "cudzysłowy", "digits": "liczby", "first_person": "pierwsza osoba (ja, my)", "second_person": "zwrot do „ty/wy”",
           "opener_div": "różnorodność początków zdań", "opener_rep": "najczęstszy początek zdania", "stock_opener": "szablonowe wtrącenia",
           "concl_last": "wniosek w ostatnim akapicie", "comma_per_sent": "przecinków na zdanie", "triads": "wyliczenia po trzy", "contrast": "konstrukcje „nie tylko… ale też”",
           "mattr": "różnorodność słownictwa", "word_len": "średnia długość słowa", "caps": "słowa wielką literą", "ellipsis": "wielokropki", "emoji": "emoji", "par_end_q": "akapity-pytania"},
}

CSS = """
@page{size:A4;margin:16mm 14mm 18mm;@bottom-left{content:"%(footer)s";font:8.5pt 'Segoe UI',Arial,sans-serif;color:#7b8394}
@bottom-right{content:"%(page)s " counter(page) " %(of)s " counter(pages);font:8.5pt 'Segoe UI',Arial,sans-serif;color:#7b8394}}
*{box-sizing:border-box}html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font:10.5pt/1.5 'Segoe UI',Arial,sans-serif;color:%(ink)s;margin:0;background:#fff}
.wrap{max-width:186mm;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid %(acc)s;padding-bottom:8px;margin-bottom:14px}
.logo{font-size:22pt;font-weight:700;letter-spacing:-.5px}.logo span{color:%(acc)s}
.top .ttl{text-align:right;font-size:13pt;font-weight:600}.top .ttl small{display:block;font-size:9pt;font-weight:400;color:%(muted)s}
.meta{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}
.meta div{background:#f3f5fa;border-radius:6px;padding:7px 10px;font-size:9pt;color:%(muted)s;min-width:0}
.meta b{display:block;color:%(ink)s;font-size:10pt;font-weight:600;overflow-wrap:anywhere}
.hero{display:grid;grid-template-columns:200px 1fr;gap:18px;align-items:center;border:1px solid #dfe3ec;border-left:8px solid var(--vc);border-radius:8px;padding:14px 18px;margin-bottom:14px;break-inside:avoid}
.gauge{width:200px;display:block}.hero h2{margin:0 0 4px;font-size:19pt;color:var(--vc)}
.hero .sub{font-size:9.5pt;color:%(muted)s;margin-bottom:8px}.hero p{margin:0;font-size:10.5pt}
.kpis{display:flex;gap:22px;margin-top:10px}.kpis div{font-size:8.5pt;color:%(muted)s}.kpis b{display:block;font-size:15pt;color:%(ink)s;line-height:1.1}
h3{font-size:12.5pt;margin:16px 0 4px;padding-left:10px;border-left:4px solid %(acc)s;break-after:avoid}
.note{font-size:9pt;color:%(muted)s;margin:0 0 8px}
.card{break-inside:avoid;margin-bottom:6px}.chart{width:100%%;height:auto;display:block}
.stack{display:flex;height:26px;border-radius:5px;overflow:hidden;background:#e3e6ee}.stack span{display:block;height:100%%}
.leg{display:flex;gap:18px;font-size:9.5pt;margin-top:6px;flex-wrap:wrap}.leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.smap{font-size:8.5pt}.smr{display:grid;grid-template-columns:22px 1fr 78px;gap:6px;align-items:center;margin:2px 0}
.smr b{color:%(muted)s;font-weight:500;text-align:right}.smr em{font-style:normal;color:%(muted)s}.smr em i{font-style:normal;color:%(acc)s}
.smb{display:flex;gap:1.5px;height:11px}.smb span{border-radius:1.5px;min-width:2px}
table{border-collapse:collapse;width:100%%;font-size:9.5pt;break-inside:auto}tr{break-inside:avoid}
td,th{padding:6px 9px;border-bottom:1px solid #e3e6ee;text-align:left;vertical-align:middle}th{color:%(muted)s;font-weight:500;font-size:8.5pt}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px;break-inside:avoid}.rng{width:200px;height:18px;display:block}
.fl{margin:0;padding:0;list-style:none}.fl li{border-left:4px solid var(--c);background:#f7f8fb;padding:6px 10px;margin:5px 0;border-radius:0 5px 5px 0;break-inside:avoid;font-size:10pt}
.fl li b{color:var(--c);font-variant-numeric:tabular-nums;margin-right:6px}
.txt{font-size:10pt;line-height:1.7;text-align:left;overflow-wrap:anywhere}.txt .s{border-radius:2px;padding:1px 0;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.s.ai{background:rgba(214,52,44,.2)}.s.uncertain{background:rgba(224,161,0,.28)}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chips span{background:#f3f5fa;border-radius:12px;padding:2px 10px;font-size:9pt}
ul.tips{margin:4px 0 0;padding-left:18px}ul.tips li{margin:3px 0}
.foot{margin-top:18px;padding:10px 14px;background:#f3f5fa;border-radius:6px;font-size:9pt;color:%(muted)s;break-inside:avoid}
.toolbar{position:sticky;top:0;background:#fff;padding:8px 0;z-index:5}.toolbar button{font:inherit;padding:8px 16px;cursor:pointer;border:0;background:%(acc)s;color:#fff;border-radius:5px}
@media print{.toolbar{display:none}}
@media screen{body{padding:18px;background:#eef0f5}.wrap{background:#fff;padding:22px 26px;box-shadow:0 2px 14px rgba(0,0,0,.12);border-radius:6px}}
"""


def render_html(rep: dict, lang: str = "ru", toolbar: bool = False) -> str:
    """Самодостаточный HTML-отчёт (графики — inline SVG)."""
    t = T.get(lang) or T["ru"]
    sents = rep.get("sentences") or []
    verdict = rep.get("verdict") or "uncertain"
    vcol = {"ai": C_AI, "human": C_HUM}.get(verdict, C_UNC)
    pct = rep.get("pct")
    if pct is None:
        pct = (rep.get("ai_share") or 0) * 100
        if verdict == 'human':
            pct = 100 - pct
    an = rep.get("analytics") or {}
    # авторство по словам из предложений (так же, как engine.authorship)
    w = {"ai": 0, "uncertain": 0, "human": 0}
    for s in sents:
        w[s["label"] if s["label"] in w else "human"] += max(1, len(s["text"].split()))
    tot = sum(w.values()) or 1
    sh = {k: v / tot * 100 for k, v in w.items()}
    org = ""
    try:
        from . import config
        ent = config.enterprise() or {}
        org = str(ent.get("organization") or ent.get("org") or ent.get("org_name") or "")
    except Exception:  # noqa: BLE001
        pass
    date = str(rep.get("generated_at") or "")[:16].replace("T", " ")
    meta = [(t["doc"], rep.get("title") or rep.get("filename") or t["untitled"]), (t["date"], date), (t["num"], rep.get("id") or "—"),
            (t["org"] if org else t["mode"], org or rep.get("mode") or "—")]
    if rep.get("filename") and rep.get("title"):
        meta[3] = (t["file"], rep["filename"])
    meta_html = "".join("<div>%s<b>%s</b></div>" % (_e(k), _e(v)) for k, v in meta)
    if rep.get('analysis_scope') in ('single','subset'):
        label = {'ru':'Выбранные модели','pl':'Wybrane modele','en':'Selected models'}.get(lang,'Selected models')
        meta_html += '<div>%s<b>%s</b></div>' % (_e(label),_e(', '.join(rep.get('models_used') or [])))
    kpis = '<div><b>%s</b>%s</div><div><b>%s</b>%s</div><div><b>%s</b>%s</div>' % (
        _e(an.get("words") or rep.get("words")), _e(t["words"]), _e(len(sents)), _e(t["sentences"]),
        '—' if rep.get('heatmap_available') is False else '%.0f%%' % ((rep.get('ai_share') or 0)*100), _e(t["ai_share"]))
    summ = t["s_" + (verdict if verdict in ("ai", "human") else "uncertain")]
    stack = ('<div class="stack"><span style="width:%.2f%%;background:%s"></span><span style="width:%.2f%%;background:%s"></span><span style="width:%.2f%%;background:%s"></span></div>'
             '<div class="leg"><span><i style="background:%s"></i>%s %.0f%%</span><span><i style="background:%s"></i>%s %.0f%%</span><span><i style="background:%s"></i>%s %.0f%%</span></div>'
             % (sh["human"], C_HUM, sh["uncertain"], C_UNC, sh["ai"], C_AI, C_HUM, _e(t["a_human"]), sh["human"], C_UNC, _e(t["a_mixed"]), sh["uncertain"], C_AI, _e(t["a_ai"]), sh["ai"]))
    tl, vi = _timeline(sents, t), _violin(rep, t)
    if rep.get('heatmap_available') is False:
        unavailable = {'ru':'Подсветка предложений недоступна для выбранной модели.',
                       'pl':'Podświetlanie zdań jest niedostępne dla wybranego modelu.',
                       'en':'Sentence heatmap is unavailable for the selected model.'}.get(lang)
        stack = tl = vi = '<p class="note">%s</p>' % _e(unavailable)
    smap = _structure_map(rep.get("structure_layout") or [], t)
    notable = [f for f in (rep.get("structure_notable") or []) if f.get("human_range")]
    if notable:
        rows = "".join("<tr><td>%s</td><td class=\"num\">%s</td><td>%s</td></tr>" % (_e(FEAT.get(lang, {}).get(f.get("key"), f.get("name"))), _e(f.get("value")), _range_row(f)) for f in notable[:10])
        feat = '<table><tr><th></th><th class="num"></th><th></th></tr>%s</table>' % rows
    else:
        feat = '<p class="note">%s</p>' % _e(t["ft_none"])
    stock = "".join("<span>%s ×%s</span>" % (_e(a[0]), _e(a[1])) for a in (an.get("stock_phrases") or [])[:8]) or _e(t["none"])
    repeated = "".join("<span>%s ×%s</span>" % (_e(a[0]), _e(a[1])) for a in (an.get("repeated_phrases") or [])[:6]) or _e(t["none"])
    metrics = [(t["m_words"], an.get("words")), (t["m_sent"], an.get("sentences")), (t["m_par"], an.get("paragraphs")), (t["m_avg"], an.get("avg_sentence_words")),
               (t["m_burst"], an.get("burstiness")), (t["m_div"], an.get("lexical_diversity")), (t["m_stock"], an.get("stock_per_1000"))]
    mrows = "".join('<tr><td>%s</td><td class="num"><b>%s</b></td></tr>' % (_e(k), _e(v if v is not None else "—")) for k, v in metrics)
    voters = rep.get("voters") or {}
    vrows = "".join('<tr><td>%s</td><td class="num"><b>%s</b></td></tr>' % (_e(k), _e(round(v, 2) if isinstance(v, (int, float)) else v))
                    for k, v in voters.items() if isinstance(v, (int, float)))
    flagged = sorted([s for s in sents if s["p_ai"] >= 0.65], key=lambda s: -s["p_ai"])[:12]
    flagged.sort(key=lambda s: s["n"])
    fl = "".join('<li style="--c:%s"><b>%d%%</b>%s</li>' % (_col(s["p_ai"]), round(s["p_ai"] * 100), _e(s["text"])) for s in flagged)
    fl = '<ul class="fl">%s</ul>' % fl if fl else '<p class="note">%s</p>' % _e(t["fl_none"])
    marked = " ".join('<span class="s %s">%s</span>' % (s["label"] if s["label"] in ("ai", "uncertain") else "h", _e(s["text"])) for s in sents)
    if not marked:
        marked = _e(rep.get("text") or "")
    tips = "".join("<li>%s</li>" % _e(t[k]) for k in ("t1", "t2", "t3", "t4"))
    css = CSS % {"ink": C_INK, "muted": C_MUTED, "acc": C_ACC, "footer": t["footer"], "page": t["page"], "of": t["of"]}
    bar = '<div class="toolbar"><button onclick="window.print()">%s</button></div>' % _e(t["print"]) if toolbar else ""
    return """<!doctype html><html lang="%(lang)s"><head><meta charset="utf-8"><title>%(title)s — Linda-Pro</title><style>%(css)s</style></head>
<body style="--vc:%(vcol)s"><div class="wrap">%(bar)s
<div class="top"><div class="logo">Linda<span>-Pro</span></div><div class="ttl">%(ttl)s<small>v%(ver)s</small></div></div>
<div class="meta">%(meta)s</div>
<div class="hero">%(gauge)s<div><h2>%(vtxt)s</h2><div class="sub">%(ai_prob)s</div><p>%(summ)s</p><div class="kpis">%(kpis)s</div></div></div>
<h3>%(authorship)s</h3><div class="card">%(stack)s<p class="note" style="margin-top:6px">%(a_note)s</p></div>
<h3>%(timeline)s</h3><div class="card">%(tl)s<p class="note">%(tl_note)s</p></div>
<h3>%(violin)s</h3><div class="card">%(vi)s<p class="note">%(vi_note)s</p></div>
<h3>%(structure)s</h3><p class="note">%(st_note)s</p>%(smap)s
<h3>%(features)s</h3><p class="note">%(ft_note)s</p>%(feat)s
<div class="two"><div><h3>%(metrics)s</h3><table>%(mrows)s</table></div><div>%(models_block)s</div></div>
<h3>%(stock_h)s</h3><div class="chips">%(stock)s</div><h3>%(rep_h)s</h3><div class="chips">%(repeated)s</div>
<h3>%(flagged)s</h3>%(fl)s
<h3>%(marked_h)s</h3><p class="note">%(marked_note)s</p><div class="txt">%(marked)s</div>
<h3>%(teacher)s</h3><ul class="tips">%(tips)s</ul>
<div class="foot"><b>%(method)s.</b> %(me)s</div>
</div></body></html>""" % {
        "lang": lang, "title": _e(t["title"]), "css": css, "vcol": vcol, "bar": bar, "ttl": _e(t["title"]), "ver": _e(rep.get("app_version")),
        "meta": meta_html, "gauge": _gauge(float(pct), vcol), "vtxt": _e(t["v_" + (verdict if verdict in ("ai", "human") else "uncertain")]),
        "ai_prob": _e(t["ai_prob" if verdict == 'uncertain' else "origin_prob"]), "summ": _e(summ), "kpis": kpis, "authorship": _e(t["authorship"]), "stack": stack, "a_note": _e(t["a_note"]),
        "timeline": _e(t["timeline"]), "tl": tl, "tl_note": _e(t["tl_note"]), "violin": _e(t["violin"]), "vi": vi, "vi_note": _e(t["vi_note"]),
        "structure": _e(t["structure"]), "st_note": _e(t["st_note"]), "smap": smap, "features": _e(t["features"]), "ft_note": _e(t["ft_note"]), "feat": feat,
        "metrics": _e(t["metrics"]), "mrows": mrows, "stock_h": _e(t["stock"]), "stock": stock, "rep_h": _e(t["rep"]), "repeated": repeated,
        "models_block": ('<h3>%s</h3><p class="note">%s</p><table>%s</table>' % (_e(t["models"]), _e(t["models_note"]), vrows)) if vrows else "",
        "flagged": _e(t["flagged"]), "fl": fl, "marked_h": _e(t["marked"]), "marked_note": _e(t["marked_note"]), "marked": marked,
        "teacher": _e(t["teacher"]), "tips": tips, "method": _e(t["method"]),
        "me": _e(t["me"]) if rep.get('analysis_scope','ensemble')=='ensemble' else _e(rep.get('disclaimer') or ''),
    }


def pdf_available() -> bool:
    import importlib.util
    return importlib.util.find_spec('fpdf') is not None


def to_pdf_bytes(rep: dict, lang: str = 'ru', timeout: int = 90) -> bytes:
    from .report import _to_pdf_bytes_fpdf
    return _to_pdf_bytes_fpdf(rep,lang)
