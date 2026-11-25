# -*- coding: utf-8 -*-
"""v2 token heads: selection, calibration sidecar, and auto markup promotion.

The v2 heads (tmp/tokenhead_20261120) carry identity keys (`schema`, `voice`, `lang`), so
the app can tell a validated head for the document's language from an unvalidated one that
merely sits in the same directory. These tests pin:

  * load_token_head picks a v2 npz over the v1 one next to it only when it IS tok_head.npz,
    and never reads the backup;
  * a calibration sidecar overrides center/scale, and a bad sidecar does not;
  * Engine.sentence_mode promotes auto markup to tokens for (essay, en), (essay, pl),
    (multi, pl) and — since night/pack15 — (essay|multi, ru); never for (multi, en) —
    and leaves explicit modes alone.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

from linda_desktop import engine as E
from linda_pro.voters import load_token_head, token_head_info

V2 = ("essay", "multi")


def write_head(folder, voice, lang, center=3.0, scale=1.5, schema=2, v1=False):
    folder.mkdir(parents=True, exist_ok=True)
    if v1:
        np.savez(folder / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3), center=0.5, scale=1.)
        return folder
    np.savez(folder / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3),
             center=np.float64(center), scale=np.float64(scale),
             schema=np.int64(schema), voice=np.str_(voice), lang=np.str_(lang))
    return folder


def test_v2_head_identity_and_schema(tmp_path):
    d = write_head(tmp_path / "essay_l14m50", "essay", "pl")
    head = load_token_head(d)
    assert head["schema"] == 2 and head["voice"] == "essay" and head["lang"] == "pl"
    assert head["calibration_source"] == "npz"
    info = token_head_info(d)
    assert info == {"schema": 2, "voice": "essay", "lang": "pl", "calibrated": True,
                    "calibration_source": "npz", "center": 3.0, "scale": 1.5}


def test_v1_head_still_loads_unchanged(tmp_path):
    d = write_head(tmp_path / "old", None, None, v1=True)
    head = load_token_head(d)
    assert head["schema"] == 1 and "voice" not in head
    assert head["calibration_source"] == "npz"
    assert float(head["center"]) == 0.5 and float(head["scale"]) == 1.0
    assert token_head_info(d)["schema"] == 1


def test_backup_head_is_not_loaded(tmp_path):
    d = write_head(tmp_path / "voice", "essay", "en", center=3.0)
    np.savez(d / "tok_head_v1_backup.npz", w=np.ones(4), b=0., conv=np.ones(3), center=0.5, scale=1.)
    assert float(load_token_head(d)["center"]) == 3.0


def test_sidecar_calibration_overrides_npz(tmp_path):
    d = write_head(tmp_path / "models" / "essay_l14m50", "essay", "pl", center=3.0, scale=1.5)
    cal = d.parent.parent / "calibration"
    cal.mkdir(parents=True)
    (cal / "token_heads_v2.json").write_text(json.dumps(
        {"schema": 2, "heads": {"essay_pl": {"center": 9.5, "scale": 0.25}}}), encoding="utf-8")
    head = load_token_head(d)
    assert head["calibration_source"] == "sidecar"
    assert (float(head["center"]), float(head["scale"])) == (9.5, 0.25)
    # a sidecar next to the head wins over the pack one, and is read the same way
    (d / "tok_head_calibration.json").write_text(json.dumps(
        {"heads": {"essay_pl": {"center": 1.0, "scale": 2.0}}}), encoding="utf-8")
    assert (float(load_token_head(d)["center"]), float(load_token_head(d)["scale"])) == (1.0, 2.0)


@pytest.mark.parametrize("payload", [
    {}, {"heads": {}}, {"heads": {"essay_pl": {"center": 1.0}}},
    {"heads": {"essay_pl": {"center": 1.0, "scale": 0.0}}},
    {"heads": {"essay_pl": {"center": "x", "scale": 1.0}}},
    {"heads": {"essay_pl": {"center": 1.0, "scale": float("nan")}}},
    {"heads": {"multi_en": {"center": 1.0, "scale": 1.0}}},
])
def test_bad_or_foreign_sidecar_leaves_npz_calibration(tmp_path, payload):
    d = write_head(tmp_path / "models" / "essay_l14m50", "essay", "pl", center=3.0, scale=1.5)
    cal = d.parent.parent / "calibration"
    cal.mkdir(parents=True)
    (cal / "token_heads_v2.json").write_text(json.dumps(payload), encoding="utf-8")
    head = load_token_head(d)
    assert head["calibration_source"] == "npz"
    assert (float(head["center"]), float(head["scale"])) == (3.0, 1.5)


def test_unreadable_head_is_not_promoted(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    np.savez(d / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3), center=1.0, scale=-1.)
    assert token_head_info(d)["schema"] == 1
    assert token_head_info(tmp_path / "absent") is None


# --- auto markup promotion -------------------------------------------------------------

class Voter:
    def __init__(self, folder, voice="essay"):
        self.model_dir, self.voice = folder, voice
        self.has_token_scores = True

    def margins(self, texts):
        return [0.0] * len(texts)

    def token_scores(self, text):
        return [(m.start(), m.end(), 2. if m.group().startswith("High") else 0.)
                for m in re.finditer(r"\S+", text)]


class Detector:
    """Routed-detector stand-in: one essay and one multi voter, one current language."""

    rules = {k: {"thr_5": 0., "thr_05": 2., "thr_1": 1.} for k in ("essay", "multi", "ensemble")}

    def __init__(self, essay, multi, lang):
        self.essay, self.multi, self.cur_lang = essay, multi, lang

    def _factory(self, key):
        return self.multi if key == "linda_multi_v2" else self.essay

    def detect(self, texts):
        return [dict(verdict="human", essay=-1., ens_z=-1.,
                     voters={"linda_essay": -1., "linda_multi_v2": -1.},
                     windows=[dict(first_word=0, last_word=len(texts[0].split()), essay=-1., multi=-1.)])]


def make_engine(monkeypatch, det, tier="full", mode="auto"):
    monkeypatch.setattr(E, "gpu_probe", lambda: {})
    monkeypatch.setattr(E, "load_settings", lambda: {"sentences": mode})
    eng = E.Engine()
    eng.tier, eng.device = tier, "cpu"
    eng.dets = {"sensitive": det}
    return eng


def heads(root, tmp_path, voice, lang, multi_voice="multi", multi_lang=None):
    """One essay + one multi model dir holding v2 heads for the given voice/language."""
    essay = write_head(tmp_path / "models" / f"essay_{lang}", voice, lang)
    multi = write_head(tmp_path / "models" / f"multi_{multi_lang or lang}", multi_voice, multi_lang or lang)
    return Detector(Voter(essay), Voter(multi, "multi"), lang)


@pytest.mark.parametrize("voice,lang,multi_voice,multi_lang,promoted", [
    ("essay", "en", "multi", "en", True),    # essay/en v2: validated (AUC 0.762)
    ("essay", "pl", "multi", "pl", True),    # essay/pl v2: validated (0.748)
    ("essay", "pl", "multi", "en", True),    # essay/pl alone is enough for auto markup
    ("essay", "en", "multi", "pl", True),
])
def test_auto_promotes_tokens_for_validated_pairs(tmp_path, monkeypatch, voice, lang, multi_voice, multi_lang, promoted):
    det = heads(None, tmp_path, voice, lang, multi_voice, multi_lang)
    eng = make_engine(monkeypatch, det)
    assert (eng.sentence_mode(300, det) == "tokens") is promoted


@pytest.mark.parametrize("voice,lang", [("multi", "en")])
def test_auto_keeps_context_path_for_unvalidated_pairs(tmp_path, monkeypatch, voice, lang):
    """multi/en is below its all-positive ceiling.

    night/pack15 added (essay|multi, ru) to TOKEN_HEADS_V2, so RU is no longer the
    "no head at all" example here — see test_auto_promotes_ru_v2_heads below.
    """
    det = heads(None, tmp_path, voice, lang)
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det) == "hybrid"


def test_auto_promotes_ru_v2_heads(tmp_path, monkeypatch):
    """night/pack15: calibrated RU v2 heads opt in to the token path like en/pl do."""
    det = heads(None, tmp_path, "essay", "ru")
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det) == "tokens"


def test_auto_keeps_context_path_without_v2_head(tmp_path, monkeypatch):
    """A v1 head (schema 1) is exactly what auto used to refuse."""
    essay = write_head(tmp_path / "models" / "essay_en", None, None, v1=True)
    multi = write_head(tmp_path / "models" / "multi_en", None, None, v1=True)
    det = Detector(Voter(essay), Voter(multi, "multi"), "en")
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det) == "hybrid"


def test_auto_keeps_context_path_when_identity_mismatches(tmp_path, monkeypatch):
    """A PL head in a directory that also serves RU must not colour RU."""
    essay = write_head(tmp_path / "models" / "essay_pl", "essay", "pl")
    multi = write_head(tmp_path / "models" / "multi_pl", "multi", "pl")
    det = Detector(Voter(essay), Voter(multi, "multi"), "ru")
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det) == "hybrid"


def test_auto_uses_the_reported_language_not_the_routed_backend(tmp_path, monkeypatch):
    """A uk text is scored by the en/ru backend but is NOT an en document.

    routed.py maps any language without a routing entry onto "en" (or the ru backend for
    uk), so `cur_lang` alone would let an English head colour Ukrainian text — the
    wrong-pairing case measured at 17.7% human-token FPR (work/tokenheads_v2_transfer_auc.json).
    """
    det = heads(None, tmp_path, "essay", "en")
    eng = make_engine(monkeypatch, det)
    eng.doc_lang = "uk"
    assert eng.sentence_mode(300, det) == "hybrid"
    assert eng.token_head_voice(det, "essay") is None
    assert eng.document_language(det) is None
    # the same engine still promotes when the document really is en
    eng.doc_lang = "en"
    assert eng.sentence_mode(300, det) == "tokens"


def test_auto_reads_pl_from_the_report_when_the_backend_says_en(tmp_path, monkeypatch):
    """PL rendered through a shared backend must still take its own PL head."""
    det = heads(None, tmp_path, "essay", "pl")
    det.cur_lang = "en"  # backend before routing resolves the document
    eng = make_engine(monkeypatch, det)
    eng.doc_lang = "pl"
    assert eng.sentence_mode(300, det) == "tokens"
    eng.doc_lang = "en"
    assert eng.token_head_voice(det, "essay") is None  # no en head installed


def test_auto_keeps_context_path_when_head_is_unreadable(tmp_path, monkeypatch):
    """A head whose scale is not positive cannot calibrate anything: no promotion."""
    essay = write_head(tmp_path / "models" / "essay_en", "essay", "en")
    multi = write_head(tmp_path / "models" / "multi_en", "multi", "en")
    det = Detector(Voter(essay), Voter(multi, "multi"), "en")
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det) == "tokens"
    np.savez(essay / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3),
             center=np.float64(3.0), scale=np.float64(-1.5), schema=np.int64(2),
             voice=np.str_("essay"), lang=np.str_("en"))
    assert eng.sentence_mode(300, det) == "hybrid"  # unreadable head -> schema 1 -> no promotion


def test_explicit_modes_are_untouched_by_v2_heads(tmp_path, monkeypatch):
    det = heads(None, tmp_path, "essay", "en")
    for mode, expected in (("context", "context"), ("smooth", "smooth"),
                           ("windows", "windows"), ("full", "full")):
        eng = make_engine(monkeypatch, det, mode=mode)
        assert eng.sentence_mode(300, det) == expected
    # explicit tokens mode still forces the token path even for multi/en
    det2 = heads(None, tmp_path, "multi", "en")
    eng = make_engine(monkeypatch, det2, mode="tokens")
    assert eng.sentence_mode(300, det2) == "tokens"
    # allow_tokens=False (single-model display paths) keeps the legacy choice
    eng = make_engine(monkeypatch, det)
    assert eng.sentence_mode(300, det, allow_tokens=False) == "hybrid"


def test_lite_tier_choice_is_independent_of_the_pro_heads(tmp_path, monkeypatch):
    """Lite already uses its own token output in auto (unchanged by v2 Pro heads)."""
    det = heads(None, tmp_path, "essay", "en")
    eng = make_engine(monkeypatch, det, tier="speed")
    v2_choice = eng.sentence_mode(300, det)
    # Same detector with no token capability at all -> Lite's legacy context path
    det.essay.has_token_scores = False
    assert eng.sentence_mode(300, det) == "context"
    assert v2_choice == "tokens"  # Lite's own head path, not the Pro promotion


def test_promoted_pairs_run_the_token_markup(tmp_path, monkeypatch):
    """End to end: auto on essay/en renders token markup, and the verdict never moves."""
    det = heads(None, tmp_path, "essay", "en")
    eng = make_engine(monkeypatch, det)
    text = "High low. High High."
    res = eng.run(text)
    assert res["sentence_stats"]["granularity"] == "tokens"
    assert res["sentence_stats"]["thresholds"] == {"ai": .20, "uncertain": .10}
    det.essay.has_token_scores = False
    baseline = eng.run(text)
    assert baseline["sentence_stats"]["granularity"] == "hybrid"
    for key in ("verdict", "verdict_raised_by", "ens_z", "essay", "voters", "windows", "p_ai"):
        assert res.get(key) == baseline.get(key)
    assert [s["p_ai"] for s in res["sentences"]] != [s["p_ai"] for s in baseline["sentences"]]
