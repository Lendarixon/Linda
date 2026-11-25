# -*- coding: utf-8 -*-
"""Bugs 2+3 regression (night/fix-2.5.0.1): batched token path, correct EN head
with the schema-2 sidecar, and markup that agrees with an AI document verdict.

  * pro_token_scores must be called with the batched callback (one forward per
    batch, not one per window) on the Pro token path;
  * the EN essay head is essay_dhi_*/tok_head.npz (schema 2, voice/lang keys)
    read through the pack calibration sidecar (center/scale), never the PL/RU
    l14m50 head;
  * a document the ensemble calls AI must not be painted 100% human by the
    token markup (bug 3: verdict 78% AI / markup 0% AI on the owner's text).
"""
from __future__ import annotations

import json
import re
import time

import numpy as np
import pytest

from linda_desktop import engine as E
from linda_pro import voters as V
from test_tokens_mode import make_engine, Voter


TEXT = ("The model pack 1.5.0 of the Linda desktop application introduced second-generation "
        "token-markup heads for all six voice/language pairs, raising Polish AI recall from "
        "79.43 to 88.86 percent on the MIGIEL/PolEval 2025 benchmark while keeping the false "
        "positive rate at 2.86 percent. The nightly build ships unsigned for reviewers only.")


def _write_head(folder, voice, lang, center=3.0, scale=1.5, schema=2):
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3),
             center=np.float64(center), scale=np.float64(scale),
             schema=np.int64(schema), voice=np.str_(voice), lang=np.str_(lang))
    return folder


def test_pro_token_path_uses_batched_windows(tmp_path):
    """pro_token_scores gets hidden_for_windows: one forward per batch of windows."""
    class Tok:
        cls_token_id, sep_token_id = 1, 2

        def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
            ids, offs, pos = [], [], 0
            for w in text.split():
                ids.append(3 + len(ids))
                offs.append((pos, pos + len(w)))
                pos += len(w) + 1
            return {"input_ids": ids, "offset_mapping": offs}

    calls = {"single": 0, "batch": 0, "seqs": 0}

    class Voter2:
        model_dir = _write_head(tmp_path / "essay", "essay", "en")
        max_len = 8  # force several windows on a short text
        batch = 4
        tok = Tok()

    def hidden(seq):
        calls["single"] += 1
        return np.zeros((len(seq), 4), dtype=np.float32)

    def hidden_batch(seqs):
        calls["batch"] += 1
        calls["seqs"] += len(seqs)
        return [np.zeros((len(s), 4), dtype=np.float32) for s in seqs]

    v = Voter2()
    text = " ".join(f"w{i}" for i in range(30))  # 30 tokens -> several windows
    out = V.pro_token_scores(v, text, hidden, hidden_batch)
    assert out
    assert calls["batch"] >= 1 and calls["single"] == 0
    assert calls["seqs"] > calls["batch"]  # several windows per forward


def test_en_head_is_essay_dhi_with_sidecar(tmp_path):
    """EN selects essay_dhi's own tok_head.npz; the pack sidecar overrides center/scale."""
    pack = tmp_path / "pack"
    voice = _write_head(pack / "models" / "essay_dhi_131_20261008", "essay", "en",
                        center=99.0, scale=99.0)  # npz values must lose to the sidecar
    (pack / "calibration").mkdir(parents=True)
    (pack / "calibration" / "token_heads_v2.json").write_text(json.dumps({
        "schema": 2,
        "heads": {"essay_en": {"center": 3.03, "scale": 1.61, "schema": 2}},
    }), encoding="utf-8")
    head = V.load_token_head(voice, lang="en")
    assert head["schema"] == 2 and head["voice"] == "essay" and head["lang"] == "en"
    assert head["calibration_source"] == "sidecar"
    assert float(head["center"]) == pytest.approx(3.03)
    assert float(head["scale"]) == pytest.approx(1.61)
    info = V.token_head_info(voice, lang="en")
    assert info["calibrated"] and info["schema"] == 2


def test_shared_voice_dir_selects_per_lang_head(tmp_path):
    """essay_l14m50 serves pl AND ru: lang must pick tok_head_<lang>.npz, not tok_head.npz."""
    d = tmp_path / "essay_l14m50"
    d.mkdir()
    np.savez(d / "tok_head.npz", w=np.ones(4), b=0., conv=np.ones(3), center=1., scale=1.,
             schema=np.int64(2), voice=np.str_("essay"), lang=np.str_("pl"))
    np.savez(d / "tok_head_ru.npz", w=np.ones(4), b=0., conv=np.ones(3), center=4.5, scale=2.,
             schema=np.int64(2), voice=np.str_("essay"), lang=np.str_("ru"))
    assert V.load_token_head(d, lang="ru")["lang"] == "ru"
    assert float(V.load_token_head(d, lang="ru")["center"]) == 4.5
    assert V.load_token_head(d, lang="pl")["lang"] == "pl"


def test_ai_verdict_marks_ai_sentences(tmp_path, monkeypatch):
    """Bug 3: ensemble verdict AI must not come with 0% AI sentences in markup."""
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=1., scale=.5,
             schema=np.int64(2), voice=np.str_("essay"), lang=np.str_("en"))
    voter = Voter(tmp_path)
    voter.token_scores = lambda text: [(m.start(), m.end(), 4.) for m in re.finditer(r"\S+", text)]
    eng = make_engine(monkeypatch, voter, "full", verdict="ai", mode="tokens")
    eng.doc_lang = "en"
    result = eng.run(TEXT)
    assert result["verdict"] == "ai"
    stats = result["sentence_stats"]
    assert stats["granularity"] == "tokens"
    assert stats["ai"] >= 1, "AI verdict with 0 AI sentences is the bug-3 inconsistency"
    assert all(s["p_ai"] >= stats["thresholds"]["ai"] for s in result["sentences"])


def test_markup_faster_than_scan_on_1000w(tmp_path, monkeypatch):
    """Bug 2: batched token pass must cost less wall time than the scan path."""
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=1., scale=.5,
             schema=np.int64(2), voice=np.str_("essay"), lang=np.str_("en"))

    scan_calls = {"n": 0}

    class SlowVoter(Voter):
        def margins(self, texts):
            scan_calls["n"] += len(texts)
            import time as _t
            _t.sleep(0.001 * len(texts))  # pretend each window costs real time
            return super().margins(texts)

        def token_scores(self, text):
            import time as _t
            _t.sleep(0.0005)  # batched: one call, cheap
            return [(m.start(), m.end(), 0.) for m in re.finditer(r"\S+", text)]

    voter = SlowVoter(tmp_path)
    eng = make_engine(monkeypatch, voter, "full", verdict="ai", mode="tokens")
    eng.doc_lang = "en"
    text = ("The model pack ships heads. " * 200).strip()  # ~1000 words
    t0 = time.perf_counter()
    result = eng.run(text)
    markup_s = time.perf_counter() - t0
    assert result["sentence_stats"]["granularity"] == "tokens"
    assert markup_s < 1.0  # batched single token call, no per-window loop
