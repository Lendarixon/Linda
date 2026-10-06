# -*- coding: utf-8 -*-
"""Краткая справка о проверке на одну страницу A4 (для преподавателя, редактора, руководителя): вердикт, что он значит, ключевые цифры,
три самых подозрительных предложения и оговорка, что это не доказательство. Тот же движок fpdf2 и шрифты, что у полного отчёта."""
from __future__ import annotations

import importlib.util

from . import report as _r


def to_short_pdf_bytes(rep: dict, lang: str | None = None) -> bytes:
    if importlib.util.find_spec("fpdf") is None:
        raise RuntimeError("PDF-библиотека не установлена")
    from fpdf import FPDF

    lang = _r._report_lang(lang)
    d = _r._report_tr(lang)
    T = lambda k, **kw: str(d.get(k, k)).format(**kw) if kw else str(d.get(k, k))  # noqa: E731
    verdict = rep.get("verdict") or "uncertain"
    key = {"ai": "ai", "human": "hum"}.get(verdict, "unc")
    sents = rep.get("sentences") or []
    tot_w = sum(max(1, len((s.get("text") or "").split())) for s in sents) or 1
    ai_w = sum(max(1, len((s.get("text") or "").split())) for s in sents if s.get("label") == "ai")
    words = rep.get("words") or tot_w
    try:
        from . import config as _cfg

        ver, org = _cfg.APP_VERSION, (_cfg.enterprise() or {}).get("org_name") or ""
    except Exception:  # noqa: BLE001
        ver, org = rep.get("app_version") or "", ""
    date_s = str(rep.get("generated_at") or "")[:16].replace("T", " ")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, 15)
    pdf.set_margins(18, 16, 18)
    fam = _r._pdf_fonts(pdf)
    uni = fam != "Helvetica"
    if not uni and lang in ("ru", "pl"):
        raise RuntimeError("Windows Unicode fonts are unavailable; restore Segoe UI or Arial")
    S = (lambda s: str(s if s is not None else "")) if uni else _r._latin
    pdf.add_page()
    B = "B" if uni else ""

    pdf.set_font(fam, B, 20)
    pdf.cell(0, 10, S("Linda-Pro"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, S("%s  ·  v%s  ·  %s" % (T("pdf_short_title"), ver, date_s)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 80, 239)
    pdf.set_line_width(0.8)
    pdf.line(18, pdf.get_y() + 1, 192, pdf.get_y() + 1)
    pdf.ln(5)
    doc = rep.get("title") or rep.get("filename") or "—"
    pdf.set_font(fam, "", 11)
    pdf.multi_cell(0, 6, S("%s: %s" % (T("pdf_doc"), doc)), new_x="LMARGIN", new_y="NEXT")
    if org:
        pdf.multi_cell(0, 6, S("%s: %s" % (T("pdf_org"), org)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # вердикт-плашка
    color = {"ai": (200, 30, 40), "hum": (31, 157, 115), "unc": (185, 120, 0)}[key]
    pdf.set_fill_color(*color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fam, B, 22)
    pdf.cell(0, 18, S("  " + T("sv_%s_t" % key)), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font(fam, "", 12)
    pdf.multi_cell(0, 6.5, S(T("sv_%s_a" % key)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ключевые цифры
    pdf.set_font(fam, B, 12)
    pdf.cell(0, 7, S(T("pdf_short_figures")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, "", 11)
    pct = rep.get("pct")
    rows = [(T("pdf_short_words"), "%s" % words), (T("pdf_short_ai_share"), "%d%%" % round(100 * ai_w / tot_w)), (T("pdf_mode"), str(rep.get("mode") or "—"))]
    if pct is not None:
        rows.insert(0, (T("pdf_short_conf"), "%s%%" % pct))
    for k, v in rows:
        pdf.cell(95, 6.5, S(k), border="B")
        pdf.cell(0, 6.5, S(v), border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # самые подозрительные предложения
    top = sorted([s for s in sents if (s.get("p_ai") or 0) >= 0.5], key=lambda s: -(s.get("p_ai") or 0))[:3]
    if top and verdict != "human":
        pdf.set_font(fam, B, 12)
        pdf.cell(0, 7, S(T("sv_why")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(fam, "", 10.5)
        for s in top:
            t = (s.get("text") or "").strip()
            t = t if len(t) <= 220 else t[:217] + "…"
            pdf.multi_cell(0, 5.5, S("%d%%  “%s”" % (round(100 * (s.get("p_ai") or 0)), t)), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(3)

    # оговорка
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(fam, B, 10.5)
    pdf.cell(0, 6, S(T("pdf_short_limits_h")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, "", 10)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(0, 5.3, S(T("pdf_short_limits")), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
