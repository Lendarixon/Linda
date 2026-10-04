"""Execute the actual result renderer: confidence must describe the shown verdict."""
import json
import shutil
import subprocess
from pathlib import Path
import pytest

@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_single_human_confidence_and_zero_score(tmp_path):
    html = (Path(__file__).resolve().parents[1] / 'web/index.html').read_text(encoding='utf-8')
    start = html.index('function renderResults(r) {')
    end = html.index('// PANGRAM HEATMAP SWITCHER', start)
    renderer = html[start:end]
    script = '''
const assert = require('node:assert/strict');
const fake = () => ({style:{},classList:{add(){},remove(){}},setAttribute(){},textContent:''});
const window = {LINDA_T:(k,v)=>k+JSON.stringify(v||{})};
const emptyState=fake(),resultsContent=fake(),verdictMeta=fake(),verdictHeader=fake(),verdictBadge=fake(),verdictPct=fake(),verdictPctLabel=fake(),metricAiSentences=fake(),metricZScore=fake(),voterScoreEssay=fake(),voterScoreMulti=fake(),voterScoreStylo=fake();
function renderExportSection() {}
''' + renderer + '''
renderResults({mode:'sensitive',custom_verdict:{verdict:'human',p_ai:0.14,score:0,model:'stylo'},voters:{},_elapsed:'1.0'});
assert.equal(verdictPct.textContent,'86%');
assert.ok(verdictPctLabel.textContent.startsWith('ui_probability_origin'));
assert.ok(verdictMeta.textContent.includes('"s":0'));
renderResults({mode:'sensitive',verdict:'human',p_ai:0.14,voters:{},_elapsed:'1.0'});
assert.equal(verdictPct.textContent,'86%');
renderResults({mode:'sensitive',custom_verdict:{verdict:'ai',p_ai:0.94,score:2,model:'stylo'},voters:{},_elapsed:'1.0'});
assert.equal(verdictPct.textContent,'94%');
renderResults({verdict:'uncertain',p_ai:.85,voters:{}});
assert.equal(verdictPct.textContent,'85%');
assert.ok(verdictPctLabel.textContent.startsWith('ui_probability_ai'));
renderResults({verdict:'ai',p_ai:.73,voters:{stylo7c:4},heatmap_available:false,ens_z:null});
assert.equal(metricAiSentences.textContent,'—');
assert.equal(metricZScore.textContent,'—');
'''
    path = tmp_path / 'renderer.js'
    path.write_text(script, encoding='utf-8')
    result = subprocess.run(['node', str(path)],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
