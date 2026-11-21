"""High-impact open-source stylometric features and distance metric fusion engine.

Implements state-of-the-art stylometry for authorship attribution and outlier detection:
1. Short-text vocabulary richness: Simpson's D, Herdan's C (Log-TTR), Hapax Legomena ratio,
   Dis Legomena ratio, Honore's R, Brunet's W, Yule's K.
2. Punctuation sequence patterns, dash/hyphen ratios, quote pairing, word casing (Word Shape).
3. Character 3-4 n-grams (crucial for Slavic inflectional morphology in Polish and Russian).
4. Distance metric fusion: Eder's MAD-normalized Z-scores + Directional Cosine Delta + Character N-Gram centroid.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from core import WORD, features as core_features
from feature_labels import feature_label

VERSION = "2.0.0"
MODEL_PATH = Path(__file__).resolve().parent / "char_ngrams_model.json"


def active_model_path() -> Path:
    """The model pack downloaded by the updater when it is installed and intact, otherwise the one shipped with the app."""
    try:
        import trace_updater
        return trace_updater.active_model_path(MODEL_PATH.name, MODEL_PATH)
    except Exception:  # the updater must never be able to break an analysis
        return MODEL_PATH


def reload_model() -> None:
    """Forget the loaded n-gram model and every cached profile (called after a model update was applied)."""
    CharacterNGramModel._instance = None
    _PROFILE_CACHE.clear()

PUNCT_SEQS = [
    "...", "--", "—", "?!", "!?", ",,", ";;", ":-",
    "— ", " - ", "«", "»", "“", "”", "„",
]

# ---------------------------------------------------------------------------
# Extended Feature Extraction
# ---------------------------------------------------------------------------
def extract_stylometric_features(text: str, language: str = "en") -> Dict[str, float]:
    """Extract linguistic, structural, punctuation, vocabulary richness, and word shape features."""
    f = dict(core_features(text, language))
    
    words = [m.group().lower() for m in WORD.finditer(text)]
    n_w = max(1, len(words))
    n_c = max(1, len(text))
    wc = Counter(words)
    V = len(wc)
    
    # 1. Short-text vocabulary richness
    # Simpson's D: probability of two random tokens belonging to the same word type
    f["simpson_d"] = sum(c * (c - 1) for c in wc.values()) / (n_w * (n_w - 1)) if n_w > 1 else 0.0
    # Herdan's C (Log-TTR): robust against text length fluctuations
    f["herdan_c"] = math.log(V) / math.log(n_w) if (n_w > 1 and V > 0) else 0.0
    # Hapax Legomena ratio (words occurring once)
    v1 = sum(1 for c in wc.values() if c == 1)
    f["hapax_ratio"] = v1 / n_w
    f["hapax_type_ratio"] = v1 / V if V > 0 else 0.0
    # Dis Legomena ratio (words occurring twice)
    v2 = sum(1 for c in wc.values() if c == 2)
    f["dis_ratio"] = v2 / n_w
    f["dis_type_ratio"] = v2 / V if V > 0 else 0.0
    # Brunet's W and Honore's R
    f["brunet_w"] = (n_w ** (V ** -0.172)) if (V > 0 and n_w > 1) else 0.0
    f["honore_r"] = (100 * math.log(n_w) / (1 - v1 / V + 1e-6)) if (V > 0 and n_w > 1 and v1 < V) else 0.0
    
    # 2. Punctuation sequence patterns & Dash/hyphen ratios
    d_em = text.count("—")
    d_en = text.count("–")
    hyph = text.count("-")
    tot_d = d_em + d_en + hyph
    f["dash_em_ratio"] = d_em / max(1, tot_d)
    f["dash_hyph_ratio"] = hyph / max(1, tot_d)
    f["dash_spaced_rate"] = (text.count(" — ") + text.count(" – ")) * 1000.0 / n_c
    
    for seq in PUNCT_SEQS:
        f[f"pseq_{seq}"] = text.count(seq) * 1000.0 / n_c
        
    # 3. Quote pairing and parity
    dq = text.count('"')
    sq = text.count("'")
    g_open = text.count("«")
    g_close = text.count("»")
    c_open = text.count("“") + text.count("„")
    c_close = text.count("”")
    f["quote_pair_guill_diff"] = abs(g_open - g_close) / max(1, g_open + g_close)
    f["quote_pair_curly_diff"] = abs(c_open - c_close) / max(1, c_open + c_close)
    f["quote_parity_dq"] = float(dq % 2 == 0)
    f["quote_parity_sq"] = float(sq % 2 == 0)
    
    # 4. Word shape / casing
    raw_words = [m.group() for m in WORD.finditer(text)]
    if raw_words:
        n_rw = len(raw_words)
        f["shape_title"] = sum(1 for w in raw_words if w.istitle()) / n_rw
        f["shape_upper"] = sum(1 for w in raw_words if len(w) > 1 and w.isupper()) / n_rw
        f["shape_lower"] = sum(1 for w in raw_words if w.islower()) / n_rw
        f["shape_mixed"] = sum(1 for w in raw_words if not w.istitle() and not w.isupper() and not w.islower()) / n_rw
    else:
        f["shape_title"] = f["shape_upper"] = f["shape_lower"] = f["shape_mixed"] = 0.0
        
    return {k: float(v) for k, v in f.items() if math.isfinite(float(v))}

# ---------------------------------------------------------------------------
# Character N-Gram Model
# ---------------------------------------------------------------------------
class CharacterNGramModel:
    """Pre-trained Character 3-4 N-Gram representation for EN, PL, RU."""
    
    _instance: Optional["CharacterNGramModel"] = None
    
    def __init__(self, model_file: Optional[Path] = None):
        self.vectorizers: Dict[str, TfidfVectorizer] = {}
        path = model_file or active_model_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for lang, cfg in data.items():
                vocab = {f: i for i, f in enumerate(cfg["features"])}
                vec = TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(3, 4),
                    vocabulary=vocab,
                    sublinear_tf=True,
                )
                vec.idf_ = np.array(cfg["idf"], dtype=np.float64)
                self.vectorizers[lang] = vec
                
    @classmethod
    def get_default(cls) -> "CharacterNGramModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def transform(self, texts: List[str], language: str) -> np.ndarray:
        if language in self.vectorizers:
            return self.vectorizers[language].transform(texts).toarray()
        # Fitting independently per document creates incompatible coordinate
        # systems, even when their vector lengths happen to match.
        raise ValueError('Character n-gram model is missing for language ' + str(language) +
                         '. Restore char_ngrams_model.json before comparison.')

# ---------------------------------------------------------------------------
# Profile Caching and Multi-Window Aggregation
# ---------------------------------------------------------------------------
_PROFILE_CACHE: Dict[Tuple[str, str], Tuple[Dict[str, float], np.ndarray]] = {}

def profile_text(text: str, language: str) -> Tuple[Dict[str, float], np.ndarray]:
    """Compute stylometric feature dictionary and char n-gram vector with window aggregation and caching."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key = (digest, language)
    if key in _PROFILE_CACHE:
        return _PROFILE_CACHE[key]
        
    char_model = CharacterNGramModel.get_default()
    matches = list(WORD.finditer(text))
    count = len(matches) // 350
    if count <= 1:
        excerpts = [text]
    else:
        # Segment into 350-word windows (up to 8 windows)
        idxs = list(range(min(count, 8)))
        excerpts = [text[matches[int(i) * 350].start():matches[(int(i) + 1) * 350 - 1].end()] for i in idxs]
        
    w_feats = [extract_stylometric_features(ex, language) for ex in excerpts]
    common_keys = sorted(set.intersection(*(set(d.keys()) for d in w_feats)))
    avg_feats = {k: float(np.mean([d[k] for d in w_feats])) for k in common_keys}
    
    w_chars = char_model.transform(excerpts, language)
    avg_char = np.mean(w_chars, axis=0)
    
    result = (avg_feats, avg_char)
    _PROFILE_CACHE[key] = result
    return result

# ---------------------------------------------------------------------------
# Distance Metric Implementations
# ---------------------------------------------------------------------------
def eder_mad_zscores(vector: np.ndarray, reference: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Eder's MAD-normalized Z-score outlier score."""
    center = np.median(reference, axis=0)
    mad = 1.4826 * np.median(np.abs(reference - center), axis=0)
    floor = np.maximum(np.abs(center) * 0.05, 0.005)
    scale = np.maximum(mad, floor)
    delta = np.clip((vector - center) / scale, -6.0, 6.0)
    score = float(np.sqrt(np.mean(delta ** 2))) if delta.size else 0.0
    return score, center, scale, delta

def directional_cosine_delta_scores(X: np.ndarray) -> np.ndarray:
    """Computes Directional Cosine Delta distance to the reference set for all items."""
    mean_X = X.mean(axis=0)
    std_X = X.std(axis=0) + 1e-6
    Z = (X - mean_X) / std_X
    norm_Z = np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
    Z_unit = Z / norm_Z
    D_cos = 1.0 - (Z_unit @ Z_unit.T)
    n = len(X)
    scores = np.zeros(n)
    for i in range(n):
        others = [D_cos[i, j] for j in range(n) if j != i]
        scores[i] = float(np.mean(others)) if others else 0.0
    return scores

def char_ngram_centroid_scores(C: np.ndarray) -> np.ndarray:
    """Computes Character N-Gram Cosine Distance to reference centroid."""
    n = len(C)
    scores = np.zeros(n)
    for i in range(n):
        ref_C = np.delete(C, i, axis=0)
        centroid = np.mean(ref_C, axis=0)
        norm_ci = np.linalg.norm(C[i]) + 1e-9
        norm_cc = np.linalg.norm(centroid) + 1e-9
        scores[i] = float(1.0 - np.dot(C[i], centroid) / (norm_ci * norm_cc))
    return scores

# ---------------------------------------------------------------------------
# Distance Metric Fusion
# ---------------------------------------------------------------------------
def compute_fusion_scores(texts: List[str], language: str = "en") -> np.ndarray:
    """Compute length-adaptive fused stylometric scores across texts in a trial/corpus."""
    n = len(texts)
    if n < 2:
        return np.zeros(n)
        
    profiles = [profile_text(t, language) for t in texts]
    f_dicts = [p[0] for p in profiles]
    C = np.array([p[1] for p in profiles])
    
    common_keys = sorted(set.intersection(*(set(d.keys()) for d in f_dicts)))
    X = np.array([[d[k] for k in common_keys] for d in f_dicts], dtype=np.float64)
    
    # Sub-metric 1: Eder's MAD-normalized RMS
    s_mad = np.zeros(n)
    for i in range(n):
        ref_X = np.delete(X, i, axis=0)
        score, _, _, _ = eder_mad_zscores(X[i], ref_X)
        s_mad[i] = score
        
    # Sub-metric 2: Directional Cosine Delta
    s_cos = directional_cosine_delta_scores(X)
    
    # Sub-metric 3: Character N-Gram Centroid Distance
    s_char = char_ngram_centroid_scores(C)
    
    # Standardize sub-scores across the candidates (Z-normalization)
    def znorm(arr: np.ndarray) -> np.ndarray:
        s = np.std(arr)
        return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)
        
    # Length-adaptive weights:
    avg_words = np.mean([len(WORD.findall(t)) for t in texts])
    if avg_words < 600:
        w_mad, w_cos, w_char = 0.05, 0.05, 0.90
    elif avg_words > 1800:
        w_mad, w_cos, w_char = 0.20, 0.20, 0.60
    else:
        alpha = (avg_words - 600) / 1200.0
        w_mad = 0.05 + 0.15 * alpha
        w_cos = 0.05 + 0.15 * alpha
        w_char = 0.90 - 0.30 * alpha
        
    fused_scores = w_mad * znorm(s_mad) + w_cos * znorm(s_cos) + w_char * znorm(s_char)
    return fused_scores

# ---------------------------------------------------------------------------
# High-Level API Compatible with outlier_engine
# ---------------------------------------------------------------------------
def analyze_corpus_upgraded(documents: List[Dict[str, Any]], language: str = "en", target_id: Optional[str] = None) -> Dict[str, Any]:
    """Drop-in upgrade for analyze_corpus using extended stylometry and metric fusion."""
    if language not in ("en", "pl", "ru"):
        raise ValueError("Language must be en, pl, or ru.")
    if not isinstance(documents, list) or len(documents) < 4:
        raise ValueError("Must provide at least 4 documents for leave-one-out outlier analysis.")
        
    usable = sorted([d for d in documents if d.get("text")], key=lambda d: d.get("id", ""))
    texts = [d["text"] for d in usable]
    ids = [d.get("id", str(i)) for i, d in enumerate(usable)]
    
    scores = compute_fusion_scores(texts, language=language)
    
    ranking = []
    for i, d in enumerate(usable):
        ranking.append({
            "id": ids[i],
            "title": d.get("title", ids[i]),
            "score": float(scores[i]),
            "words": len(WORD.findall(d["text"])),
        })
    ranking.sort(key=lambda r: (-r["score"], r["id"]))
    selected = next((r for r in ranking if r["id"] == target_id), ranking[0])
    
    return {
        "schema_version": "2.0",
        "language": language,
        "corpus_count": len(usable),
        "ranking": ranking,
        "selected": selected,
        "method": {
            "name": "fused_mad_cosine_char_ngram_stylometry",
            "version": VERSION,
        }
    }
