# -*- coding: utf-8 -*-
"""Замер ускорений Lite без потери качества (10.10): настройки ONNX Runtime и разметка «токены из окон вердикта + дочитать остальное».
    python tools/bench_lite.py MODEL_DIR TEXT.txt ROUTING.json
A) время токенного прохода и вердикта при 1 и 4 потоках: batch 12/8, без spinning, без mem pattern; проверка, что выходы совпадают;
B) вариант reuse на 132 смешанных текстах из tools/seg_eval.build(): точность разметки и число прогонов против текущего (25% перекрытия).
Окна вердикта здесь моделируются на исходном тексте (~300 слов, первые 254 токена), без clean_text: для оценки качества этого достаточно."""
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from linda_pro.voters import SpeedOnnx  # noqa: E402
from linda_desktop.sentences import split_sentences_with_offsets  # noqa: E402


def make(model_dir, threads, batch=12, spin=True, mem=True):
    v = SpeedOnnx(model_dir, threads=threads, batch=batch)
    v._load()
    so = ort.SessionOptions()
    so.intra_op_num_threads, so.inter_op_num_threads = threads, 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if not spin:
        so.add_session_config_entry("session.intra_op.allow_spinning", "0")
    so.enable_mem_pattern = mem
    v.sess = ort.InferenceSession(str(Path(model_dir) / "model.onnx"), so, providers=["CPUExecutionProvider"])
    return v


def run_chunks(v, chunks):
    """chunks: список списков id токенов (без CLS/SEP) -> список массивов tok по каждому чанку."""
    cls_id, sep_id, pad_id = v.tok.token_to_id("<s>"), v.tok.token_to_id("</s>"), v.tok.token_to_id("<pad>")
    out = [None] * len(chunks)
    order = sorted(range(len(chunks)), key=lambda j: len(chunks[j]))
    for b in range(0, len(order), v.batch):
        idx = order[b: b + v.batch]
        width = max(len(chunks[j]) for j in idx) + 2
        ids = np.full((len(idx), width), pad_id, dtype=np.int64)
        mask = np.zeros_like(ids)
        for r, j in enumerate(idx):
            seq = [cls_id, *chunks[j], sep_id]
            ids[r, : len(seq)] = seq
            mask[r, : len(seq)] = 1
        if v.vmap is not None:
            ids = v.vmap[ids].astype(np.int64)
        res = v.sess.run(None, {"input_ids": ids, "attention_mask": mask})
        tok = res[1]
        for r, j in enumerate(idx):
            out[j] = tok[r, 1: 1 + len(chunks[j])]
    return out


def word_windows(text, words=300):
    pos = [m.start() for m in re.finditer(r"\S+", text)] + [len(text)]
    return [(pos[i], pos[min(i + words, len(pos) - 1)]) for i in range(0, len(pos) - 1, words)]


def scores(v, text, mode):
    """Пары (start, end, score) для каждого токена; число прогонов модели (чанков) для разметки сверх вердикта."""
    enc = v.tok.encode(text, add_special_tokens=False)
    ids, offs = enc.ids, enc.offsets
    n = v.max_len - 2
    tot, cnt = np.zeros(len(ids)), np.zeros(len(ids))
    extra = 0
    if mode == "current":  # как в 2.0.5.0: весь текст кусками с перекрытием 25%
        starts, s = [], 0
        while True:
            starts.append(s)
            if s + n >= len(ids):
                break
            s += (n * 3) // 4
        res = run_chunks(v, [ids[s: s + n] for s in starts])
        for s, r in zip(starts, res):
            tot[s: s + len(r)] += r
            cnt[s: s + len(r)] += 1
        extra = len(starts)
    else:  # reuse: токены первых 254 токенов каждого окна вердикта (их всё равно считают) + дочитать непокрытые участки без перекрытия
        wins = word_windows(text)
        win_chunks = []
        for a, b in wins:
            first = [k for k, (cs, ce) in enumerate(offs) if cs >= a and ce <= b][:n]
            if first:
                win_chunks.append(first)
        res = run_chunks(v, [[ids[k] for k in ch] for ch in win_chunks])
        for ch, r in zip(win_chunks, res):
            tot[ch] += r[: len(ch)]
            cnt[ch] += 1
        gaps, cur = [], []
        for k in range(len(ids)):
            if cnt[k] == 0:
                cur.append(k)
            elif cur:
                gaps.append(cur)
                cur = []
        if cur:
            gaps.append(cur)
        parts = []
        for g in gaps:
            for i in range(0, len(g), n):
                parts.append(g[i: i + n])
        res = run_chunks(v, [[ids[k] for k in p] for p in parts]) if parts else []
        for p, r in zip(parts, res):
            tot[p] += r[: len(p)]
            cnt[p] += 1
        extra = len(parts)
    sc = tot / np.maximum(cnt, 1)
    return [(offs[k][0], offs[k][1], sc[k]) for k in range(len(ids))], extra


def sentence_scores(text, toks):
    out = []
    for s in split_sentences_with_offsets(text):
        vals = [x for a, b, x in toks if a >= s.start and b <= s.end]
        out.append((s, float(np.mean(vals)) if vals else -9.0))
    return out


def main():
    model_dir, text_path, routing = sys.argv[1], sys.argv[2], sys.argv[3]
    text = open(text_path, encoding="utf-8").read()
    print("== A) runtime settings, токенный проход текущего вида (25%), прогретая сессия")
    ref = None
    for threads in (1, 4):
        for name, kw in (("base b12", {}), ("batch 8", {"batch": 8}), ("no spin", {"spin": False}), ("no mem pattern", {"mem": False})):
            v = make(model_dir, threads, **kw)
            scores(v, text[:3000], "current")
            t = time.perf_counter()
            toks, extra = scores(v, text, "current")
            dt = time.perf_counter() - t
            arr = np.array([x for _, _, x in toks])
            diff = 0.0 if ref is None else float(np.abs(arr - ref).max())
            ref = arr if ref is None else ref
            print(f"threads {threads} {name:15s} token pass {dt:5.2f}s  chunks {extra}  max|diff| {diff:.2e}")
    print("== B) reuse окон вердикта, 132 смешанных текста")
    import seg_eval
    T = json.load(open(routing, encoding="utf-8"))
    v = make(model_dir, 4)
    rnd = random.Random(7)
    res = {m: defaultdict(float) for m in ("current", "reuse")}
    chunks = {m: 0 for m in res}
    times = {m: 0.0 for m in res}
    for lang in ("en", "ru", "pl"):
        h = T["languages"][lang]["tiers"]["speed"]["heat"]["essay"]
        c, s = h["thr_5"], max(1e-3, (h["thr_05"] - h["thr_5"]) / 2)
        for kind, parts in seg_eval.build(lang, 24, 10, rnd):
            doc = "\n\n".join(t for _, t in parts)
            spans, pos = [], 0
            for ch, t in parts:
                st = doc.index(t, pos)
                spans.append((st, st + len(t), ch))
                pos = st + len(t)
            for m in res:
                t0 = time.perf_counter()
                toks, extra = scores(v, doc, m)
                times[m] += time.perf_counter() - t0
                chunks[m] += extra
                for sp, sc in sentence_scores(doc, toks):
                    p = 1 / (1 + math.exp(-max(-30, min(30, (sc - c) / s))))
                    lab = "ai" if p >= 0.72 else "unc" if p >= 0.35 else "hum"
                    ai_c = sum(max(0, min(sp.end, b) - max(sp.start, a)) for a, b, k in spans if k == "A") / max(1, sp.end - sp.start)
                    tr = "A" if ai_c >= 0.5 else "H"
                    w = max(1, len(sp.text.split()))
                    res[m][tr + lab] += w
                    res[m][tr] += w
                    if kind.startswith("mixed"):
                        res[m]["mix_ok"] += w * ((tr == "A") == (lab == "ai"))
                        res[m]["mix_w"] += w
    for m, r in res.items():
        print(f"{m:8s} human words ai {r['Hai']/r['H']:.3f} | AI words ai {r['Aai']/r['A']:.3f} | mixed word acc {r['mix_ok']/r['mix_w']:.3f} | "
              f"extra chunks {chunks[m]} | marking time {times[m]:.1f}s (4 threads; in 'reuse' the verdict windows are counted here too)")


if __name__ == "__main__":
    main()
