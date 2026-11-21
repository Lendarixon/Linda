# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("fpdf")
from linda_desktop import report, report_short


def make(verdict):
    res = {"verdict": verdict, "p_ai": 0.9, "ens_z": 1.0, "mode": "sensitive", "voters": {}, "sentences": [{"text": "Первое подозрительное предложение здесь.", "p_ai": 0.95, "label": "ai", "start": 0, "end": 10},
           {"text": "Второе обычное предложение для проверки.", "p_ai": 0.1, "label": "human", "start": 11, "end": 20}]}
    return report.build_report("Первое подозрительное предложение здесь. Второе обычное предложение для проверки.", res, {"title": "Тест", "mode": "sensitive"})


@pytest.mark.parametrize("lang", ["ru", "pl", "en"])
@pytest.mark.parametrize("verdict", ["ai", "uncertain", "human"])
def test_short_pdf_one_page(lang, verdict):
    data = report_short.to_short_pdf_bytes(make(verdict), lang)
    assert data[:4] == b"%PDF" and len(data) > 2000
    assert data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") <= 2 or b"/Count 1" in data
