# -*- coding: utf-8 -*-
"""Local history, compare and the authorship verdict (1.2)."""
import pytest
from fastapi.testclient import TestClient

from linda_desktop import engine, history, updater
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


def res(labels, verdict="human", texts=None):
    sents = [{"text": (texts[i] if texts else "Sentence number %d has a few words." % i), "label": l, "p_ai": {"ai": .8, "uncertain": .3, "human": .02}[l]} for i, l in enumerate(labels)]
    return {"verdict": verdict, "ens_z": 0.5, "sentences": sents, "authorship": engine.authorship(verdict, sents)}


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    return tmp_path


def test_authorship_rules():
    a = lambda v, ls: engine.authorship(v, res(ls)["sentences"])["label"]
    assert a("human", ["human"] * 10) == "human"
    assert a("ai", ["ai"] * 8 + ["human"] * 2) == "ai"
    assert a("ai", ["ai"] * 2 + ["human"] * 8) == "mixed"        # the ensemble says AI but only part of the text carries a signal
    assert a("uncertain", ["human"] * 10) == "mixed"
    assert a("human", ["ai"] * 6 + ["human"] * 8) == "mixed"      # AI stretch inside a human verdict
    assert a("human", ["ai"] * 2 + ["human"] * 10) == "human"      # a couple of stray sentences are not "mixed"
    s = engine.authorship("ai", res(["ai", "uncertain", "human", "human"])["sentences"])
    assert abs(s["ai_share"] + s["uncertain_share"] + s["human_share"] - 1) < 0.01


def test_history_roundtrip_and_delete(home):
    r = res(["ai", "human"], "uncertain")
    i = history.add("Hello world text. Another sentence here.", r, "sensitive", filename="a.docx")
    j = history.add("Second doc.", res(["human"]), "precise")
    assert [x["id"] for x in history.list_checks()] == [j, i]
    c = history.get(i)
    assert c["title"] == "a.docx" and c["text"].startswith("Hello") and c["result"]["verdict"] == "uncertain"
    assert history.list_checks(q="a.docx")[0]["id"] == i and history.list_checks(verdict="human")[0]["id"] == j
    assert history.rename(i, "Renamed") and history.get(i)["title"] == "Renamed"
    assert history.stats()["n"] == 2
    assert history.delete(i) and history.get(i) is None
    assert history.clear() == 1 and history.list_checks() == []


def test_compare_aligns_sentences(home):
    base = ["Alpha sentence one is here.", "Beta sentence two is here.", "Gamma sentence three is here."]
    a = history.add(" ".join(base), res(["ai", "ai", "human"], texts=base), "sensitive")
    rev = [base[0], "Beta was rewritten by a person completely.", base[2], "A brand new closing sentence."]
    b = history.add(" ".join(rev), res(["ai", "human", "human", "human"], texts=rev), "sensitive")
    d = history.compare(history.get(a), history.get(b))
    assert d["counts"] == {"same": 2, "changed": 1, "added": 1, "removed": 0}
    ch = [r for r in d["rows"] if r["kind"] == "changed"][0]
    assert ch["a"]["label"] == "ai" and ch["b"]["label"] == "human"
    assert 0 < d["similarity"] < 1 and d["a"]["ai_words_share"] > d["b"]["ai_words_share"]


def test_api_saves_and_serves_history(home, monkeypatch):
    class Fake:
        lock = None
        device = "cpu"
        dets = None
        state = {"phase": "idle", "error": ""}

        def unload(self):
            pass

        def probe_gpu(self):
            pass

        def run(self, text, mode, models, cancellable=False, cancel=None):
            return res(["ai", "human"], "ai")

        def info(self):
            return {}

    monkeypatch.setattr(updater, "is_complete", lambda: True)
    core = Core()
    core.engine = Fake()
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    text = " ".join(["word"] * 60)
    r = c.post("/api/detect", json={"text": text, "title": "My doc", "filename": "f.txt"}).json()
    assert r["status"] == "ok" and r["history_id"]
    lst = c.get("/api/history").json()
    assert lst["items"][0]["title"] == "My doc" and lst["stats"]["n"] == 1
    one = c.get(f"/api/history/{r['history_id']}").json()
    assert one["text"] == text and one["result"]["authorship"]["label"] in ("ai", "mixed")
    c.post("/api/settings", json={"save_history": False})
    assert c.post("/api/detect", json={"text": text}).json()["history_id"] is None
    assert c.get("/api/history").json()["stats"]["n"] == 1
    assert c.post("/api/compare", json={"a": r["history_id"], "b": r["history_id"]}).json()["text_equal"] is True
    assert c.patch(f"/api/history/{r['history_id']}", json={"title": "X"}).status_code == 200
    assert c.delete("/api/history").json()["deleted"] == 1
    assert c.get("/api/history/999").status_code == 404
    assert "cabBtns" in c.get("/", headers={"host": "127.0.0.1"}).text  # the cabinet UI is injected into the page


def test_analytics_and_matrix():
    from linda_desktop import analytics

    t = "Moreover, this is a plain sentence. Short one. " * 6 + "However we tried something quite different and longer here, with many more words in it."
    a = analytics.analyze(t, res(["human"] * 3)["sentences"])
    assert a["words"] > 40 and a["burstiness"] >= 0 and 0 < a["lexical_diversity"] <= 1 and a["stock_per_1000"] > 0
    base = "the quick brown fox jumps over the lazy dog while the cat sleeps quietly near the warm fireplace tonight"
    m = analytics.similarity_matrix([base, base + " and then it rains", "completely different words about astronomy and distant galaxies forming slowly"])
    assert m[0][1] > 0.8 and m[0][2] == 0.0 and m[1][0] == m[0][1]


def test_folders_sort_bulk_and_retention(home):
    a = history.add("alpha text one two three four five six seven eight nine ten.", res(["ai"], "ai"), "sensitive", title="Bravo")
    b = history.add("beta text.", res(["human"]), "sensitive", title="alpha")
    f = history.folder_add("Course 1", "#0050ef")
    assert history.move([a], f) == 1
    fo = history.folders()
    assert fo["total"] == 2 and fo["unsorted"] == 1 and fo["folders"][0]["n"] == 1
    assert [x["id"] for x in history.list_checks(folder=f)] == [a] and [x["id"] for x in history.list_checks(folder=0)] == [b]
    assert [x["title"] for x in history.list_checks(sort="title", order="asc")] == ["alpha", "Bravo"]
    assert history.folder_delete(f) == 0 and history.get(a)["folder_id"] is None  # checks go back to Unsorted
    f2 = history.folder_add("Temp")
    history.move([a, b], f2)
    assert history.folder_delete(f2, with_checks=True) == 2 and history.list_checks() == []
    c = history.add("old one.", res(["human"]), "sensitive")
    import sqlite3
    from linda_desktop import config
    with sqlite3.connect(str(config.data_dir() / "history.db")) as con:
        con.execute("UPDATE checks SET ts = ts - 86400 * 40 WHERE id = ?", (c,))
    assert history.purge_older_than(30) == 1 and history.delete_many([999]) == 0


def test_shared_passages_and_structure(home):
    from linda_desktop import structure

    common = "the committee reviewed every proposal carefully before announcing the final decision to the public on Monday"
    sh = history.shared_passages("Intro words here. " + common + ". Something else follows now.", "Totally new start. " + common + "! And a different ending entirely.")
    assert sh["count"] == 1 and sh["passages"][0]["words"] >= 15 and sh["share_of_a"] > 0.5
    assert history.shared_passages("one two three", "four five six")["count"] == 0
    p = structure.profile("First paragraph here.\n\n- item a\n- item b\n\nIn conclusion, it works well.", None)
    assert len(p["features"]) == 36 and p["reference"] is not None and p["layout"][1]["kind"] == "list"
