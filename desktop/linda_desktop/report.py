# -*- coding: utf-8 -*-
"""Отчёты о проверке для корпоративных клиентов: HTML (печать/PDF через браузер),
JSON, CSV. PDF-файл — только если в окружении уже есть PDF-библиотека (fpdf);
ничего не скачиваем и не устанавливаем.

Отчёт строится из сохранённой проверки (history.get) + analytics.analyze +
structure.profile. Всё локально, тексты никуда не отправляются."""
from __future__ import annotations

import csv
import html
import importlib.util
import io
import json
import time
from datetime import datetime

from . import analytics, config, report_pdf, structure

# Подписи verdict на русском для печатного отчёта
VERDICT_RU = {"ai": "Вероятно, ИИ", "human": "Вероятно, человек", "uncertain": "Неопределённо"}
LABEL_RU = {"ai": "ИИ", "human": "Человек", "uncertain": "Неопределённо"}

DISCLAIMER_RU = ("Вероятностная оценка, а не доказательство. Не используйте вердикт "
                 "как единственное основание для решений о человеке (учебные, кадровые, юридические вопросы).")


def pdf_available() -> bool:
    """Есть ли уже установленная PDF-библиотека (без pip-установок)."""
    if report_pdf.pdf_available():
        return True
    return importlib.util.find_spec("fpdf") is not None


def _sentences_of(result: dict) -> list[dict]:
    out = []
    for i, s in enumerate(result.get("sentences") or []):
        out.append({"n": i + 1, "label": s.get("label", "human"),
                    "p_ai": round(float(s.get("p_ai", 0.0)), 3), "text": s.get("text", "")})
    return out


def build_report(text: str, result: dict, meta: dict | None = None) -> dict:
    """Собрать словарь отчёта из текста и результата анализа."""
    meta = meta or {}
    sents = _sentences_of(result)
    tot = sum(max(1, len(s["text"].split())) for s in sents) or 1
    ai_w = sum(max(1, len(s["text"].split())) for s in sents if s["label"] == "ai")
    try:
        an = analytics.analyze(text, result.get("sentences"))
    except Exception:  # noqa: BLE001 — аналитика не должна ронять отчёт
        an = {"words": len(text.split())}
    try:
        st = structure.profile(text, result.get("sentences"))
        notable = [f for f in st.get("features", []) if f.get("position") not in (None, "in_human_range")]
    except Exception:  # noqa: BLE001
        st, notable = {"features": [], "layout": []}, []
    auth = result.get("authorship") or {}
    pct = meta.get("pct")
    if result.get("p_ai") is not None:
        p = float(result["p_ai"])
        pct = min(99, max(1, round(100 * (1 - p if result.get("verdict") == "human" else p))))
    elif pct is not None and result.get('verdict') == 'human':
        pct = 100 - pct
    return {
        "app": config.APP_NAME, "app_version": config.APP_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "id": meta.get("id"), "title": meta.get("title") or "", "filename": meta.get("filename") or "",
        "mode": meta.get("mode") or "", "words": len(text.split()),
        "verdict": result.get("verdict"), "verdict_ru": VERDICT_RU.get(result.get("verdict"), ""),
        "pct": pct, "p_ai":result.get('p_ai'),"ai_share": round(ai_w / tot, 4) if result.get('heatmap_available',True) else None,
        "heatmap_available":result.get('heatmap_available',True),"analysis_scope":result.get('analysis_scope','ensemble'),"models_used":result.get('models_used'),"models_executed":result.get('models_executed'),
        "authorship": auth, "voters": result.get("voters"), "lite": "Linda-Speed" in str((result.get("routing") or {}).get("config") or ""), "ens_z": result.get("ens_z"),
        "sentences": sents, "analytics": an,
        "structure_reference": st.get("reference"), "structure_notable": notable[:12], "structure_layout": (st.get("layout") or [])[:60],
        "disclaimer": DISCLAIMER_RU, "text": text,
    }


def report_for_check(check: dict) -> dict:
    """Отчёт по сохранённой проверке из истории."""
    return build_report(check["text"], check["result"],
                        {"id": check.get("id"), "title": check.get("title"),
                         "filename": check.get("filename"), "mode": check.get("mode"), "pct": check.get("pct")})


def to_json_str(rep: dict) -> str:
    """JSON-отчёт (полный, включая текст и предложения)."""
    return json.dumps(rep, ensure_ascii=False, indent=2)


def to_csv(rep: dict) -> str:
    """CSV-отчёт: сначала сводка (ключ,значение), затем таблица предложений."""
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM, чтобы Excel открыл кириллицу правильно
    w = csv.writer(buf)
    def cell(value):
        if isinstance(value, str) and value.lstrip(' \t\r\n\ufeff').startswith(('=', '+', '-', '@')):
            return "'" + value
        return value
    for k in ("app_version", "generated_at", "id", "title", "mode", "words", "verdict", "verdict_ru", "p_ai", "pct", "ai_share", "analysis_scope", "models_used", "heatmap_available"):
        value = rep.get(k)
        if isinstance(value,list):
            value = ', '.join(str(item) for item in value)
        w.writerow([k, cell(value)])
    w.writerow([])
    w.writerow(["n", "label", "label_ru", "p_ai", "text"])
    for s in rep["sentences"]:
        w.writerow([s["n"], s["label"], LABEL_RU.get(s["label"], s["label"]), s["p_ai"], cell(s["text"])])
    return buf.getvalue()


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _to_html_legacy(rep: dict) -> str:
    """Печатный HTML-отчёт: открывается в браузере, печать/PDF — через диалог печати."""
    rows = "\n".join(
        '<tr><td>%d</td><td class="lb-%s">%s</td><td>%.0f%%</td><td>%s</td></tr>'
        % (s["n"], s["label"], LABEL_RU.get(s["label"], s["label"]), s["p_ai"] * 100, _esc(s["text"]))
        for s in rep["sentences"][:2000])
    an = rep.get("analytics") or {}
    stock = ", ".join("%s ×%s" % (a[0], a[1]) for a in (an.get("stock_phrases") or [])[:8])
    notable = "\n".join("<li>%s: <b>%s</b> (типично для человека %s)</li>"
                        % (_esc(f.get("name")), _esc(f.get("value")), _esc(f.get("human_median")))
                        for f in (rep.get("structure_notable") or []))
    voters = rep.get("voters") or {}
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Отчёт Linda — %(title)s</title>
<style>
body{font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;padding:24px;color:#111}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:26px;border-bottom:2px solid #0050ef;padding-bottom:4px}
table{border-collapse:collapse;width:100%%;font-size:.85rem}td,th{border:1px solid #ccc;padding:5px 7px;text-align:left;vertical-align:top}
th{background:#f0f2f8}.lb-ai{background:#fde2e4}.lb-uncertain{background:#fff3cd}
.meta{display:grid;grid-template-columns:180px 1fr;gap:4px 12px;font-size:.9rem}.meta dt{color:#555}.meta dd{margin:0}
.note{background:#f7f7f7;border-left:4px solid #0050ef;padding:10px 14px;font-size:.85rem}
.toolbar{margin:12px 0;display:flex;gap:8px}button{padding:8px 16px;cursor:pointer}
@media print{.toolbar{display:none}body{padding:0}}
</style></head><body>
<div class="toolbar"><button onclick="window.print()">🖨 Печать / сохранить PDF</button></div>
<h1>Отчёт о проверке текста — Linda %(app_version)s</h1>
<dl class="meta">
<dt>Документ</dt><dd>%(title)s</dd><dt>Файл</dt><dd>%(filename)s</dd>
<dt>Дата</dt><dd>%(generated_at)s</dd><dt>Проверка №</dt><dd>%(id)s</dd>
<dt>Режим</dt><dd>%(mode)s</dd><dt>Слов</dt><dd>%(words)s</dd>
<dt>Вердикт</dt><dd><b>%(verdict_ru)s</b> (%(verdict)s)</dd>
<dt>Доля ИИ-предложений</dt><dd>%(ai_share)s</dd>
</dl>
<p class="note">%(disclaimer)s Текст обработан локально на этом компьютере и никуда не отправлялся.</p>
<h2>Оценки моделей (выше = ИИ)</h2>
<p>%(v_names)s</p>
<h2>Аналитика текста</h2>
<p>Средняя длина предложения: %(avg_sent)s слов · Burstiness: %(burst)s · Лексическое разнообразие: %(div)s · Штампы: %(stock)s</p>
<h2>Структура (вне типичного для человека)</h2>
<ul>%(notable)s</ul>
<h2>Предложения (%(n_sent)s)</h2>
<table><tr><th>№</th><th>Метка</th><th>P(ИИ)</th><th>Текст</th></tr>
%(rows)s</table>
</body></html>""" % {
        "title": _esc(rep.get("title") or "без названия"), "app_version": _esc(rep.get("app_version")),
        "filename": _esc(rep.get("filename")), "generated_at": _esc(rep.get("generated_at")),
        "id": _esc(rep.get("id")), "mode": _esc(rep.get("mode")), "words": _esc(rep.get("words")),
        "verdict_ru": _esc(rep.get("verdict_ru")), "verdict": _esc(rep.get("verdict")),
        "ai_share": "%.1f%%" % ((rep.get("ai_share") or 0) * 100),
        "disclaimer": _esc(rep.get("disclaimer")),
        "v_names": ("Linda Loupe: <b>%s</b> · Stylo-D: <b>%s</b>" % (_esc(voters.get("linda_essay")), _esc(voters.get("stylo7c")))) if rep.get("lite") else ("Linda-Essay 1.3: <b>%s</b> · Linda-Multi 1.3: <b>%s</b> · Stylo-D: <b>%s</b>" % (_esc(voters.get("linda_essay")), _esc(voters.get("linda_multi_v2")), _esc(voters.get("stylo7c")))),
        "avg_sent": _esc(an.get("avg_sentence_words")), "burst": _esc(an.get("burstiness")),
        "div": _esc(an.get("lexical_diversity")), "stock": _esc(stock or "—"),
        "notable": notable or "<li>Всё в пределах типичного для человека.</li>",
        "n_sent": len(rep["sentences"]), "rows": rows or '<tr><td colspan="4">Нет данных.</td></tr>',
    }


def _pdf_fonts(pdf) -> str:
    """Системный TTF с кириллицей и польскими буквами (без скачиваний); fallback — Helvetica."""
    import os

    cands = [
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    font_dir = __import__('pathlib').Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
    cands = [(str(font_dir/'segoeui.ttf'),str(font_dir/'segoeuib.ttf')),(str(font_dir/'arial.ttf'),str(font_dir/'arialbd.ttf'))]+cands
    for reg, bold in cands:
        if os.path.isfile(reg):
            try:
                pdf.add_font("Corp", "", reg)
                try:
                    if os.path.isfile(bold):
                        pdf.add_font("Corp", "B", bold)
                except Exception:  # noqa: BLE001 — без bold выживем
                    pass
                return "Corp"
            except Exception:  # noqa: BLE001 — пробуем следующий шрифт
                continue
    return "Helvetica"


def _latin(s: str) -> str:
    return "".join(c if ord(c) < 128 else "?" for c in str(s if s is not None else ""))


def _report_lang(lang: str | None) -> str:
    if lang in ("ru", "pl", "en"):
        return lang
    try:
        from .engine import load_settings

        lang = (load_settings() or {}).get("language", "ru")
    except Exception:  # noqa: BLE001
        lang = "ru"
    return lang if lang in ("ru", "pl", "en") else "ru"


def _report_tr(lang: str) -> dict:
    try:
        from . import i18n as _i18n

        return _i18n.load_lang(lang)
    except Exception:  # noqa: BLE001
        return {}


def _verdict_label(verdict: str, d: dict) -> str:
    if verdict == "ai":
        return str(d.get("ui_ai_gen") or "AI")
    if verdict == "human":
        return str(d.get("ui_human_w") or d.get("ui_human") or "Human")
    return str(d.get("ui_unc") or "Uncertain")


def _verdict_color(verdict: str) -> tuple[int, int, int]:
    if verdict == "ai":
        return (229, 20, 0)
    if verdict == "human":
        return (74, 125, 14)
    return (179, 77, 0)


def _label_color(p: float) -> tuple[int, int, int]:
    if p >= 0.58:
        return (229, 20, 0)
    if p >= 0.38:
        return (250, 104, 0)
    return (96, 169, 23)


def _to_pdf_bytes_fpdf(rep: dict, lang: str | None = None) -> bytes:
    """Красивый PDF-отчёт A4: шапка, вердикт-плашка, шкала, векторные графики
    (rect/line средствами fpdf), таблица метрик, подозрительные предложения,
    пояснения, блок организации, колонтитулы. Многостраничный, с переносами."""
    if importlib.util.find_spec('fpdf') is None:
        raise RuntimeError("PDF-библиотека не установлена: используйте печать HTML-отчёта (Печать → сохранить PDF)")
    from fpdf import FPDF

    lang = _report_lang(lang)
    d = _report_tr(lang)
    T = lambda k: str(d.get(k, k))  # noqa: E731
    verdict = rep.get("verdict") or "uncertain"

    # Процент ИИ: pct из истории, иначе логистика ens_z, иначе доля ИИ-слов
    pct = rep.get("pct")
    try:
        if pct is None and rep.get("ens_z") is not None:
            import math as _m

            pct = min(99, max(1, round(100 / (1 + _m.exp(-1.7 * float(rep["ens_z"]))))))
        if pct is None:
            pct = round(float(rep.get("ai_share") or 0) * 100)
        pct = int(max(0, min(100, pct)))
    except Exception:  # noqa: BLE001
        pct = 0

    sents = rep.get("sentences") or []
    an = rep.get("analytics") or {}
    voters = rep.get("voters") or {}
    auth = rep.get("authorship") or {}
    # Доли авторства по словам (fallback из предложений)
    tot_w = sum(max(1, len((s.get("text") or "").split())) for s in sents) or 1
    ai_w = sum(max(1, len((s.get("text") or "").split())) for s in sents if s.get("label") == "ai")
    un_w = sum(max(1, len((s.get("text") or "").split())) for s in sents if s.get("label") == "uncertain")
    try:
        ai_share = float(auth.get("ai_share", ai_w / tot_w))
        un_share = float(auth.get("uncertain_share", un_w / tot_w))
    except Exception:  # noqa: BLE001
        ai_share, un_share = ai_w / tot_w, un_w / tot_w
    hu_share = max(0.0, 1.0 - ai_share - un_share)
    try:
        from . import config as _cfg

        org = (_cfg.enterprise() or {}).get("org_name") or ""
        ver = _cfg.APP_VERSION
    except Exception:  # noqa: BLE001
        org, ver = "", rep.get("app_version") or ""
    date_s = str(rep.get("generated_at") or "")[:16].replace("T", " ")

    class _RPDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            try:
                self.set_font(self._fam, size=8)
                self.set_text_color(120, 120, 120)
                self.cell(0, 6, self._head_txt, align="R", new_x="LMARGIN", new_y="NEXT")
                self.set_draw_color(200, 200, 200)
                self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
                self.ln(2)
            except Exception:  # noqa: BLE001
                pass

        def footer(self):
            try:
                self.set_y(-15)
                self.set_font(self._fam, size=8)
                self.set_text_color(120, 120, 120)
                self.cell(0, 8, "Linda %s  |  %s  |  %d/{nb}" % (ver, date_s, self.page_no()), align="C")
            except Exception:  # noqa: BLE001
                pass

    pdf = _RPDF(format="A4")
    pdf.alias_nb_pages("{nb}")
    pdf.set_auto_page_break(True, 20)
    pdf.set_margins(15, 15, 15)
    fam = _pdf_fonts(pdf)
    uni = fam != "Helvetica"
    if not uni and lang in ('ru','pl'):
        raise RuntimeError('Windows Unicode fonts are unavailable; restore Segoe UI or Arial')
    S = (lambda s: str(s if s is not None else "")) if uni else _latin
    pdf._fam = fam  # type: ignore[attr-defined]
    pdf._head_txt = S("Linda %s  ·  %s" % (ver, date_s))  # type: ignore[attr-defined]
    pdf.add_page()

    def h1(t: str):
        pdf.set_font(fam, "B" if uni else "", 13)
        pdf.set_text_color(0, 80, 239)
        pdf.multi_cell(0, 7, S(t), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

    def need(h: float):
        if pdf.get_y() + h > pdf.h - 20:
            pdf.add_page()

    # --- фирменная шапка ---
    pdf.set_font(fam, "B" if uni else "", 18)
    pdf.cell(0, 10, S("Linda"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, S("%s  ·  v%s  ·  %s  ·  lang:%s" % (T("pdf_title"), ver, date_s, lang)),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 80, 239)
    pdf.set_line_width(0.8)
    pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
    pdf.ln(4)
    # --- организация / номер / дата ---
    meta_lines = [
        "%s: %s" % (T("pdf_doc"), rep.get("title") or rep.get("filename") or "—"),
        "%s: %s    %s: %s    %s: %s" % (T("pdf_no"), rep.get("id") or "—",
                                        T("pdf_date"), date_s, T("pdf_mode"), rep.get("mode") or "—"),
    ]
    if org:
        pdf.set_fill_color(240, 242, 248)
        pdf.set_font(fam, "B" if uni else "", 11)
        need(16)
        pdf.multi_cell(0, 7, S("%s: %s" % (T("pdf_org"), org)), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    pdf.set_font(fam, "", 10)
    for ln in meta_lines:
        pdf.multi_cell(0, 6, S(ln), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- крупный вердикт цветной плашкой ---
    vc = _verdict_color(verdict)
    need(24)
    pdf.set_fill_color(*vc)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(fam, "B" if uni else "", 15)
    pdf.multi_cell(0, 12, S("%s: %s  ·  %d%%" % (T("pdf_verdict"), _verdict_label(verdict, d), pct)),
                   align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # --- шкала/полоса вероятности ---
    pdf.set_font(fam, "B" if uni else "", 11)
    pdf.cell(0, 6, S(T("pdf_ai_prob")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fam, "", 9)
    need(16)
    bx, bw, bh = 15, 180, 8
    by = pdf.get_y() + 1
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(bx, by, bw, bh, style="F")
    pdf.set_fill_color(*vc)
    probability = rep.get('p_ai')
    probability = max(0.0,min(1.0,float(probability))) if probability is not None else pct/100
    pdf.rect(bx, by, bw * probability, bh, style="F")
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(bx, by, bw, bh, style="D")
    pdf.set_xy(bx, by + bh + 1)
    pdf.set_font(fam, "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(bw, 4, S("0%              50%              100%"))
    pdf.set_text_color(0, 0, 0)
    pdf.ln(7)

    # --- диаграмма авторства (полосовая) ---
    h1(T("pdf_auth"))
    need(22)
    ax, aw, ah = 15, 180, 10
    ay = pdf.get_y() + 1
    leg = '—'
    if rep.get('heatmap_available',True):
        pdf.set_fill_color(96, 169, 23)
        pdf.rect(ax, ay, aw * hu_share, ah, style="F")
        pdf.set_fill_color(250, 104, 0)
        pdf.rect(ax + aw * hu_share, ay, aw * un_share, ah, style="F")
        pdf.set_fill_color(229, 20, 0)
        pdf.rect(ax + aw * (hu_share + un_share), ay, aw * ai_share + 0.5, ah, style="F")
        pdf.set_draw_color(0, 0, 0)
        pdf.rect(ax, ay, aw, ah, style="D")
        pdf.set_xy(ax, ay + ah + 1)
        pdf.set_font(fam, "", 9)
        leg = "%s %d%%   %s %d%%   %s %d%%" % (
            d.get("auth_hum", "human"), round(hu_share * 100),
            d.get("auth_mixed", "mixed"), round(un_share * 100),
            d.get("auth_ai", "AI"), round(ai_share * 100))
    pdf.multi_cell(0, 5, S(leg), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- график 'Вероятность ИИ по ходу текста' (векторные столбики) ---
    h1(T("pdf_along"))
    pdf.set_font(fam, "", 9)
    pdf.multi_cell(0, 5, S(T("pdf_along_note")), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    if sents:
        per = max(1, (len(sents) + 59) // 60)
        groups = [sents[i:i + per] for i in range(0, len(sents), per)][:60]
        vals = [max(float(g.get("p_ai") or 0) for g in grp) for grp in groups]
        n = len(vals)
        need(60)
        cx, cw, chh = 15, 180, 42
        cy = pdf.get_y() + 2
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(cx, cy, cw, chh, style="D")
        for f in (0.5, 1.0):
            yy = cy + chh * (1 - f)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(cx, yy, cx + cw, yy)
        bwdt = cw / max(1, n)
        for i, v in enumerate(vals):
            hh = max(1.2, v * (chh - 2))
            xx = cx + i * bwdt + 0.4
            ww = max(0.8, bwdt - 0.8)
            c = _label_color(v)
            pdf.set_fill_color(*c)
            pdf.rect(xx, cy + chh - 1 - hh, ww, hh, style="F")
        pdf.set_draw_color(0, 0, 0)
        pdf.line(cx, cy + chh - 1, cx + cw, cy + chh - 1)
        pdf.set_xy(cx, cy + chh + 1)
        pdf.set_font(fam, "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(cw, 4, S("1 .. %d (%d)" % (len(sents), len(groups))))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(7)
    else:
        pdf.set_font(fam, "", 10)
        pdf.cell(0, 6, S("—"), new_x="LMARGIN", new_y="NEXT")

    # --- таблица метрик ---
    h1(T("pdf_metrics"))
    stock = ", ".join("%s x%s" % (a[0], a[1]) for a in (an.get("stock_phrases") or [])[:6]) or "—"
    rep_ph = ", ".join("%s x%s" % (a[0], a[1]) for a in (an.get("repeated_phrases") or [])[:3]) or "—"
    rows = [
        (T("pdf_m_words"), str(rep.get("words") or an.get("words") or "—")),
        (T("pdf_m_sents"), str(len(sents) or an.get("sentences") or "—")),
        (T("pdf_m_avg"), str(an.get("avg_sentence_words") or "—")),
        (T("pdf_m_burst"), str(an.get("burstiness") or "—")),
        (T("pdf_m_div"), str(an.get("lexical_diversity") or "—")),
        (T("pdf_m_stock"), S(stock)[:220]),
        (T("pdf_m_rep"), S(rep_ph)[:220]),
    ]
    pdf.set_font(fam, "", 10)
    for i, (k, v) in enumerate(rows):
        need(8)
        pdf.set_fill_color(240, 242, 248 if i % 2 == 0 else 255)
        if uni:
            pdf.set_fill_color(240, 242, 248) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.set_font(fam, "B" if uni else "", 10)
        x0 = pdf.get_x()
        pdf.cell(62, 7, S(k), border=1, fill=True)
        pdf.set_font(fam, "", 10)
        pdf.multi_cell(0, 7, S(v), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    _vn = {"linda_essay": "Linda Loupe", "stylo7c": "Stylo-D"} if rep.get("lite") else {}
    voters_ln = '  ·  '.join('%s: %s' % (_vn.get(name, name), value) for name, value in voters.items() if not (rep.get("lite") and name == "linda_multi_v2"))
    pdf.set_font(fam, "", 9)
    pdf.multi_cell(0, 5, S(voters_ln), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- самые подозрительные предложения с подсветкой ---
    h1(T("pdf_susp"))
    top = sorted([s for s in sents if s.get('label')=='ai'], key=lambda s: -float(s.get("p_ai") or 0))[:8]
    pdf.set_font(fam, "", 10)
    if not top or max(float(s.get("p_ai") or 0) for s in top) < 0.38:
        pdf.multi_cell(0, 6, S(T("pdf_no_susp")), new_x="LMARGIN", new_y="NEXT")
    for s in top:
        p = float(s.get("p_ai") or 0)
        c = _label_color(p)
        need(18)
        pdf.set_font(fam, "B" if uni else "", 10)
        pdf.set_text_color(*c)
        pdf.cell(0, 6, S("#%s  [%d%%]" % (s.get("n"), round(p * 100))), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(fam, "", 10)
        if p >= 0.58:
            pdf.set_fill_color(253, 226, 228)
            pdf.multi_cell(0, 6, S(str(s.get("text") or "")[:600]), fill=True, new_x="LMARGIN", new_y="NEXT")
        elif p >= 0.38:
            pdf.set_fill_color(255, 243, 205)
            pdf.multi_cell(0, 6, S(str(s.get("text") or "")[:600]), fill=True, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.multi_cell(0, 6, S(str(s.get("text") or "")[:600]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    # --- как читать + дисклеймер ---
    h1(T("pdf_how"))
    pdf.set_font(fam, "", 10)
    pdf.multi_cell(0, 6, S(T("pdf_how_text")), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_fill_color(247, 247, 247)
    pdf.set_draw_color(0, 80, 239)
    need(24)
    y0 = pdf.get_y()
    pdf.set_font(fam, "", 10)
    pdf.multi_cell(0, 6, S("%s %s" % (T("pdf_disclaimer"), T("pdf_local"))), fill=True, new_x="LMARGIN", new_y="NEXT")
    # левая акцентная полоса
    try:
        y1 = pdf.get_y()
        pdf.set_fill_color(0, 80, 239)
        pdf.rect(15, y0, 1.5, y1 - y0, style="F")
    except Exception:  # noqa: BLE001
        pass

    from .report_native_sections import append_sections
    append_sections(pdf,rep,lang,fam,S,h1,need)
    out = pdf.output()
    return bytes(out)


LANGS = ("ru", "pl", "en")


def changelog_text(entry: dict, lang: str = "en") -> str:
    """Локализованный текст записи changelog: notes[lang] с fallback на en (задача: польский UI показывал русский текст)."""
    if lang not in LANGS:
        lang = "en"
    n = (entry or {}).get("notes")
    if isinstance(n, dict):
        return str(n.get(lang) or n.get("en") or n.get("ru") or n.get("pl") or "")
    return str((entry or {}).get("notes_%s" % lang) or (entry or {}).get("notes_en")
               or (entry or {}).get("notes") or (entry or {}).get("notes_ru") or "")


def changelog_title(entry: dict, lang: str = "en") -> str:
    """Локализованный заголовок записи changelog с fallback на en."""
    if lang not in LANGS:
        lang = "en"
    t = (entry or {}).get("title")
    if isinstance(t, dict):
        return str(t.get(lang) or t.get("en") or t.get("ru") or t.get("pl") or "")
    return str((entry or {}).get("title_%s" % lang) or (entry or {}).get("title_en")
               or (entry or {}).get("title") or "")


def _norm_entry(e: dict) -> dict:
    """Добить notes/title-словари из плоских полей (notes_ru/notes_en/notes_pl/notes), чтобы фронт с fallback en всегда нашёл текст."""
    e = dict(e or {})
    n = e.get("notes")
    if not isinstance(n, dict):
        d = dict(e.get("notes_i18n") or {}) if isinstance(e.get("notes_i18n"), dict) else {}
        for lang in LANGS:
            v = e.get("notes_%s" % lang)
            if v:
                d.setdefault(lang, v)
        if isinstance(n, str) and n:
            d.setdefault("en", n)
        if d:
            e["notes"] = d
    t = e.get("title")
    if t is not None and not isinstance(t, dict):
        if isinstance(t, str) and t:
            e["title"] = {"en": t}
        else:
            e.pop("title", None)
    else:
        td = dict(e.get("title_i18n") or {}) if isinstance(e.get("title_i18n"), dict) else {}
        for lang in LANGS:
            v = e.get("title_%s" % lang)
            if v:
                td.setdefault(lang, v)
        if td and not isinstance(e.get("title"), dict):
            e["title"] = td
    return e


def changelog_local() -> list[dict]:
    """Локальный CHANGELOG.json: рядом с web/, в data/ или в корне ресурсов."""
    from pathlib import Path

    from . import config as _config

    cands = [_config.resource_dir() / "CHANGELOG.json",
             Path(__file__).resolve().parent / "data" / "CHANGELOG.json",
             _config.resource_dir() / "linda_desktop" / "data" / "CHANGELOG.json"]
    for p in cands:
        try:
            if p.is_file():
                items = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(items, list):
                    return [_norm_entry(x) for x in items if isinstance(x, dict)]
        except Exception:  # noqa: BLE001 — битый файл не роняет статус
            pass
    return []


def changelog_merged(manifest: dict | None) -> list[dict]:
    """Манифест (changelog/notes) поверх локального CHANGELOG.json: новые версии первыми."""
    merged = [_norm_entry(x) for x in changelog_local()]
    seen = {str(x.get("version")) for x in merged}
    if manifest:
        for e in reversed(manifest.get("changelog") or []):  # от старых к новым: insert(0) ставит самую новую первой
            if str(e.get("version")) not in seen:
                item = {"version": e.get("version"), "date": e.get("date", "")}
                for k in ("notes", "notes_ru", "notes_pl", "notes_en", "notes_i18n",
                          "title", "title_ru", "title_pl", "title_en", "title_i18n"):
                    if e.get(k):
                        item[k] = e[k]
                if not item.get("notes") and not item.get("notes_i18n") \
                        and not any(item.get("notes_%s" % lang) for lang in LANGS) \
                        and manifest.get("notes"):
                    item["notes"] = manifest["notes"]
                merged.insert(0, _norm_entry(item))
                seen.add(str(e.get("version")))
        if manifest.get("notes") and str(manifest.get("version")) not in seen:
            merged.insert(0, _norm_entry({"version": manifest.get("version"), "date": manifest.get("released", ""),
                              "notes": {"en": manifest.get("notes", "")},
                              "notes_ru": manifest.get("notes", "")}))
    return merged


def to_html(rep: dict, lang: str | None = None) -> str:
    """Печатный HTML-отчёт нового образца (графики SVG, печать на А4 через диалог браузера)."""
    return report_pdf.render_html(rep, lang if lang in report_pdf.LANGS else "ru", toolbar=True)


def pdf_export(rep: dict, lang: str | None = None) -> tuple[bytes, str]:
    """Bundled native renderer; no external browser or silent layout fallback."""
    return _to_pdf_bytes_fpdf(rep,lang), 'native'


def to_pdf_bytes(rep: dict, lang: str | None = None) -> bytes:
    return pdf_export(rep, lang)[0]
