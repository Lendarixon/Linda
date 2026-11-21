from types import SimpleNamespace
from linda_pro.voters import FastSeqCls

def test_fp32_cuda_disables_autocast():
    voice=FastSeqCls('.',device='cuda',force_fp32=True)
    voice.device='cuda'
    value=SimpleNamespace(float=lambda:'fp32 logits')
    voice.model=lambda **kw:SimpleNamespace(logits=value)
    # A torch stub with no autocast makes accidental mixed precision fail.
    voice.torch=SimpleNamespace()
    assert voice._logits({'input_ids':object()})=='fp32 logits'
