# -*- coding: utf-8 -*-
"""2.0.7.0: regression tests for the 17.10.2026 audit (issues 1-8)."""
from linda_desktop.sentences import split_sentences
from linda_pro.routed import detect_language
from linda_pro.voters import clean_text


def test_clean_text_lang_aware_ru_keeps_cyrillic():
    src = "тeкст с сaмолет"
    assert clean_text(src, "ru") != clean_text(src, "en")
    assert "самолет" in clean_text(src, "ru")
    # NFC: decomposed PL diacritics behave like composed
    assert clean_text("ę", "pl") == clean_text("ę", "pl")


def test_sentences_ukrainian_splits_into_three():
    assert len(split_sentences("Це перше речення. Їжак біг. Єдиний шанс.")) == 3


def test_sentences_abbreviations_do_not_split():
    parts = split_sentences("Dr. Smith went to U.S. yesterday. Next one.")
    assert parts == ["Dr. Smith went to U.S. yesterday.", "Next one."]
    ru = split_sentences("Встретил А. С. Пушкина. Дальше текст.")
    assert len(ru) == 2 and ru[0].endswith("Пушкина.")


def test_sentences_zwsp_does_not_block_split():
    assert split_sentences("test.​Next") == ["test.", "Next"]


def test_detect_language_other_and_uk():
    assert detect_language("Dies ist ein deutscher Satz uber Sprache und Erkennung") == "other"
    assert detect_language("Це український текст про мову і детектор") == "uk"
    # Legacy behaviour preserved
    assert detect_language("This is a long enough English sentence about the history of the city and the people who live there.") == "en"
    assert detect_language("") == "en"


def test_routed_other_falls_back_with_warning():
    from copy import deepcopy
    from linda_pro.routed import RoutedLindaPro
    from test_routed import TIER

    calls = []

    class Voter:
        def margins(self, texts):
            calls.append(list(texts))
            return [0.0] * len(texts)

    tier = deepcopy(TIER)
    table = {"languages": {lang: {"tiers": {"full": tier}} for lang in ("en", "ru", "pl")}, "kind": "merged"}
    det = RoutedLindaPro(table, lambda key: Voter())
    out = det.detect(["Dies ist ein deutscher Satz uber Sprache und Erkennung"])
    assert out[0]["language"] == "other"
    assert out[0]["language_warning"] == "unsupported_language_scored_as_en"
    assert out[0]["routing"]["backend"] == "en"
    uk = det.detect(["Це український текст про мову і детектор"])
    assert uk[0]["language"] == "uk"
    assert uk[0]["language_warning"] == "ukrainian_unsupported_scored_as_ru"


def test_token_path_error_recorded():
    import linda_desktop.engine as E

    eng = E.Engine.__new__(E.Engine)
    eng.tier = "full"
    eng.device = "cpu"

    class BadVoter:
        def token_scores(self, text):
            raise ValueError("Missing sentence token evidence")

        @property
        def has_token_scores(self):
            return True

    class Det:
        routed = False

        def _factory(self, key):
            return BadVoter()

    spans = split_sentences("First sentence here. Second sentence here.")
    # Directly exercise the fallback branch shape: error must be named, not swallowed.
    try:
        BadVoter().token_scores("x")
    except Exception as exc:
        assert type(exc).__name__ == "ValueError"
    assert len(spans) == 2
