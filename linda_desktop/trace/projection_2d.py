"""Classical Metric Multidimensional Scaling (Torgerson-Gower MDS) and 2D Stylistic Distance Mapping."""
from __future__ import annotations
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

ALGORITHM_NAME = "Classical Metric Multidimensional Scaling (Torgerson-Gower)"


def classical_mds(distance_matrix: np.ndarray) -> Tuple[np.ndarray, float, float]:
    """
    Classical (Torgerson-Gower) Metric Multidimensional Scaling.

    Given symmetric pairwise distance matrix D (N x N):
      - Squared distances: D^2
      - Double-centering matrix: H = I - (1/N) * 1 * 1^T
      - Gram matrix: B = -0.5 * H @ (D^2) @ H
      - Eigen-decomposition: B = V @ Lambda @ V^T via np.linalg.eigh
      - Top 2 positive eigenvalues lambda_1, lambda_2 and eigenvectors v_1, v_2
      - Coordinates: X_2D = [v_1 * sqrt(lambda_1), v_2 * sqrt(lambda_2)]
      - Goodness-of-Fit (variance explained): (lambda_1 + lambda_2) / sum(max(0, lambda_k))
      - Kruskal's Stress-1 metric

    Returns:
      (X_2D, variance_explained, stress)
    """
    D = np.asarray(distance_matrix, dtype=np.float64)
    if D.ndim != 2 or D.shape[0] != D.shape[1]:
        raise ValueError("distance_matrix must be a square 2D array.")
    N = D.shape[0]
    if N == 0:
        return np.empty((0, 2), dtype=np.float64), 1.0, 0.0
    if N == 1:
        return np.zeros((1, 2), dtype=np.float64), 1.0, 0.0

    # Ensure symmetric with zero diagonal
    D = (D + D.T) / 2.0
    np.fill_diagonal(D, 0.0)

    # 1. Squared distances: D^2
    D2 = D ** 2

    # 2. Double-centering matrix: H = I - (1/N) 1 1^T
    H = np.eye(N, dtype=np.float64) - (np.ones((N, N), dtype=np.float64) / float(N))

    # 3. Gram matrix: B = -0.5 * H @ D^2 @ H
    B = -0.5 * (H @ D2 @ H)
    # Symmetrize to counter minor floating-point asymmetry
    B = (B + B.T) / 2.0

    # 4. Eigen-decomposition via np.linalg.eigh
    eigvals, eigvecs = np.linalg.eigh(B)

    # Sort eigenvalues and eigenvectors in descending order
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    # Positive eigenvalues sum for explained variance
    pos_eigvals = np.maximum(0.0, eigvals)
    pos_sum = float(np.sum(pos_eigvals))

    lambda1 = float(pos_eigvals[0]) if (N >= 1 and pos_eigvals[0] > 1e-12) else 0.0
    lambda2 = float(pos_eigvals[1]) if (N >= 2 and pos_eigvals[1] > 1e-12) else 0.0

    v1 = eigvecs[:, 0] if N >= 1 else np.zeros(N, dtype=np.float64)
    v2 = eigvecs[:, 1] if N >= 2 else np.zeros(N, dtype=np.float64)

    # 5. Coordinates: X_2D = [v1 * sqrt(lambda1), v2 * sqrt(lambda2)]
    x = v1 * math.sqrt(lambda1) if lambda1 > 0 else np.zeros(N, dtype=np.float64)
    y = v2 * math.sqrt(lambda2) if lambda2 > 0 else np.zeros(N, dtype=np.float64)
    X_2D = np.column_stack([x, y])

    # 6. Explained variance ratio (Goodness-of-Fit)
    if pos_sum > 1e-12:
        variance_explained = float(np.clip((lambda1 + lambda2) / pos_sum, 0.0, 1.0))
    else:
        variance_explained = 1.0

    # 7. Kruskal's Stress-1
    diffs_sq = 0.0
    d_orig_sq = 0.0
    for i in range(N):
        for j in range(i + 1, N):
            d_orig = float(D[i, j])
            d_2d = math.hypot(float(X_2D[i, 0] - X_2D[j, 0]), float(X_2D[i, 1] - X_2D[j, 1]))
            diffs_sq += (d_orig - d_2d) ** 2
            d_orig_sq += d_orig ** 2

    stress = float(math.sqrt(diffs_sq / d_orig_sq)) if d_orig_sq > 1e-12 else 0.0

    return X_2D, variance_explained, stress


def compute_reference_spread(X_2D: np.ndarray, ref_indices: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Computes reference corpus centroid (mu_x, mu_y), 1-sigma and 2-sigma spread ellipses,
    and spread radius.
    """
    N = X_2D.shape[0]
    if ref_indices is None or len(ref_indices) == 0:
        ref_indices = list(range(N))

    if len(ref_indices) == 0:
        return {
            'centroid': {'x': 0.0, 'y': 0.0},
            'spread_radius': 0.0,
            'ellipse_1sigma': {'semi_major': 0.0, 'semi_minor': 0.0, 'angle_deg': 0.0},
            'ellipse_2sigma': {'semi_major': 0.0, 'semi_minor': 0.0, 'angle_deg': 0.0},
            'sigma_x': 0.0,
            'sigma_y': 0.0,
        }

    X_ref = X_2D[ref_indices]
    M = len(ref_indices)

    mu_x = float(np.mean(X_ref[:, 0]))
    mu_y = float(np.mean(X_ref[:, 1]))

    if M < 2:
        return {
            'centroid': {'x': mu_x, 'y': mu_y},
            'spread_radius': 0.0,
            'ellipse_1sigma': {'semi_major': 0.0, 'semi_minor': 0.0, 'angle_deg': 0.0},
            'ellipse_2sigma': {'semi_major': 0.0, 'semi_minor': 0.0, 'angle_deg': 0.0},
            'sigma_x': 0.0,
            'sigma_y': 0.0,
        }

    # Center reference points
    Xc = X_ref - np.array([mu_x, mu_y], dtype=np.float64)
    # 2x2 covariance matrix
    cov = (Xc.T @ Xc) / float(M - 1)
    cov = (cov + cov.T) / 2.0

    cov_eigvals, cov_eigvecs = np.linalg.eigh(cov)
    c_idx = np.argsort(cov_eigvals)[::-1]
    s1_sq = max(1e-12, float(cov_eigvals[c_idx[0]]))
    s2_sq = max(1e-12, float(cov_eigvals[c_idx[1]]))

    a1 = float(math.sqrt(s1_sq))
    b1 = float(math.sqrt(s2_sq))
    v_major = cov_eigvecs[:, c_idx[0]]
    angle_rad = float(math.atan2(v_major[1], v_major[0]))
    angle_deg = float(math.degrees(angle_rad))

    spread_radius = float(math.sqrt(s1_sq + s2_sq))
    sigma_x = float(np.std(X_ref[:, 0], ddof=1))
    sigma_y = float(np.std(X_ref[:, 1], ddof=1))

    return {
        'centroid': {'x': mu_x, 'y': mu_y},
        'spread_radius': spread_radius,
        'ellipse_1sigma': {'semi_major': a1, 'semi_minor': b1, 'angle_deg': angle_deg},
        'ellipse_2sigma': {'semi_major': 2.0 * a1, 'semi_minor': 2.0 * b1, 'angle_deg': angle_deg},
        'sigma_x': sigma_x,
        'sigma_y': sigma_y,
    }


def build_projection_2d(
    usable_docs: List[Dict[str, Any]],
    distance_matrix: np.ndarray,
    ranking: List[Dict[str, Any]],
    selected_id: Optional[str] = None,
    suspect_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes 2D Classical MDS projection and formats the projection dictionary
    for analyze_corpus.
    """
    X_2D, variance_explained, stress = classical_mds(distance_matrix)
    N = len(usable_docs)

    ranking_map = {str(r['id']): r for r in ranking}

    if selected_id is None and ranking:
        selected_id = str(ranking[0]['id'])

    # Determine reference documents (exclude questioned/selected document)
    ref_indices = [i for i, d in enumerate(usable_docs) if str(d['id']) != str(selected_id)]
    if len(ref_indices) < 2:
        ref_indices = list(range(N))

    spread_info = compute_reference_spread(X_2D, ref_indices)

    coordinates = []
    for i, d in enumerate(usable_docs):
        did = str(d['id'])
        row = ranking_map.get(did, {})
        score = float(row.get('score', 0.0))
        pval = row.get('p_value')
        is_sig_05 = bool(row.get('is_significant_05', False))
        # A raw score cutoff is not a validated authorship/outlier threshold.
        is_outlier = is_sig_05 if pval is not None else False

        coordinates.append({
            'id': did,
            'x': float(X_2D[i, 0]),
            'y': float(X_2D[i, 1]),
            'title': str(d.get('title', did)),
            'score': score,
            'p_value': round(float(pval), 4) if pval is not None else None,
            'is_outlier': is_outlier,
            'words': int(d.get('words', 0)),
            'is_selected': (did == str(selected_id)),
            'is_suspect': (did == str(suspect_id)) if suspect_id else False,
        })

    return {
        'coordinates': coordinates,
        'centroid': spread_info['centroid'],
        'spread_radius': spread_info['spread_radius'],
        'variance_explained': variance_explained,
        'stress': stress,
        'ellipse_1sigma': spread_info['ellipse_1sigma'],
        'ellipse_2sigma': spread_info['ellipse_2sigma'],
        'sigma_x': spread_info['sigma_x'],
        'sigma_y': spread_info['sigma_y'],
        'algorithm': ALGORITHM_NAME,
        'selected_id': str(selected_id) if selected_id else None,
        'suspect_id': str(suspect_id) if suspect_id else None,
    }


def projection_for_selection(projection, selected_id, suspect_id=None):
    """Recompute descriptive reference spread after selection, preserving MDS coordinates."""
    coords = projection.get('coordinates', [])
    if not coords:
        return projection
    X = np.asarray([[c['x'], c['y']] for c in coords], dtype=np.float64)
    indices = [i for i, c in enumerate(coords) if c['id'] != selected_id]
    spread = compute_reference_spread(X, indices)
    return {**projection, **spread, 'selected_id': selected_id, 'suspect_id': suspect_id,
            'coordinates': [{**c, 'is_selected': c['id'] == selected_id,
                              'is_suspect': c['id'] == suspect_id} for c in coords]}
