"""A single confident local label must survive the document summary."""
import pytest

from linda_desktop.engine import authorship
from linda_desktop.report import build_report


@pytest.mark.parametrize('verdict', ['human', 'uncertain'])
def test_one_ai_sentence_among_many_is_reported_as_mixed(verdict):
    sentences = [{'text': 'Human sentence.', 'label': 'human'} for _ in range(100)]
    sentences.insert(50, {'text': 'AI sentence.', 'label': 'ai'})
    result = {'verdict': verdict, 'sentences': sentences, 'p_ai': .02}
    result['authorship'] = authorship(verdict, sentences)
    assert result['authorship']['label'] == 'mixed'
    assert result['authorship']['ai_share'] == round(1 / 101, 4)
    report = build_report(' '.join(s['text'] for s in sentences), result)
    assert report['verdict'] == verdict
    assert report['authorship'] == result['authorship']


def test_all_human_summary_stays_human():
    assert authorship('human', [{'text': 'Human sentence.', 'label': 'human'}]) == {
        'label': 'human', 'ai_share': 0., 'uncertain_share': 0., 'human_share': 1.}


def test_uncertain_local_label_alone_does_not_claim_ai_insertion():
    rows = [{'text': 'Human sentence.', 'label': 'human'} for _ in range(100)]
    rows.append({'text': 'Uncertain sentence.', 'label': 'uncertain'})
    assert authorship('human', rows)['label'] == 'human'
