import asyncio
import threading
import time
import sys
import types
from contextlib import nullcontext
import pytest
import httpx
from linda_desktop import app as app_mod, humanize_pack, task_cancel, trace_pack, licensing, updater

def test_request_scope_is_thread_local_and_restored():
 event=threading.Event()
 with task_cancel.bind(event):
  assert task_cancel.current() is event
  seen=[];thread=threading.Thread(target=lambda:seen.append(task_cancel.current()));thread.start();thread.join()
  assert seen==[None]
  event.set()
  try:task_cancel.check()
  except task_cancel.ToolCancelled:event.clear()
  else:raise AssertionError('not cancelled')
 assert task_cancel.current() is None

def test_tool_cancel_stops_worker_and_preserves_other_jobs(repo,monkeypatch):
 monkeypatch.setattr(licensing,'check_licensed',lambda *a:None)
 monkeypatch.setattr(updater,'is_complete',lambda:True)
 monkeypatch.setattr(humanize_pack,'unload',lambda:None)
 entered=threading.Event();finished=threading.Event()
 def fake(*a,**kw):
  entered.set()
  try:
   for _ in range(1000):task_cancel.check();time.sleep(.002)
  finally:finished.set()
 monkeypatch.setattr(humanize_pack,'humanize',fake)
 core=app_mod.Core();api=app_mod.create_app(core,token='test-tools')
 unrelated=threading.Event();core.active_checks['other']=('other-client',unrelated)
 async def scenario():
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='http://testserver',headers={'x-linda-token':'test-tools'}) as c:
   job=asyncio.create_task(c.post('/api/humanize',json={'text':'one two three four five','job_id':'rewrite-job','client_id':'test-client'}))
   for _ in range(100):
    if entered.is_set():break
    await asyncio.sleep(.01)
   assert entered.is_set()
   response=await c.post('/api/detect/cancel',json={'job_id':'rewrite-job'});assert response.status_code==200
   result=await asyncio.wait_for(job,2);assert result.status_code==499
   assert finished.is_set() and not unrelated.is_set()
   assert 'rewrite-job' not in core.active_checks and core.active_requests==0 and not core.tool_lock.locked()
 asyncio.run(scenario())

def test_generation_stopping_criterion_checks_request_event(monkeypatch):
 event=threading.Event();observed=[]
 class Tensor:
  shape=(1,8)
  def to(self,*args):return self
 class Model:
  def parameters(self):return iter([types.SimpleNamespace(device='cpu')])
  def generate(self,*args,**kwargs):
   criterion=kwargs['stopping_criteria'][0]
   observed.append(criterion(None,None));event.set();observed.append(criterion(None,None));return []
 monkeypatch.setitem(sys.modules,'torch',types.SimpleNamespace(no_grad=nullcontext))
 monkeypatch.setitem(sys.modules,'transformers',types.SimpleNamespace(StoppingCriteria=object,StoppingCriteriaList=list))
 backend=humanize_pack.HumanizerBackend();backend.model=Model();backend.tok=types.SimpleNamespace(apply_chat_template=lambda *a,**kw:{'input_ids':Tensor(),'attention_mask':Tensor()},pad_token_id=0)
 with pytest.raises(task_cancel.ToolCancelled):
  with task_cancel.bind(event):backend.generate(['one two three four'],1)
 assert observed==[False,True]

def test_precancelled_tool_never_starts_model(repo,monkeypatch):
 calls=[];monkeypatch.setattr(humanize_pack,'humanize',lambda *a,**kw:calls.append(1))
 core=app_mod.Core();api=app_mod.create_app(core,token='test-tools')
 async def scenario():
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api),base_url='http://testserver',headers={'x-linda-token':'test-tools'}) as c:
   await c.post('/api/detect/cancel',json={'job_id':'early-stop'})
   result=await c.post('/api/humanize',json={'text':'one two three four','job_id':'early-stop','client_id':'client'})
   assert result.status_code==499 and not calls
 asyncio.run(scenario())
