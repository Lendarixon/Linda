import json
from linda_desktop import engine, onnx_gpu
from linda_pro import routed, voters

def test_routed_gpu_keeps_assay_fp32_and_loupe_cpu(tmp_path, monkeypatch):
    calls=[]
    dirs={'essay_m':'essay','multi_m':'multi','speed_s':'speed'}
    for name in dirs.values(): (tmp_path/'models'/name).mkdir(parents=True)
    (tmp_path/'models/speed/model.onnx').touch()
    table={'voice_dirs':dirs,'size_mb_fp16':{'essay_m':870,'multi_m':560},'languages':{'en':{'tiers':{'full':{},'speed':{}}}}}
    path=tmp_path/'routing.json';path.write_text(json.dumps(table))
    monkeypatch.setattr(engine.config,'models_root',lambda:tmp_path)
    monkeypatch.setattr(onnx_gpu,'OnnxSeqCls',lambda d,c,i,**kw:calls.append(('gpu',d.name,kw)))
    monkeypatch.setattr(voters,'SpeedOnnx',lambda d:calls.append(('cpu',d.name,{})))
    pools=[]
    monkeypatch.setattr(routed,'ModelPool',lambda make,sizes,budget:pools.append((sizes,budget)))
    def fake_routed(table,make,*args,**kw):
        for key in dirs: make(key)
        return object()
    monkeypatch.setattr(routed,'RoutedLindaPro',fake_routed)
    e=engine.Engine.__new__(engine.Engine);e.device='dml'
    e._routed_detectors(path,{'quality':'both'})
    assert all(kw=={'fp16':False,'stable':True} for kind,name,kw in calls if kind=='gpu')
    assert any(kind=='cpu' and name=='speed' for kind,name,kw in calls)
    assert pools==[({'essay_m':1740,'multi_m':1120},5200)]

def test_long_context_sampling_is_device_independent():
    from types import SimpleNamespace
    spans=[SimpleNamespace(text=f'Sentence {i} has several words.') for i in range(740)]
    contexts=[]
    class Voice:
        def margins(self,texts):
            contexts.append(texts)
            return [float(i) for i in range(len(texts))]
    voice=Voice();det=SimpleNamespace(_factory=lambda key:voice)
    results=[]
    for device in ('cpu','dml'):
        e=engine.Engine.__new__(engine.Engine);e.device=device;e.tier='full'
        results.append(e._context_margins(det,spans))
    assert contexts[0]==contexts[1]
    assert len(contexts[0])==149
    assert results[0]==results[1]
