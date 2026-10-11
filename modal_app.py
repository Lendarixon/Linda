# -*- coding: utf-8 -*-
"""Linda-Pro 2.0.6.0 private demo: Engine-based detection with LINDA models 1.3.4."""
from pathlib import Path

import modal

app = modal.App("linda-pro-demo")
vol = modal.Volume.from_name("linda-models-131", create_if_missing=True)

LIMITS = {
    "per_ip_per_hour": 20,
    "uploads_per_ip_per_hour": 40,
    "per_day": 300,
    "max_words": 5000,
    "min_words": 20,
    "max_upload_bytes": 6_000_000,
}

gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.9.1",
        "transformers>=4.44,<5",
        "lightgbm>=4.0",
        "scikit-learn>=1.3",
        "numpy",
        "pyyaml",
        "sentencepiece",
        "tiktoken",
        "protobuf",
        "onnxruntime",
    )
    .add_local_dir("desktop/linda_desktop", "/root/linda_desktop", ignore=["__pycache__", "*.pyc"])
    .add_local_dir("linda_pro", "/root/linda_pro", ignore=["__pycache__", "*.pyc"])
    .add_local_dir("calibration", "/root/calibration")
)
web_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]", "python-docx")
    .add_local_file("modal/demo.html", "/root/demo.html")
)


@app.cls(
    image=gpu_image,
    gpu="L4",
    volumes={"/models": vol},
    scaledown_window=90,
    max_containers=1,
    timeout=300,
)
class Detector:
    @modal.enter()
    def load(self):
        import os
        import sys

        os.environ["LINDA_HOME"] = "/tmp/linda-demo"
        os.environ["LINDA_MODELS_HOME"] = "/models"
        os.environ["LINDA_ROUTING"] = "/root/calibration/routing.json"

        sys.path.insert(0, "/root")
        from linda_desktop.engine import Engine, save_settings

        self.engine = Engine()
        save_settings({'quality':'pro','device':'cuda','save_history':False,'preload':False,'sentences':'auto','model_sets':['pro']})
        import torch
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False

    @modal.method()
    def run(self, text: str, mode: str) -> dict:
        if mode not in ("sensitive", "precise"):
            raise ValueError("invalid mode")
        result = self.engine.run(text, mode=mode)
        assert self.engine.device == 'cuda', 'Modal Assay must use CUDA'
        assert result['detector_id'] == 'assay'
        result['app_version'] = '2.0.6.0'
        result['model_pack_version'] = '1.3.4'
        try:
            t = self.engine.dets[mode].tier(result.get('language','en'))
            if t:
                result['thresholds'] = {'p5':float(t['thr_p5']),'sens':float(t['thr_sensitive']),'p03':float(t['thr_p03'])}
        except Exception:  # noqa: BLE001
            pass
        return result


@app.function(
    image=web_image,
    max_containers=2,
    scaledown_window=60,
    secrets=[modal.Secret.from_name("linda-demo-access")],
)
@modal.asgi_app()
def web():
    import datetime
    import hashlib
    import hmac
    import io
    import os
    import time
    from pathlib import Path

    from fastapi import FastAPI, File, Request, UploadFile
    from fastapi.responses import HTMLResponse, JSONResponse

    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    counters = modal.Dict.from_name("linda-demo-limits-13", create_if_missing=True)
    page = Path("/root/demo.html").read_text(encoding="utf-8")

    def err(msg: str, code: int):
        return JSONResponse({"detail": msg}, status_code=code)

    async def bump(key: str, limit: int) -> bool:
        n = await counters.get.aio(key, 0)
        if n >= limit:
            return False
        await counters.put.aio(key, n + 1)
        return True

    async def who_and_auth(request: Request):
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        who = hashlib.sha256(("linda-salt:" + ip).encode()).hexdigest()[:16]
        code = request.headers.get("x-access-code", "")
        expected = os.environ.get("ACCESS_CODE", "")
        if not expected or not hmac.compare_digest(code.encode(), expected.encode()):
            if not await bump(f"bad:{who}:{int(time.time() // 3600)}", 20):
                return who, err("too many wrong codes, try again later", 429)
            return who, err("wrong access code", 401)
        return who, None

    def extract(filename: str, content: bytes) -> str:
        ext = Path(filename).suffix.lower()
        if ext in (".txt", ".md", ".text", ""):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="replace")
        if ext == ".docx":
            import docx

            return "\n\n".join(p.text for p in docx.Document(io.BytesIO(content)).paragraphs if p.text.strip())
        raise ValueError("Supported formats: .txt, .md, .docx")

    @api.get("/", response_class=HTMLResponse)
    def index():
        return page

    @api.get("/health")
    def health():
        return {"status": "ok", "app_version": "2.0.6.0", "model_version": "1.3.4"}

    @api.post("/api/upload")
    async def upload(request: Request, file: UploadFile = File(...)):
        who, bad = await who_and_auth(request)
        if bad:
            return bad
        if not await bump(f"up:{who}:{int(time.time() // 3600)}", LIMITS["uploads_per_ip_per_hour"]):
            return err("too many uploads from your address, try again in an hour", 429)
        content = await file.read(LIMITS["max_upload_bytes"] + 1)
        if len(content) > LIMITS["max_upload_bytes"]:
            return err("file is too large (max 6 MB)", 413)
        try:
            text = extract(file.filename or "file.txt", content).replace("\r\n", "\n").replace("\r", "\n").strip()
        except Exception as exc:  # noqa: BLE001
            detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            return err("could not read the file: " + detail, 400)
        if not text:
            return err("no text could be extracted from the file", 400)
        return {"status": "ok", "filename": file.filename or "file.txt", "text": text, "words": len(text.split()), "chars": len(text)}

    @api.post("/api/detect")
    async def detect(request: Request):
        who, bad = await who_and_auth(request)
        if bad:
            return bad
        try:
            body = await request.json()
            text = str(body["text"]).replace("\r\n", "\n").replace("\r", "\n").strip()
            mode = body.get("mode", "sensitive")
            if mode not in ("sensitive", "precise"):
                raise ValueError
        except Exception:  # noqa: BLE001
            return err("bad request", 400)
        n = len(text.split())
        if not LIMITS["min_words"] <= n <= LIMITS["max_words"]:
            return err("text must be %d-%d words (now %d)" % (LIMITS["min_words"], LIMITS["max_words"], n), 400)
        if not await bump(f"day:{datetime.date.today().isoformat()}", LIMITS["per_day"]):
            return err("daily limit of the demo is reached, try tomorrow", 429)
        if not await bump(f"ip:{who}:{int(time.time() // 3600)}", LIMITS["per_ip_per_hour"]):
            return err("too many checks from your address, try again in an hour", 429)
        try:
            result = await Detector().run.remote.aio(text, mode)
        except Exception:  # noqa: BLE001
            return err("detector is unavailable, try again in a minute", 503)
        return {"status": "ok", "result": result}

    return api
