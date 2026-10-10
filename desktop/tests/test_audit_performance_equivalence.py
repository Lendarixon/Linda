"""Regression oracles for the six optimizations; no real models or GPU."""
import contextlib
import re
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from linda_desktop import engine, history, protected_storage, single_model, structure
from linda_desktop.app import Core, create_app
from test_engine_colours import FakeDet, MarkerVoter
from test_single_model_contract import Detector, engine_for


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    # Exercise the real SQLite snapshot/compression path without requiring the
    # Windows account credential in a restricted test process.
    monkeypatch.setattr(protected_storage, "_crypt", lambda data, purpose, decrypt: data)


def count_connections(monkeypatch):
    original = history._db
    calls = []

    @contextlib.contextmanager
    def counted():
        calls.append(1)
        with original() as con:
            yield con

    monkeypatch.setattr(history, "_db", counted)
    return calls


def seed_history():
    folder = history.folder_add("Alpha", "blue")
    history.folder_add("Empty")
    ids = []
    for i, verdict in enumerate(("human", "ai", "uncertain", "human")):
        ids.append(history.add("Text %d with some words." % i,
                               {"verdict": verdict, "p_ai": .5, "sentences": []},
                               "sensitive", title="Title %d" % i,
                               folder_id=folder if i % 2 else None))
    with history._LOCK, history._db() as con:
        for i, identity in enumerate(ids):
            con.execute("UPDATE checks SET ts=? WHERE id=?", (100000 - i * 86400, identity))
    return folder, ids


def test_get_many_preserves_values_order_duplicates_missing_and_one_open(home, monkeypatch):
    _, ids = seed_history()
    requested = [ids[2], ids[0], ids[2], 9999, ids[1]]
    expected = [history.get(i) for i in requested]
    calls = count_connections(monkeypatch)
    actual = history.get_many(requested)
    assert actual == expected and len(calls) == 1
    actual[0]["result"]["verdict"] = "changed"
    assert actual[2] == expected[2]  # repeated entries remain independent
    assert history.get_many([]) == [] and len(calls) == 1


def test_matrix_json_matches_legacy_get_loop(home, monkeypatch):
    _, ids = seed_history()
    client = TestClient(create_app(Core(), token="audit"), headers={"x-linda-token": "audit"})
    requested = [ids[2], ids[0], ids[2], 9999]
    original = history.get_many
    monkeypatch.setattr(history, "get_many", lambda ids: [history.get(i) for i in ids])
    expected = client.post("/api/compare/matrix", json={"ids": requested}).json()
    monkeypatch.setattr(history, "get_many", original)
    calls = count_connections(monkeypatch)
    assert client.post("/api/compare/matrix", json={"ids": requested}).json() == expected
    assert len(calls) == 1


@pytest.mark.parametrize("days", [0, -1, 2])
@pytest.mark.parametrize("sort", list(history.SORTS) + ["invalid"])
@pytest.mark.parametrize("order", ["asc", "desc", "invalid"])
def test_snapshot_matches_separate_reads_and_retention(home, monkeypatch, days, sort, order):
    folder, ids = seed_history()
    monkeypatch.setattr(history.time, "time", lambda: 100000.)
    # Capture the original DB so the two paths start with precisely the same rows.
    with history._LOCK, history._db() as con:
        original = con.serialize()
    for q, verdict, fo, limit, offset in (("", "", None, 200, 0), ("Title", "human", 0, 1, 1),
                                         ("Title", "invalid", folder, 2, 0), ("missing", "ai", None, 1, 0)):
        with history._LOCK, history._db() as con:
            con.deserialize(original)
        history.purge_older_than(days)
        expected = {"items": history.list_checks(q, verdict, limit, offset, fo, sort, order),
                    "stats": history.stats(), **history.folders()}
        with history._LOCK, history._db() as con:
            con.deserialize(original)
        with monkeypatch.context() as patch:
            calls = count_connections(patch)
            assert history.list_snapshot(q, verdict, limit, offset, fo, sort, order, days) == expected
            assert len(calls) == 1
        assert [history.get(i) is None for i in ids] == [days > 0 and i > days for i in range(4)]


def test_history_api_json_and_clamping(home, monkeypatch):
    seed_history()
    monkeypatch.setattr(history.time, "time", lambda: 100000.)
    engine.save_settings({"history_retention_days": 2})
    client = TestClient(create_app(Core(), token="audit"), headers={"x-linda-token": "audit"})
    history.purge_older_than(2)
    expected = {"items": history.list_checks("Title", "human", 1, 0, 0, "title", "asc"),
                "stats": history.stats(), **history.folders()}
    calls = count_connections(monkeypatch)
    response = client.get("/api/history", params={"q": "Title", "verdict": "human", "limit": 0,
                                                "offset": -3, "folder": "0", "sort": "title", "order": "asc"})
    assert response.json() == expected and len(calls) == 1


@pytest.mark.parametrize("attribute", ["model", "sess"])
@pytest.mark.parametrize("wrapped", [False, True])
def test_voter_loading_keeps_live_identity_scores_and_reloads_after_close(attribute, wrapped):
    class Voter:
        def __init__(self):
            setattr(self, attribute, None)
            self.calls = 0

        def _load(self):
            self.calls += 1
            setattr(self, attribute, object())

        def margins(self, texts):
            return [3.5] * len(texts)

    voter = Voter()
    resident = SimpleNamespace(_v=voter) if wrapped else voter
    det = SimpleNamespace(voters=["a"], _factory=lambda key: resident)
    eng = engine.Engine()
    eng._load_voters({"sensitive": det})
    live = getattr(voter, attribute)
    scores = voter.margins(["First", "Second"])
    eng._load_voters({"sensitive": det})  # ensure_loaded followed by preload
    assert voter.calls == 1 and getattr(voter, attribute) is live
    assert voter.margins(["First", "Second"]) == scores
    setattr(voter, attribute, None)
    eng._load_voters({"sensitive": det})
    assert voter.calls == 2 and getattr(voter, attribute) is not live


@pytest.mark.parametrize("text", ["", " \t\r\n", "abc def", "abc\tdef\r\nghi",
                                  "\u00a0Alpha\u2003Beta\u2028Gamma\x1cDelta\vEnd."])
def test_bisect_word_index_matches_every_old_prefix(text):
    starts = [m.start() for m in re.finditer(r"\S+", text)]
    for position in range(len(text) + 1):
        assert engine.bisect_left(starts, position) == len(text[:position].split())


@pytest.mark.parametrize("gran", ["windows", "smooth"])
@pytest.mark.parametrize("single", [False, True])
def test_full_result_matches_legacy_prefix_split(home, monkeypatch, gran, single):
    text = "\u00a0" + "\t\r\n\u2003".join(
        ("Plain human sentence %d has several words here." % i if i < 45
         else "AIW AIW AIW AIW AIW AIW sentence %d." % i) for i in range(90))
    if single:
        det = Detector("linda_multi_v2")
        det.margins = MarkerVoter().margins
        eng = engine_for(det, gran)
        module = single_model
        models = ["linda_multi_v2"]
    else:
        eng = engine.Engine()
        eng.dets = {"sensitive": FakeDet()}
        eng.sentence_mode = lambda n: gran
        monkeypatch.setattr(FakeDet, "_factory", lambda self, key: MarkerVoter(), raising=False)
        module, models = engine, None
    actual = eng.run(text, models=models)
    monkeypatch.setattr(module, "bisect_left", lambda starts, position: len(text[:position].split()))
    assert eng.run(text, models=models) == actual  # every verdict, label, score and returned field


def old_layout(text, sentences):
    pars = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text)]
    if len(pars) == 1 and text.count("\n") >= 3:
        pars = [(m.start(), m.end(), m.group()) for m in re.finditer(r"[^\n]+", text) if m.group().strip()]
    out = []
    for a, b, t in pars:
        row = {"words": len(t.split()), "kind": "list" if structure._LIST.match(t) else
               ("heading" if len(t.split()) <= 12 and not t.rstrip().endswith((".", "!", "?", "…")) else "text")}
        if sentences:
            row["sentences"] = [{"label": s["label"], "p_ai": s["p_ai"], "words": len(s["text"].split())}
                                for s in sentences if a <= s.get("start", -1) < b]
        out.append(row)
    return out


@pytest.mark.parametrize("text", ["", " \n\t", "Header\n\nFirst text.\n\n- Item\n\nLast?",
                                  "Header\nFirst.\nSecond!\nThird?\nFourth"])
@pytest.mark.parametrize("ordering", ["ordered", "reverse", "rotated", "empty", "none"])
def test_layout_all_fields_match_original_filter(text, ordering):
    sentences = [{"start": i, "text": "one two", "label": str(i), "p_ai": i / 100}
                 for i in range(-1, len(text) + 2)]
    sentences += [dict(sentences[-1]), {"text": "missing offset", "label": "human", "p_ai": 0}]
    sentences.sort(key=lambda s: s.get("start", -1))
    if ordering == "reverse":
        sentences.reverse()
    elif ordering == "rotated":
        sentences = sentences[3:] + sentences[:3]
    elif ordering == "empty":
        sentences = []
    elif ordering == "none":
        sentences = None
    assert structure.layout(text, sentences) == old_layout(text, sentences)


@pytest.mark.parametrize("text", ["", "123. 456!", "Alpha first. Alpha second. Beta third.",
                                  "Same. " * 100 + "Other. " * 20, "Однако да. Однако нет. И ещё."])
def test_counter_features_match_legacy_counting(text, monkeypatch):
    actual = structure.features(text)

    class LegacyCounter:
        def __init__(self, firsts):
            self.firsts = firsts

        def values(self):
            return [self.firsts.count(w) for w in set(self.firsts)]

    monkeypatch.setattr(structure, "Counter", LegacyCounter)
    assert structure.features(text) == actual
