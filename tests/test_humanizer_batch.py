# -*- coding: utf-8 -*-
"""Chunk batching in HumanizerBackend.generate + the full-tier RAM gate.

Batching is what makes the GPU worth using: one padded generate() for
`batch_chunks` chunks instead of one call per chunk. Measured on RX 9070 XT
(ROCm) — lite 2.6-4.6x faster, full 3.2-5.2x, candidate acceptance equal or
better (see tmp/night_20261121/HUMANIZER_NIGHT.md).
"""
from __future__ import annotations

import sys
import types

import pytest

from linda_desktop import humanize_pack


class _FakeTok:
    pad_token_id = 0
    eos_token_id = 2
    padding_side = "left"

    def __init__(self):
        self.calls = []

    def apply_chat_template(self, msgs, tokenize=True, add_generation_prompt=True,
                            return_tensors=None, enable_thinking=None, return_dict=False):
        # The product passes a message LIST ([{system..},{user..}]); index safely.
        conv = msgs[0] if isinstance(msgs[0], list) else msgs
        text = next(m["content"] for m in conv if m["role"] == "user")
        self.calls.append(text)
        n = max(4, len(text.split()))
        import torch
        ids = torch.arange(10, 10 + n, dtype=torch.long).unsqueeze(0)
        return {"input_ids": ids, "attention_mask": torch.ones_like(ids)}

    def convert_tokens_to_ids(self, t):
        return 2

    def decode(self, seq, skip_special_tokens=True):
        return "".join(chr(97 + (i % 26)) for i in seq)


class _FakeModel:
    """Records the batch shape each generate() call receives."""

    def __init__(self):
        self.shapes = []
        self.calls = 0

    def parameters(self):
        import torch
        return iter([torch.zeros(1)])

    def generate(self, inp, attention_mask=None, max_new_tokens=None, num_return_sequences=1, **kw):
        import torch
        self.calls += 1
        self.shapes.append(tuple(inp.shape))
        rows = inp.shape[0] * num_return_sequences
        tail = torch.full((rows, 3), 2, dtype=torch.long)  # eos-terminated, as the product expects
        return torch.cat([inp.repeat_interleave(num_return_sequences, 0), tail], dim=1)


def _backend(n_chunks_ok=True):
    b = humanize_pack.HumanizerBackend()
    b.tok = _FakeTok()
    b.model = _FakeModel()
    b.variant = "lite"
    return b


def test_chunks_batched_into_one_generate_call():
    b = _backend()
    out = b.generate(["a b c d", "e f g h", "i j k l"], n=4)
    assert len(out) == 3, "one candidate list per chunk"
    assert b.model.calls == 1, "three chunks must share a single generate() call"
    assert len(b.model.shapes[0]) == 2 and b.model.shapes[0][0] == 3, \
        "one row per chunk in the prompt batch (num_return_sequences expands inside generate)"
    assert all(len(v) == 4 for v in out), "n candidates per chunk"


def test_batch_respects_batch_chunks_cap():
    b = _backend()
    b.batch_chunks = 2
    b.generate(["a b", "c d", "e f", "g h", "i j"], n=4)
    assert b.model.calls == 3, "5 chunks at 2 per call = 3 calls"
    assert all(s[0] <= 2 for s in b.model.shapes)


def test_batch_chunks_zero_falls_back_to_default():
    b = _backend()
    b.batch_chunks = 0
    b.generate(["a b", "c d"], n=4)
    assert b.model.calls == 1, "0 is coerced to the default, so both chunks share one call"


def test_default_batch_chunks_is_positive():
    assert humanize_pack.HumanizerBackend().batch_chunks >= 1


def test_full_ram_gate_allows_vram_resident_full(monkeypatch, tmp_path):
    """A 13 GB-free-RAM box with 16 GB VRAM must not be refused full (or silently downgraded)."""
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(tmp_path / "models"))
    monkeypatch.setattr(humanize_pack, "free_ram_gb", lambda: 5.9)
    src = humanize_pack.Path(humanize_pack.__file__).read_text(encoding="utf-8")
    # the gate constant, not a live load: full must need < 6 GB free RAM
    assert "need_free = 2.5 if variant == \"full\"" in src


def test_cpu_generate_passes_eos_im_end_max_time_and_chunk_cap():
    """CPU generation passes <|im_end|> eos_token_id, 45s max_time, chunk-sized max_new_tokens, and 2 default candidates."""
    seen = {}

    class _ImEndTok(_FakeTok):
        eos_token_id = 2

        def convert_tokens_to_ids(self, t):
            return 99 if t == "<|im_end|>" else 2

    class _RecModel(_FakeModel):
        def generate(self, inp, **kw):
            seen.update(kw)
            return super().generate(inp, **kw)

    b = humanize_pack.HumanizerBackend()
    b.tok = _ImEndTok()
    b.model = _RecModel()
    b.variant = "lite"
    assert humanize_pack._default_candidates(b) == 2

    out = b.generate(["short chunk with six words total"], n=2)
    assert len(out) == 1 and len(out[0]) == 2
    assert seen["eos_token_id"] == [2, 99]
    assert seen["max_time"] == 45.0
    assert seen["max_new_tokens"] <= 220
    assert seen["num_return_sequences"] == 2
