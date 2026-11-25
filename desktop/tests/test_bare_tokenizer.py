# -*- coding: utf-8 -*-
"""The bare Rust tokenizer must reproduce AutoTokenizer ids and offsets exactly.

FastSeqCls loads `tokenizers.Tokenizer.from_file(model_dir/tokenizer.json)` instead of
AutoTokenizer (which imports every transformers model module). Any difference in ids
would change verdicts and token markup, so equality is pinned here on two levels:

* a small WordLevel tokenizer built in the test, always runs;
* the shipped QA models (EN/PL/RU/OFF slices of the dev corpora), skipped when absent:
  set LINDA_MODELS_HOME (e.g. D:/Linda_2100_Dev/qa_models).
"""
import json
import os
from pathlib import Path

import pytest

from linda_pro.voters import _BareTokenizer, load_bare_tokenizer

REPO = Path(__file__).resolve().parents[1]
EN = ["The public library opened a small reading room near the station.",
      "On Tuesday I visited the building with my neighbour.",
      "Volunteers catalogued four hundred old photographs.",
      "It's a short visit — but it changed how I read the town.",
      "COVID-19 numbers fell by 12.5% in Q3 2024.",
      "naïve café résumé coöperate",
      "  leading and trailing spaces  ",
      "double  space\n\nand a new line",
      "Mixed CYRILLIC аpple homoglyph",
      "e.g. i.e. etc."]
PL = ["Biblioteka publiczna otworzyła wiosną małą czytelnię obok dworca.",
      "Mieszkańcy mogą wypożyczać książki i korzystać z komputerów.",
      "Żółć gęślą jaźń — zażółć gęślą jaźń.",
      "Zażółć gęślą jaźń, ćma, ślimak, źdźbło, ń.",
      "W 2024 r. było 12,5% więcej czytelników.",
      "Niektóre szczegóły trudno było rozpoznać, dlatego zapisaliśmy pytania.",
      "Pan Tadeusz, czyli ostatni zajazd na Litwie.",
      "Pójdźże, kińże tę chmurność w głąb — (test myślnika)",
      "Łódź, Kraków, Gdańsk, Wrocław, Poznań.",
      "a\u00a0b niełamliwa spacja"]
RU = ["Прошлой весной городская библиотека открыла небольшой читальный зал.",
      "Жители могут брать книги и пользоваться компьютерами.",
      "Во вторник я пришёл туда с соседом.",
      "На снимках был рынок на месте сегодняшней автобусной остановки.",
      "В 2024 году — 12,5% больше читателей.",
      "Некоторые подробности оказалось трудно узнать.",
      "«Война и мир» — роман-эпопея Льва Толстого.",
      "ёжик, подъезд, объявление, съезд",
      "смешанный Latin текст внутри русского",
      "Москва·Санкт-Петербург·Новосибирск"]


def _mini_tokenizer(path: Path) -> Path:
    """A WordLevel tokenizer.json with the same shape as the shipped ones."""
    from tokenizers import Tokenizer, models, pre_tokenizers, processors, decoders

    vocab = {"[PAD]": 0, "[CLS]": 1, "[SEP]": 2, "[UNK]": 3, "[MASK]": 4}
    words = "the a an library public opened small reading room it's covid naive café".split()
    for w in words:
        vocab.setdefault(w, len(vocab))
    tk = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
    tk.pre_tokenizer = pre_tokenizers.Whitespace()
    tk.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)])
    tk.decoder = decoders.WordPiece()
    tk.save(str(path))
    return path


def _ids_and_offsets(tok, text):
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    return list(enc["input_ids"]), [tuple(o) for o in enc["offset_mapping"]]


def test_bare_matches_hf_on_synthetic_tokenizer(tmp_path):
    from transformers import PreTrainedTokenizerFast

    path = _mini_tokenizer(tmp_path / "tokenizer.json")
    bare = load_bare_tokenizer(tmp_path)
    assert isinstance(bare, _BareTokenizer)
    hf = PreTrainedTokenizerFast(tokenizer_file=str(path))
    texts = ["the public library opened", "COVID unknown words here", "", "  spaces  "]
    for text in texts:
        assert _ids_and_offsets(bare, text) == _ids_and_offsets(hf, text), text
    # The facade reads the same special ids the file declares.
    assert (bare.cls_token_id, bare.sep_token_id, bare.pad_token_id, bare.unk_token_id) == (1, 2, 0, 3)


def test_bare_pad_matches_hf_padding(tmp_path):
    from transformers import PreTrainedTokenizerFast

    path = _mini_tokenizer(tmp_path / "tokenizer.json")
    bare = load_bare_tokenizer(tmp_path)
    hf = PreTrainedTokenizerFast(tokenizer_file=str(path))
    seqs = [[1, 5, 6, 2], [1, 5, 2]]
    got = bare.pad({"input_ids": seqs}, pad_to_multiple_of=32)
    # Same shape and mask contract HF uses: right padding to a multiple of 32.
    assert len(got["input_ids"]) == 2
    assert len(got["input_ids"][0]) == 32 and len(got["input_ids"][1]) == 32
    assert got["input_ids"][0][:4] == seqs[0] and got["input_ids"][0][4:] == [0] * 28
    assert got["attention_mask"][0][:4] == [1] * 4 and sum(got["attention_mask"][1]) == 3
    assert got["input_ids"][1][3:] == [0] * 29


def test_missing_tokenizer_json_returns_none(tmp_path):
    assert load_bare_tokenizer(tmp_path) is None


def _models_root() -> Path | None:
    # Read once at import: the suite's autouse fixture clears LINDA_MODELS_HOME for
    # every test so no test can touch a real user profile.
    return _MODELS_ROOT


_MODELS_ROOT = (lambda: None)()
_env_root = os.environ.get("LINDA_MODELS_HOME")
if _env_root and (Path(_env_root) / "models").is_dir():
    _MODELS_ROOT = Path(_env_root)
elif (REPO / "qa_models" / "models").is_dir():
    _MODELS_ROOT = REPO / "qa_models"


def _corpus_texts(limit: int) -> list[str]:
    """EN/PL/RU prose from the dev corpora; the shipped tokenizers must agree on all of it."""
    root = Path(os.environ.get("LINDA_DATA_HOME") or (Path.home() / "Desktop" / "детектор" / "data" / "linda"))
    out: list[str] = []
    for name, lang_n in (("l14_cloud.jsonl", 20), ("l14_seg_dev.jsonl", 30)):
        p = root / name
        if not p.is_file():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line)["text"])
                except Exception:  # noqa: BLE001 — a broken line must not fail the id check
                    continue
                if len(out) >= limit:
                    return out
    return out


@pytest.mark.skipif(_models_root() is None, reason="QA models not installed (LINDA_MODELS_HOME)")
def test_shipped_models_bare_tokenizer_ids_equal_auto():
    from transformers import AutoTokenizer

    texts = _corpus_texts(50)
    assert len(texts) >= 50, "dev corpora unavailable: cannot check 50 texts"
    checks = 0
    for folder in ("essay_dhi_131_20261008", "multi_dhi_131_20261008"):
        model_dir = _models_root() / "models" / folder
        if not (model_dir / "tokenizer.json").is_file():
            pytest.skip(f"{folder} not installed")
        bare = load_bare_tokenizer(model_dir)
        hf = AutoTokenizer.from_pretrained(str(model_dir))
        assert bare.cls_token_id == hf.cls_token_id and bare.sep_token_id == hf.sep_token_id
        assert bare.pad_token_id == hf.pad_token_id
        for text in texts:
            assert _ids_and_offsets(bare, text) == _ids_and_offsets(hf, text), (folder, text[:80])
            checks += 1
    assert checks >= 100
