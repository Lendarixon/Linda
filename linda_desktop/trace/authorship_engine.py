"""Local batch comparison against named reference samples; candidate ranking and verification."""
from __future__ import annotations

import datetime
import hashlib
import unicodedata
from pathlib import Path
import numpy as np

from core import WORD
from feature_labels import feature_label
from outlier_engine import _profile, windows_with_offsets
from stylometric_engine import CharacterNGramModel
import trace_config


def windows_with_stride(text, size=300, stride=150, maximum=16):
    """Generate sliding windows with overlapping stride for high-density stylistic sampling.
    For standard length texts, uses consecutive overlapping windows.
    For very long texts, distributes windows evenly across the document (quantile linspace)."""
    matches = list(WORD.finditer(text))
    total = len(matches)
    if total < size:
        return [text] if text else []
    max_starts = total - size
    if max_starts <= 0:
        return [text]
    max_linear_span = (maximum - 1) * stride
    if max_starts > max_linear_span:
        starts = np.linspace(0, max_starts, maximum, dtype=int)
    else:
        starts = list(range(0, max_starts + 1, stride))[:maximum]
    return [text[matches[s].start():matches[s + size - 1].end()] for s in starts]


def _char_vector(text, language):
    """Mean character 3-4-gram vector over the document's 300-word windows with 150-word stride."""
    excerpts = windows_with_stride(text, size=300, stride=150, maximum=16) or [text]
    return np.mean(CharacterNGramModel.get_default().transform(excerpts, language), axis=0)


def _unit(vector, what):
    """Return the vector scaled to unit length; refuse empty or non-finite vectors."""
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError('No character n-gram coverage for ' + what + '; the text has no usable features.')
    return vector / norm


def _try_extract_deeptrace_embeddings(docs, language):
    """CPU-only DeepTrace embeddings via deeptrace_runtime (ONNX-first)."""
    try:
        from deeptrace_runtime import extract_embeddings
        return extract_embeddings(docs, language)
    except Exception:
        return None


def analyze_authorship(
    references,
    documents,
    language='ru',
    progress=None,
    enable_false_match_guard=False,
    enable_deeptrace=True
):
    def _emit(stage, done, total):
        if progress is not None:
            progress(stage, done, total)
    from runtime_manifest import runtime_manifest
    from input_quality import quality_warnings
    if language not in ('ru', 'en', 'pl'):
        raise ValueError('Choose RU, EN or PL.')
    if not isinstance(references, list) or not 4 <= len(references) <= 200:
        raise ValueError('Add 4–200 reference documents: at least two samples per author.')
    if not isinstance(documents, list) or not 1 <= len(documents) <= 100:
        raise ValueError('Add 1–100 documents to check.')
    seen_ids, seen_hashes, total_bytes = set(), set(), 0
    refs, queries = [], []
    for is_reference, group in ((True, references), (False, documents)):
        for doc in group:
            if not isinstance(doc, dict):
                raise ValueError('Invalid document.')
            did, text = doc.get('id'), doc.get('text')
            title = doc.get('title') or did
            if not isinstance(did, str) or not did.strip() or len(did) > 200 or not did.isprintable() or did in seen_ids:
                raise ValueError('Each sample and document needs a unique nonempty ID.')
            if not isinstance(text, str) or not isinstance(title, str):
                raise ValueError('Document text and title must be strings.')
            size = len(text.encode('utf-8'))
            total_bytes += size
            if size > 2 * 1024**2 or total_bytes > 20 * 1024**2:
                raise ValueError('Limit: 2 MiB per text, 20 MiB in total (UTF-8).')
            words = len(WORD.findall(text))
            if words < 300:
                raise ValueError(f'At least 300 words required: {title[:100]}')
            normalized = ' '.join(unicodedata.normalize('NFC', text).casefold().split())
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            if digest in seen_hashes:
                raise ValueError('Duplicate text or a query identical to a reference sample: ' + title[:100])
            seen_ids.add(did)
            seen_hashes.add(digest)
            record = {'id': did, 'title': title[:300], 'text': text, 'words': words,
                      'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}
            if is_reference:
                author = doc.get('author')
                if not isinstance(author, str) or not author.strip() or len(author) > 200:
                    raise ValueError('Specify an author for every reference sample.')
                record['author'] = unicodedata.normalize('NFC', author).strip()
                refs.append(record)
            else:
                queries.append(record)
    authors = sorted({r['author'] for r in refs})
    if not 2 <= len(authors) <= 50:
        raise ValueError('Add 2–50 known authors.')
    counts = {author: sum(r['author'] == author for r in refs) for author in authors}
    if min(counts.values()) < 2:
        raise ValueError('Each author needs at least two distinct reference documents.')
    _emit('checking', 1, 1)

    profiles = []
    for _ri, _r in enumerate(refs):
        profiles.append(_profile(_r['text'], language)[0])
        _emit('references', _ri + 1, len(refs))
    names = sorted(set.intersection(*(set(p) for p in profiles)))
    if not names:
        raise ValueError('No comparable features.')
    X = np.asarray([[p[k] for k in names] for p in profiles])
    center = np.median(X, axis=0)
    mad = 1.4826 * np.median(np.abs(X - center), axis=0)
    floor = np.maximum(np.abs(center) * 0.05, 0.005)
    scale = np.maximum(np.where(mad > floor, mad, np.std(X, axis=0)), floor)
    # Each source document contributes equally, regardless of its window count.
    centroids = {a: X[[i for i, r in enumerate(refs) if r['author'] == a]].mean(axis=0) for a in authors}
    
    # N-gram vector extraction
    char_refs = np.asarray([_char_vector(r['text'], language) for r in refs])
    char_centroids = {}
    for a in authors:
        c = char_refs[[i for i, r in enumerate(refs) if r['author'] == a]].mean(axis=0)
        char_centroids[a] = _unit(c, 'author ' + a)
        
    # Internal author self-dispersion (pairwise median distance between author's own reference samples)
    author_self_disp = {}
    for a in authors:
        a_indices = [i for i, r in enumerate(refs) if r['author'] == a]
        if len(a_indices) >= 2:
            pair_dists = []
            for i_idx in range(len(a_indices)):
                for j_idx in range(i_idx + 1, len(a_indices)):
                    u_i = _unit(char_refs[a_indices[i_idx]], 'disp1')
                    u_j = _unit(char_refs[a_indices[j_idx]], 'disp2')
                    pair_dists.append(max(0.0, float(1.0 - np.dot(u_i, u_j))))
            d_self = float(np.median(pair_dists)) if pair_dists else 0.12
        else:
            d_self = 0.12
        author_self_disp[a] = max(0.04, d_self)

    # Optional DeepTrace Neural Engine
    deeptrace_active = False
    neural_embs = None
    if enable_deeptrace:
        _emit('deeptrace', 1, 2)
        neural_embs = _try_extract_deeptrace_embeddings(refs + queries, language)
        if neural_embs is not None:
            deeptrace_active = True
            neural_centroids = {}
            for a in authors:
                a_docs = [neural_embs[r['id']] for r in refs if r['author'] == a]
                c_nu = np.mean(a_docs, axis=0)
                norm_c = float(np.linalg.norm(c_nu))
                neural_centroids[a] = c_nu / norm_c if norm_c > 0 else c_nu

    rows = []
    for _qi, doc in enumerate(queries):
        profile, windows, _ = _profile(doc['text'], language)
        vector = np.asarray([profile[k] for k in names])
        char_vector = _unit(_char_vector(doc['text'], language), 'query ' + doc['id'])
        candidates = []
        for author in authors:
            z = np.clip((vector - centroids[author]) / scale, -6, 6)
            d_ng = max(0.0, float(1.0 - char_centroids[author] @ char_vector))
            
            # Combine with neural distance if DeepTrace is active
            if deeptrace_active and neural_embs is not None:
                q_nu = neural_embs.get(doc['id'])
                if q_nu is not None:
                    d_nu = max(0.0, float(1.0 - np.dot(q_nu, neural_centroids[author])))
                    final_d = 0.85 * d_ng + 0.15 * d_nu
                else:
                    final_d = d_ng
            else:
                final_d = d_ng
                
            candidates.append({
                'author': author,
                'distance': float(final_d),
                'ngram_distance': float(d_ng),
                'feature_distance': float(np.sqrt(np.mean(z*z))),
                'reference_count': counts[author]
            })
            
        candidates.sort(key=lambda c: (c['distance'], c['author']))
        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else best
        
        # Speculative Comparator / False Match Guard logic
        ratio = float(best['distance'] / (second['distance'] + 1e-9))
        disp = author_self_disp.get(best['author'], 0.10)
        rel_disp = float(best['distance'] / (disp + 1e-9))
        
        if enable_false_match_guard:
            # Rejection condition: ambiguous margin or excessive dispersion
            is_accepted = (ratio <= 0.92) and (rel_disp <= 1.35 or (best['distance'] <= 0.15 and ratio <= 0.70))
            if is_accepted:
                row_status = 'attributed'
                row_verdict = 'attributed'
                is_attributed = True
                verdict_label = {
                    'ru': f'Автор подтвержден: {best["author"]}',
                    'en': f'Author confirmed: {best["author"]}',
                    'pl': f'Autor potwierdzony: {best["author"]}'
                }[language]
                confidence = round(float(np.clip((1.0 - ratio) * 400.0, 50.0, 99.0)), 1)
            else:
                row_status = 'unknown_author'
                row_verdict = 'unknown_author'
                is_attributed = False
                verdict_label = {
                    'ru': 'Автор не установлен (защита от ложных совпадений)',
                    'en': 'Author unverified (false match guard)',
                    'pl': 'Autor nieustalony (ochrona przed błędnym dopasowaniem)'
                }[language]
                confidence = round(float(np.clip(ratio * 80.0, 20.0, 85.0)), 1)
        else:
            row_status = 'candidate_only'
            row_verdict = 'candidate_only'
            is_attributed = True
            verdict_label = None
            confidence = None

        delta = np.clip((vector - centroids[best['author']]) / scale, -6, 6)
        indexes = sorted(range(len(names)), key=lambda k: (-abs(float(delta[k])), names[k]))[:10]
        
        rows.append({k: doc[k] for k in ('id', 'title', 'words', 'sha256')} | {
            'status': 'candidate_only',
            'verdict': row_verdict,
            'rejected': (not is_attributed) if enable_false_match_guard else False,
            'verdict_label': verdict_label,
            'is_attributed': is_attributed,
            'confidence': confidence,
            'candidate': best['author'],
            'distance': best['distance'],
            'margin_ratio': round(ratio, 4),
            'tied': abs(candidates[1]['distance'] - best['distance']) <= 1e-9,
            'candidates': candidates,
            'window_count': len(windows),
            'analyzed_words': len(windows) * 300,
            'deeptrace_used': deeptrace_active,
            'top_features': [{'name': names[k], 'description': feature_label(names[k], language),
                              'value': float(vector[k]), 'reference_mean': float(centroids[best['author']][k]),
                              'standardized_delta': float(delta[k])} for k in indexes]})
        _emit('documents', _qi + 1, len(queries))

    notices = {
        'ru': ['Кандидат означает ближайший стиль среди добавленных образцов. Настоящий автор может отсутствовать в списке.',
               'Вероятность авторства и порог «автор неизвестен» не установлены. Результат не является доказательством.',
               'Добавляйте самостоятельные тексты одного языка и сопоставимого жанра; по два разных произведения на автора.',
               'Для устойчивого сравнения рекомендуется от 1000 слов. Образцы и проверяемые тексты не должны совпадать.'],
        'en': ['A candidate is the closest style among the supplied samples. The actual author may be absent.',
               'Authorship probabilities and an unknown-author threshold are not established. Results are not proof.',
               'Use original texts in one language and comparable genres, with two different works per author.',
               'At least 1000 words are recommended. Queries must not duplicate reference samples.'],
        'pl': ['Kandydat to najbliższy styl wśród podanych próbek. Prawdziwego autora może nie być na liście.',
               'Nie ustalono prawdopodobieństw autorstwa ani progu nieznanego autora. Wynik nie jest dowodem.',
               'Dodaj oryginalne teksty jednego języka i podobnego gatunku, po dwa różne utwory każdego autora.',
               'Zaleca się co najmniej 1000 słów. Teksty badane nie mogą powielać próbek.']}
               
    if enable_false_match_guard:
        guard_notices = {
            'ru': 'Защита от ложных совпадений активна: проверка отсекает кандидатов при отсутствии выраженного отрыва стиля.',
            'en': 'False match guard active: rejects candidates without significant stylistic margin.',
            'pl': 'Ochrona przed błędnymi dopasowaniami aktywna: odrzuca kandydatów w przypadku braku wyraźnego marginesu stylu.'
        }
        notices[language].insert(0, guard_notices[language])
        
    if deeptrace_active:
        dt_notices = {
            'ru': 'Модуль Linda DeepTrace активен: применен гибридный синтаксический анализ нейросетевых эмбеддингов.',
            'en': 'Linda DeepTrace active: hybrid neural stylistic embedding applied.',
            'pl': 'Linda DeepTrace aktywny: zastosowano hybrydową analizę osadzeń neuronowych stylu.'
        }
        notices[language].insert(0, dt_notices[language])

    _emit('finalizing', 1, 1)
    return {'schema_version': '1.0', 'mode': 'known_authors', 'language': language,
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'method': {'name': 'reference document centroid / character 3-4-gram cosine distance',
                       'version': '1.1.0', 'calibrated': False, 'window_words': 300, 'max_windows': 12,
                       'stride_words': 150, 'deeptrace_enabled': deeptrace_active,
                       'false_match_guard': enable_false_match_guard,
                       'implementation': runtime_manifest(),
                       'feature_count': len(names), 'z_clip': 6},
            'authors': [{'author': a, 'reference_count': counts[a]} for a in authors],
            'reference_count': len(refs), 'document_count': len(rows), 'results': rows,
            'reference_evidence': [{k: r[k] for k in ('id', 'title', 'author', 'words', 'sha256')} for r in refs],
            'input_warnings': quality_warnings(refs+queries, language),
            'warnings': notices[language] + quality_warnings(refs+queries, language)}
