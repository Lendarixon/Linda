"""CPU logistic token head, linear vs learned width-9 score convolution.

Deployment: z = hidden.astype(float32) @ w + b; for EACH window independently,
scores = np.correlate(np.pad(z, (len(conv)//2,)*2), conv, mode='valid').
conv=[1] represents the linear head. This is cross-correlation with zero padding,
no bias or activation in the conv. Sentence scores are mean token logits;
classify AI if score >= threshold. NPZ and sidecar JSON need no torch to load.
Validation selects epoch/architecture and calibrates <=3% human-word FP;
these are validation estimates, not independent test-set results.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "4"
import numpy as np


def auc(y, scores):
    y = np.asarray(y) >= .5
    pos, neg = int(y.sum()), int((~y).sum())
    if not pos or not neg:
        return None
    order = np.argsort(scores, kind="stable")
    values, starts, counts = np.unique(scores[order], return_index=True, return_counts=True)
    ranks = np.repeat(starts + (counts + 1) / 2, counts)
    return float((ranks[y[order]].sum() - pos * (pos+1) / 2) / (pos*neg))


def word_metrics(scores, human, ai):
    nh, na = int(human.sum()), int(ai.sum())
    if not nh or not len(scores):
        return dict(threshold=None, human_word_fp=None, word_accuracy=None, ai_word_recall=None,
                    human_words=nh, ai_words=na)
    # Process tied sentence scores together; empirical weighted FP cannot exceed .03.
    order = np.argsort(-scores, kind="stable")
    ordered = scores[order]
    starts = np.r_[0, np.flatnonzero(ordered[1:] != ordered[:-1]) + 1]
    ends = np.r_[starts[1:], len(order)]
    cum_h = np.cumsum(human[order])
    allowed = np.flatnonzero(cum_h[ends-1] <= .03 * nh)
    if len(allowed):
        group = int(allowed[-1])
        threshold = float(ordered[starts[group]])
    else:
        threshold = float(np.nextafter(float(ordered[0]), np.inf))
    pred = scores >= threshold
    fp, tp = int(human[pred].sum()), int(ai[pred].sum())
    return dict(threshold=threshold, human_word_fp=fp/nh,
                word_accuracy=(nh-fp+tp)/(nh+na), ai_word_recall=tp/na if na else None,
                human_words=nh, ai_words=na)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("feats", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--batch", type=int, default=8, help="windows per CPU optimizer step")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--lr", type=float, default=.001)
    a = p.parse_args()
    if a.epochs < 1 or not 1 <= a.batch <= 32 or a.lr <= 0:
        p.error("epochs/lr positive; batch 1..32")
    metrics_path = a.out.with_suffix(".metrics.json")
    if a.out.exists() or metrics_path.exists():
        raise FileExistsError("Output head or metrics already exists")
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    with np.load(a.feats, allow_pickle=False) as f:
        hidden = f["hidden"]
        labels, ptr, splits = f["labels"], f["window_ptr"], f["split"]
        sid = f["sentence_id"]
        hwords, awords, slangs = f["sentence_human_words"], f["sentence_ai_words"], f["sentence_lang"]
        metadata = json.loads(str(f["metadata"]))
    if hidden.ndim != 2 or len(labels) != len(hidden):
        raise ValueError("Expected hidden[N,H] and labels[N]")
    H = int(hidden.shape[1])  # Essay 1024, Multi 768
    if ptr[0] != 0 or ptr[-1] != len(hidden) or np.any(np.diff(ptr) <= 0):
        raise ValueError("Invalid window boundaries")
    if not np.isfinite(hidden).all() or not np.isfinite(labels).all() or np.any((labels < 0) | (labels > 1)):
        raise ValueError("Invalid features or labels")
    window_split = []
    for start,end in zip(ptr[:-1],ptr[1:]):
        if len(np.unique(splits[start:end])) != 1:
            raise ValueError("Split changes within a window")
        window_split.append(splits[start])
    window_split = np.array(window_split)
    train, val = np.flatnonzero(window_split == "train"), np.flatnonzero(window_split == "val")
    if not len(train) or not len(val):
        raise ValueError("Both source-disjoint train and val windows required")

    class Head(torch.nn.Module):
        def __init__(self, width):
            super().__init__()
            self.linear = torch.nn.Linear(H, 1)
            torch.nn.init.zeros_(self.linear.weight)
            torch.nn.init.zeros_(self.linear.bias)
            self.conv = torch.nn.Conv1d(1,1,width,padding=width//2,groups=1,bias=False) if width > 1 else None
            if self.conv is not None:
                torch.nn.init.zeros_(self.conv.weight)
                self.conv.weight.data[0,0,width//2] = 1

        def forward(self, x, mask):
            z = self.linear(x).squeeze(-1) * mask
            return self.conv(z[:,None,:]).squeeze(1) if self.conv is not None else z

    def batch(indices):
        length = max(int(ptr[i+1]-ptr[i]) for i in indices)
        x = np.zeros((len(indices),length,H),np.float32)
        y = np.zeros((len(indices),length),np.float32)
        mask = np.zeros_like(y)
        for j,i in enumerate(indices):
            start,end = ptr[i:i+2]
            n = end-start
            x[j,:n] = hidden[start:end]
            y[j,:n] = labels[start:end]
            mask[j,:n] = 1
        return torch.from_numpy(x), torch.from_numpy(y), torch.from_numpy(mask)

    def evaluate(head):
        scores, truth, sentence = [], [], []
        with torch.inference_mode():
            for b in range(0,len(val),a.batch):
                indices = val[b:b+a.batch]
                x,y,m = batch(indices)
                pred = head(x,m).numpy()
                for j,i in enumerate(indices):
                    start,end = ptr[i:i+2]
                    scores.extend(pred[j,:end-start])
                    truth.extend(labels[start:end])
                    sentence.extend(sid[start:end])
        scores, truth, sentence = np.array(scores,dtype=np.float64),np.array(truth),np.array(sentence)
        if not np.isfinite(scores).all():
            raise ValueError("Nonfinite head scores; lower --lr")
        valid = sentence >= 0
        sums = np.bincount(sentence[valid],weights=scores[valid],minlength=len(hwords))
        counts = np.bincount(sentence[valid],minlength=len(hwords))
        present = counts > 0
        ss = sums[present] / counts[present]
        result = word_metrics(ss,hwords[present],awords[present])
        result.update(token_auc=auc(truth,scores),
                      token_logistic_loss=float(np.mean(np.logaddexp(0,scores)-truth*scores)),
                      val_tokens=len(scores), val_sentences=int(present.sum()),
                      per_language={})
        if result["threshold"] is not None:
            for lang in ("en", "ru", "pl"):
                chosen = slangs[present] == lang
                h,ai,ps = hwords[present][chosen],awords[present][chosen],ss[chosen]
                nh,na = int(h.sum()),int(ai.sum())
                predicted = ps >= result["threshold"]
                fp,tp = int(h[predicted].sum()),int(ai[predicted].sum())
                result["per_language"][lang] = dict(human_words=nh,ai_words=na,
                    human_word_fp=fp/nh if nh else None,word_accuracy=(nh-fp+tp)/(nh+na) if nh+na else None)
        return result

    best, candidates = None, []
    for width in (1,9):
        torch.manual_seed(a.seed)
        rng = np.random.default_rng(a.seed)
        head = Head(width).cpu()
        opt = torch.optim.AdamW(head.parameters(),lr=a.lr,weight_decay=.001)
        candidate = None
        for epoch in range(1,a.epochs+1):
            head.train()
            shuffled = rng.permutation(train)
            for b in range(0,len(shuffled),a.batch):
                x,y,mask = batch(shuffled[b:b+a.batch])
                opt.zero_grad(set_to_none=True)
                scores = head(x,mask)
                loss = (F.binary_cross_entropy_with_logits(scores,y,reduction="none")*mask).sum()/mask.sum()
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training loss")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(head.parameters(),1)
                opt.step()
            head.eval()
            metrics = evaluate(head)
            # Primary objective matches requested word accuracy at <=3% human-word FP.
            rank = (metrics["word_accuracy"] if metrics["word_accuracy"] is not None else -1,
                    -metrics["token_logistic_loss"])
            if candidate is None or rank > candidate["rank"]:
                candidate = dict(rank=rank,metrics=metrics,width=width,epoch=epoch,
                                 w=head.linear.weight.detach().numpy().ravel().copy(),
                                 b=head.linear.bias.detach().numpy()[0].copy(),
                                 conv=head.conv.weight.detach().numpy().ravel().copy() if head.conv is not None else np.ones(1,np.float32))
            print(json.dumps(dict(width=width,epoch=epoch,**metrics)),flush=True)
        candidates.append(dict(width=width,epoch=candidate["epoch"],metrics=candidate["metrics"]))
        if best is None or candidate["rank"] > best["rank"]:
            best = candidate
    # Verify deployment correlation orientation/padding on real validation windows.
    check = Head(best["width"])
    with torch.no_grad():
        check.linear.weight.copy_(torch.from_numpy(best["w"][None,:]))
        check.linear.bias.fill_(float(best["b"]))
        if check.conv is not None:
            check.conv.weight.copy_(torch.from_numpy(best["conv"][None,None,:]))
    check.eval()
    for i in val[:2]:
        start,end = ptr[i:i+2]
        x,y,m = batch([i])
        with torch.inference_mode():
            reference = check(x,m)[0].numpy()
        z = hidden[start:end].astype(np.float32) @ best["w"] + best["b"]
        radius = len(best["conv"])//2
        actual = np.correlate(np.pad(z,(radius,radius)),best["conv"],mode="valid")
        np.testing.assert_allclose(actual,reference,rtol=2e-4,atol=2e-4)
    metrics = dict(best["metrics"], selected_width=best["width"],selected_epoch=best["epoch"],
                   candidates=candidates,train_windows=len(train),val_windows=len(val),seed=a.seed,
                   feature_metadata=metadata,conv_semantics="cross-correlation, zero padding, per window",
                   threshold_scope="pooled validation human words; also used for architecture selection")
    encoded = json.dumps(metrics,indent=2,allow_nan=False)
    with a.out.open("xb") as f:
        np.savez(f,w=best["w"].astype(np.float32),b=np.array(best["b"],np.float32),
                 conv=best["conv"].astype(np.float32),
                 threshold=np.array(metrics["threshold"] if metrics["threshold"] is not None else np.nan),
                 metrics=np.array(encoded))
    with metrics_path.open("x",encoding="utf-8") as f:
        f.write(encoded+"\n")
    print(f"Saved {a.out} and {metrics_path}; selected width {best['width']}")


if __name__ == "__main__":
    main()
