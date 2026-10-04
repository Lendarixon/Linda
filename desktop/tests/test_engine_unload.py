from linda_desktop import engine

def test_unload_updates_requested_device_and_clears_previous_error(monkeypatch):
    monkeypatch.setattr(engine,'load_settings',lambda:{'device':'cpu'})
    monkeypatch.setattr(engine,'pick_device',lambda preference:preference)
    value=engine.Engine()
    value.device='dml'
    value.gpu_error='previous adapter failure'
    value.dets={'sensitive':object()}
    value.unload()
    assert value.dets is None and value.device=='cpu'
    assert value.info()['gpu_error']=='' and value.info()['phase']=='idle'
