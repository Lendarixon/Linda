# -*- coding: utf-8 -*-
"""The ONNX/DirectML voter: windows, padding and scoring are identical to FastSeqCls (checked against a stub session, no GPU needed)."""
import numpy as np

from linda_desktop import onnx_gpu


class StubTok:
    cls_token_id, sep_token_id, pad_token_id = 1, 2, 0

    def __call__(self, texts, add_special_tokens=False):
        return {"input_ids": [[10 + (i % 50) for i, _ in enumerate(t.split())] for t in texts]}


class StubSession:
    """Returns logits whose difference equals the number of real tokens (so the mean over windows is checkable); records the batches."""

    def __init__(self, L):
        self.L, self.batches = L, []

    def run(self, names, feed):
        ids, mask = feed["input_ids"], feed["attention_mask"]
        assert ids.shape == mask.shape and ids.shape[1] == self.L and ids.dtype == np.int64  # fixed length, int64
        assert (ids[mask == 0] == 0).all() and (mask.sum(1) >= 2).all()  # padding hidden by the mask
        self.batches.append(len(ids))
        n = mask.sum(1).astype(np.float32)
        return [np.stack([np.zeros_like(n), n], axis=1)]


def make(tmp_path, max_len=32):
    o = onnx_gpu.OnnxSeqCls.__new__(onnx_gpu.OnnxSeqCls)
    o.max_len, o.tok, o.sess = max_len, StubTok(), StubSession(max_len)
    return o


def test_short_text_is_one_padded_window(tmp_path):
    o = make(tmp_path)
    z = o.margins(["one two three four five"])  # 5 tokens + CLS + SEP
    assert z == [7.0]


def test_long_text_is_split_in_windows_and_averaged(tmp_path):
    o = make(tmp_path)
    text = " ".join(["w"] * 100)  # 100 tokens; windows of max_len - 2 = 30 tokens
    z = o.margins([text])
    assert len(o._windows(list(range(100)))) == 4 and z == [32.0]  # four full windows of 30 + CLS + SEP
    assert max(o.sess.batches) <= onnx_gpu.MAX_BATCH


def test_batches_never_exceed_the_directml_limit(tmp_path):
    o = make(tmp_path)
    o.margins([" ".join(["w"] * 200)] * 5)  # 5 texts x 7 windows = 35 windows
    assert sum(o.sess.batches) == 35 and max(o.sess.batches) == onnx_gpu.MAX_BATCH


def test_each_text_gets_its_own_mean(tmp_path):
    o = make(tmp_path)
    z = o.margins(["a b c", " ".join(["w"] * 100)])
    assert z == [5.0, 32.0]
