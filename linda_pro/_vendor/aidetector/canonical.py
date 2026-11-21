"""Cleaning text from "attacks" before model votes (RAID-like obfuscations).

Attacks from the RAID benchmark (homoglyph, zero_width_space, whitespace) and "humanizers" break
neural network detectors while barely changing the text for the reader: Latin "a" is replaced with Cyrillic "а",
invisible characters are inserted between letters, extra spaces between words. The model sees
unfamiliar tokens and responds "human".

We do not touch case: the upper_lower attack in RAID changes the first letter of random words ("quantum Systems"), and
distinguishing this from proper nouns without a dictionary is impossible, and editing case inside words corrupted abbreviations
(CNNs, LSTMs). Here, only substitutions reversible in meaning are made, and ONLY where there is an attack trace; normal text does not change
by a single character (quotes, ellipses, dashes, NFC — as is), so the evaluation cache and model behavior on
clean texts remain the same. The heuristics vote receives the original text: for it, attack traces are evidence
(`_rule_unicode_forensics`), not noise."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

RAW_TEXT_VOTERS = {"heuristics"}  # they need the original text

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­᠎⁡⁢⁣⁤"), None)
_ODD_SPACES = {ord(c): " " for c in "              　"}
_FULLWIDTH = {cp: cp - 0xFEE0 for cp in range(0xFF01, 0xFF5F)}  # ！..～ -> !..~

# homoglyphs: Cyrillic/Greek -> Latin and vice versa (only visually indistinguishable pairs)
_TO_LATIN = dict(zip(
    "аеорсухіјѕԁԛԝӏАВЕКМНОРСТХІЈЅԚԜοαενιρτυχκΑΒΕΖΗΙΚΜΝΟΡΤΥΧУ",
    "aeopcyxijsdqwlABEKMHOPCTXIJSQWoaeviptuxkABEZHIKMNOPTYXY"))
_TO_CYRILLIC = {lat: cyr for cyr, lat in zip("аеорсухАВЕКМНОРСТХ", "aeopcyxABEKMHOPCTX")}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r" +([,.;:!?])")


def _script(ch: str) -> str | None:
    if "a" <= ch.lower() <= "z":
        return "LATIN"
    name = unicodedata.name(ch, "")
    for s in ("CYRILLIC", "LATIN", "GREEK"):
        if name.startswith(s):
            return s
    return None


@dataclass
class Canon:
    text: str
    changed: bool = False
    counts: dict = field(default_factory=dict)

    def note(self) -> str | None:
        if not self.changed:
            return None
        parts = [f"{k}: {v}" for k, v in self.counts.items() if v]
        return ("в тексте следы маскировки (" + ", ".join(parts) + ") — голоса-модели считали очищенный текст, "
                "heuristics — исходный")


def _fix_word(word: str, doc_script: str) -> str:
    scripts = [s for ch in word if (s := _script(ch))]
    if not scripts:
        return word
    n_lat = scripts.count("LATIN")
    n_cyr = scripts.count("CYRILLIC")
    n_grk = scripts.count("GREEK")
    if doc_script == "LATIN":
        if n_lat and (n_cyr or n_grk):  # mixed word: "аpple"
            return "".join(_TO_LATIN.get(ch, ch) for ch in word)
        # entirely "Cyrillic" word consisting solely of Latin lookalikes ("а", "сор") in Latin text;
        # Greek letter-symbols (α, ν, ρ in scientific texts) are left completely untouched
        if n_cyr and not n_grk and all(ch in _TO_LATIN for ch in word):
            return "".join(_TO_LATIN[ch] for ch in word)
        return word
    if doc_script == "CYRILLIC" and n_lat and n_cyr and n_cyr >= n_lat:
        return "".join(_TO_CYRILLIC.get(ch, ch) for ch in word)
    return word


def canonicalize(text: str, lang: str | None = None) -> Canon:
    if not text:
        return Canon(text or "")
    counts = {}
    t = text.translate(_ZERO_WIDTH)
    counts["невидимых символов"] = len(text) - len(t)
    t2 = t.translate(_ODD_SPACES).translate(_FULLWIDTH)
    counts["нетипичных пробелов/широких символов"] = sum(a != b for a, b in zip(t, t2))
    t = t2

    letters = [s for ch in t if (s := _script(ch))]
    if lang in ("en", "pl"):
        doc_script = "LATIN"
    elif lang == "ru":
        doc_script = "CYRILLIC"
    else:
        doc_script = max(("LATIN", "CYRILLIC"), key=letters.count) if letters else "LATIN"
    n_homo = 0

    def repl(m: re.Match) -> str:
        nonlocal n_homo
        w = m.group(0)
        f = _fix_word(w, doc_script)
        if f != w:
            n_homo += 1
        return f

    t = _WORD.sub(repl, t)
    counts["слов с гомоглифами"] = n_homo

    # extra spaces are cleaned only if there are other traces of an attack or there are many of them: a double space after a period is normal
    lines = t.split("\n")
    fixed = [_SPACE_BEFORE_PUNCT.sub(r"\1", _MULTI_SPACE.sub(" ", ln)) for ln in lines]
    n_space = sum(a != b for a, b in zip(lines, fixed))
    if n_space and (any(counts.values()) or len(_MULTI_SPACE.findall(t)) + len(_SPACE_BEFORE_PUNCT.findall(t)) >= 5):
        t = "\n".join(fixed)
        counts["строк с лишними пробелами"] = n_space
    changed = t != text
    return Canon(t, changed, counts if changed else {})


@lru_cache(maxsize=65536)
def _canonical_text(text: str, lang: str | None) -> str:
    return canonicalize(text, lang).text


def prepare_for_voter(voter_name: str, text: str, lang: str | None = None) -> str:
    if voter_name in RAW_TEXT_VOTERS:
        return text
    return _canonical_text(text, lang)
