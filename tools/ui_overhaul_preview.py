"""Isolated, stdlib UI fixture. Never loads models or mutates a user profile."""
import base64
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/ui_overhaul_20261024'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / 'before.zip'
if not BACKUP.exists():
    with zipfile.ZipFile(BACKUP, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['web/index.html','web/cabinet.html','web/metro-dev.css','linda_desktop/app.py','web/i18n/en.json','web/i18n/ru.json','web/i18n/pl.json']:
            z.write(ROOT/name, name)

def fixture():
    try:
        info=json.loads((Path.home()/'AppData/Local/Linda-Pro/instance.json').read_text())
        url=f'http://127.0.0.1:{info["port"]}'
        html=urllib.request.urlopen(url+'/',timeout=2).read().decode('utf-8')
        token=re.search(r'''window\.__lindaToken\s*=\s*['"]([^'"]+)''',html)[1]
        req=urllib.request.Request(url+'/api/status',headers={'x-linda-token':token})
        state=json.loads(urllib.request.urlopen(req,timeout=3).read())
    except Exception:
        state={'settings':{},'engine':{},'model_sets':{},'license':{}}
    state.update(models_ready=True, installed_version='2.3.0.0',startup={'phase':'ready','error':''})
    state['settings'].update(language='ru',language_source='manual',theme='dark',ui_mode='simple',tour_done=True,preload=False,auto_models=False)
    state['engine'].update(phase='ready',device='cpu',have_pro=True,have_lite=True)
    state['license'].update(licensed=True,plan='personal')
    state['download']={'phase':'idle','done':0,'total':0}
    state['installer']={'phase':'idle'}
    state['update']=None
    state['update_error']=''
    return state

STATE=fixture()
STATE['installer_job']={'phase':'idle','done':0,'total':0,'error':''}
STATE['buy']={'personal_team':'https://example.invalid/qa','org':'https://example.invalid/qa','email':'qa@example.invalid'}
STATE['app_version']='2.3.0.0'
STATE['license'].update(tier='personal',status='ok',key_hint='QA')
(OUT/'fixture.json').write_text(json.dumps(STATE,ensure_ascii=False,indent=2),encoding='utf-8')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def send(self,body,kind='application/json',code=200):
        if not isinstance(body,bytes):
            body=json.dumps(body,ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        url=urllib.parse.urlsplit(self.path)
        path=url.path
        if path=='/':
            state=copy.deepcopy(STATE)
            query=urllib.parse.parse_qs(url.query)
            for key in ['language','theme','ui_mode']:
                if key in query: state['settings'][key]=query[key][0]
            html=(ROOT/'web/index.html').read_text(encoding='utf-8')
            cabinet=(ROOT/'web/cabinet.html').read_text(encoding='utf-8')
            html=html.replace('</body>',cabinet+'\n</body>',1)
            html=html.replace('</head>','<style>'+(ROOT/'web/metro-dev.css').read_text(encoding='utf-8')+'</style></head>',1)
            html=html.replace('<body>','<body>'+(ROOT/'web/startup.html').read_text(encoding='utf-8'),1)
            if 'legacy' not in query and (ROOT/'web/desktop-shell.css').exists():
                html=html.replace('</head>','<style>'+(ROOT/'web/desktop-shell.css').read_text(encoding='utf-8')+'</style></head>',1)
                html=html.replace('</body>','<script>'+(ROOT/'web/desktop-shell.js').read_text(encoding='utf-8')+'</script></body>',1)
            boot=base64.b64encode(json.dumps({'language':state['settings']['language'],'settings':state['settings'],'version':'2.3.0.0'}).encode()).decode()
            html=html.replace('__LINDA_TOKEN__','ui-fixture').replace('__LINDA_VERSION__','2.3.0.0').replace('__LINDA_BOOT_B64__',boot)
            return self.send(html.encode(),'text/html')
        if path=='/api/status': return self.send(STATE)
        if path.startswith('/api/i18n/'):
            lang=path.rsplit('/',1)[-1]
            return self.send({'lang':lang,'strings':json.loads((ROOT/f'web/i18n/{lang}.json').read_text(encoding='utf-8'))})
        if path.startswith('/api/history'):
            return self.send({'items':[],'folders':[],'total':0,'unsorted':0,'stats':{'n':0,'ai':0,'unc':0,'hum':0,'words':0},'settings':{'save_history':True,'retention_days':0}})
        if path.startswith('/api/audit'): return self.send({'items':[],'total':0})
        if path=='/api/packs/status': return self.send(STATE.get('packs') or {'trace':{'installed':False},'humanizer':{'installed':False},'licensed':True,'job':{'phase':'idle'}})
        if path.startswith('/api/'):
            return self.send({'items':[],'events':[],'folders':[],'files':[],'total':0,'phase':'idle','settings':STATE['settings']})
        resource=(ROOT/path.lstrip('/')).resolve()
        if ROOT not in resource.parents or not resource.is_file(): return self.send({'detail':'not found'},code=404)
        return self.send(resource.read_bytes(),mimetypes.guess_type(str(resource))[0] or 'application/octet-stream')
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or '{}')
        if self.path=='/api/settings':
            STATE['settings'].update(body)
            return self.send({'settings':STATE['settings']})
        return self.send({'detail':'Preview fixture: this action does not run a model or change files'},code=422)

if __name__=='__main__':
    print('Isolated UI preview at http://127.0.0.1:18826',flush=True)
    ThreadingHTTPServer(('127.0.0.1',18826),Handler).serve_forever()
