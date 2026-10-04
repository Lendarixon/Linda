"""Exercise actual render branches: Store cannot advertise EXE actions."""
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def test_audit_store_localizations_match_embedded_offline_dictionary():
    html = (ROOT / 'web/index.html').read_text('utf-8')
    embedded = json.loads(re.search(r'window\.LINDA_I18N = (.*?);\n',html).group(1))
    for lang in ('en','ru','pl'):
        strings = json.loads((ROOT / 'web/i18n' / f'{lang}.json').read_text('utf-8'))
        assert embedded[lang] == strings
        assert strings['a_note'] and 'Microsoft Store' in strings['banner_store_required']

@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_store_banner_and_setup_guidance_use_store_without_exe_action(tmp_path):
    html = (ROOT / 'web/index.html').read_text('utf-8')
    banner = html[html.index("    const ban = $('lpBanner')"):html.index("    ban.classList.toggle('show', !!text)")]
    setup = html[html.index('      const storeRequired ='):html.index('    // banner')].rsplit('    }',1)[0]
    script = """
const assert=require('node:assert/strict');
const elements = {};
const $=id=>elements[id]||(elements[id]={style:{},disabled:false,textContent:''});
const T=key=>key, textInput={}, btnUploadTrigger={}, btnAnalyze={};
const checkCtl=null,uploadCtl=null,fmt=x=>String(x),chgText=x=>'';
function bannerResult(s) {
 const d=s.download,busy=false;
"""+banner+"""
 return {text,btn,act,warn};
}
function setupResult(up) {
 const s={update:up};
"""+setup+"""
 return {disabled:$('lpSetupGo').disabled,display:$('lpSetupGo').style.display,message:$('lpSetupErr').textContent};
}
const base={download:{phase:'idle'},models_ready:true,installer_job:{phase:'pending'},update_pending:{version:'99'}};
const required={distribution:'store',app_required:true,app_new:true,installer:{version:'99'}};
assert.deepEqual(bannerResult({...base,update:required}),{text:'banner_store_required',btn:'',act:null,warn:true});
assert.deepEqual(setupResult(required),{disabled:true,display:'none',message:'banner_store_required'});
const standalone=bannerResult({...base,installer_job:{phase:'idle'},update_pending:null,update:{app_required:true,installer:{version:'99'}}});
assert.equal(standalone.act,'app');assert.equal(standalone.btn,'btn_update_app');
const storeModels=bannerResult({...base,update:{distribution:'store',weights_update:true,remote_version:'2'}});
assert.equal(storeModels.act,'models');assert.equal(storeModels.btn,'btn_models');
"""
    path = tmp_path / 'store-render.js'
    path.write_text(script,encoding='utf-8')
    result = subprocess.run(['node',str(path)],capture_output=True,text=True)
    assert result.returncode == 0,result.stderr
