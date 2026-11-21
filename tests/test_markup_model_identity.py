"""Separate actual model identity and independent token sources from display."""
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from linda_desktop import engine as E
from test_tokens_mode import make_engine, Voter


def test_assay_token_sources_use_their_own_head(tmp_path, monkeypatch):
    essay_dir, multi_dir = tmp_path/'essay', tmp_path/'multi'
    for folder, center in [(essay_dir, 1.), (multi_dir, 3.)]:
        folder.mkdir()
        np.savez(folder/'tok_head.npz', w=np.ones(1), b=0., center=center, scale=.5)
    essay, multi = Voter(essay_dir), Voter(multi_dir)
    eng = make_engine(monkeypatch, essay, 'full', verdict='uncertain', mode='tokens')
    eng.dets['sensitive']._factory = lambda name: essay if name == 'linda_essay' else multi
    result = eng.run('High low. High High.')
    row = result['sentences'][0]
    assert row['essay_prob'] == .5
    assert row['multi_prob'] == round(E._sig(1., 3., .5), 3)
    assert row['essay_label'] == 'ai' and row['multi_label'] == 'human'
    assert row['p_ai'] == round((.5 + E._sig(1., 3., .5))/2, 3)
    assert result['detector_id'] == 'assay'
    from linda_desktop.report import build_report
    report = build_report('High low. High High.', result)
    assert report['detector_id'] == 'assay' and report['lite'] is False
    assert report['sentences'][0]['essay_label'] == 'ai'
    assert report['sentences'][0]['multi_label'] == 'human'


def test_loupe_identity_and_missing_local_evidence(tmp_path, monkeypatch):
    voter = Voter(tmp_path)
    voter.token_scores = lambda text: [(0, len(text), -10.)]
    eng = make_engine(monkeypatch, voter, 'speed', verdict='uncertain')
    result = eng.run('A sentence.')
    assert result['detector_id'] == 'loupe'
    assert result['authorship']['label'] == 'uncertain'
    assert result['authorship']['human_share'] == 1
    assert result['verdict'] == 'uncertain'
    assert result['local_document_disagreement'] is True
    assert result['sentence_stats']['sources'] == ['ensemble']
    from linda_desktop.report import build_report
    report = build_report('A sentence.', result)
    assert report['lite'] is True
    assert report['local_document_disagreement'] is True


def test_invalid_original_token_coordinates_are_rejected():
    spans = E.split_sentences_with_offsets('One.')
    for tokens in [[(-1, 4, .2)], [(0, 10, .2)], [(0, 4, float('inf'))]]:
        with pytest.raises(ValueError):
            E._sentence_token_evidence('One.', spans, tokens, 0., 1.)


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_rendered_header_uses_executed_detector_before_any_hooks(tmp_path):
    root = Path(__file__).resolve().parents[1]
    html = (root/'web/index.html').read_text(encoding='utf-8')
    start = html.index('function LINDA_detectorId(r) {')
    renderer = html[start:html.index('// PANGRAM HEATMAP SWITCHER', start)]
    # Execute the actual renderer; this catches the previous ordering bug that
    # string searches and checking translations alone could not detect.
    js = r"""const assert = require('node:assert/strict');
function el(){return {style:{},classList:{add(){},remove(){},toggle(){}},setAttribute(k,v){this[k]=v},textContent:''};}
const window={LINDA_T:(k,v)=>k,LINDA_liteRes:()=>{}};
const document={getElementById:()=>null};
const emptyState=el(),resultsContent=el(),verdictMeta=el(),verdictHeader=el(),verdictBadge=el(),verdictPct=el(),verdictPctLabel=el(),metricAiSentences=el(),metricZScore=el(),voterScoreEssay=el(),voterScoreMulti=el(),voterScoreStylo=el();
function renderExportSection(){}
""" + renderer + r"""
for (const r of [{detector_id:'loupe'}, {routing:{voters:['speed_s'],config:'renamed'}}, {routing:{config:'Linda-Speed'}}]) {
 renderResults({...r,verdict:'uncertain',p_ai:.6316});
 assert.equal(verdictHeader.textContent,'ui_ens_verdict_lite');
}
renderResults({detector_id:'assay',routing:{config:'Linda-Speed stale'},verdict:'ai',p_ai:.9063});
assert.equal(verdictHeader.textContent,'ui_ens_verdict');
"""
    path = tmp_path/'render.js';path.write_text(js,encoding='utf-8')
    proc = subprocess.run(['node',str(path)],capture_output=True,text=True,encoding='utf-8')
    assert proc.returncode == 0,proc.stderr
    embedded = json.loads(html.split('window.LINDA_I18N = ',1)[1].split(';\n',1)[0])
    for lang in ('en','ru','pl'):
        assert embedded[lang] == json.loads((root/'web/i18n'/f'{lang}.json').read_text(encoding='utf-8'))
