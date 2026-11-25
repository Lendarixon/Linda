# -*- coding: utf-8 -*-
"""CPU token budget for Russian (~2.3 tok/word), candidate count, and completeness guard."""
from types import SimpleNamespace

from linda_desktop import humanize_pack, stylize_core


class _RussianRatioTok:
    """Mock tokenizer returning ~2.3 tokens per Russian word."""

    def encode(self, text: str, add_special_tokens: bool = False):
        n = int(len(text.split()) * 2.35)
        return list(range(max(1, n)))


def test_cpu_token_budget_exceeds_old_220_cap_for_110_word_russian_chunk():
    tok = _RussianRatioTok()
    ru_110 = " ".join(["экономика"] * 110)
    budget = humanize_pack.compute_cpu_max_new_tokens(tok, [ru_110])
    # 110 words * 2.35 = 258 tokens -> 258 * 1.35 + 24 = 372 (was hard-capped at 220!)
    assert budget >= 360
    assert budget <= 420


def test_cpu_token_budget_capped_at_420():
    tok = _RussianRatioTok()
    ru_300 = " ".join(["слово"] * 300)
    assert humanize_pack.compute_cpu_max_new_tokens(tok, [ru_300]) == 420


def test_default_candidates_cpu_short_vs_long():
    cpu_param = SimpleNamespace(device=SimpleNamespace(type="cpu"))
    fake_backend = SimpleNamespace(model=SimpleNamespace(parameters=lambda: iter([cpu_param])))
    assert humanize_pack._default_candidates(fake_backend, ["короткий русский абзац из десяти слов"]) == 3
    assert humanize_pack._default_candidates(fake_backend, [" ".join(["слово"] * 80)]) == 2


def test_completeness_guard_catches_silent_mid_paragraph_cutoff():
    src = (
        "Банк России сохранил ключевую ставку на уровне 21 процента годовых. "
        "Инфляционное давление остаётся высоким в сегменте продовольственных товаров. "
        "Следующее заседание совета директоров запланировано на 20 декабря текущего года. "
        "Большинство аналитиков ожидают сохранения жёсткой денежно-кредитной политики."
    )
    # Truncated after 2 sentences, even though it ends with a period!
    cand_cut = (
        "Центробанк оставил ставку на уровне 21 процента. "
        "Давление цен на продукты питания по-прежнему высоко."
    )
    assert "truncation_suspect" in stylize_core.candidate_problems(src, cand_cut)

    cand_full = (
        "Центробанк оставил ставку на уровне 21 процента. "
        "Рост цен на продукты остаётся заметным. "
        "Ближайшая встреча совета пройдёт 20 декабря. "
        "Эксперты полагают, что жёсткая политика сохранится."
    )
    assert "truncation_suspect" not in stylize_core.candidate_problems(src, cand_full)
