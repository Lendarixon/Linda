import shutil
import subprocess
from pathlib import Path
import pytest
from linda_desktop import analytics


@pytest.mark.skipif(shutil.which('node') is None,reason='Node unavailable')
def test_precision_controls_reset_and_reenable(tmp_path):
    html = (Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    start = html.index('function updatePrecisionAvailability()')
    func = html[start:html.index("document.addEventListener('linda-i18n', updatePrecisionAvailability)",start)]
    script = '''const assert=require('node:assert/strict');
let activeSens='precise', selectedModels=new Set(['stylo7c']);
const precise={dataset:{sens:'precise'},classList:{toggle(){}}};
const sensitive={dataset:{sens:'sensitive'},classList:{toggle(k,v){this.active=v}}};
const document={querySelector:()=>precise,querySelectorAll:()=>[precise,sensitive]};
const window={LINDA_T:k=>k};
'''+func+'''
updatePrecisionAvailability();
assert.ok(precise.disabled && sensitive.classList.active);
assert.equal(activeSens,'sensitive');
assert.equal(precise.title,'err_precise_requires_ensemble');
selectedModels=new Set(['a','b','c']);
updatePrecisionAvailability();
assert.equal(precise.disabled,false);
assert.equal(precise.title,'');
'''
    path = tmp_path/'precision.js'
    path.write_text(script,encoding='utf-8')
    subprocess.run(['node',str(path)],check=True,capture_output=True,text=True)


def test_plain_analytics_counts_sentences_without_model_labels():
    result = analytics.analyze('A short sentence. Here is another sentence. Finally one more sentence.',[])
    assert result['sentences']==3 and result['avg_sentence_words']==pytest.approx(11/3,abs=.1)
    assert 'p_ai_mean' not in result and 'longest_ai_streak' not in result


@pytest.mark.skipif(shutil.which('node') is None,reason='Node unavailable')
def test_actual_no_evidence_authorship_and_export_renderers(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cabinet = (root/'web/cabinet.html').read_text(encoding='utf-8')
    start = cabinet.index('  function drawAuthorship(')
    auth = cabinet[start:cabinet.index('  async function drawAnalytics(',start)]
    html = (root/'web/index.html').read_text(encoding='utf-8')
    start = html.index('function renderExportSection(')
    end = html.index('function copySingleSent(',start)
    export = html[start:end]
    start = html.index('function exportSentenceScores(')
    scores = html[start:html.index('function buildHumanizerPrompt(',start)]
    script = '''const assert=require('node:assert/strict');
const el={innerHTML:'',textContent:''};
const T=key=>key;
const window={LINDA_T:T};
const document={getElementById:()=>el};
'''+auth+export+scores+'''
drawAuthorship(el,{authorship:{label:'unavailable'},heatmap_available:false});
assert.ok(el.innerHTML.includes('ui_heatmap_unavailable'));
assert.ok(!el.innerHTML.includes('NaN') && !el.innerHTML.includes('%'));
renderExportSection({sentences:[],heatmap_available:false});
assert.equal(el.textContent,'ui_heatmap_unavailable');
renderExportSection({sentences:[{label:'uncertain',p_ai:.8}],heatmap_available:true});
assert.ok(el.innerHTML.includes('ui_no_ai') && !el.innerHTML.includes('exp_flagged_h'));
drawAuthorship(el,{authorship:{label:'unavailable',ai_share:0,uncertain_share:0,human_share:1}});
assert.ok(el.innerHTML.includes('ui_heatmap_unavailable'));
assert.equal(exportSentenceScores({multi_margin:3}),'exp_multi_score');
assert.equal(exportSentenceScores({}),'');
'''
    path = tmp_path/'renderers.js'
    path.write_text(script,encoding='utf-8')
    result = subprocess.run(['node',str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
