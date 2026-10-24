"""Offline stylometry and literal evidence retrieval; no identity probabilities."""
from __future__ import annotations
import hashlib
import re
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler

WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)

def linda():
    try:
        from vendor import linda_stylometry as module
    except ImportError as exc:
        raise RuntimeError('Нет vendor/linda_stylometry.py: скопируйте исходный модуль Linda, см. README.') from exc
    # Optional external YAML dictionaries are deliberately excluded from this prototype.
    module._yaml_patterns = lambda lang: {}
    return module

def tokens(text):
    return [m.group().casefold() for m in WORD.finditer(text)]

def normalized_hash(text):
    value = ' '.join(linda().normalize(text).casefold().split())
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def validate_query(text, minimum=300):
    n = len(tokens(text or ''))
    if n < minimum:
        raise ValueError(f'Нужно минимум {minimum} слов; сейчас {n}.')
    return n

class DocumentStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, author TEXT NOT NULL, title TEXT, path TEXT, text TEXT NOT NULL, hash TEXT UNIQUE NOT NULL)')
        self.db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(text)')
        self.db.commit()

    def close(self):
        self.db.close()

    def add(self, author, text, title='', path=''):
        if not author.strip() or not tokens(text):
            raise ValueError('Пустая метка автора или текст.')
        digest = normalized_hash(text)
        old = self.db.execute('SELECT id,author FROM documents WHERE hash=?', (digest,)).fetchone()
        if old:
            if old['author'] != author:
                raise ValueError('Одинаковый нормализованный текст у разных авторов: ' + author + ' / ' + old['author'])
            return old['id']
        with self.db:
            row = self.db.execute('INSERT INTO documents(author,title,path,text,hash) VALUES(?,?,?,?,?)', (author, title, str(path), text, digest))
            self.db.execute('INSERT INTO document_fts(rowid,text) VALUES(?,?)', (row.lastrowid, text))
        return row.lastrowid

    def documents(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM documents ORDER BY author,id')]

    def import_folder(self, folder):
        root = Path(folder).resolve()
        pending = []
        for p in sorted(root.rglob('*.txt')):
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                continue
            parts = p.relative_to(root).parts
            if len(parts) < 2:
                raise ValueError('Файлы должны находиться внутри папки автора: ' + p.name)
            pending.append((parts[0], p.read_text(encoding='utf-8-sig'), p.stem, str(p)))
        # Validate the entire batch before any inserts, including existing labels.
        seen = {d['hash']: d['author'] for d in self.documents()}
        for author, text, _, _ in pending:
            h = normalized_hash(text)
            if h in seen and seen[h] != author:
                raise ValueError('Дубликат между авторами: ' + author + ' / ' + seen[h])
            seen[h] = author
        for args in pending:
            self.add(*args)
        return len(pending)

    def exact_search(self, query, limit=20):
        if not query.strip():
            raise ValueError('Введите фразу для поиска.')
        # Semantics: case-insensitive literal substring (re.IGNORECASE, Unicode
        # simple case-insensitive match, NOT full casefold: 'ß' != 'ss').
        # FTS phrase is only a candidate prefilter (token-adjacent, e.g. extra
        # spaces/punctuation still match FTS); the re search on the original
        # text is authoritative for offsets/excerpts. Limit applies AFTER postfilter.
        phrase = '"' + query.replace('"', '""') + '"'
        rows = self.db.execute('SELECT d.* FROM document_fts f JOIN documents d ON d.id=f.rowid WHERE document_fts MATCH ? ORDER BY d.id', (phrase,))
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        result = []
        for row in rows:
            d = dict(row)
            m = pattern.search(d['text'])
            if m:
                d['excerpt'] = m.group(0)
                d['offset'] = m.start()
                result.append(d)
                if len(result) >= limit:
                    break
        return result

    def overlap_search(self, query, shingle=5, limit=10):
        qmatches = list(WORD.finditer(query))
        q = tokens(query)
        if len(q) < shingle:
            raise ValueError(f'Для поиска фрагментов нужно минимум {shingle} слов.')
        def shingles(ws):
            return {tuple(ws[i:i+shingle]) for i in range(len(ws)-shingle+1)}
        qs = shingles(q)
        hits = []
        for d in self.documents():
            matches = list(WORD.finditer(d['text']))
            ws = tokens(d['text'])
            ds = shingles(ws)
            common = qs & ds
            if not common:
                continue
            evidence = []
            for block in SequenceMatcher(None, q, ws, autojunk=False).get_matching_blocks():
                if block.size < shingle:
                    continue
                a, b, size = block
                start, end = matches[b].start(), matches[b+size-1].end()
                qa, qb = qmatches[a].start(), qmatches[a+size-1].end()
                source, query_piece = d['text'][start:end], query[qa:qb]
                # Always provide byte-for-byte exact evidence, falling back to an exact shingle.
                if source != query_piece:
                    exact = next((query[m.start():qmatches[i+shingle-1].end()] for i, m in enumerate(qmatches[:len(q)-shingle+1]) if query[m.start():qmatches[i+shingle-1].end()] in d['text']), None)
                    if exact is None:
                        continue
                    start = d['text'].find(exact)
                    end = start + len(exact)
                    source = exact
                    qa = query.find(exact)
                    qb = qa + len(exact)
                evidence.append({'excerpt': source, 'source_start': start, 'source_end': end, 'query_start': qa, 'query_end': qb})
            if evidence:
                hits.append({'document_id': d['id'], 'author': d['author'], 'title': d['title'], 'path': d['path'], 'hash': d['hash'], 'jaccard': len(common)/len(qs | ds), 'evidence': evidence[:5]})
        return sorted(hits, key=lambda h: -h['jaccard'])[:limit]

def features(text, language):
    f = linda().extract_features(text, language)
    # Omit detector-oriented marker groups and optional external pattern features.
    # Absolute sample length is not authorial style; fixed-size training windows
    # give it near-zero variance and arbitrary-size queries become huge outliers.
    return {k: float(v) for k, v in f.items() if k not in ('log_words', 'log_lines') and not k.startswith(('m_', 'y_')) and np.isfinite(v)}

class StyleModel:
    def __init__(self, language='en'):
        if language not in ('en', 'ru', 'pl'):
            raise ValueError('Язык: en, ru или pl.')
        self.language = language
        self.threshold = None
        self.fitted = False

    def fit(self, texts, labels):
        if not texts or len(texts) != len(labels):
            raise ValueError('Нет обучающих текстов или меток.')
        seen = {}
        for t, a in zip(texts, labels):
            validate_query(t)
            h = normalized_hash(t)
            if h in seen and seen[h] != a:
                raise ValueError('Дубликат между авторами.')
            seen[h] = a
        self.training_hashes = set(seen)
        self.vectorizer = DictVectorizer(sparse=False)
        raw = self.vectorizer.fit_transform([features(t, self.language) for t in texts])
        self.scaler = StandardScaler().fit(raw)
        x = self.scaler.transform(raw)
        self.authors = sorted(set(labels))
        self.centroids = np.stack([x[np.array(labels) == a].mean(axis=0) for a in self.authors])
        self.raw_centroids = self.scaler.inverse_transform(self.centroids)
        self.threshold = None
        self.fitted = True
        return self

    def predict(self, text):
        n = validate_query(text)
        if not self.fitted:
            raise ValueError('Сначала обучите модель на корпусе.')
        raw = self.vectorizer.transform([features(text, self.language)])
        x = self.scaler.transform(raw)[0]
        distances = np.sqrt(np.mean((self.centroids - x)**2, axis=1))
        order = np.argsort(distances)
        best = int(order[0])
        delta = x - self.centroids[best]
        names = self.vectorizer.get_feature_names_out()
        return {'words': n, 'warning': 'Меньше 1000 слов: сравнение менее устойчиво.' if n < 1000 else '', 'status': 'candidate_only' if self.threshold is None else ('heuristic_unknown' if distances[best] > self.threshold else 'candidate_within_threshold'), 'threshold': self.threshold, 'candidates': [{'author': self.authors[i], 'distance': float(distances[i])} for i in order], 'feature_deltas': [{'feature': str(names[i]), 'query': float(raw[0,i]), 'author_mean': float(self.raw_centroids[best,i]), 'standardized_delta': float(delta[i])} for i in np.argsort(-np.abs(delta))[:12]]}

    def calibrate(self, known, unknown):
        if not known or not unknown:
            raise ValueError('Нужны отдельные известные и неизвестные validation-тексты.')
        if any(normalized_hash(t) in self.training_hashes for t in known + unknown):
            raise ValueError('Калибровочный текст совпал с обучающим.')
        kd = [self.predict(t)['candidates'][0]['distance'] for t in known]
        ud = [self.predict(t)['candidates'][0]['distance'] for t in unknown]
        candidates = sorted(set(kd + ud))
        thresholds = [float(np.nextafter(candidates[0], -np.inf))] + candidates
        self.threshold = min(thresholds, key=lambda t: (sum(d > t for d in kd)/len(kd) + sum(d <= t for d in ud)/len(ud), t))
        return {'threshold': self.threshold, 'known_n': len(kd), 'unknown_n': len(ud), 'criterion': 'minimum balanced known rejection + unknown acceptance; ties conservative'}

def book_windows(text, size=1000, maximum=24):
    matches = list(WORD.finditer(text))
    count = len(matches)//size
    indexes = np.linspace(0, count-1, min(count, maximum), dtype=int) if count else []
    return [text[matches[int(i)*size].start():matches[(int(i)+1)*size-1].end()] for i in indexes]

def validate_manifest(records, root):
    allowed = {'train', 'validation', 'test', 'unknown_validation', 'unknown_test'}
    ids, hashes, loaded = set(), {}, []
    root = Path(root).resolve()
    for r in records:
        if not all(k in r for k in ('author', 'title', 'id', 'split', 'path', 'language')):
            raise ValueError('Неполная запись manifest.')
        if r['id'] in ids or r['split'] not in allowed:
            raise ValueError('Пересечение ID книг или неверный split.')
        ids.add(r['id'])
        p = (root / r['path']).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Путь книги вне каталога manifest.')
        raw = p.read_bytes()
        text = raw.decode('utf-8-sig')
        h = normalized_hash(text)
        if h in hashes:
            raise ValueError('Дубликат целой книги: ' + r['id'])
        hashes[h] = r['id']
        loaded.append(dict(r, text=text, sha256=hashlib.sha256(raw).hexdigest(), normalized_sha256=h))
    known = {r['author'] for r in loaded if r['split']=='train'}
    if any(r['author'] in known for r in loaded if r['split'].startswith('unknown')):
        raise ValueError('Неизвестный автор присутствует в train.')
    if any(r['author'] not in known for r in loaded if r['split'] in ('validation','test')):
        raise ValueError('Известный validation/test автор отсутствует в train.')
    return loaded
