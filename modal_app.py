"""Public Linda Metro demo; Engine 2.0.6.2 (unchanged scoring), model pack 1.3.4."""
from pathlib import Path
import modal
app=modal.App('linda-pro-demo')
vol=modal.Volume.from_name('linda-models-131')
quota_vol=modal.Volume.from_name('linda-public-demo-quota',create_if_missing=True)
session_secret=modal.Secret.from_name('linda-public-demo-session')
gpu_image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install('torch==2.9.1','transformers>=4.44,<5','lightgbm>=4.0','scikit-learn>=1.3','numpy','pyyaml','sentencepiece','tiktoken','protobuf','onnxruntime')
    .add_local_dir('desktop/linda_desktop','/root/linda_desktop',ignore=['__pycache__','*.pyc'])
    .add_local_dir('linda_pro','/root/linda_pro',ignore=['__pycache__','*.pyc'])
    .add_local_file('modal/model_manifest.json','/root/model_manifest.json'))
web_image=(modal.Image.debian_slim(python_version='3.12').pip_install('fastapi[standard]','python-docx>=1.2,<2')
    .add_local_file('modal/demo.html','/root/demo.html',copy=True)
    .add_local_file('modal/demo_api.py','/root/demo_api.py',copy=True)
    .add_local_file('modal/demo_quota.py','/root/demo_quota.py',copy=True))

def load_engine(detector):
    import os,sys,json,hashlib
    os.environ['LINDA_HOME']='/tmp/linda-demo-'+detector
    os.environ['LINDA_MODELS_HOME']='/models'
    os.environ['LINDA_ROUTING']='/models/calibration/routing.json'
    sys.path.insert(0,'/root')
    expected=json.loads(Path('/root/model_manifest.json').read_text())
    needed_set=('lite','shared') if detector=='loupe' else ('pro','shared')
    for item in expected['files']:
        if item.get('set') not in needed_set:continue
        p=Path('/models')/item['path']
        if not p.is_file() or p.stat().st_size!=item['size']:raise RuntimeError('Model pack file missing or size differs: '+item['path'])
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
        if h.hexdigest()!=item['sha256']:raise RuntimeError('Model pack hash differs: '+item['path'])
    from linda_desktop.engine import Engine,save_settings
    save_settings({'quality':'lite' if detector=='loupe' else 'pro','device':'cpu' if detector=='loupe' else 'cuda','save_history':False,'preload':False,'sentences':'auto','model_sets':['lite'] if detector=='loupe' else ['pro']})
    import torch
    torch.set_num_threads(4 if detector=='loupe' else 2)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    engine=Engine()
    try:
        engine.run('Warmup Linda detector sentence.',mode='sensitive')
    except Exception:
        pass
    return engine

def run_engine(engine,text,mode,detector):
    if mode not in ('sensitive','precise'):raise ValueError('invalid mode')
    result=engine.run(text,mode=mode)
    assert result['detector_id']==detector,'Incorrect detector tier'
    assert engine.device==('cpu' if detector=='loupe' else 'cuda'),'Incorrect compute backend'
    result.update(app_version='2.0.6.2',model_pack_version='1.3.4',markup_version='2.0.6.2',demo_revision='public-release-2062-20261017')
    tier=engine.dets[mode].tier(result.get('language','en'))
    if tier:result['thresholds']={'p5':float(tier['thr_p5']),'sens':float(tier['thr_sensitive']),'p03':float(tier['thr_p03'])}
    return result

@app.cls(image=gpu_image,gpu='L4',volumes={'/models':vol},scaledown_window=300,max_containers=1,timeout=300)
class Detector:
    @modal.enter()
    def load(self):self.engine=load_engine('assay')
    @modal.method()
    def run(self,text:str,mode:str)->dict:return run_engine(self.engine,text,mode,'assay')

@app.cls(image=gpu_image,volumes={'/models':vol},cpu=4,memory=8192,scaledown_window=300,max_containers=2,timeout=300)
class LoupeDetector:
    @modal.enter()
    def load(self):self.engine=load_engine('loupe')
    @modal.method()
    def run(self,text:str,mode:str)->dict:return run_engine(self.engine,text,mode,'loupe')

@app.function(image=web_image,volumes={'/quota':quota_vol},max_containers=1,scaledown_window=300,timeout=30)
def quota_operation(operation:str,visitor:str,network:str,request_id:str|None=None):
    # One input/container (Modal default), one writer and SQLite transactions.
    import sys
    sys.path.insert(0,'/root')
    from demo_quota import quota
    result=quota('/quota/checks.sqlite3',operation,visitor,network,request_id)
    quota_vol.commit()
    return result

@app.function(image=web_image,max_containers=2,scaledown_window=60,timeout=600,secrets=[session_secret])
@modal.asgi_app()
def web():
    import os,sys
    sys.path.insert(0,'/root')
    from demo_api import create_api
    async def count(op,visitor,network,rid):return await quota_operation.remote.aio(op,visitor,network,rid)
    async def run(text,mode,detector):
        backend=LoupeDetector() if detector=='loupe' else Detector()
        return await backend.run.remote.aio(text,mode)
    return create_api(Path('/root/demo.html').read_text(encoding='utf-8'),count,run,os.environ.get('SESSION_SECRET',''))
