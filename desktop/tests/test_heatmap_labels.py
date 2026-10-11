"""Реальный рендер разметки: цвета, счётчики и значки сохраняют метки движка."""
import shutil
import subprocess
import json
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="Node unavailable")
def test_heatmap_uses_labels_before_rounding_and_mode_thresholds(tmp_path):
    html = (Path(__file__).resolve().parents[1] / "web/index.html").read_text(encoding="utf-8")
    start = html.index("function LINDA_localResult(r, source")
    renderer = html[start:html.index("function renderExportSection(r)", start)]
    script = r'''
const assert = require('node:assert/strict');
function node() {
  const classes = new Set();
  return {dataset:{},style:{},children:[],textContent:'',innerHTML:'',
    classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),toggle:(x,on)=>on?classes.add(x):classes.delete(x),contains:x=>classes.has(x)},
    appendChild(x){this.children.push(x)},addEventListener(){}};
}
const window={LINDA_T:(k,v)=>k+JSON.stringify(v||{})};
const document={createElement:node,createTextNode:text=>({textContent:text})};
const heatmapSwitcher=node(),heatmapCard=node(),docView=node(),statAiCount=node(),statUncCount=node(),statHuCount=node(),sentTooltip=node();
const metricAiSentences=node(); function renderExportSection() {}
let activeHeatmapSource='ensemble';
''' + renderer + r'''
const sentences=[
  {text:'First.',start:0,end:6,p_ai:.1,label:'human',essay_label:'human',multi_label:'ai',essay_prob:.1,multi_prob:.2},
  {text:'Second.',start:7,end:14,p_ai:.2,label:'uncertain',essay_label:'uncertain',multi_label:'human',essay_prob:.2,multi_prob:.1},
  {text:'Third.',start:15,end:21,p_ai:.3,label:'ai',essay_label:'ai',multi_label:'uncertain',essay_prob:.3,multi_prob:.2}
];
const report={_text:'First. Second. Third.',sentences,sentence_stats:{granularity:'context',thresholds:{ai:.2,uncertain:.1}}};
for (const source of ['ensemble','essay','multi']) {
  activeHeatmapSource=source;
  docView.children=[];
  renderSentenceHeatmap(report);
  const spans=docView.children.filter(x=>x.dataset);
  const expected=source==='multi'?['ai','human','uncertain']:['human','uncertain','ai'];
  assert.deepEqual(spans.map(x=>expected.find(c=>x.classList.contains(c))),expected);
  assert.deepEqual(spans.map(x=>x.children.length),expected.map(c=>c==='ai'?1:0));
  assert.equal(statAiCount.dataset.n,1); assert.equal(statUncCount.dataset.n,1); assert.equal(statHuCount.dataset.n,1);
}
// Older token results have one token source for all tabs; its label is canonical.
activeHeatmapSource='multi'; docView.children=[];
renderSentenceHeatmap({...report,sentences:[{text:'First.',start:0,end:6,p_ai:.7,label:'human'}],sentence_stats:{granularity:'tokens',thresholds:{ai:.815,uncertain:.35}}});
assert.ok(docView.children[0].classList.contains('human'));
assert.equal(docView.children[0].children.length,0);
renderSentenceHeatmap({...report,heatmap_available:false});
assert.ok(heatmapCard.classList.contains('hidden')); assert.equal(docView.innerHTML,'');
for (const [start,end] of [[-1,6],[0,999],[.5,6],[0,null],[6,0]]) {
  renderSentenceHeatmap({...report,sentences:[{...sentences[0],start,end}]});
  assert.ok(heatmapCard.classList.contains('hidden')); assert.equal(docView.innerHTML,'');
}
'''
    path = tmp_path / "heatmap.js"
    path.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(path)], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node unavailable")
def test_reader_keeps_python_offsets_with_emoji_and_unicode(tmp_path):
    html = (Path(__file__).resolve().parents[1] / "web/cabinet.html").read_text(encoding="utf-8")
    start = html.index("  function renderDoc() {")
    renderer = html[start:html.index("  document.querySelector('#cabViewer .modebar')", start)]
    samples = []
    for first, second in [("🙂 First sentence.", "Second sentence."),
                          ("🙂 Первый абзац.", "Второе предложение."),
                          ("🙂 Zażółć gęślą jaźń.", "Drugie zdanie.")]:
        samples.append({"text":first + " " + second, "first":first, "second":second,
                        "sentences":[{"start":0,"end":len(first),"text":first,"label":"human","p_ai":.1},
                                     {"start":len(first)+1,"end":len(first)+1+len(second),"text":second,"label":"ai","p_ai":.9}]})
    script = """const assert=require('node:assert/strict');
const elements={}; const $=id=>(elements[id]??={innerHTML:'',textContent:''});
const T=k=>k; const esc=s=>s; const window={}; let V;
""" + renderer + "\nconst samples=" + json.dumps(samples,ensure_ascii=False) + ";\n" + r"""
for(const sample of samples){
  V={text:sample.text,r:{sentences:sample.sentences},src:'ensemble',shared:[]};
  renderDoc();
  const spans=[...$('vDoc').innerHTML.matchAll(/<span class="vs (human|ai)"[^>]*>(.*?)<\/span>/g)];
  assert.deepEqual(spans.map(x=>[x[1],x[2]]),[['human',sample.first],['ai',sample.second]]);
  assert.equal($('vpA').textContent,'v_ai_n');
}
"""
    path = tmp_path / "reader_unicode.js"
    path.write_text(script,encoding="utf-8")
    result = subprocess.run(["node",str(path)],capture_output=True,text=True,encoding="utf-8")
    assert result.returncode == 0,result.stderr
