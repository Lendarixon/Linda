# -*- coding: utf-8 -*-
"""Russian numeral agreement and glued CamelCase word guards in stylize_core."""
from linda_desktop import stylize_core


def test_rejects_bad_decimal_agreement():
    src = "Инфляция составила 1,8 процента, а ключевая ставка достигла 4 процента."
    bad = "Рост цен составил 1,8 процентов, при этом ставка осталась на уровне 4 процента."
    assert "numeral_agreement" in stylize_core.candidate_problems(src, bad)


def test_rejects_bad_integer_agreement():
    src = "Ключевая ставка поднялась выше целевых 4 процента, а налог составил 21 процент и 5 процентов."
    bad1 = "Ключевая ставка поднялась выше целевых 4 процентов, а налог составил 21 процент и 5 процентов."
    bad2 = "Ключевая ставка поднялась выше целевых 4 процента, а налог составил 21 процентов и 5 процентов."
    bad3 = "Ключевая ставка поднялась выше целевых 4 процента, а налог составил 21 процент и 5 процента."
    assert "numeral_agreement" in stylize_core.candidate_problems(src, bad1)
    assert "numeral_agreement" in stylize_core.candidate_problems(src, bad2)
    assert "numeral_agreement" in stylize_core.candidate_problems(src, bad3)


def test_accepts_valid_russian_numerals():
    src = "Ставка составила 1,8 процента, налог вырос на 4 процента, доля достигла 15 процентов и 1 процент."
    good = "Показатель составил 1,8 процента, сбор увеличился на 4 процента, часть достигла 15 процентов и 1 процент."
    probs = stylize_core.candidate_problems(src, good)
    assert "numeral_agreement" not in probs
    assert "glued_word" not in probs


def test_rejects_glued_russian_word():
    src = "Клиенты крупного банка получили уведомления о новых условиях обслуживания."
    bad = "Клиенты берБанка получили уведомления о новых условиях обслуживания счетов."
    assert "glued_word" in stylize_core.candidate_problems(src, bad)
