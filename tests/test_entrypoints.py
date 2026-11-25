# -*- coding: utf-8 -*-
"""README entry points stay wired to the routed loader (no real models: fake folders and fake voices)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import linda_pro  # noqa: E402
from linda_pro import __main__ as cli  # noqa: E402
from linda_pro import loader, server  # noqa: E402
from linda_pro.routed import RoutedLindaPro  # noqa: E402

VOICE_DIRS = {"essay_m": "essay_m_dir", "multi_m": "multi_m_dir", "stylo_d": "stylo_d", "essay_l14": "essay_l14_dir",
              "multi_l14": "multi_l14_dir", "stylo_l_pl": "stylo_l", "speed_s": "speed_dir"}


def _tier(voters, essay, multi):
    return {"voters": voters, "z": {v: [0.0, 1.0] for v in voters}, "weights": {v: 1.0 / len(voters) for v in voters},
            "thr_sensitive": 1.0, "thr_p03": 2.0, "thr_p5": 0.5,
            "heat": {"essay": {"voter": essay, "win_thr_1": 1.0, "thr_5": 0.5, "thr_05": 2.0, "thr_1": 1.0},
                     "multi": {"voter": multi, "thr_5": 0.5, "thr_05": 2.0, "thr_1": 1.0}}}


def _table(with_lite=True):
    """Shape of routing 1.4.1: the PL tier has no stylometry voter; the speed tiers are the Lite overlay."""
    en = {"full": _tier(["essay_m", "multi_m", "stylo_d"], "essay_m", "multi_m")}
    pl = {"full": _tier(["essay_l14", "multi_l14"], "essay_l14", "multi_l14")}
    if with_lite:
        en["speed"] = _tier(["speed_s", "stylo_d"], "speed_s", "speed_s")
        pl["speed"] = _tier(["speed_s", "stylo_d", "stylo_l_pl"], "speed_s", "speed_s")
    return {"kind": "merged", "voice_dirs": VOICE_DIRS, "languages": {"en": {"tiers": en}, "pl": {"tiers": pl}}}


def _root(tmp_path, full=True, lite=True, table=None):
    (tmp_path / "calibration").mkdir()
    (tmp_path / "calibration" / "routing.json").write_text(json.dumps(table or _table()), encoding="utf-8")
    models = tmp_path / "models"
    keys = (["essay_m", "multi_m", "stylo_d", "essay_l14", "multi_l14"] if full else []) + (["stylo_d", "stylo_l_pl"] if lite else [])
    for k in keys:
        (models / VOICE_DIRS[k]).mkdir(parents=True, exist_ok=True)
        (models / VOICE_DIRS[k] / "config.json").write_text("{}", encoding="utf-8")
    if lite:
        (models / "speed_dir").mkdir(parents=True, exist_ok=True)
        (models / "speed_dir" / "model.onnx").write_bytes(b"x")
    return tmp_path


def test_readme_import_from_package_root():
    from linda_pro import load_detector, load_detectors  # noqa: F401  (README: from linda_pro import load_detector)
    assert "load_detector" in linda_pro.__all__


def test_cli_parser_accepts_documented_tier_flags():
    p = cli.build_parser()
    assert p.parse_args(["a.txt", "--lite"]).tier == "lite"
    assert p.parse_args(["a.txt", "--tier", "full"]).tier == "full"
    assert p.parse_args(["a.txt"]).tier == "auto"
    with pytest.raises(SystemExit):
        p.parse_args(["a.txt", "--lite", "--tier", "full"])


def test_cli_help_lists_lite():
    out = subprocess.run([sys.executable, "-m", "linda_pro", "--help"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert "--lite" in out and "--tier" in out


@pytest.mark.parametrize("full,lite,tier,expect", [
    (True, True, None, None), (True, True, "auto", None), (True, True, "full", None), (True, True, "lite", "speed"),
    (False, True, None, "speed"), (True, False, None, None)])
def test_tier_selection(tmp_path, full, lite, tier, expect):
    root = _root(tmp_path, full, lite, table=_table(with_lite=lite))
    dets = loader.load_detectors(root, tier=tier)
    assert set(dets) == {"sensitive", "precise"}
    assert all(isinstance(d, RoutedLindaPro) and d.tier_pref == expect for d in dets.values())
    assert dets["sensitive"].pool is dets["precise"].pool  # weights loaded once


def test_missing_tier_is_an_error_not_a_silent_fallback(tmp_path):
    root = _root(tmp_path, full=True, lite=False, table=_table(with_lite=False))
    with pytest.raises(FileNotFoundError, match="Lite"):
        loader.load_detectors(root, tier="lite")


def test_full_needs_polish_russian_voices(tmp_path):
    root = _root(tmp_path, full=True, lite=False, table=_table(with_lite=False))
    for k in ("essay_l14", "multi_l14"):
        for f in (root / "models" / VOICE_DIRS[k]).iterdir():
            f.unlink()
    assert loader.installed_tiers(root) == {"full": False, "lite": False}
    with pytest.raises(FileNotFoundError, match="download_models"):
        loader.load_detectors(root)


def test_no_weights_message(tmp_path):
    (tmp_path / "calibration").mkdir()
    with pytest.raises(FileNotFoundError, match="download_models.py"):
        loader.load_detector("sensitive", root=tmp_path)


def test_bad_tier_and_mode(tmp_path):
    with pytest.raises(ValueError):
        loader.load_detectors(tmp_path, tier="speed")
    with pytest.raises(ValueError):
        loader.load_detector("strict", root=tmp_path)


class FakeVoice:
    def __init__(self, value):
        self.value = value

    def margins(self, texts):
        return [self.value for _ in texts]

    def close(self):
        pass


def test_routed_tier_without_stylometry_detects(tmp_path):
    """Routing 1.4.1: PL/RU full tiers have no stylo voter; detect() and the 1.x compatibility properties must not fail."""
    det = RoutedLindaPro(_table(with_lite=False), lambda key: FakeVoice(3.0), mode="sensitive")
    pl = "To jest tekst, który się sprawdza. Nie jest długi, ale może być przez to trudny dla modelu. " * 20
    [r] = det.detect([pl])
    assert r["language"] == "pl" and r["verdict"] == "ai"
    assert set(r["voters"]) == {"linda_essay", "linda_multi_v2"}
    assert set(det.mean) == {"linda_essay", "linda_multi_v2"} and set(det.std) == set(det.mean)


def test_cli_end_to_end_with_fake_detector(tmp_path, monkeypatch, capsys):
    calls = {}

    class Det:
        tier_pref = "speed"

        def detect(self, texts):
            return [{"verdict": "human", "mode": "sensitive", "essay": 0.1, "ens_z": -1.0, "ai_share": 0.0, "n_windows": 1, "windows": [],
                     "language": "en", "_lite_token_scores": [object()]} for _ in texts]

    def fake_load(mode, device=None, tier=None):
        calls.update(mode=mode, tier=tier)
        return Det()

    monkeypatch.setattr(cli, "load_detector", fake_load)
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    assert cli.main([str(f), "--lite"]) == 0
    assert calls == {"mode": "sensitive", "tier": "lite"}
    assert "tier=lite" in capsys.readouterr().out
    assert cli.main([str(f), "--json"]) == 0
    assert "_lite_token_scores" not in capsys.readouterr().out  # internal field dropped, output stays valid JSON


def test_cli_reports_missing_weights_without_traceback(tmp_path, monkeypatch, capsys):
    def fake_load(mode, device=None, tier=None):
        raise FileNotFoundError("Linda-Pro Lite weights are not installed; run `python download_models.py --set lite`")

    monkeypatch.setattr(cli, "load_detector", fake_load)
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    assert cli.main([str(f), "--lite"]) == 2
    assert "download_models.py --set lite" in capsys.readouterr().err


def test_server_uses_routed_loader(monkeypatch):
    seen = {}
    monkeypatch.setattr(server, "installed_tiers", lambda: {"full": True, "lite": False})
    monkeypatch.setattr(server, "load_detectors", lambda device=None, tier=None: seen.setdefault("tier", tier) and {"x": 1})
    monkeypatch.setattr(server, "make_detectors", lambda device=None: pytest.fail("legacy path used with routed weights"))
    server.load_service_detectors(None, "auto")
    assert seen["tier"] == "auto"
