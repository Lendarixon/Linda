# -*- coding: utf-8 -*-
"""Unit tests for Linda 2.6.0.0 upgrades (Engine LRU cache, seg_v3 routing, stylize_core)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from linda_desktop import config, stylize_core
from linda_desktop.engine import Engine


def test_stylize_core_strip_meta_and_guards():
    src = "The quarterly report shows 12 percent growth across 3 regions."
    raw = "<text>\nHere is the rewritten text: Across 3 regions, the quarterly report indicates 12 percent expansion.\n</text>"
    cleaned = stylize_core.strip_meta_wrapper(raw)
    assert cleaned == "Across 3 regions, the quarterly report indicates 12 percent expansion."
    assert stylize_core.candidate_problems(src, raw) == []

    # Markdown injection guard
    md_bad = "**Quarterly** report shows 12 percent growth across 3 regions."
    assert "markdown_injected" in stylize_core.candidate_problems(src, md_bad)

    # Latin glued CamelCase guard
    glued_bad = "The quarterlyReport shows 12 percent growth across 3 regions."
    assert "glued_word" in stylize_core.candidate_problems(src, glued_bad)

    # RU glued CamelCase guard
    ru_src = "В этом квартале продажи выросли на 12 процентов."
    ru_glued = "В этом квартале продажиВыросли на 12 процентов."
    assert "glued_word" in stylize_core.candidate_problems(ru_src, ru_glued)


def test_stylize_core_pick_best_candidate():
    src = "Artificial intelligence systems are transforming how teams review long documents every day."
    near_copy = "Artificial intelligence systems are transforming how teams review long documents daily."
    natural = "Modern AI tools are changing the way teams inspect lengthy documents on a daily basis."
    best, why = stylize_core.pick_best_candidate(src, [near_copy, natural])
    assert why == []
    assert best == natural


def test_engine_segmenter_prefers_seg_v3(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "models_root", lambda: tmp_path)
    eng = Engine()
    assert eng.segmenter_available() is False

    # Create dummy seg_v3 files
    s3 = tmp_path / "models" / "seg_v3"
    (s3 / "onnx").mkdir(parents=True)
    (s3 / "onnx" / "model.onnx").write_bytes(b"onnx")
    (s3 / "tokenizer.json").write_text("{}", encoding="utf-8")

    assert eng.segmenter_available() is True
    assert eng.segmenter_dir().name == "seg_v3"
    assert eng.sentence_mode(nwords=100, allow_tokens=True) == "segmenter"
    assert eng.sentence_mode(nwords=100, allow_tokens=True, skip=("segmenter",)) != "segmenter"


def test_engine_lru_cache_hit_miss_and_invalidation(monkeypatch):
    eng = Engine()
    calls = {"n": 0}

    def fake_run(text, mode="sensitive", models=None):
        calls["n"] += 1
        return {"verdict": "human", "p_ai": 0.05, "sentences": [], "n": calls["n"]}

    monkeypatch.setattr(eng, "_run_locked", fake_run)
    r1 = eng.run("Sample text for caching check.")
    assert calls["n"] == 1
    assert "cached" not in r1

    r2 = eng.run("Sample text for caching check.")
    assert calls["n"] == 1
    assert r2.get("cached") is True

    # Mutating returned dict must not corrupt cached entry
    r2["verdict"] = "ai"
    r3 = eng.run("Sample text for caching check.")
    assert r3["verdict"] == "human"

    # no_cache bypasses cache read
    r4 = eng.run("Sample text for caching check.", no_cache=True)
    assert calls["n"] == 2
    assert "cached" not in r4

    # unload clears cache
    eng.unload()
    r5 = eng.run("Sample text for caching check.")
    assert calls["n"] == 3
    assert "cached" not in r5


def test_prune_stale_preserves_manifest_onnx_buckets(tmp_path):
    import json
    from linda_desktop import updater

    keep = tmp_path / "onnx" / "fp32_stable_v1" / "essay_dhi_131_20261008" / "model.onnx"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_bytes(b"ok")

    orphan_sub = tmp_path / "onnx" / "fp32_stable_v1" / "orphan_sub" / "model.onnx"
    orphan_sub.parent.mkdir(parents=True, exist_ok=True)
    orphan_sub.write_bytes(b"stale")

    orphan_voice = tmp_path / "onnx" / "orphan_voice" / "model.onnx"
    orphan_voice.parent.mkdir(parents=True, exist_ok=True)
    orphan_voice.write_bytes(b"stale")

    (tmp_path / "models" / "essay_dhi_131_20261008").mkdir(parents=True, exist_ok=True)
    (tmp_path / "models" / "essay_dhi_131_20261008" / "config.json").write_text("{}", encoding="utf-8")

    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema": 1, "version": "1.5.1", "files": [{"path": "onnx/fp32_stable_v1/essay_dhi_131_20261008/model.onnx", "size": 2, "sha256": "0" * 64}]}),
        encoding="utf-8",
    )

    removed = updater.prune_stale(tmp_path)
    assert keep.is_file()
    assert not orphan_sub.exists()
    assert not orphan_voice.exists()
    assert "onnx/fp32_stable_v1/orphan_sub" in removed
    assert "onnx/orphan_voice" in removed
