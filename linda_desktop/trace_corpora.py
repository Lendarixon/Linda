# -*- coding: utf-8 -*-
"""Saved stylometric corpora and corpus-comparison statistics for Linda Trace."""
from __future__ import annotations

import datetime
import json
import math
import re
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from . import config

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def corpora_dir() -> Path:
    p = config.data_dir() / "trace" / "corpora"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _expand_academic_text(seed_paragraphs: list[str], target_words: int = 340) -> str:
    parts = list(seed_paragraphs)
    idx = 0
    while _word_count(" \n\n".join(parts)) < target_words and idx < 12:
        base = seed_paragraphs[idx % len(seed_paragraphs)]
        parts.append(f"Section {idx + 2}. " + base)
        idx += 1
    return "\n\n".join(parts)


def _builtin_corpora() -> dict[str, dict[str, Any]]:
    en_docs = [
        {
            "id": "acad_en_1",
            "title": "Empirical Methods in Quantitative Linguistics",
            "text": _expand_academic_text([
                "Quantitative linguistics examines measurable regularities in natural language across genres, registers, and historical periods. Researchers routinely evaluate lexical richness, syntactic complexity, and punctuation rhythm to characterize how individual writers structure arguments under institutional constraints. Because short excerpts exhibit high sampling variance, methodological guidelines emphasize window-based averaging and robust scale estimators such as the median absolute deviation.",
                "When comparing two manuscripts from different editorial traditions, analysts must separate topic vocabulary from structural habits. Function words, clause boundaries, and sentence-length dispersion remain comparatively stable even when an author shifts from theoretical exposition to empirical reporting. Nevertheless, translation, copy-editing, and collaborative revision can alter surface distributions without implying a change of primary authorship.",
                "In reproducible stylometry, every preprocessing step should be documented alongside corpus composition and sample lengths. Reporting both multivariate distances and individual feature deviations allows readers to inspect whether a divergence stems from formatting artifacts, quotation density, or genuine lexical and syntactic preferences.",
            ]),
        },
        {
            "id": "acad_en_2",
            "title": "Experimental Design in Cognitive Psychology",
            "text": _expand_academic_text([
                "Controlled behavioral experiments require careful balancing of stimulus lists, counterbalancing of condition order, and transparent exclusion criteria. In memory and reading-time paradigms, participant fatigue and item familiarity frequently introduce systematic drift unless trials are randomized within blocks. Statistical power analyses conducted prior to data collection reduce the risk of overinterpreting noisy effect sizes.",
                "Mixed-effects regression models have largely replaced aggregated analyses of variance in psycholinguistics because they account simultaneously for by-participant and by-item variability. Researchers specify random intercepts and slopes justified by the experimental design, while verifying convergence and inspecting residual distributions for skewness or influential observations.",
                "Open protocols, preregistered hypotheses, and archived analysis scripts strengthen cumulative science. When replication studies diverge from earlier findings, detailed reporting of sample demographics, task instructions, and measurement apparatus helps distinguish boundary conditions from false positives.",
            ]),
        },
        {
            "id": "acad_en_3",
            "title": "Urban Hydrology and Stormwater Resilience",
            "text": _expand_academic_text([
                "Rapid urbanization replaces permeable soils and vegetated floodplains with impervious pavements, rooftops, and compacted drainage corridors. During convective cloudbursts, reduced infiltration accelerates surface runoff and compresses hydrograph lag times, overwhelming legacy combined sewer networks. Municipal engineers increasingly combine gray infrastructure upgrades with distributed green retention basins.",
                "Hydrological modeling integrates high-resolution elevation grids, rainfall intensity-duration-frequency curves, and land-cover classifications to identify bottlenecks at the neighborhood scale. Sensitivity analyses demonstrate that antecedent soil moisture and maintenance of street inlets strongly influence peak discharge estimates. Calibration against stream-gauge records remains essential before projecting flood risk under altered climate regimes.",
                "Long-term resilience depends not only on hydraulic capacity but also on governance, land-use zoning, and equitable maintenance funding. Participatory planning with local residents improves the siting of bioswales and permeable plazas while clarifying trade-offs between capital costs and avoided property damage.",
            ]),
        },
        {
            "id": "acad_en_4",
            "title": "Comparative Constitutional Courts and Review",
            "text": _expand_academic_text([
                "Constitutional adjudication varies widely across legal systems depending on whether review is centralized in a specialized tribunal or diffused across ordinary appellate courts. Scholars of comparative public law study how appointment procedures, docket control, and dissenting opinions shape judicial independence and institutional legitimacy over time.",
                "Proportionality analysis has emerged as a prominent doctrinal framework for resolving conflicts between statutory objectives and fundamental rights. Judges sequentially assess whether a legislative measure pursues a legitimate aim, is rationally connected to that aim, impairs the right no more than necessary, and achieves an acceptable balance between public benefits and individual burdens.",
                "Empirical scholarship on judicial behavior complements doctrinal interpretation by coding citation networks, opinion length, and coalition patterns. Careful contextual reading remains indispensable, however, because procedural rules and legal terminology differ substantially between civil-law and common-law jurisdictions.",
            ]),
        },
        {
            "id": "acad_en_5",
            "title": "Electrochemical Storage and Grid Integration",
            "text": _expand_academic_text([
                "Utility-scale battery energy storage systems provide fast frequency regulation, peak shaving, and renewable curtailment reduction across modern electricity grids. Lithium-ion chemistries dominate short-duration deployments due to high round-trip efficiency and declining pack costs, whereas flow batteries and thermal reservoirs are investigated for multi-day balancing.",
                "Cell degradation arises from coupled electrochemical and mechanical mechanisms, including solid-electrolyte interphase growth, lithium plating at low temperatures, and active-material cracking under rapid cycling. Battery management systems monitor voltage, current, and cell temperature to estimate state of charge and state of health while enforcing safe operating envelopes.",
                "Techno-economic assessments evaluate levelized cost of storage under realistic tariff structures, degradation curves, and augmentation schedules. Policy frameworks that reward ancillary services and capacity adequacy accelerate deployment alongside transmission expansion and demand-response programs.",
            ]),
        },
    ]
    for d in en_docs:
        d["words"] = _word_count(d["text"])

    ru_docs = [
        {
            "id": "acad_ru_1",
            "title": "Количественные методы в корпусной лингвистике",
            "text": _expand_academic_text([
                "Количественная лингвистика изучает измеримые закономерности естественного языка в различных жанрах, регистрах и исторических периодах. Исследователи регулярно оценивают лексическое разнообразие, синтаксическую сложность и ритм пунктуации, чтобы описать структуру аргументации в научных и публицистических текстах. Поскольку короткие фрагменты обладают высокой выборочной дисперсией, методические рекомендации опираются на оконное усреднение и робастные оценки масштаба.",
                "При сопоставлении рукописей из разных редакционных традиций важно отделять тематическую лексику от устойчивых структурных привычек. Служебные слова, границы клауз и разброс длины предложений сохраняют относительную стабильность даже при смене предмета описания. Вместе с тем перевод, научное редактирование и коллективная правка способны заметно изменять поверхностные распределения признаков.",
                "В воспроизводимой стилометрии каждый этап предобработки должен фиксироваться вместе с составом корпуса и объёмом выборок. Совместное представление многомерных дистанций и отклонений по отдельным признакам позволяет проверить, вызвано ли расхождение оформлением, цитированием или реальными стилистическими особенностями текста.",
            ]),
        },
        {
            "id": "acad_ru_2",
            "title": "Экспериментальный дизайн в когнитивной психологии",
            "text": _expand_academic_text([
                "Контролируемые поведенческие эксперименты требуют тщательного уравновешивания стимульных списков, балансировки порядка условий и прозрачных критериев исключения данных. В парадигмах исследования памяти и времени чтения утомление испытуемых и знакомость стимулов часто создают систематический дрейф, если пробы не рандомизированы внутри блоков. Предварительный расчёт статистической мощности снижает риск неверной интерпретации случайных колебаний.",
                "Смешанные регрессионные модели во многом заменили агрегированный дисперсионный анализ в психолингвистике, поскольку одновременно учитывают вариативность по участникам и по стимулам. Исследователи задают случайные свободные члены и наклоны в соответствии со структурой эксперимента, проверяя сходимость алгоритма и распределение остатков на асимметрию.",
                "Открытые протоколы, пререгистрация гипотез и публикация скриптов анализа укрепляют воспроизводимость научных выводов. Когда повторные исследования расходятся с прежними результатами, подробное описание выборки и измерительной процедуры помогает отличить границы применимости эффекта от ложноположительных находок.",
            ]),
        },
        {
            "id": "acad_ru_3",
            "title": "Городская гидрология и управление ливневым стоком",
            "text": _expand_academic_text([
                "Интенсивная урбанизация заменяет проницаемые почвы и озеленённые поймы водонепроницаемыми покрытиями, кровлями и уплотнёнными дренажными коридорами. Во время конвективных ливней снижение инфильтрации ускоряет поверхностный сток и сокращает время добегания, перегружая существующие сети ливневой канализации. Инженеры всё чаще сочетают модернизацию коллекторов с распределёнными накопительными бассейнами.",
                "Гидрологическое моделирование объединяет цифровые модели рельефа высокого разрешения, кривые интенсивности осадков и классификацию землепользования для выявления узких мест на уровне кварталов. Анализ чувствительности показывает, что предшествующее увлажнение почвы и состояние дождеприёмников существенно влияют на расчётный пиковый расход воды.",
                "Долгосрочная устойчивость городской инфраструктуры зависит не только от пропускной способности сетей, но и от градостроительного зонирования и регулярного обслуживания. Совместное планирование с жителями позволяет эффективнее размещать биодренажные канавы и проницаемые площадки, снижая ущерб от локальных подтоплений.",
            ]),
        },
        {
            "id": "acad_ru_4",
            "title": "Сравнительный анализ конституционного контроля",
            "text": _expand_academic_text([
                "Конституционное правосудие заметно различается в разных правовых системах в зависимости от того, сосредоточено ли оно в специализированном суде или распределено между судами общей юрисдикции. Специалисты по сравнительному публичному праву изучают, как порядок назначения судей, фильтрация жалоб и особые мнения влияют на независимость и институциональный авторитет судов.",
                "Принцип пропорциональности стал одной из ведущих доктринальных схем разрешения конфликтов между целями законодателя и основными правами граждан. Судьи последовательно оценивают легитимность цели, пригодность выбранной меры, отсутствие менее обременительных альтернатив и соразмерность достигаемого общественного блага.",
                "Эмпирические исследования судебной практики дополняют доктринальный анализ за счёт изучения сетей цитирования, объёма мотивировочной части и устойчивости судейских позиций. Тем не менее внимательное контекстное чтение остаётся необходимым из-за различий процессуальных правил и юридической терминологии.",
            ]),
        },
        {
            "id": "acad_ru_5",
            "title": "Электрохимические накопители в энергосистемах",
            "text": _expand_academic_text([
                "Промышленные аккумуляторные накопители энергии обеспечивают быстрое регулирование частоты, сглаживание пиковых нагрузок и сокращение вынужденных ограничений возобновляемой генерации. Литий-ионные системы преобладают в проектах кратковременного хранения благодаря высокому коэффициенту полезного действия, тогда как проточные батареи исследуются для многодневного балансирования.",
                "Деградация ячеек обусловлена совокупностью электрохимических и механических процессов, включая рост межфазного слоя, осаждение лития при низких температурах и микротрещины активного материала при интенсивном циклировании. Системы управления батареей контролируют напряжение, ток и температуру для оценки остаточного ресурса.",
                "Технико-экономические модели оценивают приведённую стоимость хранения энергии с учётом реальных тарифных графиков, кривых старения и плановой замены модулей. Нормативные механизмы оплаты системных услуг ускоряют внедрение накопителей наряду с развитием магистральных линий электропередачи.",
            ]),
        },
    ]
    for d in ru_docs:
        d["words"] = _word_count(d["text"])

    return {
        "builtin_academic_en": {
            "id": "builtin_academic_en",
            "name": "Academic corpus (EN)",
            "language": "en",
            "builtin": True,
            "updated_at": "2026-01-01T00:00:00Z",
            "documents": en_docs,
        },
        "builtin_academic_ru": {
            "id": "builtin_academic_ru",
            "name": "Академический корпус (RU)",
            "language": "ru",
            "builtin": True,
            "updated_at": "2026-01-01T00:00:00Z",
            "documents": ru_docs,
        },
    }


_BUILTINS = _builtin_corpora()


def _summary(c: dict[str, Any]) -> dict[str, Any]:
    docs = c.get("documents") or []
    return {
        "id": str(c.get("id") or ""),
        "name": str(c.get("name") or ""),
        "language": str(c.get("language") or "en"),
        "count": len(docs),
        "total_words": sum(int(d.get("words") or _word_count(str(d.get("text") or ""))) for d in docs),
        "builtin": bool(c.get("builtin", False)),
        "updated_at": str(c.get("updated_at") or ""),
    }


def list_corpora() -> list[dict[str, Any]]:
    out = [_summary(c) for c in _BUILTINS.values()]
    cdir = corpora_dir()
    for p in sorted(cdir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("id"):
                data["builtin"] = False
                out.append(_summary(data))
        except Exception:
            continue
    return out


def get_corpus(corpus_id: str) -> dict[str, Any] | None:
    cid = str(corpus_id or "").strip()
    if cid in _BUILTINS:
        return json.loads(json.dumps(_BUILTINS[cid]))
    if not _SAFE_ID.match(cid):
        return None
    p = corpora_dir() / f"{cid}.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["builtin"] = False
            return data
    except Exception:
        return None
    return None


def save_corpus(name: str, documents: list[dict[str, Any]], language: str = "en", corpus_id: str | None = None) -> dict[str, Any]:
    clean_name = str(name or "").strip()[:120]
    if not clean_name:
        raise ValueError("Corpus name is required")
    lang = str(language or "en").strip().lower()
    if lang not in ("en", "ru", "pl"):
        lang = "en"
    if not isinstance(documents, list) or not (1 <= len(documents) <= 200):
        raise ValueError("Corpus must contain 1..200 documents")
    norm_docs = []
    total_bytes = 0
    for i, d in enumerate(documents):
        if not isinstance(d, dict):
            raise ValueError("Invalid document entry")
        text = str(d.get("text") or "")
        if not text.strip():
            continue
        b = len(text.encode("utf-8", "ignore"))
        if b > 2_000_000:
            raise ValueError("Document too large (2 MB)")
        total_bytes += b
        if total_bytes > 20_000_000:
            raise ValueError("Corpus too large (20 MB)")
        did = str(d.get("id") or f"doc_{i + 1}")[:80]
        title = str(d.get("title") or did).strip()[:200] or f"Document {i + 1}"
        norm_docs.append({"id": did, "title": title, "text": text, "words": _word_count(text)})
    if not norm_docs:
        raise ValueError("Corpus has no non-empty documents")
    cid = str(corpus_id or "").strip()
    if cid:
        if cid in _BUILTINS or cid.startswith("builtin_"):
            raise ValueError("Cannot overwrite built-in corpus")
        if not _SAFE_ID.match(cid):
            raise ValueError("Invalid corpus id")
    else:
        cid = "c_" + uuid.uuid4().hex[:12]
    payload = {
        "id": cid,
        "name": clean_name,
        "language": lang,
        "builtin": False,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "documents": norm_docs,
    }
    p = corpora_dir() / f"{cid}.json"
    tmp = corpora_dir() / f"{cid}.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return _summary(payload)


def delete_corpus(corpus_id: str) -> bool:
    cid = str(corpus_id or "").strip()
    if cid in _BUILTINS or cid.startswith("builtin_"):
        raise ValueError("Cannot delete built-in corpus")
    if not _SAFE_ID.match(cid):
        return False
    p = corpora_dir() / f"{cid}.json"
    if p.is_file():
        p.unlink()
        return True
    return False


def compute_corpus_comparison(analysis: dict[str, Any], target_id: str) -> dict[str, Any]:
    """Derive per-feature percentiles and distance histogram for target vs corpus."""
    pf = analysis.get("pairwise_features") or {}
    names = pf.get("names") or []
    descs = pf.get("descriptions") or names
    scales = pf.get("scale") or []
    vectors = pf.get("vectors") or {}

    target_vec = vectors.get(target_id)
    ref_ids = [k for k in vectors.keys() if k != target_id]
    percentiles: list[dict[str, Any]] = []

    if target_vec and ref_ids and len(names) == len(target_vec):
        ref_mat = np.asarray([vectors[k] for k in ref_ids], dtype=np.float64)
        t_arr = np.asarray(target_vec, dtype=np.float64)
        for i, fname in enumerate(names):
            col = ref_mat[:, i]
            tval = float(t_arr[i])
            med = float(np.median(col))
            mean = float(np.mean(col))
            sc = float(scales[i]) if i < len(scales) and float(scales[i]) > 1e-6 else max(float(np.std(col)), 1e-6)
            z = float(np.clip((tval - med) / sc, -6.0, 6.0))
            lt = float(np.sum(col < tval))
            eq = float(np.sum(col == tval))
            pct = 100.0 * (lt + 0.5 * eq) / float(len(col))
            percentiles.append({
                "name": str(fname),
                "description": str(descs[i] if i < len(descs) else fname),
                "value": tval,
                "corpus_median": med,
                "corpus_mean": mean,
                "percentile": round(pct, 1),
                "z_score": round(z, 3),
                "direction": "above" if z > 0.05 else ("below" if z < -0.05 else "equal"),
            })
        percentiles.sort(key=lambda r: (-abs(r["z_score"]), r["name"]))
        percentiles = percentiles[:16]

    ranking = analysis.get("ranking") or []
    target_row = next((r for r in ranking if str(r.get("id")) == str(target_id)), None)
    ref_scores = [float(r["score"]) for r in ranking if str(r.get("id")) != str(target_id) and r.get("score") is not None]
    target_dist = float(target_row["score"]) if target_row and target_row.get("score") is not None else 0.0

    bins: list[dict[str, Any]] = []
    if ref_scores:
        all_vals = ref_scores + [target_dist]
        lo = float(min(all_vals))
        hi = float(max(all_vals))
        if not math.isfinite(lo) or not math.isfinite(hi):
            lo, hi = 0.0, 1.0
        if hi - lo < 1e-6:
            lo = max(0.0, lo - 0.1)
            hi = hi + 0.1
        n_bins = min(10, max(5, len(ref_scores)))
        counts, edges = np.histogram(ref_scores, bins=n_bins, range=(lo, hi))
        for idx in range(len(counts)):
            bins.append({
                "start": round(float(edges[idx]), 4),
                "end": round(float(edges[idx + 1]), 4),
                "count": int(counts[idx]),
            })
        lt = sum(1 for s in ref_scores if s < target_dist)
        eq = sum(1 for s in ref_scores if s == target_dist)
        dist_pct = round(100.0 * (lt + 0.5 * eq) / len(ref_scores), 1)
        c_med = round(float(np.median(ref_scores)), 4)
        c_min = round(float(min(ref_scores)), 4)
        c_max = round(float(max(ref_scores)), 4)
    else:
        dist_pct = 50.0
        c_med = target_dist
        c_min = target_dist
        c_max = target_dist

    return {
        "target_id": str(target_id),
        "target_percentiles": percentiles,
        "distance_histogram": {
            "bins": bins,
            "target_distance": round(target_dist, 4),
            "target_percentile": dist_pct,
            "corpus_median": c_med,
            "corpus_min": c_min,
            "corpus_max": c_max,
            "corpus_count": len(ref_scores),
        },
    }
