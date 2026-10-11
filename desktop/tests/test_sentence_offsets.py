import pytest
from linda_desktop.sentences import split_sentences_with_offsets,split_paragraphs_with_offsets


@pytest.mark.parametrize('text,expected',[
    ('"Am I."\n\nThe balcony was open.',['"Am I."','The balcony was open.']),
    ('«Привет!» Следующее предложение.',['«Привет!»','Следующее предложение.']),
    ('“Witaj.” Następne zdanie.',['“Witaj.”','Następne zdanie.']),
    ('(Really?) Yes.',['(Really?)','Yes.']),
    ('First! Second? Third…',['First!','Second?','Third…']),
])
def test_closing_quotes_are_part_of_sentence(text,expected):
    spans=split_sentences_with_offsets(text)
    assert [s.text for s in spans]==expected
    assert all(text[s.start:s.end]==s.text for s in spans)
    covered={i for s in spans for i in range(s.start,s.end)}
    assert all(c.isspace() or i in covered for i,c in enumerate(text))


def test_paragraph_offsets_are_unchanged():
    text='  "First." Second.\n\n«Третий.»  '
    spans=split_paragraphs_with_offsets(text)
    assert [s.text for s in spans]==['"First." Second.','«Третий.»']
    assert all(text[s.start:s.end]==s.text for s in spans)
