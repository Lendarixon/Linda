import shutil
import subprocess
from pathlib import Path
import pytest


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_update_button_blocks_double_click_before_poll_refresh(tmp_path):
    html = (Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    start = html.index("$('lpBannerBtn').onclick = async () => {")
    end = html.index('  const show =', start)
    script = """
const assert = require('node:assert/strict');
const button = {dataset:{act:'app'},disabled:false};
const $ = () => button;
let bannerActionPending = false, S = {installer_job:{phase:'idle'}}, release;
const paths=[];
function post(path) {paths.push(path);return new Promise(resolve=>release=resolve);}
function render() { button.disabled=bannerActionPending; }
function toast() {throw new Error('unexpected error');}
async function fetch() {return {ok:true,json:async()=>S};}
""" + html[start:end] + """
(async()=>{
const first=button.onclick();
assert.equal(button.disabled,true);
await button.onclick();
assert.deepEqual(paths,['/api/app/update']);
release({status:'started'});
await first;
assert.equal(button.disabled,false);
assert.equal(bannerActionPending,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    file = tmp_path/'update-button.js'
    file.write_text(script,encoding='utf-8')
    result = subprocess.run(['node',str(file)],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
