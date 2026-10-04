"""Provider selection guards with fake runtimes; no GPU, model export or inference."""
import json
import sys
import types

import pytest

from linda_desktop import onnx_gpu


@pytest.fixture
def synthetic_runtime(tmp_path, monkeypatch):
    captured = {"sessions": [], "tokenizers": []}
    ort = types.ModuleType("onnxruntime")
    transformers = types.ModuleType("transformers")
    sequential = object()

    class Options:
        def __init__(self):
            self.config_entries = {}

        def add_session_config_entry(self, name, value):
            self.config_entries[name] = value

    class Session:
        def __init__(self, path, sess_options, providers):
            captured["sessions"].append(self)
            self.path, self.options, self.requested_providers = path, sess_options, providers

        def get_providers(self):
            return list(captured["actual_providers"])

        def run(self, *args, **kwargs):
            pytest.fail("Provider guard test must not execute inference")

    class Tokenizer:
        @staticmethod
        def from_pretrained(path):
            captured["tokenizers"].append(path)
            return object()

    ort.SessionOptions = Options
    ort.ExecutionMode = types.SimpleNamespace(ORT_SEQUENTIAL=sequential)
    ort.InferenceSession = Session
    ort.get_available_providers = lambda: list(captured["actual_providers"])
    transformers.AutoTokenizer = Tokenizer
    monkeypatch.setitem(sys.modules, "onnxruntime", ort)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setattr(onnx_gpu, "export", lambda *args, **kwargs: pytest.fail("Cached fixture must not export a model"))

    model = tmp_path / "synthetic-model"
    model.mkdir()
    (model / "train_args.json").write_text(json.dumps({"max_len": 64}), encoding="utf-8")
    cache_root = tmp_path / "synthetic-cache"
    cache = cache_root / model.name
    cache.mkdir(parents=True)
    (cache / "model.onnx").write_bytes(b"synthetic fixture, fake runtime never parses weights")
    captured.update(model=model, cache_root=cache_root, cache=cache, sequential=sequential)
    return captured


def _classifier(runtime, fp16=False):
    (runtime["cache"] / "meta.json").write_text(
        json.dumps({"max_len": 64, "dtype": "fp16" if fp16 else "fp32"}), encoding="utf-8")
    return onnx_gpu.OnnxSeqCls(runtime["model"], runtime["cache_root"], device_id=3, fp16=fp16)


@pytest.mark.parametrize("actual_providers", [["CPUExecutionProvider"], []])
def test_cpu_fallback_is_rejected_and_session_cleared(synthetic_runtime, actual_providers):
    runtime = synthetic_runtime
    runtime["actual_providers"] = actual_providers
    voter = _classifier(runtime)
    with pytest.raises(RuntimeError, match="DirectML session is unavailable"):
        voter._load()
    assert voter.sess is None
    assert len(runtime["sessions"]) == 1


@pytest.mark.parametrize("fp16", [False, True])
def test_directml_accepted_with_safe_session_options(synthetic_runtime, fp16):
    runtime = synthetic_runtime
    runtime["actual_providers"] = ["DmlExecutionProvider", "CPUExecutionProvider"]
    voter = _classifier(runtime, fp16=fp16)
    voter._load()
    assert voter.sess is runtime["sessions"][0]
    session = voter.sess
    assert session.requested_providers == [("DmlExecutionProvider", {"device_id": 3}), "CPUExecutionProvider"]
    assert session.options.execution_mode is runtime["sequential"]
    assert session.options.enable_mem_pattern is False
    assert 1 <= session.options.intra_op_num_threads <= 6
    assert session.options.inter_op_num_threads == 1
    assert session.options.config_entries["session.intra_op.allow_spinning"] == "0"
    assert session.options.log_severity_level == 3
    assert runtime["tokenizers"] == [str(runtime["model"])]
    voter.close()
    assert voter.sess is None


@pytest.mark.parametrize("providers, expected", [(["CPUExecutionProvider"], False), (["DmlExecutionProvider"], True)])
def test_available_uses_provider_enumeration(synthetic_runtime, providers, expected):
    synthetic_runtime["actual_providers"] = providers
    assert onnx_gpu.available() is expected
