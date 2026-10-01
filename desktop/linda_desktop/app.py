# -*- coding: utf-8 -*-
"""Local web backend of the desktop app (127.0.0.1 only). The UI is served from web/index.html."""
from __future__ import annotations

import hmac
import io
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from . import config, licensing, updater
from .engine import Engine, load_settings, save_settings

MAX_UPLOAD = 20_000_000


def launch_installer(path: Path) -> None:
    """Start the silent installer AFTER this process has exited: Setup cannot close a windowless app by itself and would cancel the update, so a detached
    shell waits ~3 s first. /RELAUNCH=1 makes Setup start the new version when it is done; its log is kept in the data folder."""
    log = config.data_dir() / "update_setup.log"
    cmd = f'cmd /c "ping -n 4 127.0.0.1 >nul & "{path}" /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /FORCECLOSEAPPLICATIONS /RELAUNCH=1 /LOG="{log}""'
    flags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    note = config.data_dir() / "update_launch.log"
    try:
        pr = subprocess.Popen(cmd, creationflags=flags | 0x01000000, close_fds=True)  # + CREATE_BREAKAWAY_FROM_JOB
        note.write_text("started pid %s (breakaway)\n%s\n" % (pr.pid, cmd), encoding="utf-8")
    except OSError as e:  # the job does not allow breakaway
        pr = subprocess.Popen(cmd, creationflags=flags, close_fds=True)
        note.write_text("started pid %s (no breakaway: %s)\n%s\n" % (pr.pid, e, cmd), encoding="utf-8")


def extract(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md", ".text", ""):
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return content.decode("cp1252", errors="replace")
    if ext == ".docx":
        import docx

        return "\n\n".join(p.text for p in docx.Document(io.BytesIO(content)).paragraphs if p.text.strip())
    if ext == ".pdf":
        import pypdf

        pages = [(pg.extract_text() or "").strip() for pg in pypdf.PdfReader(io.BytesIO(content)).pages]
        return "\n\n".join(p for p in pages if p)
    raise ValueError("Supported formats: .txt, .md, .docx, .pdf")


class Core:
    """Shared state of the running app."""

    def __init__(self) -> None:
        self.engine = Engine()
        self.job = updater.Job()
        self.job.on_done = lambda m: (self.engine.unload(), self.preload())  # new weights: drop the old ones and, if enabled, load the new ones right away
        self.manifest: dict | None = None
        self.manifest_raw: bytes = b""
        self.update: dict | None = None
        self.update_error = ""
        self.checked_at = 0.0
        self.installer_job = {"phase": "idle", "done": 0, "total": 0, "error": ""}

    def check_updates(self) -> None:
        try:
            self.manifest, self.manifest_raw = updater.get_manifest()
            self.update = updater.update_status(self.manifest)
            self.update_error = ""
            licensing.apply_revocations(self.manifest.get("revoked", []))
        except Exception as e:  # noqa: BLE001
            self.update_error = str(e)
        self.checked_at = time.time()

    def preload(self) -> bool:
        """Load the models into memory in the background (setting "preload", on by default) so that the first analysis is fast. Returns True if a load was started."""
        if not load_settings().get("preload", True) or self.engine.dets is not None or not updater.is_complete():
            return False

        def work():
            try:
                with self.engine.lock:
                    self.engine.ensure_loaded()
            except Exception as e:  # noqa: BLE001
                self.engine.state = {"phase": "error", "error": f"{type(e).__name__}: {e}"}

        threading.Thread(target=work, daemon=True).start()
        return True

    def background(self) -> None:
        self.preload()

        def loop():
            try:
                licensing.revalidate()
            except Exception:  # noqa: BLE001
                pass
            while True:
                if time.time() - self.checked_at > config.UPDATE_CHECK_HOURS * 3600:
                    self.check_updates()
                time.sleep(600)

        threading.Thread(target=loop, daemon=True).start()


def create_app(core: Core | None = None, token: str | None = None, port: int = 0) -> FastAPI:
    core = core or Core()
    token = token or secrets.token_urlsafe(24)
    api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    api.state.core, api.state.token = core, token
    html = (config.resource_dir() / "web" / "index.html").read_text(encoding="utf-8")

    @api.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "testserver"):  # DNS-rebinding guard
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        if request.url.path.startswith("/api/") and not hmac.compare_digest(request.headers.get("x-linda-token", ""), token):
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    def err(msg: str, code: int = 400):
        return JSONResponse({"detail": msg}, status_code=code)

    @api.get("/", response_class=HTMLResponse)
    def index():
        return html.replace("__LINDA_TOKEN__", token).replace("__LINDA_VERSION__", config.APP_VERSION)

    @api.get("/api/status")
    def status():
        ready = updater.is_complete()
        return {"app_version": config.APP_VERSION, "installed_version": updater.installed_version(), "models_ready": ready,
                "license": licensing.public_state(), "update": core.update, "update_error": core.update_error,
                "download": core.job.snapshot(), "engine": core.engine.info(), "settings": load_settings(),
                "installer_job": core.installer_job, "buy": {"personal_team": config.BUY_URL_PERSONAL_TEAM, "org": config.BUY_URL_ORG, "email": config.CONTACT_EMAIL}}

    @api.post("/api/update/check")
    def check():
        core.check_updates()
        return {"update": core.update, "error": core.update_error}

    @api.post("/api/models/download")
    def download():
        if core.manifest is None:
            core.check_updates()
        if core.manifest is None:
            return err(core.update_error or "cannot reach the update server", 502)
        if core.update and core.update.get("app_required"):
            return err("this version of the app is too old for the latest models; update the app first", 409)
        if not core.job.start(core.manifest, core.manifest_raw):
            return err("a download is already running", 409)
        return {"status": "started"}

    @api.post("/api/models/cancel")
    def cancel():
        core.job.cancel()
        return {"status": "ok"}

    @api.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        content = await file.read()
        if len(content) > MAX_UPLOAD:
            return err("file is too large (max 20 MB)", 413)
        try:
            text = extract(file.filename or "file.txt", content).replace("\r\n", "\n").replace("\r", "\n").strip()
        except Exception as e:  # noqa: BLE001
            return err("could not read the file: " + (str(e) if isinstance(e, ValueError) else type(e).__name__))
        if not text:
            return err("no text could be extracted from the file")
        return {"status": "ok", "filename": file.filename or "file.txt", "text": text, "words": len(text.split()), "chars": len(text)}

    @api.post("/api/detect")
    def detect(body: dict):
        if not updater.is_complete():
            return err("model files are not installed yet", 409)
        try:
            text = str(body["text"]).replace("\r\n", "\n").replace("\r", "\n").strip()
            mode = body.get("mode", "sensitive")
            models = body.get("models")
            assert mode in ("sensitive", "precise") and (models is None or (isinstance(models, list) and all(m in ("linda_essay", "linda_multi_v2", "stylo7c") for m in models)))
        except Exception:  # noqa: BLE001
            return err("bad request")
        n = len(text.split())
        if not config.MIN_WORDS <= n <= config.MAX_WORDS:
            return err("text must be %d-%d words (now %d)" % (config.MIN_WORDS, config.MAX_WORDS, n))
        try:
            res = core.engine.run(text, mode, models)
        except Exception as e:  # noqa: BLE001
            return err(f"analysis failed: {type(e).__name__}: {e}", 500)
        return {"status": "ok", "result": res}

    @api.post("/api/license/activate")
    def lic_activate(body: dict):
        try:
            return {"license": licensing.activate(str(body.get("key", "")))}
        except licensing.LicenseError as e:
            return err(str(e), 422)

    @api.post("/api/license/remove")
    def lic_remove():
        licensing.deactivate_local()
        return {"license": licensing.public_state()}

    @api.post("/api/settings")
    def settings(body: dict):
        cur = load_settings()
        if body.get("sentences") in ("auto", "full", "windows"):
            cur["sentences"] = body["sentences"]
        if isinstance(body.get("preload"), bool):
            cur["preload"] = body["preload"]
        if body.get("device") in ("auto", "cpu", "cuda"):
            if cur.get("device") != body["device"]:
                core.engine.unload()
            cur["device"] = body["device"]
        save_settings(cur)
        if cur.get("preload", True):
            core.preload()  # switched on (or the device changed): load now
        return {"settings": cur}

    @api.post("/api/app/update")
    def app_update():
        """Download the new installer named in the signed manifest, check its hash and run it silently; the app closes."""
        ins = (core.manifest or {}).get("installer")
        if not ins or not core.update or not core.update.get("app_new"):
            return err("no application update available", 409)
        if core.installer_job["phase"] == "downloading":
            return err("already downloading", 409)

        def work():
            try:
                core.installer_job.update(phase="downloading", done=0, total=int(ins.get("size") or 0), error="")
                path = updater.download_installer(ins, lambda d, t: core.installer_job.update(done=d, total=t or core.installer_job["total"]))
                core.installer_job["phase"] = "launching"
                launch_installer(path)
                time.sleep(0.5)
                os._exit(0)
            except Exception as e:  # noqa: BLE001
                core.installer_job.update(phase="error", error=str(e))
                (config.data_dir() / "update_launch.log").write_text("error: %s: %s\n" % (type(e).__name__, e), encoding="utf-8")

        threading.Thread(target=work, daemon=True).start()
        return {"status": "started"}

    return api
