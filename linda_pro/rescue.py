# -*- coding: utf-8 -*-
"""Linda-Pro 1.3 EN rescue — opt-in source draft, NOT enabled in any installed pack.

Classic 1.1 calls a text "ai" when Essay OR the D3 ensemble z passes the 0.5% human false-positive threshold.
The frozen research rule (eval/reports/existing_rescue_freeze.json, primary; re-checked on the DirectML run in
eval/reports/existing_rescue_dml.json) adds exactly one more signal and changes nothing else:

    rescue_i  =  top25(window margins of Linda-Essay-I) > 9.406153877258303   AND   old_soft

`old_soft` is the pre-existing "possibly AI" band of the shipped calibration: any D3 voice or the ensemble z at its
5%-of-humans threshold `thr_5` (`>=`). Rows are eligible only when the mode is `sensitive` and the baseline verdict
is not already "ai"; `precise` and PL/RU are never touched.

Invariants of this wrapper:
  * baseline verdicts/scores are preserved; I only ADDS `i` and `i_flag` per window. When the rescue fires, `flag`
    becomes the union of the baseline flag and the I flag, and `ai_share` is recomputed from that union. Nothing is
    rescaled and no probability is invented — only raw I margins are reported;
  * the I voter is never resident together with D3 models: before I is created the TRUE underlying NN residents are
    closed (the `_Resident` wrapper's own close() is a no-op), the baseline factory cache is cleared and gc runs;
    I is closed again in `finally`, also on failure;
  * close() releases I and the baseline cache without instantiating any model that was never loaded;
  * when the prebuilt fp16 ONNX of Essay-I is missing, nothing is exported at runtime — the detector keeps plain
    classic behaviour instead of a minute-long export or a crash, and says so: every eligible row then carries
    `rescue = {available: false, applied: false, reason: "essay_i_unavailable"}` (baseline verdict/windows/share are
    still untouched). An unavailable Essay-I is never silent: the row-level metadata is the only difference;
  * the same happens if the number of I margins does not match the baseline window count (`reason:
    "essay_i_window_mismatch"`): window flags are never shifted by index;
  * an invalid configured threshold (missing, non-numeric, NaN, ±inf, or <= 0) never enables a made-up gate — the
    frozen `RESCUE_THR` is used instead.

Windows, cleaning and top25 come from `linda_pro.core` and `linda_pro.voters`, so the numbers are identical to the
classic path.
"""
from __future__ import annotations

import gc
import json
import math
from pathlib import Path

from .core import split_windows, top25
from .voters import clean_text

RESCUE_THR = 9.406153877258303   # frozen: 99.5% quantile of human Essay-I (qi=2 of Q_THR=[.99,.995,.999,1.0])
I_MODEL_DIR = "linda_essay_i"     # already shipped in the 1.3 model pack (shared with the RU voice)
ONNX_SUBDIR = "onnx"
I_MAX_LEN = 384
CPU_BATCH = 4                    # explicit CPU batch; the classic DML path uses one window per run
CONFIG_REL = ("calibration", "en_rescue.json")
REASON_NO_I = "essay_i_unavailable"
REASON_NO_WINDOWS = "essay_i_window_mismatch"


# ── configuration (absent file or enabled=false -> byte-for-byte classic behaviour) ────────────────────────────
def read_config(data_dir: str | Path) -> dict:
    """data_dir()/calibration/en_rescue.json. Any problem -> {} (i.e. the feature stays off)."""
    p = Path(data_dir).joinpath(*CONFIG_REL)
    try:
        if not p.is_file():
            return {}
        blob = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a broken opt-in file must not affect analysis
        return {}
    return blob if isinstance(blob, dict) else {}


def valid_thr(value) -> float | None:
    """A usable threshold, or None. Rejects missing/non-numeric/NaN/inf and anything <= 0:
    a margin gate of 0 or -inf would flag every window, NaN would silently disable the rule."""
    if value is None or isinstance(value, bool):
        return None
    try:
        thr = float(value)
    except (TypeError, ValueError):
        return None
    return thr if math.isfinite(thr) and thr > 0 else None


def threshold_of(cfg: dict) -> float:
    """The configured threshold, or the frozen one. An invalid value never enables a new gate."""
    return valid_thr(cfg.get("thr")) or RESCUE_THR


# ── resident teardown helpers ─────────────────────────────────────────────────────────────────────────────────
def _close_voter(voter) -> None:
    """Close the true model owner: `_Resident(v).close()` does nothing, `v.close()` is the real one."""
    if voter is None:
        return
    inner = getattr(voter, "_v", voter)
    for fn in (getattr(inner, "close", None), getattr(voter, "close", None)):
        if callable(fn):
            try:
                fn()
            except Exception:  # noqa: BLE001 — unloading must not break the caller
                pass
            return


def _close_baseline(base) -> None:
    """Close already-loaded baseline residents, clear the factory cache, collect. Never instantiates a voter."""
    factory = getattr(base, "_factory", None)
    cache = getattr(factory, "_cache", None)
    if isinstance(cache, dict):
        for voter in list(cache.values()):
            _close_voter(voter)
        try:
            cache.clear()
        except Exception:  # noqa: BLE001
            pass
    gc.collect()


# ── Essay-I voter factory (lazy) ─────────────────────────────────────────────────────────────────────────────
def _prebuilt_i_onnx(cache_dir: Path, model_dir: Path) -> bool:
    """True only when a matching prebuilt fp16 ONNX graph exists. Never triggers an export."""
    graph, meta = cache_dir / I_MODEL_DIR / "model.onnx", cache_dir / I_MODEL_DIR / "meta.json"
    if not graph.is_file() or not meta.is_file():
        return False
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    try:
        want = int(json.loads((model_dir / "train_args.json").read_text(encoding="utf-8")).get("max_len", I_MAX_LEN))
    except Exception:  # noqa: BLE001
        want = I_MAX_LEN
    try:
        return int(m.get("max_len", -1)) == want and m.get("dtype") == "fp16"
    except (TypeError, ValueError):
        return False


def default_i_factory(data_dir: str | Path, device: str = "cpu", gpu_index: int = 0,
                      onnx_cls=None, batch: int = CPU_BATCH):
    """-> callable() -> Essay-I voter or None. Created only after the baseline residents were released."""
    data_dir = Path(data_dir)
    model_dir = data_dir / "models" / I_MODEL_DIR
    cache_dir = data_dir / ONNX_SUBDIR

    def make():
        if not ((model_dir / "config.json").is_file()):
            return None  # weights not installed: stay classic
        if device == "dml" and onnx_cls is not None:
            if not _prebuilt_i_onnx(cache_dir, model_dir):
                return None  # no auto-export on the user's machine
            return onnx_cls(model_dir, cache_dir, gpu_index, fp16=True)
        from .voters import FastSeqCls

        return FastSeqCls(model_dir, batch=batch, device="cpu")

    return make


# ── detector ────────────────────────────────────────────────────────────────────────────────────────────────────
class RescueLindaPro:
    """Classic EN detector plus the frozen Essay-I rescue. Delegates rules/mean/std/voters/_factory/... to the base."""

    def __init__(self, base, thr: float = RESCUE_THR, i_factory=None):
        self.__dict__["_base"] = base
        # a NaN/inf/non-positive threshold would either flag every window or silently disable the rule
        self.__dict__["rescue_thr"] = valid_thr(thr) or RESCUE_THR
        self.__dict__["_i_factory"] = i_factory
        self.__dict__["_i"] = None

    def __getattr__(self, name):  # rules, mean, std, voters, _factory, window_thr, models_dir, mode, ...
        return getattr(self.__dict__["_base"], name)

    def __setattr__(self, name, value):
        if name in ("rescue_thr", "_i_factory", "_i"):
            self.__dict__[name] = value
        else:
            setattr(self.__dict__["_base"], name, value)

    # ── eligibility ──────────────────────────────────────────────────────────────────────────────────────────
    def _soft_thr(self) -> tuple[float, float, float, float]:
        """thr_5 of essay / multi / stylo / ensemble, exactly the keys `linda_pro.core.LindaPro.detect` writes.
        A band missing from the calibration can never be satisfied (-inf) instead of raising."""
        rules = self._base.rules or {}
        out = []
        for name in ("essay", "multi", "stylo", "ensemble"):
            band = rules.get(name) or {}
            try:
                out.append(float(band["thr_5"]))
            except (KeyError, TypeError, ValueError):
                out.append(float("-inf"))
        return tuple(out)

    def _eligible(self, results: list[dict]) -> list[int]:
        """Indices of sensitive rows that are not already AI and sit in the old soft (5%) band.
        Reads exactly the classic keys: `verdict`, `ens_z`, `voters.{linda_essay,linda_multi_v2,stylo7c}`."""
        if getattr(self._base, "mode", "sensitive") != "sensitive":
            return []
        e5, m5, s5, z5 = self._soft_thr()
        out = []
        for i, r in enumerate(results):
            if r.get("verdict") == "ai":
                continue  # baseline AI is preserved; the rescue never re-decides such a row
            v = r.get("voters") or {}
            if (float(v.get("linda_essay", float("-inf"))) >= e5
                    or float(v.get("linda_multi_v2", float("-inf"))) >= m5
                    or float(v.get("stylo7c", float("-inf"))) >= s5
                    or float(r.get("ens_z", float("-inf"))) >= z5):
                out.append(i)
        return out

    # ── Essay-I ──────────────────────────────────────────────────────────────────────────────────────────────
    def _ensure_i(self):
        """Baseline residents go away BEFORE I is created; nothing of D3/M3/Stylo stays resident."""
        if self.__dict__["_i"] is not None:
            return self.__dict__["_i"]
        _close_baseline(self.__dict__["_base"])
        factory = self.__dict__["_i_factory"]
        if factory is None:
            return None
        voter = factory()
        if voter is None:
            return None
        self.__dict__["_i"] = voter
        return voter

    def _close_i(self) -> None:
        voter = self.__dict__.get("_i")
        self.__dict__["_i"] = None
        if voter is None:
            return
        _close_voter(voter)
        gc.collect()

    def _score_i(self, texts: list[str]):
        """-> [(top25, [per-window margins])] with the classic cleaning/windows, or None if I is unavailable."""
        voter = self._ensure_i()
        if voter is None:
            return None
        base = self.__dict__["_base"]
        out = []
        for t in texts:
            wins = split_windows(t, base.window_words, base.max_windows)
            margins = [float(x) for x in voter.margins([clean_text(w[0]) for w in wins])]
            out.append((top25(margins), margins))
        return out

    # ── public API (same contract as LindaPro.detect) ─────────────────────────────────────────────────────
    @staticmethod
    def _unavailable(results: list[dict], eligible: list[int], reason: str) -> list[dict]:
        """Baseline rows stay byte-for-byte classic; only the explicit reason is added."""
        for idx in eligible:
            results[idx]["rescue"] = {"available": False, "applied": False, "reason": reason}
        return results

    def detect(self, texts: list[str] | str) -> list[dict]:
        if isinstance(texts, str):
            texts = [texts]
        results = self.__dict__["_base"].detect(texts)
        if not results:
            return results
        eligible = self._eligible(results)
        if not eligible:
            return results  # nothing to rescue: the classic answer, untouched
        thr = self.__dict__["rescue_thr"]
        try:
            scored = self._score_i([texts[i] for i in eligible])
        finally:
            self._close_i()  # I never stays in memory, not even on an exception
        if scored is None:
            # Essay-I is not installed/usable: the classic verdict stands, but the row says WHY it was not rescued.
            return self._unavailable(results, eligible, REASON_NO_I)
        for idx, (agg, margins) in zip(eligible, scored):
            r = results[idx]
            if len(margins) != len(r["windows"]):
                self._unavailable(results, [idx], REASON_NO_WINDOWS)  # never shift flags by index
                continue
            applied = agg > thr
            for w, mi in zip(r["windows"], margins):
                w["i"] = float(mi)
                w["i_flag"] = bool(mi > thr)
                if applied:
                    w["flag"] = bool(w["flag"] or w["i_flag"])
            if applied:
                tot = sum(w["last_word"] - w["first_word"] for w in r["windows"]) or 1
                r["ai_share"] = sum(w["last_word"] - w["first_word"] for w in r["windows"] if w["flag"]) / tot
                r["verdict"] = "ai"  # baseline OR rescue
            r["rescue"] = {"available": True, "applied": bool(applied), "raw_i": float(agg),
                           "thr": float(thr), "mode": "sensitive"}
        return results

    def close(self) -> None:
        """Release Essay-I and the baseline cache. Never instantiates a model that was not loaded."""
        self._close_i()
        _close_baseline(self.__dict__["_base"])


def wrap_rescue(dets: dict, i_factory=None, thr: float | None = None, batch: int = CPU_BATCH) -> dict:
    """Wrap dets['sensitive'] only. dets['precise'] is returned as-is (precise stays exactly classic)."""
    base = dets.get("sensitive")
    if base is None or isinstance(base, RescueLindaPro) or i_factory is None:
        return dets
    out = dict(dets)
    out["sensitive"] = RescueLindaPro(base, thr=RESCUE_THR if thr is None else thr, i_factory=i_factory)
    return out