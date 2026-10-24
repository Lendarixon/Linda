"""Sentence segmentation that keeps character offsets (used for the sentence heat map)."""
from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?…])(?P<closing>[\"')»”]*)(?:[\s\u200b\ufeff]+|\n\s*\n)(?=[\"'«“—–-]*[A-ZА-ЯЁІЇЄҐĄĆĘŁŃÓŚŹŻÄÖÜÀ-Þ0-9])|\n\s*\n"
)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
# Abbreviations that must not end a sentence: "Dr. Smith", "А. С. Пушкин",
# "prof. Kowalski", "т.е.", "U.S.". Checked on the text before the split.
_ABBR_RE = re.compile(
    r"(?:\b(?:dr|mr|mrs|ms|st|prof|doc|ing|np|nr|godz|tzw|tzn|tj|ang|fr|niem"
    r"|dr|mr|г|им|ул|см|рис|стр|напр|т|m|in)\.?|\b[Uu]\.[Ss]\.?"
    r"|\b[Тт]\.[Ее]\.|\b[Тт]\.[Кк]\.|\b[Тт]\.[Дд]\.|\b[Тт]\.[Пп]\."
    r"|\b[A-ZА-ЯЁІЇЄҐĄĆĘŁŃÓŚŹŻÄÖÜÀ-Þ]\.)\s*$",
    re.IGNORECASE,
)


@dataclass
class Span:
    text: str
    start: int
    end: int


def words(s: str) -> list[str]:
    return _WORD_RE.findall(s)


def _split_by(regex: re.Pattern, text: str) -> list[Span]:
    spans: list[Span] = []
    prev_end = 0
    is_sentence = regex is _SENTENCE_SPLIT_RE
    for m in regex.finditer(text):
        # Closing punctuation belongs to the preceding sentence, not its gap.
        closing = m.groupdict().get('closing') or ''
        chunk = text[prev_end : m.start()+len(closing)]
        if is_sentence and _ABBR_RE.search(chunk):
            # Abbreviation ("Dr.", "А.", "т.е.") — not a sentence boundary.
            continue
        stripped = chunk.strip().strip("\u200b\ufeff")
        if stripped:
            offset = prev_end + chunk.find(stripped)
            spans.append(Span(stripped, offset, offset + len(stripped)))
        prev_end = m.end()
    chunk = text[prev_end:]
    stripped = chunk.strip().strip("\u200b\ufeff")
    if stripped:
        offset = prev_end + chunk.find(stripped)
        spans.append(Span(stripped, offset, offset + len(stripped)))
    return spans


def split_sentences_with_offsets(text: str) -> list[Span]:
    if not text or not text.strip():
        return []
    return _split_by(_SENTENCE_SPLIT_RE, text)


def split_sentences(text: str) -> list[str]:
    return [s.text for s in split_sentences_with_offsets(text)]


def split_paragraphs_with_offsets(text: str) -> list[Span]:
    if not text or not text.strip():
        return []
    return _split_by(_PARAGRAPH_SPLIT_RE, text)


def even_sample_indices(n: int, k: int) -> list[int]:
    """k индексов от 0 до n-1, равномерно распределённых по всему диапазону
    (включая первый и последний), а не только начало — общий приём, которым
    в проекте уже ограничивается число окон при разбиении длинного текста
    (см. chunking.MAX_WINDOWS) и число предложений в карте по предложениям
    (см. pipeline.MAX_HEATMAP_SENTENCES) на огромных документах."""
    if k <= 0 or n <= 0:
        return []
    if k >= n:
        return list(range(n))
    if k == 1:
        return [0]
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})
