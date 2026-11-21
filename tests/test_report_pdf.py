# -*- coding: utf-8 -*-
"""PDF-отчёт с графиками: EN/RU/PL заголовок %PDF, размер >10 КБ, стойкость к 20000 словам."""
import pytest

from linda_desktop import report

fpdf = pytest.importorskip("fpdf")


@pytest.mark.parametrize("verdict,p_ai,expected", [("human", .14, 86), ("ai", .94, 94), ("uncertain", .48, 48)])
def test_report_confidence_uses_calibrated_probability(verdict, p_ai, expected):
    rep = report.build_report("Sample text.", {"verdict": verdict, "p_ai": p_ai, "sentences": []}, {"pct": 99})
    assert rep["pct"] == expected

TEXTS = {
    "en": ("The cat sat on the mat. Moreover, furthermore, additionally, in conclusion, "
           "the tapestry of modern science unfolds. Delve into the realm of knowledge. "
           "It is important to note that results vary. " * 6),
    "ru": ("Кот сидел на коврике. Кроме того, более того, таким образом, в заключение, "
           "важно отметить, что результаты различаются. Следует отметить ключевую роль метода. "
           "В современном мире данные решают всё. " * 6),
    "pl": ("Kot siedział na macie. Ponadto, co więcej, podsumowując, warto zauważyć, "
           "że wyniki się różnią. Należy podkreślić kluczową rolę metody. "
           "W dzisiejszym świecie dane decydują o wszystkim. " * 6),
}


def _rep(text, verdict="ai"):
    words = text.split()
    sents, idx, n = [], 0, 0
    chunk = 9
    while idx < len(words):
        part = words[idx:idx + chunk]
        if not part:
            break
        n += 1
        sents.append({"label": "ai" if n % 3 else ("uncertain" if n % 3 == 1 else "human"),
                      "p_ai": 0.9 if n % 3 == 1 else (0.45 if n % 3 == 1 else 0.1),
                      "text": " ".join(part) + "."})
        idx += chunk
    res = {"verdict": verdict, "ens_z": 1.2 if verdict == "ai" else -1.2,
           "voters": {"linda_essay": 1.1, "linda_multi_v2": 0.8, "stylo7c": 0.5},
           "authorship": {}, "sentences": sents}
    return report.build_report(text, res, {"title": "t", "mode": "sensitive"})


@pytest.mark.parametrize("lang", ["en", "ru", "pl"])
def test_pdf_matrix_header_and_size(lang):
    rep = _rep(TEXTS[lang], "ai" if lang != "ru" else "uncertain")
    data = report.to_pdf_bytes(rep, lang)
    assert data[:4] == b"%PDF"
    assert len(data) > 10 * 1024, len(data)


def test_pdf_20000_words_no_crash():
    text = ("word " * 20000).strip()
    sents = [{"label": "human" if i % 5 else "ai", "p_ai": 0.8 if i % 5 == 0 else 0.1,
              "text": "word " * 25} for i in range(800)]
    res = {"verdict": "human", "ens_z": -0.5, "voters": {}, "authorship": {}, "sentences": sents}
    rep = report.build_report(text, res, {"title": "long", "mode": "precise"})
    data = report.to_pdf_bytes(rep, "en")
    assert data[:4] == b"%PDF"
    assert len(data) > 10 * 1024
