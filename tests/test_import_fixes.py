"""Regression tests for PDF paragraph reconstruction and multi-file Compare documents."""
from fpdf import FPDF
from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, document_worker


def _make_word_positioned_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    for page_no in range(1, 4):
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        pdf.text(20, 15, f"Journal of Testing Vol. 1 - Page {page_no}")
        pdf.set_font("Helvetica", size=12)
        # Paragraph 1: positioned word-by-word with hyphenation across lines
        words_l1 = ["The", "quick", "brown", "fox", "jumps", "over", "inter-"]
        x = 20
        for w in words_l1:
            pdf.text(x, 35, w)
            x += pdf.get_string_width(w + " ") + 1.5
        words_l2 = ["national", "boundaries", "every", "single", "morning."]
        x = 20
        for w in words_l2:
            pdf.text(x, 42, w)
            x += pdf.get_string_width(w + " ") + 1.5
        # Paragraph 2: separated by vertical gap
        words_p2 = ["Second", "paragraph", "starts", "here", "clearly."]
        x = 20
        for w in words_p2:
            pdf.text(x, 60, w)
            x += pdf.get_string_width(w + " ") + 1.5
        pdf.set_font("Helvetica", size=10)
        pdf.text(20, 280, f"Footer Notice {page_no}")
    return bytes(pdf.output())


def _make_two_column_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    left_lines = [
        "Left column line one starts",
        "the academic introduction with",
        "clear empirical evidence and",
        "strong statistical results.",
        "Left column second block.",
    ]
    right_lines = [
        "Right column begins after the",
        "entire left column finishes so",
        "reading order stays intact and",
        "never interleaves columns.",
        "Right column second block.",
    ]
    for i, ln in enumerate(left_lines):
        pdf.text(15, 30 + i * 7, ln)
    for i, ln in enumerate(right_lines):
        pdf.text(115, 30 + i * 7, ln)
    return bytes(pdf.output())


def test_pdf_joins_words_dehyphenates_and_drops_repeated_hf():
    text = document_worker.parse("sample.pdf", _make_word_positioned_pdf())
    assert "The quick brown fox jumps over international boundaries every single morning." in text
    assert "Second paragraph starts here clearly." in text
    assert "\n\n" in text
    assert "Journal of Testing" not in text
    assert "Footer Notice" not in text
    non_empty = [ln for ln in text.splitlines() if ln.strip()]
    assert all(len(ln.split()) >= 4 for ln in non_empty)


def test_pdf_two_column_reading_order():
    text = document_worker.parse("twocol.pdf", _make_two_column_pdf())
    assert "Left column line one starts the academic introduction" in text
    assert "Right column begins after the entire left column finishes" in text
    assert text.index("Left column") < text.index("Right column")


def test_compare_multi_file_upload_and_matrix(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(tmp_path / "models"))
    client = TestClient(app_mod.create_app(token="tok"), headers={"x-linda-token": "tok"})
    shared = "the quick brown fox jumps over the lazy dog near the quiet river bank"
    files = [
        ("files", ("doc1.txt", (shared + " in spring.").encode("utf-8"), "text/plain")),
        ("files", ("doc2.txt", (shared + " in autumn.").encode("utf-8"), "text/plain")),
        ("files", ("doc3.txt", b"astronomy studies distant galaxies and nebulae across deep space.", "text/plain")),
    ]
    up = client.post("/api/upload/batch", files=files)
    assert up.status_code == 200
    items = up.json()["items"]
    assert len(items) == 3
    assert [it["filename"] for it in items] == ["doc1.txt", "doc2.txt", "doc3.txt"]
    assert all(it["status"] == "ok" for it in items)

    docs = [{"id": f"f-{i}", "title": it["filename"], "text": it["text"]} for i, it in enumerate(items)]
    mx = client.post("/api/compare/matrix", json={"documents": docs})
    assert mx.status_code == 200
    data = mx.json()
    assert len(data["items"]) == 3
    assert data["matrix"][0][1] > 0.5
    assert data["matrix"][0][2] == 0.0

    bad = client.post("/api/compare/matrix", json={"documents": docs[:1]})
    assert bad.status_code == 400
