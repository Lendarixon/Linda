"""Explainable corpus-relative style analysis; all uploaded text remains local."""
from __future__ import annotations
import datetime
import hashlib
import math
import platform
import unicodedata
import numpy as np
from core import WORD, features, linda
from feature_labels import feature_label
from stylometric_engine import (
    extract_stylometric_features,
    CharacterNGramModel,
    directional_cosine_delta_scores,
    char_ngram_centroid_scores,
)

VERSION = '2.0.1'
MAX_DOCUMENTS = 200
MIN_WORDS = 300
MAX_WINDOWS = 12
EXCLUDED = {'log_words', 'log_lines', 'word_count', 'char_count', 'sentence_count'}

def windows_with_offsets(text, size=300, maximum=MAX_WINDOWS):
    matches = list(WORD.finditer(text))
    count = len(matches) // size
    if not count:
        if matches:
            return [{'start': matches[0].start(),
                     'end': matches[-1].end(),
                     'excerpt': text[matches[0].start():matches[-1].end()]}]
        return []
    blocks = np.linspace(0, count-1, min(count, maximum), dtype=int)
    return [{'start': matches[int(i)*size].start(),
             'end': matches[(int(i)+1)*size-1].end(),
             'excerpt': text[matches[int(i)*size].start():matches[(int(i)+1)*size-1].end()]}
            for i in blocks]

def _profile(text, language):
    windows = windows_with_offsets(text)
    rows = [extract_stylometric_features(w['excerpt'], language) for w in windows]
    keys = sorted({k for r in rows for k,v in r.items()
                   if k not in EXCLUDED and isinstance(v,(int,float,np.number)) and math.isfinite(float(v))})
    profile = {k:float(np.mean([r[k] for r in rows if k in r and math.isfinite(float(r[k]))])) for k in keys}
    return profile, windows, rows

def _compare(vector, reference):
    center = np.median(reference, axis=0)
    mad = 1.4826 * np.median(np.abs(reference-center),axis=0)
    q25,q75 = np.percentile(reference,[25,75],axis=0)
    std = np.std(reference,axis=0)
    floor = np.maximum(np.abs(center)*0.05,0.005)
    scale = np.maximum(np.where(mad>floor,mad,np.where((q75-q25)/1.349>floor,(q75-q25)/1.349,std)),floor)
    delta = np.clip((vector-center)/scale,-6.0,6.0)
    score = float(np.sqrt(np.mean(delta**2))) if delta.size else 0.0
    return score,center,scale,delta

def _feature_rows(vector,center,scale,delta,names,limit=10,language='ru'):
    indexes = sorted(range(len(names)),key=lambda i:(-abs(float(delta[i])),names[i]))[:limit]
    return [{'name':names[i], 'description':feature_label(names[i],language),
             'value':float(vector[i]), 'reference_median':float(center[i]),
             'delta':float(vector[i]-center[i]), 'standardized_delta':float(delta[i]),
             'reference_scale':float(scale[i]),
             'direction':'above' if delta[i]>0 else 'below' if delta[i]<0 else 'equal'} for i in indexes]

def _run_permutation_test(usable, matrix, window_sets, window_profiles, names, observed_scores, n_permutations=100, seed=42):
    """Legacy experimental MAD null. Not valid for fused scores; unused by the app."""
    if n_permutations <= 0:
        return [None] * len(usable), {'iterations': 0, 'strategy': 'none'}
    rng = np.random.RandomState(seed)
    n_docs = len(usable)
    n_features = len(names)
    window_counts = [len(wp) for wp in window_profiles]
    total_windows = sum(window_counts)
    counts = np.zeros(n_docs, dtype=np.int32)

    use_window_resampling = (total_windows > n_docs and min(window_counts) > 0)
    if use_window_resampling:
        window_matrix = np.zeros((total_windows, n_features), dtype=np.float64)
        w_idx = 0
        for i, wp_list in enumerate(window_profiles):
            for wp in wp_list:
                window_matrix[w_idx] = [wp.get(k, matrix[i, j]) for j, k in enumerate(names)]
                w_idx += 1
        splits = np.cumsum(window_counts)[:-1]
        for _ in range(n_permutations):
            perm_idx = rng.permutation(total_windows)
            shuffled = window_matrix[perm_idx]
            perm_doc_matrix = np.array([chunk.mean(axis=0) for chunk in np.split(shuffled, splits)], dtype=np.float64)
            for i in range(n_docs):
                perm_ref = np.delete(perm_doc_matrix, i, axis=0)
                s, _, _, _ = _compare(perm_doc_matrix[i], perm_ref)
                if s >= observed_scores[i] - 1e-9:
                    counts[i] += 1
        strategy = 'Monte Carlo window feature vector exchange'
    else:
        for _ in range(n_permutations):
            perm_doc_matrix = np.zeros_like(matrix)
            for col in range(n_features):
                perm_doc_matrix[:, col] = rng.permutation(matrix[:, col])
            for i in range(n_docs):
                perm_ref = np.delete(perm_doc_matrix, i, axis=0)
                s, _, _, _ = _compare(perm_doc_matrix[i], perm_ref)
                if s >= observed_scores[i] - 1e-9:
                    counts[i] += 1
        strategy = 'Monte Carlo column-wise feature permutation'

    p_values = (1.0 + counts) / (1.0 + n_permutations)
    return p_values, {'iterations': n_permutations, 'seed': seed, 'strategy': strategy}

def _pairwise_details(target_vec, suspect_vec, scale, names, language='ru', limit=8):
    """Computes symmetric distance and top divergent / concordant features for a pair."""
    delta = np.clip((target_vec - suspect_vec) / scale, -6.0, 6.0)
    dist = float(np.sqrt(np.mean(delta ** 2))) if delta.size else 0.0

    div_idx = sorted(range(len(names)), key=lambda k: (-abs(float(delta[k])), names[k]))[:limit]
    divergent = [{'name': names[k], 'description': feature_label(names[k], language),
                  'target_value': float(target_vec[k]), 'suspect_value': float(suspect_vec[k]),
                  'delta': float(target_vec[k] - suspect_vec[k]), 'standardized_delta': float(delta[k]),
                  'direction': 'above' if delta[k] > 0 else 'below' if delta[k] < 0 else 'equal'}
                 for k in div_idx]

    con_idx = sorted(range(len(names)), key=lambda k: (abs(float(delta[k])), names[k]))[:limit]
    concordant = [{'name': names[k], 'description': feature_label(names[k], language),
                   'target_value': float(target_vec[k]), 'suspect_value': float(suspect_vec[k]),
                   'delta': float(target_vec[k] - suspect_vec[k]), 'standardized_delta': float(delta[k]),
                   'direction': 'equal' if abs(delta[k]) < 0.05 else ('above' if delta[k] > 0 else 'below')}
                  for k in con_idx]

    return dist, divergent, concordant

def analyze_corpus(documents, language='en', target_id=None, suspect_id=None, n_permutations=100, seed=42, progress=None):
    def _emit(stage, done, total):
        if progress is not None:
            progress(stage, done, total)
    if language not in ('en','pl','ru'):
        raise ValueError('Выберите язык EN, PL или RU.')
    if not isinstance(documents,list) or not 4<=len(documents)<=MAX_DOCUMENTS:
        raise ValueError('Нужно от 4 до 200 документов: исследуемый и минимум три для сравнения.')
    ids=set(); hashes=set(); usable=[]; skipped=[]; total_bytes=0
    for d in documents:
        if not isinstance(d,dict): raise ValueError('Некорректная запись документа.')
        did=d.get('id')
        if not isinstance(did,str) or not did.strip() or len(did)>200 or not did.isprintable():
            raise ValueError('Каждый документ должен иметь непустой уникальный ID.')
        if did in ids: raise ValueError('Повторяется ID документа: '+did)
        ids.add(did)
        text=d.get('text'); title=d.get('title') or did
        if not isinstance(text,str) or not isinstance(title,str): raise ValueError('Название и текст должны быть строками.')
        if len(text.encode('utf-8'))>2*1024**2: raise ValueError('Документ больше 2 МБ: '+title[:100])
        total_bytes += len(text.encode('utf-8'))
        if total_bytes > 20*1024**2:
            raise ValueError('Корпус превышает 20 МиБ в UTF-8.')
        normalized=' '.join(unicodedata.normalize('NFC',text).casefold().split())
        digest=hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        if digest in hashes: raise ValueError('Повторяется текст: '+title[:100]+'. Дубликаты искажают профиль корпуса.')
        hashes.add(digest)
        words=len(WORD.findall(text))
        text_sha256 = hashlib.sha256(text.encode('utf-8')).hexdigest()
        file_sha256 = d.get('file_sha256') or text_sha256
        doc_format = d.get('format', 'txt')
        filename = d.get('filename') or title
        if words<MIN_WORDS:
            skipped.append({'id':did,'title':title[:300],'words':words,'reason':'Меньше 300 слов',
                            'sha256':text_sha256,'file_sha256':file_sha256,'format':doc_format,
                            'filename':filename,'status':'skipped'})
            continue
        usable.append({'id':did,'title':title[:300],'text':text,'words':words,
                       'sha256':text_sha256,'file_sha256':file_sha256,'format':doc_format,
                       'filename':filename,'status':'analyzed'})
    if target_id is not None and target_id not in {d['id'] for d in usable}:
        raise ValueError('Выбранный документ отсутствует или слишком короткий.')
    if suspect_id is not None and suspect_id not in {d['id'] for d in usable}:
        raise ValueError('Выбранный подозреваемый отсутствует или слишком короткий.')
    if suspect_id is not None and target_id is not None and suspect_id == target_id:
        raise ValueError('Подозреваемый должен отличаться от исследуемого документа.')
    if len(usable)<4: raise ValueError('После исключения коротких текстов нужно минимум 4 документа.')
    _emit('checking', 1, 1)
    # Stable ordering makes results independent of upload order, including ties.
    usable.sort(key=lambda d:d['id'])
    profiles=[]; window_sets=[]; window_profiles=[]
    for _pi, d in enumerate(usable):
        p,w,wp=_profile(d['text'],language)
        profiles.append(p); window_sets.append(w); window_profiles.append(wp)
        _emit('profiling', _pi + 1, len(usable))
    names=sorted(set.intersection(*(set(p) for p in profiles)))
    if not names: raise ValueError('Не удалось извлечь сопоставимые признаки.')
    matrix=np.array([[p[k] for k in names] for p in profiles],dtype=np.float64)

    # Compute corpus-level robust scale for symmetric pairwise distances
    center_full = np.median(matrix, axis=0)
    mad_full = 1.4826 * np.median(np.abs(matrix - center_full), axis=0)
    q25_f, q75_f = np.percentile(matrix, [25, 75], axis=0)
    std_full = np.std(matrix, axis=0)
    floor_f = np.maximum(np.abs(center_full) * 0.05, 0.005)
    corpus_scale = np.maximum(np.where(mad_full > floor_f, mad_full, np.where((q75_f - q25_f) / 1.349 > floor_f, (q75_f - q25_f) / 1.349, std_full)), floor_f)

    # Compute leave-one-out outlier scores
    raw_scores = []
    top_feature_list = []
    window_results_list = []
    centers = []
    scales = []
    deltas = []
    for i, d in enumerate(usable):
        reference = np.delete(matrix, i, axis=0)
        score, center, scale, delta = _compare(matrix[i], reference)
        raw_scores.append(score)
        centers.append(center); scales.append(scale); deltas.append(delta)
        top = _feature_rows(matrix[i], center, scale, delta, names, language=language)
        top_feature_list.append(top)
        w_res = []
        for w, p in zip(window_sets[i], window_profiles[i]):
            v = np.array([p.get(k, matrix[i, j]) for j, k in enumerate(names)], dtype=np.float64)
            z = np.clip((v - center) / scale, -6.0, 6.0)
            w_res.append(dict(w, score=float(np.sqrt(np.mean(z * z))),
                              top_features=_feature_rows(v, center, scale, z, names, 5, language)))
        window_results_list.append(w_res)
        _emit('comparing', i + 1, len(usable))

    # Multi-Metric Stylometric Fusion (Eder MAD + Directional Cosine Delta + Character 3-4 N-Gram Centroid)
    s_mad = np.array(raw_scores, dtype=np.float64)
    s_cos = directional_cosine_delta_scores(matrix)
    char_model = CharacterNGramModel.get_default()
    c_list = []
    for i, d in enumerate(usable):
        _emit('character_features', i, len(usable))
        excerpts = [w['excerpt'] for w in window_sets[i]] if window_sets[i] else [d['text']]
        w_chars = char_model.transform(excerpts, language)
        c_list.append(np.mean(w_chars, axis=0))
    C = np.array(c_list, dtype=np.float64)
    s_char = char_ngram_centroid_scores(C)

    def _znorm(arr: np.ndarray) -> np.ndarray:
        s = np.std(arr)
        return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)

    avg_words = float(np.mean([d['words'] for d in usable]))
    if avg_words < 600:
        w_mad, w_cos, w_char = 0.05, 0.05, 0.90
    elif avg_words > 1800:
        w_mad, w_cos, w_char = 0.20, 0.20, 0.60
    else:
        alpha = (avg_words - 600) / 1200.0
        w_mad = 0.05 + 0.15 * alpha
        w_cos = 0.05 + 0.15 * alpha
        w_char = 0.90 - 0.30 * alpha

    fused_z = w_mad * _znorm(s_mad) + w_cos * _znorm(s_cos) + w_char * _znorm(s_char)
    mad_mean = float(np.mean(s_mad))
    mad_std = float(np.std(s_mad))
    final_scores = np.maximum(0.001, mad_mean + (mad_std if mad_std > 1e-6 else 1.0) * fused_z)

    # The legacy null uses raw MAD while the observed score is a fusion.
    # It cannot support significance claims for this ranking. Retain nullable
    # schema fields until a matching, validated permutation protocol exists.
    p_values = [None] * len(usable)
    perm_meta = {'iterations': 0, 'strategy': 'disabled',
                 'reason': 'No validated permutation null for the fused ranking statistic.'}

    # Pairwise distances matrix and candidate rankings
    n_usable = len(usable)
    dist_matrix = np.zeros((n_usable, n_usable), dtype=np.float64)
    pairwise_matrix = {}
    pairwise_candidates = {}
    for i, di in enumerate(usable):
        pw_row = {}
        for j, dj in enumerate(usable):
            if i != j:
                d_ij = float(np.sqrt(np.mean(np.clip((matrix[i] - matrix[j]) / corpus_scale, -6.0, 6.0) ** 2)))
                dist_matrix[i, j] = d_ij
                pw_row[dj['id']] = d_ij
        pairwise_matrix[di['id']] = pw_row
        sorted_cands = sorted(pw_row.items(), key=lambda item: (item[1], item[0]))
        pairwise_candidates[di['id']] = [
            {'id': cid, 'title': next(x['title'] for x in usable if x['id'] == cid),
             'distance': cdist, 'rank': r}
            for r, (cid, cdist) in enumerate(sorted_cands, 1)
        ]
        _emit('comparing', i + 1, n_usable)

    ranking = []
    for i, d in enumerate(usable):
        score = float(final_scores[i])
        top = top_feature_list[i]
        window_results = window_results_list[i]
        scale = scales[i]
        nearest = min((j for j in range(len(usable)) if j != i),
                      key=lambda j: (float(np.mean(np.clip((matrix[j] - matrix[i]) / scale, -6, 6) ** 2)), usable[j]['id']))
        major = [x['description'] for x in top[:3] if abs(x['standardized_delta']) > 0.05]
        prefix = {'ru': 'Главные отличия: ', 'en': 'Main differences: ', 'pl': 'Główne różnice: '}[language]
        empty = {'ru': 'Заметных отличий по измеренным признакам не найдено.',
                 'en': 'No notable differences in the measured features.',
                 'pl': 'Nie stwierdzono wyraźnych różnic w mierzonych cechach.'}[language]
        summary = prefix + ', '.join(major) + '.' if major else empty

        p_val = round(float(p_values[i]), 4) if p_values[i] is not None else None
        is_sig_05 = bool(p_val < 0.05) if p_val is not None else False
        is_sig_01 = bool(p_val < 0.01) if p_val is not None else False
        sig_label = ('p < 0.01' if is_sig_01 else ('p < 0.05' if is_sig_05 else 'not significant')) if p_val is not None else 'N/A'

        cands = pairwise_candidates[d['id']]
        ranking.append({'id': d['id'], 'title': d['title'], 'score': score, 'words': d['words'],
                        'p_value': p_val, 'is_significant_05': is_sig_05, 'is_significant_01': is_sig_01,
                        'significance_label': sig_label, 'permutations_tested': 0,
                        'reference_count': len(usable) - 1, 'window_count': len(window_results),
                        'feature_count': len(names), 'top_features': top, 'summary': summary,
                        'windows': window_results, 'sha256': d['sha256'],
                        'representative_reference': {'id': usable[nearest]['id'], 'title': usable[nearest]['title'],
                                                    'excerpt': window_sets[nearest][0]['excerpt'][:400]},
                        'closest_suspect': cands[0] if cands else None,
                        'suspect_candidates': cands})

    ranking.sort(key=lambda r: (-r['score'], r['id']))
    selected = next((r for r in ranking if r['id'] == target_id), ranking[0])

    # Build active Pairwise Suspect Attribution
    target_idx = next(i for i, d in enumerate(usable) if d['id'] == selected['id'])
    cand_list = pairwise_candidates[selected['id']]
    if suspect_id and suspect_id != selected['id'] and suspect_id in pairwise_matrix.get(selected['id'], {}):
        chosen_suspect_id = suspect_id
    else:
        chosen_suspect_id = cand_list[0]['id'] if cand_list else None

    if chosen_suspect_id:
        suspect_idx = next(i for i, d in enumerate(usable) if d['id'] == chosen_suspect_id)
        pw_dist, pw_div, pw_con = _pairwise_details(matrix[target_idx], matrix[suspect_idx],
                                                    corpus_scale, names, language=language)
        s_rank = next(c['rank'] for c in cand_list if c['id'] == chosen_suspect_id)
        pairwise_attribution = {
            'target_id': usable[target_idx]['id'],
            'target_title': usable[target_idx]['title'],
            'suspect_id': usable[suspect_idx]['id'],
            'suspect_title': usable[suspect_idx]['title'],
            'distance': pw_dist,
            'attribution_rank': s_rank,
            'total_candidates': len(usable) - 1,
            'top_divergent_features': pw_div,
            'top_concordant_features': pw_con,
            'candidates': cand_list
        }
    else:
        pairwise_attribution = None

    # 2D Stylistic Distance Map (Classical Metric Multidimensional Scaling / MDS)
    from projection_2d import build_projection_2d
    _emit('projection', 1, 1)
    projection_2d = build_projection_2d(
        usable_docs=usable,
        distance_matrix=dist_matrix,
        ranking=ranking,
        selected_id=selected['id'],
        suspect_id=chosen_suspect_id
    )

    # Forensic Chain of Custody
    custody_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    chain_of_custody = {
        'timestamp_utc': custody_timestamp,
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'machine': platform.machine(),
        },
        'algorithm': {
            'name': 'corpus-relative robust leave-one-out stylometry',
            'version': VERSION,
            'hash_encoding': 'SHA-256 (UTF-8 bytes of decoded text)',
            'schema_version': '1.2'
        },
        'evidence_count': len(documents),
        'analyzed_count': len(usable),
        'skipped_count': len(skipped),
        'evidence_files': [
            {'id': d['id'], 'title': d['title'], 'filename': d.get('filename', d['title']),
             'format': d.get('format', 'txt'), 'words': d['words'], 'sha256': d['sha256'],
             'file_sha256': d.get('file_sha256', d['sha256']), 'status': 'analyzed'}
            for d in usable
        ] + [
            {'id': d['id'], 'title': d['title'], 'filename': d.get('filename', d['title']),
             'format': d.get('format', 'txt'), 'words': d['words'], 'sha256': d['sha256'],
             'file_sha256': d.get('file_sha256', d['sha256']), 'status': 'skipped'}
            for d in skipped
        ]
    }

    result = {'schema_version': '1.2', 'language': language, 'corpus_count': len(usable),
              'input_count': len(documents), 'skipped': skipped, 'ranking': ranking, 'selected': selected,
              'pairwise_attribution': pairwise_attribution,
              'pairwise_matrix': pairwise_matrix,
              'pairwise_features': {'names': names,
                                    'descriptions': [feature_label(k, language) for k in names],
                                    'scale': corpus_scale.tolist(),
                                    'vectors': {d['id']: matrix[i].tolist() for i, d in enumerate(usable)}},
              'projection_2d': projection_2d,
              'chain_of_custody': chain_of_custody,
              'method': {'name': 'corpus-relative robust leave-one-out stylometry', 'version': VERSION,
                        'window_words': 300, 'max_windows_per_document': MAX_WINDOWS,
                        'reference_excludes_target': True, 'feature_count': len(names), 'z_clip': 6,
                        'text_hash_encoding': 'SHA-256 of decoded text encoded as UTF-8; not original file bytes',
                        'offset_unit': 'Unicode codepoints; end exclusive',
                        'absolute_length_features_excluded': sorted(EXCLUDED),
                        'permutation_test': perm_meta},
              'warnings': ['Оценка показывает отличия от этого корпуса, а не вероятность другого авторства.',
                          'Разные жанры, темы, переводы и оформление могут создавать отличия без смены автора.',
                          'Нет универсального порога: даже первый в рейтинге текст может быть обычной частью корпуса.',
                          'Объяснения статистические; они не доказывают утечку, плагиат или применение ИИ.']}
    if any(d['words'] < 1000 for d in usable):
        result['warnings'].append('Есть тексты короче 1000 слов: сравнение менее устойчиво.')
    if language != 'ru':
        result['warnings'] = {
            'en': ['Scores measure differences within this corpus, not the probability of another author.',
                   'Genre, topic, translation and formatting can create differences without a change of author.',
                   'There is no universal threshold; the highest-ranked text can still be typical of this corpus.',
                   'Statistical explanations do not prove a leak, plagiarism or AI use.'],
            'pl': ['Wyniki mierzą różnice w tym korpusie, a nie prawdopodobieństwo innego autorstwa.',
                   'Gatunek, temat, tłumaczenie i formatowanie mogą powodować różnice bez zmiany autora.',
                   'Nie istnieje uniwersalny próg; pierwszy tekst w rankingu nadal może być typowy dla korpusu.',
                   'Wyjaśnienia statystyczne nie dowodzą wycieku, plagiatu ani użycia AI.']
        }[language]
        if any(d['words'] < 1000 for d in usable):
            result['warnings'].append('Some texts have fewer than 1000 words; comparison is less stable.' if language == 'en'
                                      else 'Niektóre teksty mają mniej niż 1000 słów; porównanie jest mniej stabilne.')
        for item in skipped:
            item['reason'] = 'Fewer than 300 words' if language == 'en' else 'Mniej niż 300 słów'
    result['warnings'].append({
        'ru': 'Статистическая значимость не вычисляется: перестановочный тест для смешанной оценки не валидирован.',
        'en': 'Statistical significance is unavailable: the permutation test for the fused score has not been validated.',
        'pl': 'Istotność statystyczna jest niedostępna: test permutacyjny wyniku łączonego nie został zwalidowany.'
    }[language])
    result['method']['fusion_weights'] = {'mad': w_mad, 'cosine': w_cos, 'character_ngrams': w_char}
    result['method']['calibrated'] = False
    result['method']['feature_explanation_scope'] = 'MAD feature component; not a decomposition of the fused ranking'
    from runtime_manifest import runtime_manifest
    result['method']['implementation'] = runtime_manifest()
    from input_quality import quality_warnings
    result['input_warnings'] = quality_warnings(usable, language)
    result['warnings'].extend(result['input_warnings'])
    _emit('finalizing', 1, 1)
    return result
