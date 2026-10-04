import shutil
import subprocess
from pathlib import Path
import pytest

@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_restart_draft_restores_text_but_does_not_overwrite_new_input(tmp_path):
    html = (Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    start = html.index('async function restoreRestartDraft() {')
    end = html.index("textInput.addEventListener('input', () =>",start)
    code = """
const assert=require('node:assert/strict');
let draftAllowed=true;
const textInput={value:'',dispatchEvent(){}};
let calls=[];
function saveDraft() {}
async function fetch(path, options) {
  calls.push([path,options]);
  return {ok:true,json:async()=>({draft:{id:'id-1',text:'Unsaved document'}})};
}
"""+html[start:end]+"""
(async()=>{
await restoreRestartDraft();
assert.equal(textInput.value,'Unsaved document');
assert.equal(calls[1][0],'/api/draft/ack');
assert.equal(JSON.parse(calls[1][1].body).id,'id-1');
textInput.value='New input';calls=[];
await restoreRestartDraft();
assert.equal(textInput.value,'New input');
assert.equal(calls.length,1);
textInput.value='';draftAllowed=false;calls=[];
await restoreRestartDraft();
assert.equal(textInput.value,'');
assert.equal(calls.length,1);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    path=tmp_path/'restart-draft.js'
    path.write_text(code,encoding='utf-8')
    result=subprocess.run(['node',str(path)],capture_output=True,text=True)
    assert result.returncode == 0,result.stderr
