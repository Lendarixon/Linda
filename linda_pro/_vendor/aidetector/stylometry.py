"""Stylometry without neural networks: text features and a trained statistical model.

Two parts, both on CPU, milliseconds per text:

1. Handcrafted features (`extract_features`) — ~250 numbers per language: punctuation,
   rhythm and spread of sentence/paragraph lengths, lexical diversity (MATTR,
   MTLD, Yule K), function word frequencies, discourse markers and "AI phrases",
   repetitiveness and compressibility of text, markup (lists, headings),
   Unicode forensics. All frequencies are per 1000 words/characters or in fixed-length
   windows so that the feature does not depend on text length.
2. N-gram model (`ngram_matrix`) — character 2–5-grams within words and
   word 1–2-grams hashed into a sparse vector; logistic
   regression on them yields a single score, which goes into boosting as a feature.

Result — gradient boosting (LightGBM) on features + n-gram score, a separate
model for each language (train/train_stylometry.py). The model is stored as LightGBM
text and numpy arrays (without pickle) in src/aidetector/stylometry_model/.

Normalization before features removes typography that reflects the text's
source rather than the author: quotes of all kinds → ", apostrophes → ',
ellipsis … → ..., non-breaking and other spaces → space. We don't touch dashes:
em dash is a known stylistic feature of LLMs."""
from __future__ import annotations

import json
import math
import re
import unicodedata
import zlib
from collections import Counter
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "stylometry_model"
# separate profile "for benchmarks" (train splits of RAID/MAGE/SemEval/COLING/CoAT in training): stylometry_bench voice,
# only for benchmark reports and submission — the main voice does not use it (eval/reports/stylometry_v6_bench.md)
BENCH_MODEL_DIR = Path(__file__).resolve().parent / "stylometry_model_bench"
LANGS = ("en", "ru", "pl")

# ---------------------------------------------------------------- normalization

_QUOTES = str.maketrans({
    "“": '"', "”": '"', "„": '"', "‟": '"', "«": '"', "»": '"', "″": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "`": "'", "ʼ": "'", "′": "'",
    "…": "...",
})
_ZERO_WIDTH = "​‌‍⁠﻿"
_ODD_SPACES = re.compile(r"[  -   　\t]")
_MULTISPACE = re.compile(r" {2,}")
_SPACE_NL = re.compile(r" *\n *")
_MANY_NL = re.compile(r"\n{3,}")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch not in _ZERO_WIDTH)
    text = _ODD_SPACES.sub(" ", text.translate(_QUOTES))
    text = _SPACE_NL.sub("\n", _MULTISPACE.sub(" ", text))
    return _MANY_NL.sub("\n\n", text).strip()


# ---------------------------------------------------------------- dictionaries

FUNCTION_WORDS: dict[str, list[str]] = {
    "en": """the a an and or but if then so because as of in on at to for with by from about into through over under
        between after before during without within among against i me my we us our you your he him his she her it its
        they them their this that these those there here which who whom whose what when where why how is are was were be
        been being am have has had do does did not no can could will would should may might must just also very more most
        such only even still yet however moreover furthermore additionally therefore thus overall indeed perhaps often
        both each every all any some many much own other than while although though whether like well really actually
        quite rather simply truly essentially ultimately significantly particularly notably""".split(),
    "ru": """и в во не на я он с со что а по это она этот к но они мы как из у который то за свой весь от так о для ты же
        все тот вы такой его её ее только или если бы уже когда где чтобы даже ещё еще также тоже лишь ли ни вот там тут
        здесь потому поэтому однако кроме того таким образом более менее очень самый может можно нужно необходимо важно
        при через после перед между под над без до об про их им ему ей меня мне нас нам вас вам себя этом этой этих эти
        эта чем чего был была было были есть будет является являются именно ведь вообще просто действительно впрочем
        итак целом особенно значительно различных различные ключевую""".split(),
    "pl": """i w we nie na się z ze że do to jest a o jak ale po co tak za od jego jej ich go mu przez dla przy czy być
        może już tylko też także również jednak więc oraz lub albo gdy kiedy gdzie który która które którzy tego ten ta
        te tym tej tych są był była było były będzie ma mają mnie mi my nas nam ja ty on ona oni one sobie siebie swój
        swoje swoich bardzo więcej bardziej można należy warto ważne istotne ponadto dodatkowo zatem dlatego natomiast
        wreszcie podsumowując właśnie nawet jeszcze bo ponieważ aby żeby jeśli jeżeli między pod nad przed bez u około
        wśród stanowi kluczowe kluczową szczególnie znacząco różnych""".split(),
}

# category -> phrases (searched as separate words/phrases, case-insensitive)
MARKERS: dict[str, dict[str, list[str]]] = {
    "en": {
        "m_add": ["moreover", "furthermore", "additionally", "in addition", "besides", "what's more"],
        "m_contrast": ["however", "nevertheless", "nonetheless", "on the other hand", "conversely", "that said"],
        "m_result": ["therefore", "thus", "consequently", "as a result", "hence", "accordingly"],
        "m_summary": ["in conclusion", "overall", "ultimately", "in summary", "to summarize", "all in all", "in essence"],
        "m_hedge": ["perhaps", "possibly", "likely", "arguably", "somewhat", "seems", "appears to", "tends to"],
        "m_boost": ["clearly", "certainly", "undoubtedly", "definitely", "truly", "indeed", "crucial", "essential", "vital",
                    "significant", "significantly", "profound", "profoundly"],
        "m_llm": ["it is important to", "it's important to", "plays a crucial role", "plays a vital role", "a testament to",
                  "not only", "in today's", "a wide range of", "a variety of", "various", "ensure", "ensuring", "enhance",
                  "enhancing", "valuable", "insights", "notably", "key", "landscape", "journey", "delve", "foster",
                  "navigate", "realm", "robust", "leverage", "comprehensive", "nuanced", "intricate", "vibrant",
                  "whether it's", "embrace", "crucial", "pivotal", "seamless", "tapestry", "underscore", "showcase"],
        "m_personal": ["i think", "i guess", "i mean", "you know", "kind of", "sort of", "lol", "honestly", "gonna",
                       "wanna", "stuff", "things like"],
    },
    "ru": {
        "m_add": ["кроме того", "более того", "помимо этого", "помимо того", "вдобавок", "к тому же"],
        "m_contrast": ["однако", "тем не менее", "с другой стороны", "напротив", "впрочем", "вместе с тем"],
        "m_result": ["поэтому", "таким образом", "следовательно", "в результате", "в связи с этим", "благодаря этому"],
        "m_summary": ["в заключение", "в целом", "подводя итог", "в итоге", "итак", "резюмируя"],
        "m_hedge": ["возможно", "вероятно", "по-видимому", "может быть", "скорее всего", "как правило"],
        "m_boost": ["безусловно", "несомненно", "крайне", "ключевой", "ключевую", "значительно", "существенно",
                    "особенно", "важнейш*", "огромн*"],
        "m_llm": ["играет важную роль", "играет ключевую роль", "стоит отметить", "важно отметить", "важно понимать",
                  "является", "являются", "представляет собой", "широкий спектр", "широкий круг", "различных",
                  "обеспечивает", "обеспечить", "позволяет", "способствует", "эффективн*", "уникальн*", "инновационн*",
                  "комплексн*", "в современном мире", "неотъемлем*", "данный", "данной", "данного"],
        "m_personal": ["короче", "блин", "ну", "вот", "типа", "как бы", "честно говоря", "кстати", "имхо", "лол"],
    },
    "pl": {
        "m_add": ["ponadto", "dodatkowo", "co więcej", "oprócz tego", "poza tym"],
        "m_contrast": ["jednak", "jednakże", "natomiast", "z drugiej strony", "mimo to", "niemniej"],
        "m_result": ["dlatego", "zatem", "w rezultacie", "w konsekwencji", "w związku z tym", "dzięki temu"],
        "m_summary": ["podsumowując", "w podsumowaniu", "ostatecznie", "reasumując", "w sumie", "w skrócie"],
        "m_hedge": ["prawdopodobnie", "możliwe", "wydaje się", "zazwyczaj", "zwykle", "raczej"],
        "m_boost": ["niezwykle", "kluczowy", "kluczowe", "kluczową", "istotny", "istotne", "znacząco", "szczególnie",
                    "niewątpliwie", "z pewnością", "ogromn*"],
        "m_llm": ["odgrywa kluczową rolę", "odgrywa ważną rolę", "warto zauważyć", "warto podkreślić", "należy podkreślić",
                  "stanowi", "szeroki zakres", "szerokiej gamy", "różnorodn*", "pozwala", "umożliwia", "zapewnia",
                  "efektywn*", "innowacyjn*", "kompleksow*", "we współczesnym świecie", "nieodłączn*", "unikaln*"],
        "m_personal": ["no", "kurczę", "serio", "chyba", "wiesz", "szczerze mówiąc", "w sumie", "jakby", "xd"],
    },
}

# Text structure (following SlopShape, arXiv 2609.15369: "neat, self-announcing" AI text — outline and thesis at the beginning,
# summary and thesis restatement at the end; humans lack these milestones). Phrases are searched not in the entire text, but in the first/last block.
_STRUCT: dict[str, dict[str, list[str]]] = {
    "en": {
        "roadmap": ["this essay", "this article", "this post", "this paper", "this review", "in this essay", "in this article",
                    "in this post", "in this paper", "we will", "we'll", "i will argue", "i will discuss", "let's explore",
                    "let us explore", "below, we", "the following", "we examine", "we present", "we explore", "this study"],
        "thesis": ["i believe", "i argue", "i would argue", "in my opinion", "in my view", "i think that", "i am convinced",
                   "should be", "must be", "it is clear that"],
        "close": ["in conclusion", "in summary", "to summarize", "to sum up", "in short", "overall", "ultimately", "in the end",
                  "all in all", "taken together", "together, these", "these results", "these findings", "our results",
                  "in essence", "to conclude"],
        "uplift": ["future", "generations", "remember", "together", "truly", "meaningful", "lasting", "hope", "journey",
                   "matters", "worth"],
        "ordinal": ["first", "firstly", "second", "secondly", "third", "thirdly", "finally", "lastly", "first of all",
                    "moreover", "furthermore", "additionally", "in addition", "on the other hand", "however"],
    },
    "ru": {
        "roadmap": ["в этой статье", "в данной статье", "в статье", "в этом эссе", "в своём сочинении", "в своем сочинении",
                    "в этой работе", "в данной работе", "в работе", "рассмотрим", "хочу рассказать", "поговорим",
                    "попробую", "мы рассмотрим", "будет рассмотрен*", "статья посвящена", "работа посвящена"],
        "thesis": ["я считаю", "я уверен*", "на мой взгляд", "по моему мнению", "мне кажется", "я думаю", "по-моему",
                   "должен", "должна", "должны", "необходимо"],
        "close": ["таким образом", "подводя итог", "в заключение", "итак", "в итоге", "в целом", "резюмируя",
                  "полученные результаты", "результаты свидетельствуют", "сделан вывод", "можно сделать вывод"],
        "uplift": ["будущ*", "поколени*", "помнить", "вместе", "надежд*", "навсегда", "важно", "ценн*", "смысл*"],
        "ordinal": ["во-первых", "во-вторых", "в-третьих", "наконец", "кроме того", "более того", "однако",
                    "с одной стороны", "с другой стороны", "прежде всего", "также"],
    },
    "pl": {
        "roadmap": ["w tym artykule", "w artykule", "w niniejszym", "w niniejszej pracy", "w tej pracy", "w pracy",
                    "w tym eseju", "przyjrzyjmy się", "omówię", "chciałbym", "chciałabym", "celem pracy", "celem artykułu",
                    "artykuł dotyczy", "w opracowaniu"],
        "thesis": ["uważam", "moim zdaniem", "sądzę", "myślę, że", "jestem przekonan*", "powinien", "powinna", "powinny",
                   "należy"],
        "close": ["podsumowując", "reasumując", "w podsumowaniu", "ostatecznie", "tak więc", "w sumie", "wyniki wskazują",
                  "uzyskane wyniki", "stwierdzono", "wnioski", "w konsekwencji"],
        "uplift": ["przyszł*", "pokoleń", "pokolenia", "pamiętać", "razem", "nadziej*", "warto", "wartość*"],
        "ordinal": ["po pierwsze", "po drugie", "po trzecie", "wreszcie", "ponadto", "co więcej", "jednak", "natomiast",
                    "z jednej strony", "z drugiej strony", "przede wszystkim"],
    },
}
STRUCT_FEATURES: list[tuple[str, str]] = [
    ("s_para_mode", "в тексте ≥ 3 абзацев (иначе начало/конец — первые/последние 2 предложения)"),
    ("s_open_roadmap", "план или анонс в начале («в этой статье», «this essay will»)"),
    ("s_open_thesis", "тезис-мнение в начале («я считаю», «I believe»)"),
    ("s_open_question", "текст начинается с вопроса"),
    ("s_open_address", "обращения к читателю (ты/вы) в начале, на 100 слов"),
    ("s_close_summary", "итоговый оборот в начале последнего блока («таким образом», «in conclusion»)"),
    ("s_close_overlap", "повтор тезиса: лексическое пересечение начала и конца"),
    ("s_close_uplift", "«возвышенная» концовка (будущее, поколения, надежда), на 100 слов конца"),
    ("s_close_len", "длина последнего блока относительно средней"),
    ("s_open_len", "длина первого блока относительно средней"),
    ("s_last_sent_len", "длина последнего предложения относительно средней"),
    ("s_para_ordinal", "доля абзацев, начатых с вводного/порядкового оборота"),
    ("s_para_uniform", "ровность абзацев: 1 − CV длин средних абзацев (без первого и последнего)"),
]

_CONJ_START: dict[str, list[str]] = {
    "en": ["and", "but", "so", "or", "yet", "because"],
    "ru": ["и", "но", "а", "да", "зато", "ведь", "потому"],
    "pl": ["i", "ale", "a", "więc", "bo", "lecz"],
}

_PRONOUN_1S = {"en": {"i", "me", "my", "mine", "myself"}, "ru": {"я", "меня", "мне", "мной", "мой", "моя", "моё", "мое", "мои"},
               "pl": {"ja", "mnie", "mi", "mną", "mój", "moja", "moje", "moi"}}
_PRONOUN_2 = {"en": {"you", "your", "yours", "yourself"}, "ru": {"ты", "тебя", "тебе", "вы", "вас", "вам", "ваш", "твой"},
              "pl": {"ty", "cię", "ciebie", "tobie", "wy", "was", "wam", "twój", "wasz"}}

_WORD_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[^\W\d_])|\n+")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_BULLET_RE = re.compile(r"^\s*(?:[-*•·▪–—]|\d{1,2}[.)])\s+")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+|^[^\n.!?]{2,60}:\s*$")
_BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
_EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

PUNCT_CHARS = {
    "comma": ",", "period": ".", "semicolon": ";", "colon": ":", "excl": "!", "quest": "?", "lparen": "(",
    "dquote": '"', "squote": "'", "hyphen": "-", "endash": "–", "emdash": "—", "star": "*", "hash": "#", "slash": "/",
    "percent": "%", "amp": "&", "lbracket": "[",
}


@lru_cache(maxsize=None)
def _phrase_regex(phrases: tuple[str, ...]) -> re.Pattern:
    parts = []
    for p in sorted(phrases, key=len, reverse=True):
        # "stem*" matches any ending (эффективн* -> эффективный, эффективно, ...)
        stem = p.endswith("*")
        esc = re.escape(p.rstrip("*")).replace(r"\ ", r"\s+")
        parts.append(esc + (r"\w*" if stem else ""))
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.IGNORECASE | re.UNICODE)


@lru_cache(maxsize=None)
def _yaml_patterns(lang: str) -> dict[str, list[re.Pattern]]:
    import yaml

    path = Path(__file__).resolve().parent / "patterns" / f"{lang}.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {k: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in data.get(k, [])]
            for k in ("antithesis", "simile_markers", "conclusive_markers", "tell_words")}


# ---------------------------------------------------------------- auxiliary


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s and s.strip()]


def _stats(xs: list[float]) -> tuple[float, float, float, float]:
    """mean, std, coefficient of variation, skewness."""
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    a = np.asarray(xs, dtype=float)
    m = float(a.mean())
    s = float(a.std())
    skew = float(((a - m) ** 3).mean() / (s ** 3)) if s > 0 else 0.0
    return m, s, (s / m if m > 0 else 0.0), skew


def _mattr(ws: list[str], window: int = 50) -> float:
    if len(ws) < 2:
        return 1.0
    if len(ws) <= window:
        return len(set(ws)) / len(ws)
    counts = Counter(ws[:window])
    total = len(counts)
    acc = total
    for i in range(window, len(ws)):
        out, inc = ws[i - window], ws[i]
        counts[out] -= 1
        if counts[out] == 0:
            del counts[out]
            total -= 1
        if counts[inc] == 0:
            total += 1
        counts[inc] += 1
        acc += total
    return acc / ((len(ws) - window + 1) * window)


def _mtld_pass(ws: list[str], threshold: float = 0.72) -> float:
    factors, types, count = 0.0, set(), 0
    for w in ws:
        count += 1
        types.add(w)
        if len(types) / count <= threshold:
            factors += 1
            types, count = set(), 0
    if count:
        ttr = len(types) / count
        factors += (1 - ttr) / (1 - threshold) if ttr < 1 else 0.0
    return len(ws) / factors if factors > 0 else float(len(ws))


def _mtld(ws: list[str]) -> float:
    if len(ws) < 10:
        return 0.0
    return (_mtld_pass(ws) + _mtld_pass(ws[::-1])) / 2


def _yule_k(ws: list[str]) -> float:
    n = len(ws)
    if n < 2:
        return 0.0
    freq_of_freq = Counter(Counter(ws).values())
    s2 = sum(r * r * v for r, v in freq_of_freq.items())
    return 1e4 * (s2 - n) / (n * n)


def _windows(ws: list[str], size: int) -> list[list[str]]:
    if len(ws) <= size:
        return [ws]
    return [ws[i:i + size] for i in range(0, len(ws) - size + 1, size)]


def _compress_ratio(text: str, size: int = 1000) -> float:
    raw = text.encode("utf-8")
    if not raw:
        return 0.0
    chunks = [raw[i:i + size] for i in range(0, max(1, len(raw) - size // 2), size)] or [raw]
    chunks = [c for c in chunks if len(c) >= 200] or [raw]
    return float(np.mean([len(zlib.compress(c, 9)) / len(c) for c in chunks if c]))


def _char_script(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    name = unicodedata.name(ch, "")
    if name.startswith("LATIN"):
        return "L"
    if name.startswith("CYRILLIC"):
        return "C"
    return "O"


# ---------------------------------------------------------------- features

# (name, description) — description is shown in the voice explanation
BASE_FEATURES: list[tuple[str, str]] = [
    ("log_words", "длина текста (слов, лог)"),
    ("word_len_mean", "средняя длина слова"),
    ("word_len_std", "разброс длины слов"),
    ("long_word_share", "доля длинных слов (≥10 букв)"),
    ("short_word_share", "доля коротких слов (≤2 буквы)"),
    ("mattr50", "лексическое разнообразие (MATTR, окно 50)"),
    ("mtld", "лексическое разнообразие (MTLD)"),
    ("yule_k", "концентрация словаря (Yule K)"),
    ("hapax100", "доля слов, встреченных один раз (окна по 100 слов)"),
    ("entropy200", "энтропия словаря (окна по 200 слов)"),
    ("fw_share", "доля служебных слов"),
    ("pron_1s", "местоимения 1-го лица ед. ч. на 1000 слов"),
    ("pron_2", "обращения ко 2-му лицу на 1000 слов"),
    ("cap_inner_share", "доля слов с заглавной не в начале предложения"),
    ("allcaps_share", "доля слов капсом"),
    ("num_rate", "чисел на 1000 слов"),
    ("sent_len_mean", "средняя длина предложения"),
    ("sent_len_std", "разброс длины предложений"),
    ("sent_len_cv", "неровность длины предложений (CV)"),
    ("sent_len_skew", "асимметрия длин предложений"),
    ("sent_len_median", "медианная длина предложения"),
    ("sent_short_share", "доля коротких предложений (≤6 слов)"),
    ("sent_long_share", "доля длинных предложений (≥30 слов)"),
    ("burstiness", "скачки длины соседних предложений"),
    ("sent_len_ac1", "автокорреляция длин соседних предложений"),
    ("first_word_div", "разнообразие первых слов предложений"),
    ("first_word_top", "доля самого частого первого слова"),
    ("conj_start", "предложения, начатые с союза"),
    ("marker_start", "предложения, начатые с вводного оборота"),
    ("quest_share", "доля вопросительных предложений"),
    ("excl_share", "доля восклицательных предложений"),
    ("commas_per_sent", "запятых на предложение"),
    ("commas_per_sent_std", "разброс числа запятых в предложениях"),
    ("no_comma_share", "доля предложений без запятых"),
    ("log_lines", "число абзацев (лог)"),
    ("line_len_mean", "средняя длина абзаца (слов)"),
    ("line_len_cv", "неровность длины абзацев (CV)"),
    ("single_sent_lines", "доля абзацев из одного предложения"),
    ("bullet_share", "доля строк-пунктов списка"),
    ("heading_share", "доля строк-заголовков"),
    ("bold_rate", "выделений **жирным** на 1000 слов"),
    ("emoji_rate", "эмодзи на 1000 символов"),
    ("compress", "сжимаемость текста (zlib)"),
    ("rep_trigram", "повторы словесных триграмм"),
    ("rep_bigram", "повторы словесных биграмм"),
    ("adj_overlap", "лексическое сцепление соседних предложений"),
    ("upper_share", "доля заглавных букв"),
    ("digit_share", "доля цифр"),
    ("punct_share", "доля знаков препинания"),
    ("foreign_script", "доля букв чужого алфавита"),
    ("mixed_script_words", "слова со смешанными алфавитами"),
    ("zero_width", "невидимые символы"),
    ("odd_spaces", "нетипичные пробелы"),
    ("dash_spaced", "тире с пробелами на 1000 символов"),
    ("hyphen_as_dash", "дефис вместо тире на 1000 символов"),
    ("ellipsis_rate", "многоточий на 1000 символов"),
    ("paren_rate", "скобок на 1000 слов"),
    ("quote_rate", "кавычек на 1000 слов"),
    ("y_antithesis", "антитезы «не X, а Y» (доля предложений)"),
    ("y_simile", "сравнения на 1000 слов"),
    ("y_conclusive", "«выводные» обороты на 1000 слов"),
    ("y_tell", "«ИИ-слова» из словаря на 1000 слов"),
    ("diacritics", "доля польских диакритических букв"),
    ("yo_share", "доля буквы ё среди е/ё"),
]
_PUNCT_FEATURES = [(f"p_{k}", f"«{v}» на 1000 символов") for k, v in PUNCT_CHARS.items()]


STRUCT_ENABLED = False  # structure features in training — only with train_stylometry.py --struct (eval/reports/stylometry_structure.md)


def feature_names(lang: str) -> list[str]:
    """Features for training a new model; a trained model takes its list from meta (LangModel.names)."""
    return ([n for n, _ in BASE_FEATURES] + [n for n, _ in _PUNCT_FEATURES]
            + sorted(MARKERS[lang]) + [f"fw:{w}" for w in _fw_list(lang)]
            + ([n for n, _ in STRUCT_FEATURES] if STRUCT_ENABLED else []))


def feature_description(name: str) -> str:
    if name.startswith("fw:"):
        return f"частота слова «{name[3:]}»"
    if name.startswith("m_"):
        return {"m_add": "обороты «кроме того/более того»", "m_contrast": "обороты «однако/тем не менее»",
                "m_result": "обороты «таким образом/поэтому»", "m_summary": "обороты «в заключение/в целом»",
                "m_hedge": "смягчения («возможно», «вероятно»)", "m_boost": "усилители («безусловно», «ключевой»)",
                "m_llm": "типичные обороты LLM", "m_personal": "разговорные/личные обороты"}.get(name, name)
    return dict(BASE_FEATURES + _PUNCT_FEATURES + STRUCT_FEATURES).get(name, name)


@lru_cache(maxsize=None)
def _fw_list(lang: str) -> tuple[str, ...]:
    seen, out = set(), []
    for w in FUNCTION_WORDS[lang]:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return tuple(out)


def extract_features(text: str, lang: str) -> dict[str, float]:
    """Features of a single text. text — original (invisible characters and spaces
    are counted before normalization), everything else — on the normalized one."""
    raw = text
    zero_width = sum(raw.count(ch) for ch in _ZERO_WIDTH)
    odd_spaces = len(_ODD_SPACES.findall(raw.replace("\t", "")))
    text = normalize(raw)
    lower = text.lower()
    n_chars = max(1, len(text))

    ws_orig = _WORD_RE.findall(text)
    ws = [w.lower() for w in ws_orig]
    n_w = max(1, len(ws))
    per_kw = 1000.0 / n_w
    per_kc = 1000.0 / n_chars

    f: dict[str, float] = {}
    f["log_words"] = math.log1p(len(ws))
    lens = [len(w) for w in ws] or [0]
    f["word_len_mean"], f["word_len_std"], _, _ = _stats(lens)
    f["long_word_share"] = sum(1 for x in lens if x >= 10) / n_w
    f["short_word_share"] = sum(1 for x in lens if x <= 2) / n_w
    f["mattr50"] = _mattr(ws)
    f["mtld"] = min(_mtld(ws), 500.0)
    f["yule_k"] = _yule_k(ws)
    hap = []
    for win in _windows(ws, 100):
        c = Counter(win)
        hap.append(sum(1 for v in c.values() if v == 1) / max(1, len(win)))
    f["hapax100"] = float(np.mean(hap))
    ent = []
    for win in _windows(ws, 200):
        c = np.array(list(Counter(win).values()), dtype=float)
        p = c / c.sum() if c.size else c
        ent.append(float(-(p * np.log2(p)).sum()) if c.size else 0.0)
    f["entropy200"] = float(np.mean(ent))

    fw = _fw_list(lang)
    fw_set = set(fw)
    wc = Counter(ws)
    f["fw_share"] = sum(wc[w] for w in fw_set) / n_w
    f["pron_1s"] = sum(wc[w] for w in _PRONOUN_1S[lang]) * per_kw
    f["pron_2"] = sum(wc[w] for w in _PRONOUN_2[lang]) * per_kw
    f["allcaps_share"] = sum(1 for w in ws_orig if len(w) >= 2 and w.isupper()) / n_w
    f["num_rate"] = len(_NUM_RE.findall(text)) * per_kw

    # sentences
    sents = split_sentences(text)
    n_s = max(1, len(sents))
    s_words = [_WORD_RE.findall(s) for s in sents]
    s_lens = [len(x) for x in s_words if x] or [0]
    f["sent_len_mean"], f["sent_len_std"], f["sent_len_cv"], f["sent_len_skew"] = _stats(s_lens)
    f["sent_len_median"] = float(np.median(s_lens))
    f["sent_short_share"] = sum(1 for x in s_lens if x <= 6) / len(s_lens)
    f["sent_long_share"] = sum(1 for x in s_lens if x >= 30) / len(s_lens)
    if len(s_lens) >= 3 and f["sent_len_mean"] > 0:
        diffs = np.abs(np.diff(s_lens))
        f["burstiness"] = float(diffs.mean() / f["sent_len_mean"])
        a = np.asarray(s_lens, dtype=float)
        a0, a1 = a[:-1] - a.mean(), a[1:] - a.mean()
        den = float(np.sqrt((a0 ** 2).sum() * (a1 ** 2).sum()))
        f["sent_len_ac1"] = float((a0 * a1).sum() / den) if den > 0 else 0.0
    else:
        f["burstiness"] = 0.0
        f["sent_len_ac1"] = 0.0
    firsts = [x[0].lower() for x in s_words if x]
    fc = Counter(firsts)
    f["first_word_div"] = len(fc) / max(1, len(firsts))
    f["first_word_top"] = (fc.most_common(1)[0][1] / len(firsts)) if firsts else 0.0
    f["conj_start"] = sum(1 for w in firsts if w in _CONJ_START[lang]) / max(1, len(firsts))
    inner = sum(1 for x in s_words for w in x[1:] if w[:1].isupper() and not w.isupper())
    f["cap_inner_share"] = inner / n_w
    all_markers = tuple(p for ps in MARKERS[lang].values() for p in ps if p not in ("no", "ну", "вот"))
    mre = _phrase_regex(all_markers)
    f["marker_start"] = sum(1 for s in sents if mre.match(s.lstrip("\"'(-—– ")) is not None) / n_s
    f["quest_share"] = sum(1 for s in sents if s.rstrip("\"')").endswith("?")) / n_s
    f["excl_share"] = sum(1 for s in sents if s.rstrip("\"')").endswith("!")) / n_s
    commas = [s.count(",") for s in sents] or [0]
    f["commas_per_sent"], f["commas_per_sent_std"], _, _ = _stats(commas)
    f["no_comma_share"] = sum(1 for c in commas if c == 0) / len(commas)

    # paragraphs = non-empty lines (different sources separate paragraphs differently)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    n_l = max(1, len(lines))
    f["log_lines"] = math.log1p(len(lines))
    l_lens = [len(_WORD_RE.findall(ln)) for ln in lines] or [0]
    f["line_len_mean"], _, f["line_len_cv"], _ = _stats(l_lens)
    f["single_sent_lines"] = sum(1 for ln in lines if len(split_sentences(ln)) <= 1) / n_l
    f["bullet_share"] = sum(1 for ln in lines if _BULLET_RE.match(ln)) / n_l
    f["heading_share"] = sum(1 for ln in lines if _HEADING_RE.match(ln)) / n_l
    f["bold_rate"] = len(_BOLD_RE.findall(text)) * per_kw
    f["emoji_rate"] = len(_EMOJI_RE.findall(text)) * per_kc

    # repetitions and compression
    f["compress"] = _compress_ratio(text)
    tri, bi = [], []
    for win in _windows(ws, 200):
        t = Counter(zip(win, win[1:], win[2:]))
        b = Counter(zip(win, win[1:]))
        tri.append(sum(v for v in t.values() if v > 1) / max(1, sum(t.values())))
        bi.append(sum(v for v in b.values() if v > 1) / max(1, sum(b.values())))
    f["rep_trigram"] = float(np.mean(tri))
    f["rep_bigram"] = float(np.mean(bi))
    content = [{w.lower() for w in x if len(w) >= 4 and w.lower() not in fw_set} for x in s_words]
    ov = [len(a & b) / max(1, len(a | b)) for a, b in zip(content, content[1:]) if a or b]
    f["adj_overlap"] = float(np.mean(ov)) if ov else 0.0

    # characters
    letters = [ch for ch in text if ch.isalpha()]
    n_let = max(1, len(letters))
    f["upper_share"] = sum(1 for ch in letters if ch.isupper()) / n_let
    f["digit_share"] = sum(1 for ch in text if ch.isdigit()) / n_chars
    f["punct_share"] = sum(1 for ch in text if unicodedata.category(ch).startswith("P")) / n_chars
    scripts = Counter(_char_script(ch) for ch in letters)
    main = "C" if lang == "ru" else "L"
    f["foreign_script"] = 1.0 - scripts.get(main, 0) / n_let
    mixed = 0
    for w in ws_orig:
        sc = {_char_script(ch) for ch in w} - {None}
        if len(sc) > 1:
            mixed += 1
    f["mixed_script_words"] = mixed * per_kw
    f["zero_width"] = float(zero_width)
    f["odd_spaces"] = odd_spaces * 1000.0 / max(1, len(raw))
    f["dash_spaced"] = (text.count(" — ") + text.count(" – ")) * per_kc
    f["hyphen_as_dash"] = text.count(" - ") * per_kc
    f["ellipsis_rate"] = text.count("...") * per_kc
    f["paren_rate"] = text.count("(") * per_kw
    f["quote_rate"] = text.count('"') * per_kw
    for k, ch in PUNCT_CHARS.items():
        f[f"p_{k}"] = text.count(ch) * per_kc

    yp = _yaml_patterns(lang)
    if yp:
        f["y_antithesis"] = sum(1 for s in sents if any(r.search(s) for r in yp["antithesis"])) / n_s
        f["y_simile"] = sum(len(r.findall(text)) for r in yp["simile_markers"]) * per_kw
        f["y_conclusive"] = sum(len(r.findall(text)) for r in yp["conclusive_markers"]) * per_kw
        f["y_tell"] = sum(len(r.findall(text)) for r in yp["tell_words"]) * per_kw
    else:
        f["y_antithesis"] = f["y_simile"] = f["y_conclusive"] = f["y_tell"] = 0.0
    f["diacritics"] = sum(1 for ch in lower if ch in "ąćęłńóśźż") / n_let if lang == "pl" else 0.0
    e_all = lower.count("е") + lower.count("ё")
    f["yo_share"] = lower.count("ё") / e_all if lang == "ru" and e_all else 0.0

    for cat, phrases in MARKERS[lang].items():
        f[cat] = len(_phrase_regex(tuple(phrases)).findall(lower)) * per_kw
    for w in fw:
        f[f"fw:{w}"] = wc[w] * per_kw
    f.update(_structure_features(lines, sents, lang, fw_set))
    return f


def _structure_features(lines: list[str], sents: list[str], lang: str, fw_set: set[str]) -> dict[str, float]:
    """Where text milestones are located: outline/thesis in the first block, summary/thesis restatement in the last. A block is a paragraph if there are
    ≥ 3 paragraphs, otherwise the first/last two sentences (abstracts and short answers are written as a single paragraph)."""
    rx = {k: _phrase_regex(tuple(v)) for k, v in _STRUCT[lang].items()}
    if len(lines) >= 4 and len(_WORD_RE.findall(lines[0])) <= 12 and not lines[0].rstrip().endswith((".", "!", "?", "…")):
        lines = lines[1:]  # heading — not the first paragraph
    para = len(lines) >= 3
    blocks = lines if para else [" ".join(sents[:2]), " ".join(sents[2:-2]), " ".join(sents[-2:])] if len(sents) >= 4 else (
        [" ".join(sents)] * 3 if sents else ["", "", ""])
    first, last = blocks[0], blocks[-1]
    b_len = [len(_WORD_RE.findall(b)) for b in blocks]
    mean_len = float(np.mean(b_len)) if b_len and np.mean(b_len) > 0 else 1.0
    fw_first = [w.lower() for w in _WORD_RE.findall(first)]
    fw_last = [w.lower() for w in _WORD_RE.findall(last)]
    c1 = {w for w in fw_first if len(w) >= 4 and w not in fw_set}
    c2 = {w for w in fw_last if len(w) >= 4 and w not in fw_set}
    head = " ".join(fw_last[:8])
    s_lens = [len(_WORD_RE.findall(x)) for x in sents] or [0]
    mid = b_len[1:-1] if len(b_len) >= 5 else []
    f = {
        "s_para_mode": float(para),
        "s_open_roadmap": float(rx["roadmap"].search(first) is not None),
        "s_open_thesis": float(rx["thesis"].search(first) is not None),
        "s_open_question": float(bool(sents) and sents[0].rstrip("\"')»").endswith("?")),
        "s_open_address": 100.0 * sum(1 for w in fw_first if w in _PRONOUN_2[lang]) / max(1, len(fw_first)),
        "s_close_summary": float(rx["close"].search(head) is not None),
        "s_close_overlap": len(c1 & c2) / max(1, len(c1 | c2)),
        "s_close_uplift": 100.0 * len(rx["uplift"].findall(last)) / max(1, len(fw_last)),
        "s_close_len": b_len[-1] / mean_len if b_len else 0.0,
        "s_open_len": b_len[0] / mean_len if b_len else 0.0,
        "s_last_sent_len": s_lens[-1] / max(1.0, float(np.mean(s_lens))),
        "s_para_ordinal": (sum(1 for ln in lines if rx["ordinal"].match(ln.lstrip("\"'(-—– "))) / len(lines)) if para else 0.0,
        "s_para_uniform": (1.0 - float(np.std(mid) / np.mean(mid))) if mid and np.mean(mid) > 0 else 0.0,
    }
    return f


def feature_vector(text: str, lang: str, names: list[str] | None = None) -> np.ndarray:
    """names — list of model features (from its meta): old models without new features continue to work."""
    f = extract_features(text, lang)
    return np.array([f.get(n, 0.0) for n in (names or feature_names(lang))], dtype=np.float32)


# ---------------------------------------------------------------- n-grams

NGRAM_CHAR_BITS = 19
NGRAM_WORD_BITS = 18
NGRAM_SKEL_BITS = 18
_SKEL_TOKEN = re.compile(r"\w+|[^\w\s]|\n", re.UNICODE)


def skeleton(text: str, lang: str) -> str:
    """"Skeleton" of the text: function words and punctuation marks remain, other words
    -> W, numbers -> D, newline -> NL. Skeleton n-grams are syntax and rhythm without
    the topic of the text (a text distortion technique from stylometry), so they depend less on
    what the text is about."""
    fw = set(_fw_list(lang))
    out = []
    for tok in _SKEL_TOKEN.findall(text.lower()):
        if tok == "\n":
            out.append("NL")
        elif tok in fw:
            out.append(tok)
        elif tok[0].isdigit():
            out.append("D")
        elif tok[0].isalpha() or tok[0] == "_":
            out.append("W")
        else:
            out.append(tok)
    return " ".join(out)


@lru_cache(maxsize=None)
def _vectorizers():
    from sklearn.feature_extraction.text import HashingVectorizer

    char = HashingVectorizer(analyzer="char_wb", ngram_range=(2, 5), n_features=2 ** NGRAM_CHAR_BITS,
                             alternate_sign=False, norm=None, lowercase=True, dtype=np.float32)
    word = HashingVectorizer(analyzer="word", ngram_range=(1, 2), n_features=2 ** NGRAM_WORD_BITS,
                             alternate_sign=False, norm=None, lowercase=True, token_pattern=r"(?u)\b\w+\b|[^\w\s]",
                             dtype=np.float32)
    skel = HashingVectorizer(analyzer="word", ngram_range=(1, 4), n_features=2 ** NGRAM_SKEL_BITS,
                             alternate_sign=False, norm=None, lowercase=False, token_pattern=r"\S+", dtype=np.float32)
    return char, word, skel


def ngram_matrix(texts: list[str], lang: str):
    """Sparse matrix: log(1+tf) of character 2–5-grams (within words), word
    1–2-grams and skeleton 1–4-grams; each part is normalized by L2 separately."""
    import scipy.sparse as sp
    from sklearn.preprocessing import normalize as l2

    char, word, skel = _vectorizers()
    norm = [normalize(t) for t in texts]
    parts = []
    for vec, docs in ((char, norm), (word, norm), (skel, [skeleton(t, lang) for t in norm])):
        m = vec.transform(docs).tocsr()
        m.data = np.log1p(m.data)
        parts.append(l2(m))
    return sp.hstack(parts, format="csr")


# ---------------------------------------------------------------- model


class LangModel:
    """Trained model for a single language.

    m_lr — logistic regression on n-grams (average of fold models), m_gb —
    LightGBM boosting on handcrafted features. Result:
        z = a·(m_lr − μ_lr)/σ_lr + (1 − a)·(m_gb − μ_gb)/σ_gb,   logit(p_ai) = c1·z + c0
    a, μ, σ, c1, c0 are tuned on out-of-fold predictions (train/train_stylometry.py)."""

    def __init__(self, lang: str, booster, ngram_coef: np.ndarray, ngram_bias: float, meta: dict, oof: dict[str, float]):
        self.lang = lang
        self.booster = booster
        self.ngram_coef = ngram_coef
        self.ngram_bias = ngram_bias
        self.meta = meta
        self.oof = oof  # text key -> out-of-fold logit (for training set texts from eval sets)
        self.names = meta["feature_names"]
        self.blend = meta["blend"]

    def _combine(self, m_lr: np.ndarray, m_gb: np.ndarray) -> np.ndarray:
        b = self.blend
        z = b["a"] * (m_lr - b["mu_lr"]) / b["sd_lr"] + (1 - b["a"]) * (m_gb - b["mu_gb"]) / b["sd_gb"]
        return b["c1"] * z + b["c0"]

    def margins(self, texts: list[str]) -> np.ndarray:
        """Logits of p_ai (final model, without substitution of out-of-fold predictions)."""
        X = ngram_matrix(texts, self.lang)
        m_lr = np.asarray(X @ self.ngram_coef, dtype=np.float64).ravel() + self.ngram_bias
        F = np.stack([feature_vector(t, self.lang, self.names) for t in texts])
        return self._combine(m_lr, self.booster.predict(F, raw_score=True))

    def explain(self, text: str, top: int = 6) -> dict:
        """Logit and its breakdown: contribution of the n-gram part and feature part, largest in magnitude
        contributions of individual features and word n-grams of this text."""
        b = self.blend
        X = ngram_matrix([text], self.lang)
        m_lr = float(np.asarray(X @ self.ngram_coef).ravel()[0] + self.ngram_bias)
        F = feature_vector(text, self.lang, self.names)[None, :]
        contrib = self.booster.predict(F, pred_contrib=True)[0]
        m_gb = float(contrib.sum())
        k_lr = b["c1"] * b["a"] / b["sd_lr"]
        k_gb = b["c1"] * (1 - b["a"]) / b["sd_gb"]
        order = np.argsort(-np.abs(contrib[:-1]))[:top]
        feats = [(self.names[i], float(F[0, i]), float(k_gb * contrib[i])) for i in order]
        return {
            "margin": float(self._combine(np.array([m_lr]), np.array([m_gb]))[0]),
            "ngram_part": k_lr * (m_lr - b["mu_lr"]),
            "feature_part": k_gb * (m_gb - b["mu_gb"]),
            "features": feats,
            "ngrams": [(g, k_lr * c) for g, c in _word_ngram_contrib(text, X, self.ngram_coef, 60)],
        }


@lru_cache(maxsize=None)
def _identity_hasher():
    from sklearn.feature_extraction.text import HashingVectorizer

    return HashingVectorizer(analyzer=lambda s: [s], n_features=2 ** NGRAM_WORD_BITS, alternate_sign=False, norm=None)


def _word_ngram_contrib(text: str, X, coef: np.ndarray, top: int) -> list[tuple[str, float]]:
    """Contributions of text word 1–2-grams to the n-gram regression logit (same hashes as
    HashingVectorizer: hasher with identity analyzer gives column index by string)."""
    _, word, _ = _vectorizers()
    grams = sorted(set(word.build_analyzer()(normalize(text))))
    if not grams:
        return []
    cols = _identity_hasher().transform(grams).indices + 2 ** NGRAM_CHAR_BITS
    row = X.getrow(0).toarray().ravel()
    items = [(g, float(row[c] * coef[c])) for g, c in zip(grams, cols) if row[c] > 0]
    items.sort(key=lambda t: -abs(t[1]))
    return items[:top]


def text_key(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


@lru_cache(maxsize=None)
def load_model(lang: str, model_dir: str | None = None) -> LangModel | None:
    import gzip

    d = Path(model_dir) if model_dir else MODEL_DIR
    meta_p, lgb_p, ng_p, oof_p = d / f"{lang}.meta.json", d / f"{lang}.lgb.txt", d / f"{lang}.ngram.npz", d / f"{lang}.oof.json.gz"
    if not (meta_p.exists() and lgb_p.exists() and ng_p.exists()):
        return None
    import lightgbm as lgb

    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    booster = lgb.Booster(model_str=lgb_p.read_text(encoding="utf-8"))
    ng = np.load(ng_p, allow_pickle=False)
    oof = json.loads(gzip.decompress(oof_p.read_bytes()).decode("utf-8")) if oof_p.exists() else {}
    return LangModel(lang, booster, ng["coef"].astype(np.float32), float(ng["bias"]), meta, oof)


def model_version(model_dir: Path | None = None) -> str:
    """Hash of model files — in voice cache_salt: retrained model = new voice version."""
    import hashlib

    h = hashlib.sha1(Path(__file__).read_bytes())  # feature code is part of the model
    for p in sorted(Path(model_dir or MODEL_DIR).glob("*.meta.json")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]
