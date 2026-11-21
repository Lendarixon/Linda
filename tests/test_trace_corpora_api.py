from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from linda_desktop import app as app_mod
from linda_desktop import config, trace_corpora, trace_pack


def _sample_text(seed: str) -> str:
    base = (
        f"{seed} empirical evaluation demonstrates that structured methodology improves reproducibility "
        "across independent cohorts. Statistical controls, pre-registered protocols, and transparent "
        "reporting reduce variance when comparing textual corpora across academic disciplines. "
    )
    return (base * 14).strip()


def test_trace_corpora_crud_and_compare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

    items = trace_corpora.list_corpora()
    ids = [c["id"] for c in items]
    assert "builtin_academic_en" in ids

    builtin = trace_corpora.get_corpus("builtin_academic_en")
    assert builtin is not None
    assert builtin["builtin"] is True
    assert len(builtin["documents"]) >= 4

    docs = [
        {"id": f"d{i}", "title": f"Essay {i}", "text": _sample_text(f"Topic {i} variation {i * 7}")}
        for i in range(4)
    ]
    saved = trace_corpora.save_corpus(name="My Test Corpus", language="en", documents=docs)
    cid = saved["id"]
    assert cid and saved["count"] == 4

    loaded = trace_corpora.get_corpus(cid)
    assert loaded is not None
    assert loaded["name"] == "My Test Corpus"
    assert len(loaded["documents"]) == 4

    combined = [{"id": "__target__", "title": "Draft", "text": _sample_text("Novel conversational draft")}] + loaded["documents"]
    res = trace_pack.analyze_corpus(combined, language="en", target_id="__target__")
    cc = trace_corpora.compute_corpus_comparison(res, "__target__")
    assert "projection_2d" in res
    assert len(res["projection_2d"].get("coordinates", [])) == 5
    assert "pairwise_features" in res
    assert isinstance(cc["target_percentiles"], list) and len(cc["target_percentiles"]) > 0
    hist = cc["distance_histogram"]
    assert isinstance(hist["bins"], list) and len(hist["bins"]) >= 4
    assert 0.0 <= float(hist["target_percentile"]) <= 100.0
    assert hist["corpus_count"] == 4

    with pytest.raises(ValueError):
        trace_corpora.delete_corpus("builtin_academic_en")

    assert trace_corpora.delete_corpus(cid) is True
    assert trace_corpora.get_corpus(cid) is None


def test_trace_corpora_http_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(trace_pack, "installed", lambda: True)
    monkeypatch.setattr(app_mod.licensing, "check_licensed", lambda _feat=None: None)

    client = TestClient(app_mod.create_app(app_mod.Core(), token="test"), headers={"x-linda-token": "test"})

    r = client.get("/api/trace/corpora")
    assert r.status_code == 200
    body = r.json()
    assert any(c["id"] == "builtin_academic_en" for c in body["corpora"])

    r_get = client.get("/api/trace/corpora/builtin_academic_en")
    assert r_get.status_code == 200
    assert r_get.json()["corpus"]["builtin"] is True

    docs = [
        {"id": f"s{i}", "title": f"Sample {i}", "text": _sample_text(f"Sample {i} corpus text")}
        for i in range(4)
    ]
    r_save = client.post(
        "/api/trace/corpora",
        json={"name": "API Corpus", "language": "en", "documents": docs},
    )
    assert r_save.status_code == 200
    cid = r_save.json()["corpus"]["id"]

    r_cmp = client.post(
        "/api/trace/compare_corpus",
        json={
            "target": {"title": "Query", "text": _sample_text("Query style text")},
            "corpus_id": cid,
            "language": "en",
        },
    )
    assert r_cmp.status_code == 200
    cmp_res = r_cmp.json()["result"]
    assert "corpus_comparison" in cmp_res
    assert "distance_histogram" in cmp_res["corpus_comparison"]
    assert "target_percentiles" in cmp_res["corpus_comparison"]
    assert "projection_2d" in cmp_res

    r_del_builtin = client.delete("/api/trace/corpora/builtin_academic_en")
    assert r_del_builtin.status_code == 400

    r_del = client.delete(f"/api/trace/corpora/{cid}")
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True
