"""Cross-runtime contract: selected local labels, shares, exports and rounding."""
import json
import shutil
import subprocess
from pathlib import Path
import pytest
from linda_desktop.analytics import labelled_word_summary, display_probability
from linda_desktop.report import build_report


def test_share_rounding_and_document_confidence_are_separate():
    rows=[{'text':'one', 'label':k,'p_ai':.5} for k in ('ai','uncertain','human')]
    local=labelled_word_summary(rows)
    assert local['word_percentages']=={'ai':34,'uncertain':33,'human':33}
    assert local['word_shares']['ai']==1/3
    rep=build_report('one one one',{'verdict':'ai','p_ai':.905,'sentences':rows})
    assert rep['pct']==91
    assert rep['local_summary']==local
    assert display_probability(.125,'human')==88
    assert display_probability(.125,'ai')==13
    assert sum(labelled_word_summary([])['word_percentages'].values())==0


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_actual_projection_preserves_global_score_and_original_sources(tmp_path):
    html=(Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    helper=html[html.index('function LINDA_localResult(r, source'):html.index('function renderSentenceHeatmap(r)')]
    rows=[
      {'text':'A\u0085B', 'label':'human','p_ai':.02,'essay_label':'ai','essay_prob':.9,'multi_label':'uncertain','multi_prob':.5},
      {'text':'C D E', 'label':'ai','p_ai':.8,'essay_label':'human','essay_prob':.1,'multi_label':'human','multi_prob':.1},
      {'text':'\ufeffF', 'label':'uncertain','p_ai':.8149,'essay_label':'uncertain','essay_prob':.3,'multi_label':'ai','multi_prob':.9},
    ]
    case={'verdict':'ai','p_ai':.905,'sentences':rows,'sentence_stats':{'granularity':'tokens','thresholds':{'ai':.815,'uncertain':.35}}}
    script="const assert=require('node:assert/strict');\n"+helper+'\nconst r='+json.dumps(case)+';\n'+r'''
const before=JSON.stringify(r), results=[];
for (const source of ['ensemble','essay','multi']) {
 const v=LINDA_localResult(r,source);
 assert.equal(v.p_ai,.905); assert.equal(v.verdict,'ai');
 assert.equal(v.markup_source,source);
 assert.equal(Object.values(v.local_summary.word_percentages).reduce((a,b)=>a+b),100);
 assert.deepEqual(v.sentences.map(s=>s.ensemble_label),r.sentences.map(s=>s.label));
 assert.deepEqual(v.sentences.map(s=>s.ensemble_prob),r.sentences.map(s=>s.p_ai));
 assert.deepEqual(LINDA_localResult(v,'ensemble').sentences.map(s=>s.label),r.sentences.map(s=>s.label));
 results.push(v);
}
assert.equal(JSON.stringify(r),before);
console.log(JSON.stringify(results));
'''
    path=tmp_path/'projection.js';path.write_text(script,encoding='utf-8')
    proc=subprocess.run(['node',str(path)],capture_output=True,text=True,encoding='utf-8')
    assert proc.returncode==0,proc.stderr
    results=json.loads(proc.stdout)
    assert [r['sentence_stats']['ai'] for r in results]==[1,1,1]
    for view in results:
        assert view['local_summary']==labelled_word_summary(view['sentences'])
        rep=build_report('A B C D E F',view)
        assert rep['markup_source']==view['markup_source']
        assert rep['local_summary']==view['local_summary']
        assert rep['pct']==91
        assert rep['sentences'][2]['ensemble_prob']==.8149
    assert results[0]['sentences'][2]['label']=='uncertain'


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_stale_analytics_response_cannot_overwrite_new_source(tmp_path):
    html=(Path(__file__).resolve().parents[1]/'web/cabinet.html').read_text(encoding='utf-8')
    fn=html[html.index('  async function drawAnalytics'):html.index('  // violin:')]
    script=r'''
const assert=require('node:assert/strict'); const T=k=>k,esc=s=>s;
const pending=[]; const jpost=()=>new Promise(resolve=>pending.push(resolve));
''' + fn + r'''
(async()=>{
const el={innerHTML:''}, data={stock_phrases:[],repeated_phrases:[]};
const a=drawAnalytics(el,{sentences:[]},'old');
const b=drawAnalytics(el,{sentences:[]},'new');
pending[1]({...data,avg_sentence_words:222});await b;
assert.ok(el.innerHTML.includes('222'));
pending[0]({...data,avg_sentence_words:111});await a;
assert.ok(el.innerHTML.includes('222')); assert.ok(!el.innerHTML.includes('111'));
})().catch(e=>{console.error(e);process.exit(1)});
'''
    path=tmp_path/'race.js';path.write_text(script,encoding='utf-8')
    proc=subprocess.run(['node',str(path)],capture_output=True,text=True,encoding='utf-8')
    assert proc.returncode==0,proc.stderr
