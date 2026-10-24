import datetime
import hashlib
import html
import json
import math
import platform
from typing import List, Dict, Any, Optional, Tuple

LOCALES = {
    'en': {
        'report_title': 'Text Investigation Report',
        'analysis_id': 'Analysis ID',
        'language': 'Language',
        'timestamp_utc': 'Timestamp (UTC)',
        'ranking': 'Document Ranking',
        'title': 'Title',
        'score': 'Score',
        'words': 'Words',
        'references': 'Reference documents',
        'summary': 'Summary',
        'sha256': 'SHA-256',
        'selected_document': 'Selected Document Comparison',
        'features': 'Top Features',
        'feature_name': 'Feature',
        'description': 'Description',
        'value': 'Value',
        'ref_median': 'Reference Median',
        'std_delta': 'Standardized Delta',
        'ref_scale': 'Reference Scale',
        'direction': 'Direction',
        'strongest_windows': 'Strongest Windows',
        'start': 'Start',
        'end': 'End',
        'excerpt': 'Excerpt',
        'original_text': 'Original Text',
        'warnings': 'Warnings',
        'skipped_documents': 'Skipped Documents',
        'method': 'Method',
        'notice': 'Scores represent relative distances within the corpus. They are not probabilities and do not constitute proof of identity, leak, plagiarism, or AI generation.',
        'no_selected': 'No document selected for detailed comparison.',
        'id': 'ID',
        'reason': 'Reason',
        'p_value': 'p-value',
        'significance': 'Statistical Significance',
        'significant_01': 'Statistically significant (p < 0.01)',
        'significant_05': 'Statistically significant (p < 0.05)',
        'not_significant': 'Not statistically significant (p ≥ 0.05)',
        'chain_of_custody': 'Forensic Chain of Custody',
        'platform': 'Platform Environment',
        'algorithm_version': 'Algorithm Version',
        'status': 'Status',
        'analyzed': 'Analyzed',
        'skipped': 'Skipped',
        'evidence_files': 'Evidence Integrity Hashes (SHA-256)',
        'pairwise_attribution': 'Pairwise Suspect Attribution',
        'questioned_doc': 'Questioned Document',
        'suspect_doc': 'Candidate Suspect',
        'stylistic_distance': 'Stylistic Distance',
        'proximity_rank': 'Proximity Rank',
        'divergent_features': 'Top Divergent Features',
        'concordant_features': 'Top Concordant (Shared) Features',
        'target_val': 'Questioned Value',
        'suspect_val': 'Suspect Value',
        'stylistic_map': '2D Stylistic Distance Map (MDS)',
        'variance_explained': 'Explained Variance',
        'stress': 'MDS Stress',
        'spread_radius': 'Corpus Spread Radius',
        'reference_centroid': 'Reference Corpus Centroid',
        'confidence_region_1s': '1σ descriptive spread (not a confidence region)',
        'reference_doc': 'Reference Document'
    },
    'ru': {
        'report_title': 'Отчет о расследовании текста',
        'analysis_id': 'ИД анализа',
        'language': 'Язык',
        'timestamp_utc': 'Временная метка (UTC)',
        'ranking': 'Рейтинг документов',
        'title': 'Название',
        'score': 'Оценка',
        'words': 'Слова',
        'references': 'Документы для сравнения',
        'summary': 'Резюме',
        'sha256': 'SHA-256',
        'selected_document': 'Сравнение выбранного документа',
        'features': 'Основные признаки',
        'feature_name': 'Признак',
        'description': 'Описание',
        'value': 'Значение',
        'ref_median': 'Медиана корпуса',
        'std_delta': 'Стандартизированная дельта',
        'ref_scale': 'Устойчивый масштаб сравнения',
        'direction': 'Направление',
        'strongest_windows': 'Наиболее отличающиеся фрагменты',
        'start': 'Начало',
        'end': 'Конец',
        'excerpt': 'Фрагмент',
        'original_text': 'Исходный текст',
        'warnings': 'Предупреждения',
        'skipped_documents': 'Пропущенные документы',
        'method': 'Метод',
        'notice': 'Оценки показывают относительные отличия внутри корпуса. Это не вероятность авторства и не доказательство утечки, плагиата или применения ИИ.',
        'no_selected': 'Документ для подробного сравнения не выбран.',
        'id': 'ИД',
        'reason': 'Причина',
        'p_value': 'p-значение',
        'significance': 'Статистическая значимость',
        'significant_01': 'Статистически значимо (p < 0.01)',
        'significant_05': 'Статистически значимо (p < 0.05)',
        'not_significant': 'Статистически не значимо (p ≥ 0.05)',
        'chain_of_custody': 'Цепочка обеспечения сохранности (Chain of Custody)',
        'platform': 'Платформа и окружение',
        'algorithm_version': 'Версия алгоритма',
        'status': 'Статус',
        'analyzed': 'Исследован',
        'skipped': 'Пропущен',
        'evidence_files': 'Хэши файлов доказательств (SHA-256)',
        'pairwise_attribution': 'Попарная атрибуция подозреваемого',
        'questioned_doc': 'Исследуемый документ',
        'suspect_doc': 'Кандидат / Подозреваемый',
        'stylistic_distance': 'Стилистическая дистанция',
        'proximity_rank': 'Ранг близости',
        'divergent_features': 'Главные различия с подозреваемым',
        'concordant_features': 'Главные сходства с подозреваемым',
        'target_val': 'Значение цели',
        'suspect_val': 'Значение подозреваемого',
        'stylistic_map': '2D-карта стилистических дистанций (MDS)',
        'variance_explained': 'Объясненная дисперсия',
        'stress': 'Стресс MDS',
        'spread_radius': 'Радиус разброса корпуса',
        'reference_centroid': 'Центроид корпуса',
        'confidence_region_1s': 'Разброс 1σ (не доверительная область)',
        'reference_doc': 'Документ корпуса'
    },
    'pl': {
        'report_title': 'Raport z badania tekstu',
        'analysis_id': 'Identyfikator analizy',
        'language': 'Język',
        'timestamp_utc': 'Znacznik czasu (UTC)',
        'ranking': 'Ranking dokumentów',
        'title': 'Tytuł',
        'score': 'Wynik',
        'words': 'Słowa',
        'references': 'Dokumenty odniesienia',
        'summary': 'Podsumowanie',
        'sha256': 'SHA-256',
        'selected_document': 'Porównanie wybranego dokumentu',
        'features': 'Główne cechy',
        'feature_name': 'Cecha',
        'description': 'Opis',
        'value': 'Wartość',
        'ref_median': 'Mediana referencyjna',
        'std_delta': 'Standaryzowana delta',
        'ref_scale': 'Skala referencyjna',
        'direction': 'Kierunek',
        'strongest_windows': 'Najbardziej odmienne fragmenty',
        'start': 'Początek',
        'end': 'Koniec',
        'excerpt': 'Fragment',
        'original_text': 'Tekst oryginalny',
        'warnings': 'Ostrzeżenia',
        'skipped_documents': 'Pominięte dokumenty',
        'method': 'Metoda',
        'notice': 'Wyniki reprezentują względne odległości wewnątrz korpusu. Nie są prawdopodobieństwami i nie stanowią dowodu tożsamości, wycieku, plagiatu ani generowania przez AI.',
        'no_selected': 'Nie wybrano dokumentu do szczegółowego porównania.',
        'id': 'ID',
        'reason': 'Powód',
        'p_value': 'wartość p',
        'significance': 'Istotność statystyczna',
        'significant_01': 'Statystycznie istotne (p < 0,01)',
        'significant_05': 'Statystycznie istotne (p < 0,05)',
        'not_significant': 'Brak istotności statystycznej (p ≥ 0,05)',
        'chain_of_custody': 'Łańcuch dowodowy (Chain of Custody)',
        'platform': 'Środowisko platformy',
        'algorithm_version': 'Wersja algorytmu',
        'status': 'Status',
        'analyzed': 'Zbadany',
        'skipped': 'Pominięty',
        'evidence_files': 'Skróty dowodów (SHA-256)',
        'pairwise_attribution': 'Parowe przypisanie podejrzanego',
        'questioned_doc': 'Badany dokument',
        'suspect_doc': 'Kandydat / Podejrzany',
        'stylistic_distance': 'Odległość stylistyczna',
        'proximity_rank': 'Ranga bliskości',
        'divergent_features': 'Najbardziej rozbieżne cechy',
        'concordant_features': 'Najbardziej zgodne cechy',
        'target_val': 'Wartość badana',
        'suspect_val': 'Wartość podejrzanego',
        'stylistic_map': 'Mapa odległości stylistycznych 2D (MDS)',
        'variance_explained': 'Wyjaśniona wariancja',
        'stress': 'Stres MDS',
        'spread_radius': 'Promień rozrzutu korpusu',
        'reference_centroid': 'Centroid korpusu',
        'confidence_region_1s': 'Rozrzut 1σ (nie obszar ufności)',
        'reference_doc': 'Dokument odniesienia'
    }
}

for language, values in {'ru': ('выше', 'ниже', 'совпадает'), 'en': ('above', 'below', 'equal'),
                        'pl': ('powyżej', 'poniżej', 'równa')}.items():
    LOCALES[language].update(dict(zip(['above', 'below', 'equal'], values)))

CSS = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f4f4; color: #333; line-height: 1.6; padding: 20px; }
  .container { max-width: 1000px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  h1 { color: #005a9e; font-size: 24px; margin-bottom: 10px; font-weight: 300; }
  h2 { color: #005a9e; font-size: 20px; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid #eaeaea; padding-bottom: 5px; font-weight: 400; }
  h3 { color: #333; font-size: 16px; margin-top: 20px; margin-bottom: 10px; font-weight: 600; }
  .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin-bottom: 20px; font-size: 14px; }
  .meta-item { background: #f9f9f9; padding: 8px 12px; border-left: 3px solid #005a9e; }
  .meta-label { font-weight: 600; color: #555; display: block; font-size: 12px; text-transform: uppercase; }
  .notice { background: #fff4ce; border-left: 4px solid #ffb900; padding: 15px; margin-bottom: 20px; font-size: 14px; color: #665000; }
  .sig-badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: 600; }
  .sig-badge.sig { background: #dff6dd; color: #107c10; }
  .sig-badge.not-sig { background: #f3f2f1; color: #605e5c; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eaeaea; }
  th { background: #f2f2f2; font-weight: 600; color: #333; }
  tr:hover { background: #fafafa; }
  .highlight { background-color: #ffeb3b; padding: 1px 2px; border-radius: 2px; }
  .warning-list { list-style: none; margin-bottom: 20px; }
  .warning-list li { background: #fde7e9; color: #a80000; padding: 8px 12px; margin-bottom: 5px; border-radius: 2px; font-size: 14px; }
  .original-text { white-space: pre-wrap; word-wrap: break-word; background: #fafafa; padding: 20px; border: 1px solid #eaeaea; font-family: 'Segoe UI', monospace; font-size: 14px; line-height: 1.8; }
  .map-container { margin: 20px 0; background: #fafafa; border: 1px solid #eaeaea; border-radius: 4px; padding: 15px; }
  .map-svg { width: 100%; height: auto; max-height: 440px; display: block; }
  .map-meta-bar { display: flex; flex-wrap: wrap; gap: 15px; font-size: 13px; color: #555; margin-top: 10px; padding-top: 8px; border-top: 1px solid #eaeaea; align-items: center; }
  .tooltip { position: relative; cursor: help; border-bottom: 1px dotted #666; }
  .tooltip:hover::after { content: attr(data-tooltip); position: absolute; bottom: 100%; left: 0; background: #333; color: #fff; padding: 5px 8px; border-radius: 3px; font-size: 12px; white-space: nowrap; z-index: 10; }
  @media print {
    body { background: #fff; padding: 0; }
    .container { max-width: 100%; box-shadow: none; padding: 0; }
    @page { size: A4; margin: 15mm; }
    h1, h2, h3 { page-break-after: avoid; }
    tr { page-break-inside: avoid; } th,td { overflow-wrap:anywhere; }
  }
</style>
"""

def _esc(val: Any) -> str:
    if val is None:
        return ''
    return html.escape(str(val), quote=True)

def _esc_json(obj: Any) -> str:
    return _esc(json.dumps(obj, ensure_ascii=False))

def coverage_note(analysis, row):
    size = analysis.get('method', {}).get('window_words')
    count = row.get('window_count')
    if not isinstance(size, int) or not isinstance(count, int) or size <= 0 or count <= 0:
        return ''
    used = size * count
    total = row.get('words', 0)
    return {
        'ru': f'Для расчёта использовано слов: {used} / {total}. Окна по {size} слов распределены по документу; хвост короче окна не участвует. Остальной текст показан для контекста.',
        'en': f'Words used for scoring: {used} / {total}. Windows of {size} words are distributed across the document; a final fragment shorter than a window is excluded. Remaining text is shown for context.',
        'pl': f'Słowa użyte do obliczeń: {used} / {total}. Okna po {size} słów są rozmieszczone w dokumencie; końcowy fragment krótszy od okna jest pomijany. Pozostały tekst służy jako kontekst.'
    }.get(analysis.get('language'), '')

CLIP_NOTES = {
    'ru': 'Некоторые отклонения достигли предела ±6. Равные полосы не означают равные исходные различия; порядок признаков при равенстве условный. Это статистические признаки, не доказанная причина смены автора.',
    'en': 'Some differences reached the ±6 cap. Equal bars do not imply equal original differences; tied features have an arbitrary order. These are statistical features, not proven causes of an author change.',
    'pl': 'Niektóre odchylenia osiągnęły limit ±6. Równe paski nie oznaczają równych pierwotnych różnic; kolejność cech przy remisie jest umowna. Są to cechy statystyczne, nie dowiedzione przyczyny zmiany autora.'
}

def clipped_feature_note(analysis, row):
    cap = analysis.get('method', {}).get('z_clip')
    if not isinstance(cap, (int, float)) or cap <= 0:
        return ''
    if not any(abs(f.get('standardized_delta', 0)) >= cap - 1e-9 for f in row.get('top_features', [])):
        return ''
    return CLIP_NOTES.get(analysis.get('language'), '')

def _format_platform(plat):
    if not isinstance(plat, dict):
        return str(plat or 'Local host environment')
    p_str = plat.get('platform') or f"{plat.get('system', '')} {plat.get('release', '')}".strip()
    py = plat.get('python_version', '')
    return f"{p_str} (Python {py})" if py else p_str

def _format_algo(algo):
    if not isinstance(algo, dict):
        return str(algo or 'corpus-relative robust leave-one-out stylometry v1.2.0')
    name = algo.get('name', 'corpus-relative robust leave-one-out stylometry')
    ver = algo.get('version', '')
    return f"{name} v{ver}" if ver else name

def _build_default_custody(analysis, documents):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ranking_map = {str(r.get('id')): r for r in analysis.get('ranking', [])}
    skipped_map = {str(s.get('id')): s for s in analysis.get('skipped', [])}
    evidence_files = []
    for d in documents:
        did = str(d.get('id'))
        title = d.get('title') or did
        text = d.get('text', '')
        sha = ranking_map.get(did, {}).get('sha256') or skipped_map.get(did, {}).get('sha256') or hashlib.sha256(text.encode('utf-8')).hexdigest()
        status = 'analyzed' if did in ranking_map else ('skipped' if did in skipped_map else 'analyzed')
        from core import WORD
        words = len(WORD.findall(text)) if text else d.get('words', 0)
        evidence_files.append({'id': did, 'title': title, 'words': words, 'sha256': sha, 'status': status})
    return {
        'timestamp_utc': ts,
        'platform': {
            'platform': platform.platform(),
            'python_version': platform.python_version()
        },
        'algorithm': {
            'name': analysis.get('method', {}).get('name', 'corpus-relative robust leave-one-out stylometry'),
            'version': analysis.get('method', {}).get('version', '1.2.0')
        },
        'evidence_files': evidence_files
    }

def _get_pairwise_attribution(analysis, selected_id, suspect_id=None):
    if suspect_id is not None and (suspect_id == selected_id or
            suspect_id not in {r.get('id') for r in analysis.get('ranking', [])}):
        raise ValueError('Choose a different candidate present in the analyzed corpus.')
    pw = analysis.get('pairwise_attribution')
    if pw and (suspect_id is None or pw.get('suspect_id') == suspect_id) and pw.get('target_id') == selected_id:
        return pw
    ranking = analysis.get('ranking', [])
    sel_row = next((r for r in ranking if str(r.get('id')) == str(selected_id)), None)
    if not sel_row:
        return pw
    cands = sel_row.get('suspect_candidates', [])
    if not cands:
        return pw
    chosen_cand = next((c for c in cands if c['id'] == suspect_id), cands[0]) if suspect_id else cands[0]
    suspect_row = next((r for r in ranking if str(r.get('id')) == str(chosen_cand['id'])), None)
    if not suspect_row:
        return pw
    full = analysis.get('pairwise_features')
    if full and selected_id in full['vectors'] and chosen_cand['id'] in full['vectors']:
        import numpy as np
        from outlier_engine import _pairwise_details
        distance, divergent, concordant = _pairwise_details(
            np.asarray(full['vectors'][selected_id]), np.asarray(full['vectors'][chosen_cand['id']]),
            np.asarray(full['scale']), full['names'], language=analysis.get('language', 'en'))
        return {'target_id': sel_row['id'], 'target_title': sel_row['title'],
                'suspect_id': suspect_row['id'], 'suspect_title': suspect_row['title'],
                'distance': distance, 'attribution_rank': chosen_cand['rank'],
                'total_candidates': len(cands), 'top_divergent_features': divergent,
                'top_concordant_features': concordant, 'candidates': cands}
    sel_feats = {f['name']: f for f in sel_row.get('top_features', [])}
    susp_feats = {f['name']: f for f in suspect_row.get('top_features', [])}
    common = sorted(set(sel_feats) & set(susp_feats))
    diffs = []
    for k in common:
        v_t = sel_feats[k].get('value', 0.0)
        v_s = susp_feats[k].get('value', 0.0)
        scale = sel_feats[k].get('reference_scale', 1.0) or 1.0
        std_d = (v_t - v_s) / scale
        diffs.append({
            'name': k,
            'description': sel_feats[k].get('description', k),
            'target_value': v_t,
            'suspect_value': v_s,
            'delta': v_t - v_s,
            'standardized_delta': std_d,
            'direction': 'above' if std_d > 0 else 'below' if std_d < 0 else 'equal'
        })
    diffs.sort(key=lambda x: -abs(x['standardized_delta']))
    div = diffs[:8]
    con = sorted(diffs, key=lambda x: abs(x['standardized_delta']))[:8]
    return {
        'target_id': sel_row['id'],
        'target_title': sel_row['title'],
        'suspect_id': suspect_row['id'],
        'suspect_title': suspect_row['title'],
        'distance': chosen_cand.get('distance', 0.0),
        'attribution_rank': chosen_cand.get('rank', 1),
        'total_candidates': len(cands),
        'top_divergent_features': div,
        'top_concordant_features': con,
        'candidates': cands
    }

def analysis_for_selection(analysis, selected_id=None, suspect_id=None):
    """Canonical immutable export view, shared by JSON and document exports."""
    did = selected_id or (analysis.get('selected') or {}).get('id')
    selected = next((r for r in analysis.get('ranking', []) if r.get('id') == did), None)
    if selected is None:
        raise ValueError('Selected document is absent from analysis ranking.')
    pair = _get_pairwise_attribution(analysis, did, suspect_id)
    result = {**analysis, 'selected': selected, 'report_selected_id': did, 'pairwise_attribution': pair}
    if analysis.get('projection_2d'):
        from projection_2d import projection_for_selection
        result['projection_2d'] = projection_for_selection(
            analysis['projection_2d'], did, pair.get('suspect_id') if pair else None)
    return result


def generate_svg_map(projection_2d: Dict[str, Any], selected_id: Optional[str] = None, suspect_id: Optional[str] = None, lang: str = 'en') -> str:
    """Renders a self-contained SVG for the 2D Stylistic Distance Map."""
    if not projection_2d or not projection_2d.get('coordinates'):
        return ''
    L = LOCALES.get(lang, LOCALES['en'])
    coords = projection_2d['coordinates']
    cent = projection_2d.get('centroid', {'x': 0.0, 'y': 0.0})
    ell = projection_2d.get('ellipse_1sigma') or {}
    spread_r = float(projection_2d.get('spread_radius', 1.0))
    extra = max(float(ell.get('semi_major', 0.0)), float(ell.get('semi_minor', 0.0)), spread_r) * 1.4

    min_x = min(float(c['x']) for c in coords)
    max_x = max(float(c['x']) for c in coords)
    min_y = min(float(c['y']) for c in coords)
    max_y = max(float(c['y']) for c in coords)

    min_x = min(min_x, float(cent['x']) - extra)
    max_x = max(max_x, float(cent['x']) + extra)
    min_y = min(min_y, float(cent['y']) - extra)
    max_y = max(max_y, float(cent['y']) + extra)

    span_x = max(max_x - min_x, 2.0)
    span_y = max(max_y - min_y, 2.0)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0

    width, height = 700, 380
    pad = 40.0
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)

    def to_screen(wx: float, wy: float) -> Tuple[float, float]:
        sx = width / 2.0 + (wx - mid_x) * scale
        sy = height / 2.0 - (wy - mid_y) * scale
        return sx, sy

    svg = []
    svg.append('<div class="map-container">')
    svg.append(f'<svg class="map-svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:#ffffff;border:1px solid #e0e0e0;border-radius:4px;">')
    units = {'en': 'arbitrary units', 'ru': '\u0443\u0441\u043b\u043e\u0432\u043d\u044b\u0435 \u0435\u0434\u0438\u043d\u0438\u0446\u044b', 'pl': 'jednostki umowne'}.get(lang, 'arbitrary units')
    svg.append(f'<text x="{width / 2:.1f}" y="{height - 6:.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="#777777">MDS-1 \u00b7 {units}</text>')
    svg.append(f'<text transform="rotate(-90 14 {(height / 2):.1f})" x="14" y="{(height / 2):.1f}" font-size="11" font-family="sans-serif" text-anchor="middle" fill="#777777">MDS-2 \u00b7 {units}</text>')

    # Grid lines
    for i in range(1, 6):
        gx = (width / 6.0) * i
        svg.append(f'<line x1="{gx:.1f}" y1="0" x2="{gx:.1f}" y2="{height}" stroke="#f0f0f0" stroke-width="1" />')
        gy = (height / 6.0) * i
        svg.append(f'<line x1="0" y1="{gy:.1f}" x2="{width}" y2="{gy:.1f}" stroke="#f0f0f0" stroke-width="1" />')

    # Ellipses (2-sigma and 1-sigma)
    cx, cy = to_screen(float(cent['x']), float(cent['y']))
    a1 = float(ell.get('semi_major', 0.0)) * scale
    b1 = float(ell.get('semi_minor', 0.0)) * scale
    angle = -float(ell.get('angle_deg', 0.0))

    if a1 > 0 and b1 > 0:
        svg.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{2.0 * a1:.2f}" ry="{2.0 * b1:.2f}" transform="rotate({angle:.2f} {cx:.2f} {cy:.2f})" fill="rgba(0,80,239,0.03)" stroke="rgba(0,80,239,0.2)" stroke-width="1" stroke-dasharray="4,4" />')
        svg.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{a1:.2f}" ry="{b1:.2f}" transform="rotate({angle:.2f} {cx:.2f} {cy:.2f})" fill="rgba(0,80,239,0.08)" stroke="rgba(0,80,239,0.5)" stroke-width="1.5" stroke-dasharray="4,4" />')

    # Centroid crosshair
    svg.append(f'<line x1="{cx - 6:.1f}" y1="{cy:.1f}" x2="{cx + 6:.1f}" y2="{cy:.1f}" stroke="#0050ef" stroke-width="1.5" />')
    svg.append(f'<line x1="{cx:.1f}" y1="{cy - 6:.1f}" x2="{cx:.1f}" y2="{cy + 6:.1f}" stroke="#0050ef" stroke-width="1.5" />')
    svg.append(f'<text x="{cx + 8:.1f}" y="{cy - 3:.1f}" font-size="11" font-family="sans-serif" fill="#0050ef">μ</text>')

    # Active questioned and suspect IDs
    active_target_id = selected_id or projection_2d.get('selected_id')
    active_suspect_id = suspect_id or projection_2d.get('suspect_id')

    target_coord = next((c for c in coords if str(c['id']) == str(active_target_id)), None)
    suspect_coord = next((c for c in coords if str(c['id']) == str(active_suspect_id)), None)

    # Stylistic distance vector
    if target_coord and suspect_coord and str(target_coord['id']) != str(suspect_coord['id']):
        p1 = to_screen(float(target_coord['x']), float(target_coord['y']))
        p2 = to_screen(float(suspect_coord['x']), float(suspect_coord['y']))
        svg.append(f'<line x1="{p1[0]:.2f}" y1="{p1[1]:.2f}" x2="{p2[0]:.2f}" y2="{p2[1]:.2f}" stroke="#d97706" stroke-width="2" stroke-dasharray="6,4" />')
        mx = (p1[0] + p2[0]) / 2.0
        my = (p1[1] + p2[1]) / 2.0
        dist_val = math.hypot(float(target_coord['x']) - float(suspect_coord['x']), float(target_coord['y']) - float(suspect_coord['y']))
        lbl = f"d = {dist_val:.3f}"
        svg.append(f'<rect x="{mx - 32:.1f}" y="{my - 9:.1f}" width="64" height="18" rx="3" fill="#ffffff" stroke="#d97706" stroke-width="1" />')
        svg.append(f'<text x="{mx:.1f}" y="{my + 4:.1f}" font-size="10" font-family="sans-serif" text-anchor="middle" fill="#d97706" font-weight="bold">{lbl}</text>')

    # Nodes with collision-avoided labels (mirrors pdf_report.py).
    compact_svg = len(coords) > 15
    _SVG_OFFSETS = [(0, 17), (0, -11), (14, 6), (-14, 6), (14, -8), (-14, -8), (0, 26), (0, -20)]
    _svg_placed = []
    if target_coord and suspect_coord and str(target_coord['id']) != str(suspect_coord['id']):
        _p1 = to_screen(float(target_coord['x']), float(target_coord['y']))
        _p2 = to_screen(float(suspect_coord['x']), float(suspect_coord['y']))
        _smx, _smy = (_p1[0] + _p2[0]) / 2.0, (_p1[1] + _p2[1]) / 2.0
        _svg_placed.append((_smx - 32, _smy - 9, _smx + 32, _smy + 9))
    def _svg_hit(a, b):
        return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])
    _svg_label_pos = {}
    _svg_order = []
    for _i, _c in enumerate(coords):
        _cid = str(_c['id'])
        if _cid == str(active_target_id):
            _pr = 0
        elif _cid == str(active_suspect_id):
            _pr = 1
        elif bool(_c.get('is_outlier', False)):
            _pr = 2
        else:
            _pr = 3
        _t = str(_c.get('title', _cid))
        _d = f"[{_i + 1}]" if compact_svg else (_t[:16] + ('…' if len(_t) > 16 else ''))
        _svg_order.append((_pr, _i, _cid, _d, max(len(_d) * 6.0 + 6.0, 18.0)))
    for _pr, _i, _cid, _d, _w in sorted(_svg_order):
        _sx0, _sy0 = to_screen(float(coords[_i]['x']), float(coords[_i]['y']))
        _chosen = None
        for _ox, _oy in _SVG_OFFSETS:
            _lx, _ly = _sx0 + _ox, _sy0 + _oy
            _box = (_lx - _w / 2.0, _ly - 7.0, _lx + _w / 2.0, _ly + 7.0)
            if _box[0] < 2 or _box[2] > width - 2 or _box[1] < 2 or _box[3] > height - 2:
                continue
            if any(_svg_hit(_box, _b) for _b in _svg_placed):
                continue
            _chosen = (_ox, _oy, _box)
            break
        if _chosen is None:
            for _k in range(40):
                _ox = ((_k % 5) - 2) * 18
                _oy = 17 + (_k // 5) * 14 - ((_k % 2) * 5)
                _lx, _ly = _sx0 + _ox, _sy0 + _oy
                _box = (_lx - _w / 2.0, _ly - 7.0, _lx + _w / 2.0, _ly + 7.0)
                if _box[0] < 2 or _box[2] > width - 2 or _box[1] < 2 or _box[3] > height - 2:
                    continue
                if any(_svg_hit(_box, _b) for _b in _svg_placed):
                    continue
                _chosen = (_ox, _oy, _box)
                break
            if _chosen is None:
                _ox, _oy = 0, 17 + _i * 14
                _lx, _ly = _sx0 + _ox, _sy0 + _oy
                _box = (_lx - _w / 2.0, _ly - 7.0, _lx + _w / 2.0, _ly + 7.0)
                _chosen = (_ox, _oy, _box)
        _svg_placed.append(_chosen[2])
        _svg_label_pos[_cid] = (_chosen[0], _chosen[1], _d)
    # Nodes
    for c in coords:
        sx, sy = to_screen(float(c['x']), float(c['y']))
        cid = str(c['id'])
        is_t = (cid == str(active_target_id))
        is_s = (cid == str(active_suspect_id))
        is_out = bool(c.get('is_outlier', False))

        if is_t:
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="14" fill="none" stroke="rgba(216,59,1,0.4)" stroke-width="3" />')
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="8" fill="#d83b01" stroke="#ffffff" stroke-width="2" />')
            txt_color = '#d83b01'
            weight = 'bold'
        elif is_s:
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="12" fill="none" stroke="rgba(245,158,11,0.4)" stroke-width="2.5" />')
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="7" fill="#f59e0b" stroke="#ffffff" stroke-width="1.8" />')
            txt_color = '#d97706'
            weight = 'bold'
        elif is_out:
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="10" fill="none" stroke="rgba(225,29,72,0.3)" stroke-width="2" />')
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="6.5" fill="#e11d48" stroke="#ffffff" stroke-width="1.5" />')
            txt_color = '#e11d48'
            weight = 'normal'
        else:
            svg.append(f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="6" fill="#0050ef" stroke="#ffffff" stroke-width="1.5" />')
            txt_color = '#333333'
            weight = 'normal'

        title = str(c.get('title', cid))
        _trunc_default = title[:16] + ('…' if len(title) > 16 else '')
        _ox, _oy, _disp = _svg_label_pos.get(cid, (0, 13, _trunc_default))
        svg.append(f'<text x="{sx + _ox:.2f}" y="{sy + _oy:.2f}" font-size="10" font-family="sans-serif" text-anchor="middle" fill="{txt_color}" font-weight="{weight}">{html.escape(_disp)}</text>')

    svg.append('</svg>')

    # Legend & Meta bar
    var_exp = float(projection_2d.get('variance_explained', 1.0)) * 100.0
    stress_val = projection_2d.get('stress')
    stress_str = f"{float(stress_val):.3f}" if stress_val is not None else '—'
    radius_val = float(projection_2d.get('spread_radius', 0.0))
    algo_name = projection_2d.get('algorithm', 'Classical Metric Multidimensional Scaling')

    svg.append('<div class="map-meta-bar">')
    svg.append(f'<span><strong>{_esc(L.get("questioned_doc", "Questioned"))}:</strong> <span style="color:#d83b01;font-weight:bold;">●</span></span>')
    svg.append(f'<span><strong>{_esc(L.get("suspect_doc", "Suspect"))}:</strong> <span style="color:#f59e0b;font-weight:bold;">●</span></span>')
    svg.append(f'<span><strong>{_esc(L.get("reference_doc", "Reference"))}:</strong> <span style="color:#0050ef;font-weight:bold;">●</span></span>')
    svg.append(f'<span><strong>{_esc(L.get("confidence_region_1s", "1σ Region"))}:</strong> <span style="border-bottom:2px dashed #0050ef;display:inline-block;width:16px;"></span></span>')
    svg.append(f'<span style="margin-left:auto;">{_esc(algo_name)} · {_esc(L.get("variance_explained", "Explained Variance"))}: <strong>{var_exp:.1f}%</strong> · {_esc(L.get("stress", "Stress"))}: <strong>{stress_str}</strong> · {_esc(L.get("spread_radius", "Radius"))}: <strong>{radius_val:.3f}</strong></span>')
    svg.append('</div>')
    svg.append('</div>')

    return ''.join(svg)

def render_report(analysis: Dict[str, Any], documents: List[Dict[str, Any]], selected_id: Optional[str] = None, suspect_id: Optional[str] = None) -> str:
    if analysis.get('projection_2d'):
        from projection_2d import projection_for_selection
        active_id = selected_id or (analysis.get('selected') or {}).get('id')
        pair = _get_pairwise_attribution(analysis, active_id, suspect_id)
        analysis = {**analysis, 'projection_2d': projection_for_selection(
            analysis['projection_2d'], active_id, pair.get('suspect_id') if pair else None)}
    lang = analysis.get('language', 'en')
    if lang not in LOCALES:
        lang = 'en'
    L = LOCALES[lang]

    doc_map = {str(d['id']): d for d in documents}

    if selected_id is not None:
        if str(selected_id) not in doc_map:
            raise ValueError(f"selected_id '{selected_id}' does not exist in documents")
        selected_row = next((r for r in analysis.get('ranking', []) if str(r.get('id')) == str(selected_id)), None)
        if selected_row is None:
            raise ValueError(f"selected_id '{selected_id}' does not exist in analysis ranking")
    else:
        selected_row = analysis.get('selected') or next(iter(analysis.get('ranking', [])), None)

    parts = []
    parts.append('<!DOCTYPE html>')
    parts.append(f'<html lang="{_esc(lang)}">')
    parts.append('<head>')
    parts.append('<meta charset="UTF-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append(f'<title>{_esc(L["report_title"])}</title>')
    parts.append(CSS)
    parts.append('</head>')
    parts.append('<body>')
    parts.append('<div class="container">')

    parts.append(f'<h1>{_esc(L["report_title"])}</h1>')
    parts.append(f'<div class="notice"><span class="tooltip" data-tooltip="{_esc(L["notice"])}">&#9432;</span> {_esc(L["notice"])}</div>')

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    parts.append('<div class="meta">')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["analysis_id"])}</span>{_esc(analysis.get("analysis_id", ""))}</div>')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["language"])}</span>{_esc(lang)}</div>')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["timestamp_utc"])}</span>{_esc(timestamp)}</div>')
    parts.append('</div>')

    warnings = analysis.get('warnings', [])
    if warnings:
        parts.append(f'<h2>{_esc(L["warnings"])}</h2>')
        parts.append('<ul class="warning-list">')
        for w in warnings:
            parts.append(f'<li>{_esc(w)}</li>')
        parts.append('</ul>')

    ranking = analysis.get('ranking', [])
    if ranking:
        parts.append(f'<h2>{_esc(L["ranking"])}</h2>')
        has_p = any('p_value' in r and r.get('p_value') is not None for r in ranking)
        cols = ['id', 'title', 'score', 'p_value', 'words', 'references', 'summary', 'sha256'] if has_p else ['id', 'title', 'score', 'words', 'references', 'summary', 'sha256']
        parts.append('<table><thead><tr>')
        for col in cols:
            parts.append(f'<th>{_esc(L[col])}</th>')
        parts.append('</tr></thead><tbody>')
        for row in ranking:
            parts.append('<tr>')
            parts.append(f'<td>{_esc(row.get("id", ""))}</td>')
            parts.append(f'<td>{_esc(row.get("title", ""))}</td>')
            parts.append(f'<td>{_esc(row.get("score", ""))}</td>')
            if has_p:
                pval = row.get('p_value')
                if pval is not None:
                    badge_cls = 'sig' if row.get('is_significant_05') else 'not-sig'
                    badge_lbl = f"{pval:.3f}" + ('*' if row.get('is_significant_05') else '')
                    parts.append(f'<td><span class="sig-badge {badge_cls}">{_esc(badge_lbl)}</span></td>')
                else:
                    parts.append('<td>—</td>')
            parts.append(f'<td>{_esc(row.get("words", ""))}</td>')
            parts.append(f'<td>{_esc(row.get("reference_count", ""))}</td>')
            parts.append(f'<td>{_esc(row.get("summary", ""))}</td>')
            parts.append(f'<td style="font-family:monospace;font-size:12px;">{_esc(row.get("sha256", ""))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')

    if analysis.get('projection_2d'):
        parts.append(f'<h2>{_esc(L["stylistic_map"])}</h2>')
        parts.append(generate_svg_map(analysis['projection_2d'], selected_id=selected_row.get('id') if selected_row else None, suspect_id=suspect_id, lang=lang))

    if selected_row:
        sel_doc = doc_map.get(str(selected_row.get('id')))
        if sel_doc:
            parts.append(f'<h2>{_esc(L["selected_document"])}</h2>')
            parts.append(f'<h3>{_esc(selected_row.get("title", ""))}</h3>')
            parts.append(f'<p>ID: {_esc(selected_row.get("id", ""))}</p>')
            if selected_row.get('p_value') is not None:
                p_val = selected_row.get('p_value')
                sig_text = L['significant_01'] if selected_row.get('is_significant_01') else (L['significant_05'] if selected_row.get('is_significant_05') else L['not_significant'])
                parts.append(f'<p><strong>{_esc(L["significance"])}:</strong> p = {_esc(p_val)} ({_esc(sig_text)})</p>')
            parts.append(f'<p>{_esc(coverage_note(analysis, selected_row))}</p>')
            clip_note = clipped_feature_note(analysis, selected_row)
            if clip_note:
                parts.append(f'<p class="notice">{_esc(clip_note)}</p>')
            original_text = sel_doc.get('text', '')

            features = selected_row.get('top_features', [])
            if features:
                parts.append(f'<h3>{_esc(L["features"])}</h3>')
                parts.append('<table><thead><tr>')
                for col in ['feature_name', 'description', 'value', 'ref_median', 'std_delta', 'ref_scale', 'direction']:
                    parts.append(f'<th>{_esc(L[col])}</th>')
                parts.append('</tr></thead><tbody>')
                for f in features:
                    parts.append('<tr>')
                    parts.append(f'<td>{_esc(f.get("name", ""))}</td>')
                    parts.append(f'<td>{_esc(f.get("description", ""))}</td>')
                    parts.append(f'<td>{_esc(f.get("value", ""))}</td>')
                    parts.append(f'<td>{_esc(f.get("reference_median", ""))}</td>')
                    parts.append(f'<td>{_esc(f.get("standardized_delta", ""))}</td>')
                    parts.append(f'<td>{_esc(f.get("reference_scale", ""))}</td>')
                    parts.append(f'<td>{_esc(L.get(f.get("direction", ""), f.get("direction", "")))}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table>')

            # Pairwise Suspect Attribution Block
            pw = _get_pairwise_attribution(analysis, str(selected_row.get('id')), suspect_id)
            if pw:
                parts.append(f'<h2>{_esc(L["pairwise_attribution"])}</h2>')
                parts.append('<div class="meta">')
                parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["questioned_doc"])}</span>{_esc(pw.get("target_title", ""))} (ID: {_esc(pw.get("target_id", ""))})</div>')
                parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["suspect_doc"])}</span>{_esc(pw.get("suspect_title", ""))} (ID: {_esc(pw.get("suspect_id", ""))})</div>')
                parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["stylistic_distance"])}</span>{_esc(f"{float(pw.get("distance", 0.0)):.3f}")}</div>')
                parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["proximity_rank"])}</span>#{_esc(pw.get("attribution_rank", ""))} / {_esc(pw.get("total_candidates", ""))}</div>')
                parts.append('</div>')

                if pw.get('top_divergent_features'):
                    parts.append(f'<h3>{_esc(L["divergent_features"])}</h3>')
                    parts.append('<table><thead><tr>')
                    parts.append(f'<th>{_esc(L["feature_name"])}</th><th>{_esc(L["description"])}</th><th>{_esc(L["target_val"])}</th><th>{_esc(L["suspect_val"])}</th><th>{_esc(L["std_delta"])}</th><th>{_esc(L["direction"])}</th>')
                    parts.append('</tr></thead><tbody>')
                    for df in pw['top_divergent_features']:
                        parts.append('<tr>')
                        parts.append(f'<td>{_esc(df.get("name", ""))}</td>')
                        parts.append(f'<td>{_esc(df.get("description", ""))}</td>')
                        parts.append(f'<td>{_esc(f"{float(df.get("target_value", 0)):.4g}")}</td>')
                        parts.append(f'<td>{_esc(f"{float(df.get("suspect_value", 0)):.4g}")}</td>')
                        parts.append(f'<td>{_esc(f"{float(df.get("standardized_delta", 0)):+.2f}")}</td>')
                        parts.append(f'<td>{_esc(L.get(df.get("direction", ""), df.get("direction", "")))}</td>')
                        parts.append('</tr>')
                    parts.append('</tbody></table>')

                if pw.get('top_concordant_features'):
                    parts.append(f'<h3>{_esc(L["concordant_features"])}</h3>')
                    parts.append('<table><thead><tr>')
                    parts.append(f'<th>{_esc(L["feature_name"])}</th><th>{_esc(L["description"])}</th><th>{_esc(L["target_val"])}</th><th>{_esc(L["suspect_val"])}</th><th>{_esc(L["std_delta"])}</th>')
                    parts.append('</tr></thead><tbody>')
                    for cf in pw['top_concordant_features']:
                        parts.append('<tr>')
                        parts.append(f'<td>{_esc(cf.get("name", ""))}</td>')
                        parts.append(f'<td>{_esc(cf.get("description", ""))}</td>')
                        parts.append(f'<td>{_esc(f"{float(cf.get("target_value", 0)):.4g}")}</td>')
                        parts.append(f'<td>{_esc(f"{float(cf.get("suspect_value", 0)):.4g}")}</td>')
                        parts.append(f'<td>{_esc(f"{float(cf.get("standardized_delta", 0)):+.2f}")}</td>')
                        parts.append('</tr>')
                    parts.append('</tbody></table>')

            all_windows = sorted(selected_row.get('windows', []), key=lambda w: w['start'])
            cursor = 0
            for win in all_windows:
                s, e = win['start'], win['end']
                if type(s) is not int or type(e) is not int or not 0 <= s < e <= len(original_text):
                    raise ValueError('Invalid window offsets')
                if s < cursor:
                    raise ValueError('Overlapping intervals')
                if original_text[s:e] != win['excerpt']:
                    raise ValueError('Excerpt mismatch')
                cursor = e
            windows = [w for w in all_windows if float(w.get('score', 0)) > 0.05]
            windows.sort(key=lambda x: float(x.get('score', 0)), reverse=True)

            if windows:
                parts.append(f'<h3>{_esc(L["strongest_windows"])}</h3>')
                parts.append('<table><thead><tr>')
                for col in ['start', 'end', 'score', 'excerpt']:
                    parts.append(f'<th>{_esc(L[col])}</th>')
                parts.append('</tr></thead><tbody>')
                for win in windows:
                    parts.append('<tr>')
                    parts.append(f'<td>{_esc(win.get("start", ""))}</td>')
                    parts.append(f'<td>{_esc(win.get("end", ""))}</td>')
                    parts.append(f'<td>{_esc(win.get("score", ""))}</td>')
                    parts.append(f'<td>{_esc(win.get("excerpt", ""))}</td>')
                    parts.append('</tr>')
                parts.append('</tbody></table>')

                intervals = []
                for win in windows:
                    s = int(win['start'])
                    e = int(win['end'])
                    exc = win.get('excerpt', '')
                    if s < 0 or e <= s or e > len(original_text):
                        raise ValueError(f"Invalid window offsets [{s}, {e}) for text length {len(original_text)}")
                    if original_text[s:e] != exc:
                        raise ValueError(f"Excerpt mismatch at [{s}:{e}]. Expected {repr(original_text[s:e])}, got {repr(exc)}")
                    intervals.append((s, e))

                intervals.sort()
                for i in range(len(intervals) - 1):
                    if intervals[i][1] > intervals[i+1][0]:
                        raise ValueError(f"Overlapping intervals: {intervals[i]} and {intervals[i+1]}")

                parts.append(f'<h3>{_esc(L["original_text"])}</h3>')
                parts.append('<div class="original-text">')
                last_idx = 0
                for s, e in intervals:
                    parts.append(_esc(original_text[last_idx:s]))
                    parts.append(f'<span class="highlight">{_esc(original_text[s:e])}</span>')
                    last_idx = e
                parts.append(_esc(original_text[last_idx:]))
                parts.append('</div>')
            else:
                parts.append(f'<h3>{_esc(L["original_text"])}</h3>')
                parts.append('<div class="original-text">' + _esc(original_text) + '</div>')
    else:
        parts.append(f'<p>{_esc(L["no_selected"])}</p>')

    # Forensic Chain of Custody Block
    coc = analysis.get('chain_of_custody') or _build_default_custody(analysis, documents)
    parts.append(f'<h2>{_esc(L["chain_of_custody"])}</h2>')
    parts.append('<div class="meta">')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["timestamp_utc"])}</span>{_esc(coc.get("timestamp_utc", timestamp))}</div>')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["platform"])}</span>{_esc(_format_platform(coc.get("platform")))}</div>')
    parts.append(f'<div class="meta-item"><span class="meta-label">{_esc(L["algorithm_version"])}</span>{_esc(_format_algo(coc.get("algorithm")))}</div>')
    parts.append('</div>')

    ev_files = coc.get('evidence_files', [])
    if ev_files:
        parts.append(f'<h3>{_esc(L["evidence_files"])}</h3>')
        parts.append('<table><thead><tr>')
        parts.append(f'<th>{_esc(L["id"])}</th><th>{_esc(L["title"])}</th><th>{_esc(L["status"])}</th><th>{_esc(L["words"])}</th><th>{_esc(L["sha256"])}</th>')
        parts.append('</tr></thead><tbody>')
        for ev in ev_files:
            parts.append('<tr>')
            parts.append(f'<td>{_esc(ev.get("id", ""))}</td>')
            parts.append(f'<td>{_esc(ev.get("title", ""))}</td>')
            parts.append(f'<td>{_esc(L.get(ev.get("status", ""), ev.get("status", "")))}</td>')
            parts.append(f'<td>{_esc(ev.get("words", ""))}</td>')
            parts.append(f'<td style="font-family:monospace;font-size:12px;">{_esc(ev.get("sha256", ""))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')

    skipped = analysis.get('skipped', [])
    if skipped:
        parts.append(f'<h2>{_esc(L["skipped_documents"])}</h2>')
        parts.append('<table><thead><tr>')
        parts.append(f'<th>{_esc(L["id"])}</th>')
        parts.append(f'<th>{_esc(L["reason"])}</th>')
        parts.append('</tr></thead><tbody>')
        for sk in skipped:
            parts.append('<tr>')
            parts.append(f'<td>{_esc(sk.get("id", ""))}</td>')
            parts.append(f'<td>{_esc(sk.get("reason", ""))}</td>')
            parts.append('</tr>')
        parts.append('</tbody></table>')

    method = analysis.get('method', {})
    if method:
        parts.append(f'<h2>{_esc(L["method"])}</h2>')
        parts.append(f'<pre>{_esc_json(method)}</pre>')

    parts.append('</div>')
    parts.append('</body>')
    parts.append('</html>')

    return ''.join(parts)
