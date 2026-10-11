# -*- coding: utf-8 -*-
"""Canonical label markup: colors/suspicious lists follow label, not rounded p_ai."""
import inspect
import io

from linda_desktop import report, report_pdf
from pypdf import PdfReader

C_HUM, C_UNC, C_AI = report_pdf.C_HUM, report_pdf.C_UNC, report_pdf.C_AI
T_EN = report_pdf.T["en"]

H_TXT = "Human high score sentence one here."
U_TXT = "Uncertain mid score sentence two here."
A_TXT = "AI low score sentence three here."


def _result(gran="sentence"):
    sents = [
        {"label": "human", "p_ai": 0.9, "text": H_TXT},
        {"label": "uncertain", "p_ai": 0.7, "text": U_TXT},
        {"label": "ai", "p_ai": 0.2, "text": A_TXT},
    ]
    stats = {"total": 3, "ai": 1, "uncertain": 1, "human": 1, "ai_pct": 33,
             "granularity": gran, "thresholds": {"ai": 0.9, "uncertain": 0.5}}
    ref = {"human_hist": [1.0] * 10, "ai_hist": [1.0] * 10, "n_texts": 4, "n_sentences": [2, 2]}
    return sents, stats, ref


def _rep(gran="sentence", verdict="uncertain"):
    sents, stats, ref = _result(gran)
    text = " ".join(s["text"] for s in sents)
    res = {"verdict": verdict, "p_ai": 0.5, "sentences": [dict(s) for s in sents],
           "sentence_stats": dict(stats), "authorship": {}, "voters": {}}
    rep = report.build_report(text, res, {"title": "t", "mode": "m"})
    rep["structure_reference"] = dict(ref)
    rep["structure_layout"] = [{"words": 9, "kind": "text", "sentences": [
        {"label": "human", "p_ai": 0.9, "words": 3},
        {"label": "uncertain", "p_ai": 0.7, "words": 3},
        {"label": "ai", "p_ai": 0.2, "words": 3}]}]
    return rep


def test_sentence_stats_preserved():
    rep = _rep("tokens_sentence")
    assert rep["sentence_stats"]["granularity"] == "tokens_sentence"
    assert rep["sentence_stats"]["thresholds"] == {"ai": 0.9, "uncertain": 0.5}
    assert rep["sentence_stats"]["ai"] == 1


def test_short_pdf_preserves_low_score_ai_label_in_human_document():
    from linda_desktop import report_short
    rep = _rep("tokens_sentence", verdict="human")
    data = report_short.to_short_pdf_bytes(rep, "en")
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == 1
    content = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert A_TXT in content
    assert H_TXT not in content and U_TXT not in content
    assert "AI signals" in content


def test_timeline_bins_canonical_not_numeric():
    rep = _rep()
    tl = report_pdf._timeline(rep["sentences"], T_EN)
    assert tl.count(C_AI) == 1 and tl.count(C_UNC) == 1 and tl.count(C_HUM) == 1


def test_structure_map_uses_chunk_label():
    rep = _rep()
    smap = report_pdf._structure_map(rep["structure_layout"], T_EN)
    assert smap.count(C_AI) == 1 and smap.count(C_UNC) == 1 and smap.count(C_HUM) == 1


def test_flagged_and_marked_use_canonical_ai():
    rep = _rep()
    html = report_pdf.render_html(rep, "en")
    flag_sec = html.split(T_EN["flagged"])[1].split(T_EN["marked"])[0]
    assert A_TXT in flag_sec and H_TXT not in flag_sec and U_TXT not in flag_sec
    assert ('<span class="s ai">%s</span>' % A_TXT) in html
    assert C_AI in flag_sec


def test_violin_hidden_for_tokens_and_kept_for_legacy():
    rep_tok = _rep("tokens_sentence")
    assert report_pdf._violin(rep_tok, T_EN) == ""
    html_tok = report_pdf.render_html(rep_tok, "en")
    assert T_EN["violin"] not in html_tok
    rep_tok2 = _rep("tokens")
    assert report_pdf._violin(rep_tok2, T_EN) == ""
    rep_leg = _rep("sentence")
    assert report_pdf._violin(rep_leg, T_EN) != ""
    assert T_EN["violin"] in report_pdf.render_html(rep_leg, "en")


def test_human_summary_mentions_local_ai_fragments():
    for lang, needle in (("en", "local passages marked as AI"),
                         ("ru", "локальные фрагменты"),
                         ("pl", "lokalne fragmenty")):
        rep = _rep("sentence", verdict="human")
        html = report_pdf.render_html(rep, lang)
        assert needle in html
    html_en = report_pdf.render_html(_rep("sentence", verdict="human"), "en")
    assert "No clear signs" not in html_en


def test_wording_truthful_units():
    for lang in ("en", "ru", "pl"):
        html = report_pdf.render_html(_rep(), lang)
        t = report_pdf.T[lang]
        assert t["ai_share"] in html and t["ai_prob"] in html or t["origin_prob"] in html
        assert t["a_note"] in html and t["marked_note"] in html
    assert "Model AI score" in report_pdf.render_html(_rep(), "en")
    assert "AI-labelled word share" in report_pdf.render_html(_rep(), "en")
    assert "Вероятность ИИ" not in report_pdf.render_html(_rep(), "ru")
    assert "доля слов с меткой ИИ" in report_pdf.render_html(_rep(), "ru")
    legacy = report._to_html_legacy(_rep())
    assert "Доля слов с меткой ИИ" in legacy and "Доля ИИ-предложений" not in legacy


def test_native_helpers_canonical_and_no_label_color_callsites():
    assert report._canon_rgb("ai") == (229, 20, 0)
    assert report._group_top_label([{"label": "human", "p_ai": 0.9}, {"label": "ai", "p_ai": 0.2}]) == "ai"
    top = report._suspicious_top([{"label": "human", "p_ai": 0.9, "n": 1, "text": H_TXT},
                                  {"label": "uncertain", "p_ai": 0.7, "n": 2, "text": U_TXT},
                                  {"label": "ai", "p_ai": 0.2, "n": 3, "text": A_TXT}])
    assert [s["label"] for s in top] == ["ai"]
    assert "_label_color" not in inspect.getsource(report._to_pdf_bytes_fpdf)
    import re
    for fn in (report_pdf._timeline, report_pdf._structure_map, report_pdf.render_html):
        assert not re.search(r"(?<![A-Za-z0-9_])_col\(", inspect.getsource(fn))
