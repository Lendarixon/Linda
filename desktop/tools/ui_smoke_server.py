"""Reusable UX smoke server for Linda desktop web UI (single RTX 5060, Russian text, hybrid Full 4B)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LINDA_HOME"] = str(ROOT / "qa_ui_profile")

import uvicorn
import linda_desktop.updater as updater
import linda_desktop.licensing as licensing
import linda_desktop.humanize_pack as humanize_pack
from linda_desktop.app import Core, create_app

updater.is_complete = lambda: True
licensing.public_state = lambda: {"licensed": True, "tier": "personal", "key_hint": "TEST-2505"}
licensing.check_licensed = lambda *_a, **_k: None

core = Core()
core.engine.gpu = {
    "available": True,
    "backend": "CUDA",
    "name": "NVIDIA GeForce RTX 5060",
    "names": ["NVIDIA GeForce RTX 5060"],
    "discrete": True,
}
core.engine.device = "cuda"
core.engine.state = {"phase": "ready", "error": ""}


def _stub_run(text: str, mode: str = "sensitive", *args, **kw):
    sents = [s.strip() for s in text.split(".") if s.strip()]
    pos = 0
    sent_rows = []
    for s in sents:
        idx = text.find(s, pos)
        if idx < 0:
            idx = pos
        end = idx + len(s) + (1 if (idx + len(s) < len(text) and text[idx + len(s)] == ".") else 0)
        sent_rows.append({"start": idx, "end": end, "text": text[idx:end], "p_ai": 0.74, "label": "ai"})
        pos = end
    return {
        "verdict": "ai",
        "mode": mode,
        "language": "ru",
        "ai_share": 0.76,
        "score": 1.38,
        "ens_z": 1.38,
        "n_windows": 1,
        "windows": [{"start": 0, "end": len(text), "p_ai": 0.76}],
        "sentences": sent_rows,
        "voters": {"linda_essay": 1.4, "linda_multi_v2": 1.3, "stylo7c": 1.2},
        "words": len(text.split()),
        "token_markup": True,
    }


core.engine.run = _stub_run
core.engine.loaded = lambda: True

humanize_pack.status = lambda: {
    "device": {"tier": "full", "ok": True, "note": "", "vram_gb": 7.9, "ram_gb": 15.9, "nvidia_vram_gb": 7.9, "cuda_ready": True},
    "lite": {"installed": True, "base_ready": True, "adapter_ready": True, "size": 1400000000, "repo": "Qwen/Qwen3-0.6B"},
    "full": {"installed": True, "base_ready": True, "adapter_ready": True, "size": 8500000000, "repo": "Qwen/Qwen3-4B"},
}
humanize_pack.humanize = lambda text, spans=None, mode="all", variant="auto", progress=None: {
    "text": "В текущем квартале инфляция опустилась до 1,8 процента, при этом ключевая ставка сохранилась на уровне 4 процента годовых. Эксперты отмечают стабилизацию потребительского спроса на фоне сдержанной монетарной политики.",
    "changes": [{"start": 0, "end": len(text), "status": "changed", "new": "rewritten"}],
    "changed": 1,
    "variant": "full" if variant in ("auto", "full") else "lite",
    "placement": "hybrid (5.3 GB GPU + CPU)",
    "resolve": {"requested": variant, "used": "full" if variant in ("auto", "full") else "lite", "plan": {"note": "hybrid (5.3 GB GPU + CPU)"}},
    "input_words": len(text.split()),
    "output_words": 28,
}

if __name__ == "__main__":
    uvicorn.run(create_app(core, token="ui-test-token"), host="127.0.0.1", port=18765, log_level="warning")
