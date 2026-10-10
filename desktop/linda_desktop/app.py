# -*- coding: utf-8 -*-
"""Local web backend of the desktop app (127.0.0.1 only). The UI is served from web/index.html."""
from __future__ import annotations

import hmac
import base64
import asyncio
import io
import json
import re
import os
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.concurrency import run_in_threadpool

from . import analytics, config, diagnostics, history, inbox, licensing, report, structure, updater, restart_draft, models_location
from . import i18n as ui18n
from .documents import extract
from linda_pro.voters import Cancelled
from .engine import DEFAULT_SETTINGS, Engine, load_settings, save_settings
from .engine import UI_ACCENTS, UI_DENSITIES, UI_FONT_SCALES, UI_LANGUAGES, UI_RADII, UI_SIDEBARS, UI_THEMES

MAX_UPLOAD = 20_000_000


def launch_installer(path: Path) -> None:
    """A detached helper waits for this PID to exit, installs silently, and relaunches.
    A failed installer brings the existing executable back; logs stay in the data folder."""
    if config.is_store_package():
        raise RuntimeError('Store packages are updated through Microsoft Store')
    log = config.data_dir() / "update_setup.log"
    note = config.data_dir() / "update_launch.log"
    failure = config.data_dir() / 'update_failure.json'
    lock = config.data_dir() / 'installing.lock'
    ready = path.parent / updater.INSTALLER_READY_NAME
    # Encoded PowerShell avoids cmd metacharacter expansion in paths. The helper
    # waits for the actual app PID, rather than guessing how long shutdown takes.
    literal = lambda value: "'" + str(value).replace("'", "''") + "'"
    arguments = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS', '/RELAUNCH=1', f'/LOG="{log}"']
    if os.environ.get('LINDA_DEV') == '1':
        if not config.DEV_INSTALLER_ENABLED or Path(sys.executable).name != 'Linda-Pro Dev.exe':
            raise RuntimeError('Only the packaged Dev app can install a Dev update')
        arguments.append(f'/DIR="{Path(sys.executable).parent}"')
    script = f"""$ErrorActionPreference = 'Stop'
$owner = {os.getpid()}
$note = {literal(note)}
try {{
    if (Get-Process -Id $owner -ErrorAction SilentlyContinue) {{ Wait-Process -Id $owner -Timeout 60 -ErrorAction Stop }}
    [IO.File]::WriteAllText({literal(lock)}, [string][DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
    $setup = Start-Process -FilePath {literal(path)} -ArgumentList @({','.join(literal(a) for a in arguments)}) -PassThru -WindowStyle Hidden
    $setup.WaitForExit()
    Remove-Item -LiteralPath {literal(lock)} -ErrorAction SilentlyContinue
    if ($setup.ExitCode -ne 0) {{ throw "Installer exit code $($setup.ExitCode)" }}
    Remove-Item -LiteralPath {literal(failure)} -ErrorAction SilentlyContinue
    Add-Content -LiteralPath $note -Value 'Installer finished successfully' -Encoding UTF8
}} catch {{
    $failureMessage = $_.Exception.Message
    Remove-Item -LiteralPath {literal(lock)} -ErrorAction SilentlyContinue
    Add-Content -LiteralPath $note -Value $failureMessage -Encoding UTF8
    if (Test-Path -LiteralPath {literal(ready)}) {{ Move-Item -LiteralPath {literal(ready)} -Destination {literal(path.parent / 'INSTALLER_FAILED')} -Force }}
    $failureJson = @{{version={literal(path.parent.name)};error=$failureMessage;ts=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()}} | ConvertTo-Json
    [IO.File]::WriteAllText({literal(failure)}, $failureJson, [Text.UTF8Encoding]::new($false))
    if (-not (Get-Process -Id $owner -ErrorAction SilentlyContinue)) {{ Start-Process -FilePath {literal(sys.executable)} -WindowStyle Normal }}
    exit 1
}}
"""
    cmd = ['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-EncodedCommand', base64.b64encode(script.encode('utf-16le')).decode('ascii')]
    flags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    try:
        pr = subprocess.Popen(cmd, creationflags=flags | 0x01000000, close_fds=True)  # + CREATE_BREAKAWAY_FROM_JOB
        note.write_text("started helper pid %s (breakaway)\n" % pr.pid, encoding="utf-8")
    except OSError as e:  # the job does not allow breakaway
        pr = subprocess.Popen(cmd, creationflags=flags, close_fds=True)
        note.write_text("started helper pid %s (no breakaway: %s)\n" % (pr.pid, e), encoding="utf-8")


class Core:
    """Shared state of the running app."""

    def __init__(self) -> None:
        self.engine = Engine()
        self.job = updater.Job()
        self.job.apply_lock = self.engine.lock
        self.job.before_apply = self.engine.unload
        self._auto_tried: str | None = None
        self.job.on_done = lambda m: (self.engine.unload(), self.preload())  # new weights: drop the old ones and, if enabled, load the new ones right away
        self.manifest: dict | None = None
        self.manifest_raw: bytes = b""
        self.update: dict | None = None
        self.update_error = ""
        self.checked_at = 0.0
        self.installer_job = {"phase": "idle", "done": 0, "total": 0, "error": ""}
        self.installer_cancel = threading.Event()  # отмена фоновой загрузки инсталлера (без зависаний)
        self.installer_lock = threading.Lock()
        self.settings_lock = threading.Lock()
        self.folder_lock = threading.Lock()
        self.folder_cancel = threading.Event()
        self.batch_cancel = threading.Event()
        self.checks_lock = threading.Lock()
        self.active_checks = {}  # job_id -> (client_id, cancel event)
        self.active_requests = 0
        self.first_check_pending = False
        self.preloading = False
        self.cancelled_checks = {}  # cancellation may arrive before the worker request
        self.move = models_location.MoveJob()  # moving the downloaded models to another folder
        self._preload_started = False
        self.open_allowed = set()  # paths received through the inbox that the page may open
        self.progress = {}  # job_id -> {pct, phase, ts}: progress of a running check, polled by the UI progress bar
        try:
            _ff = config.data_dir() / 'update_failure.json'
            failed = json.loads(_ff.read_text(encoding='utf-8'))
            _vt = lambda v: tuple(int(x) for x in str(v).split('.') if x.isdigit())  # noqa: E731
            if isinstance(failed, dict) and failed.get('version') and _vt(failed['version']) <= _vt(config.APP_VERSION):
                _ff.unlink()  # the failed update is already installed (or older): the old error must not be shown at every start
            elif isinstance(failed, dict) and failed.get('error'):
                self.installer_job.update(phase='error', error=str(failed['error'])[:2000])
        except (OSError, ValueError):
            pass
        try:  # порядок видеокарт в списке изменился (дискретные первыми, как в DirectML): старый номер мог указывать на встроенную графику
            _cur = load_settings()
            changed = False
            if _cur.get("gpu_map") != 2:
                _cur["gpu_map"] = 2
                changed = True
                if int(_cur.get("gpu_index", 0) or 0) != 0:
                    _cur["gpu_index"] = 0
            if not _cur.get("preload_v2"):  # 2.0.3.1: warming the models up at start is the default now (the old stored "off" was never a deliberate choice)
                _cur["preload_v2"] = True
                _cur["preload"] = True
                changed = True
            if changed:
                save_settings(_cur)
        except Exception:  # noqa: BLE001
            pass
        self.update_pending: dict | None = None  # {"version": ..., "staging": ...} — ждёт перезапуска
        try:  # инсталлер, скачанный в прошлый раз, но не установленный: баннер «Перезапустите» остаётся
            _st = updater.staged_installer()
            if _st:
                self.update_pending = {"version": _st["version"], "staging": _st["staging"]}
        except Exception:  # noqa: BLE001
            pass

    def check_updates(self) -> None:
        try:
            self.manifest, self.manifest_raw = updater.get_manifest()
            self.update = updater.update_status(self.manifest)
            self.update_error = ""
            licensing.apply_revocations(self.manifest.get("revoked", []))
        except Exception as e:  # noqa: BLE001
            self.update_error = str(e)
        self.checked_at = time.time()
        self.first_check_pending = False
        try:
            self._maybe_auto_models()
        except Exception:  # noqa: BLE001 — automatic update is best effort
            pass

    def _maybe_auto_models(self) -> None:
        """A new weights version appeared (a release with new models): download and apply it in the background, once per version, if the user did not switch it off,
        the app itself is new enough and the models disk has room. The old models stay in use until the new ones are verified; the progress shows in the banner."""
        up, m = self.update, self.manifest
        if not up or not m or not up.get("weights_update") or up.get("app_required") or not updater.is_complete():
            return
        if not load_settings().get("auto_models", True) or self.job.running() or self.move.busy() or self._auto_tried == m.get("version"):
            return
        need = float(up.get("bytes_to_download") or 0)
        if need and models_location.free_gb(Path(config.models_root())) * 2**30 < need * 1.15 + 1.5 * 2**30:
            return  # not enough room: the banner still offers the manual update with an explanation
        self._auto_tried = m.get("version")
        self.job.start(m, self.manifest_raw)

    def preload(self) -> bool:
        """Optional explicit background warmup. Default CPU loading is on demand."""
        if not load_settings().get("preload", True) or self.engine.dets is not None or not updater.is_complete():
            return False

        def work():
            t_wait = time.time()
            while self.first_check_pending and time.time() - t_wait < 25:
                time.sleep(0.5)
            try:
                pending = bool(self.manifest) and bool(updater.files_to_fetch(self.manifest))
            except Exception:
                pending = False
            if self.job.running() or pending:
                return
            self.preloading = True
            try:
                with self.engine.lock:
                    detectors = self.engine.ensure_loaded()
                    self.engine.state = {'phase':'loading','error':''}
                    self.engine._load_voters(detectors)
                    try:
                        self.engine.warm_all("en")  # routed backend: both transformer voices, so the first check is fast
                    except Exception:  # noqa: BLE001 — warm-up is best effort
                        pass
                    self.engine.state = {'phase':'ready','error':''}
            except Exception as e:  # noqa: BLE001
                self.engine.state = {"phase": "error", "error": f"{type(e).__name__}: {e}"}
            finally:
                self.preloading = False

        threading.Thread(target=work, daemon=True).start()
        return True

    def background(self) -> None:
        threading.Thread(target=self.engine.probe_gpu, daemon=True).start()
        self.first_check_pending = True
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
    cabinet = (config.resource_dir() / "web" / "cabinet.html").read_text(encoding="utf-8")  # history, batch and compare views
    html = html.replace("</body>", cabinet + "\n</body>", 1)
    metro = (config.resource_dir() / "web" / "metro-dev.css").read_text(encoding="utf-8")
    html = html.replace("</head>", "<style>" + metro + "</style></head>", 1)

    @api.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "testserver"):  # DNS-rebinding guard
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        if request.url.path.startswith("/api/") and not hmac.compare_digest(request.headers.get("x-linda-token", ""), token):
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        origin = request.headers.get("origin")
        if request.url.path.startswith("/api/") and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "forbidden"}, status_code=403)
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
        return resp

    def err(msg: str, code: int = 400):
        return JSONResponse({"detail": msg}, status_code=code)

    def terr(key: str, code: int = 400, *args):
        """Ошибка бэкенда на языке интерфейса из настроек (задача E)."""
        try:
            lang = ui18n.resolve_lang(load_settings())
        except Exception:  # noqa: BLE001
            lang = ui18n.DEFAULT_LANG
        return err(ui18n.tr(key, lang, *args), code)

    @api.get("/api/i18n/{lang}")
    def i18n_dict(lang: str):
        """Словарь интерфейса для фронта (ru/pl/en); фронт также встраивает его при сборке."""
        lang = lang if lang in ui18n.SUPPORTED else ui18n.DEFAULT_LANG
        return {"lang": lang, "strings": ui18n.load_lang(lang)}

    @api.get("/", response_class=HTMLResponse)
    def index():
        return html.replace("__LINDA_TOKEN__", token).replace("__LINDA_VERSION__", config.APP_VERSION)

    @api.get("/api/status")
    def status():
        ready = updater.is_complete()
        if ready and not core._preload_started:  # models just downloaded / applied: warm them up in the background
            core._preload_started = True
            try:
                core.preload()
            except Exception:  # noqa: BLE001
                pass
        pend = updater.pending_status()  # баннер «Перезапустите для обновления»
        rollback_msg = ""
        try:
            log = config.data_dir() / updater.ROLLBACK_LOG
            if log.is_file():
                rollback_msg = log.read_text(encoding="utf-8").strip().splitlines()[-1][:200]
        except OSError:
            pass
        try:
            chlog = report.changelog_merged(core.manifest)[:5]  # встроенный changelog для баннера/настроек
        except Exception:  # noqa: BLE001
            chlog = []
        return {"app_version": config.APP_VERSION, "installed_version": updater.installed_version(), "models_ready": ready,
                "license": licensing.public_state(), "update": core.update, "update_error": core.update_error,
                "download": core.job.snapshot(), "engine": core.engine.info(), "settings": load_settings(),
                "installer_job": core.installer_job, "pending_restart": pend, "update_pending": core.update_pending,
                "model_sets": {"selected": updater.selected_sets(), "info": updater.set_info(core.manifest or _raw_installed()), "recommend": "pro" if (core.engine.gpu or {}).get("discrete") else "lite"},
                "rollback": rollback_msg, "enterprise": config.enterprise(), "pdf_available": report.pdf_available(),
                "changelog": chlog, "models_location": models_location.info(), "models_move": dict(core.move.state),
                "buy": {"personal_team": config.BUY_URL_PERSONAL_TEAM, "org": config.BUY_URL_ORG, "email": config.CONTACT_EMAIL}}

    @api.post("/api/update/check")
    def check():
        core.check_updates()
        return {"update": core.update, "error": core.update_error}

    def _raw_installed():
        try:
            return json.loads((Path(config.models_root()) / "manifest.json").read_text(encoding="utf-8"))
        except Exception:
            return None

    @api.post("/api/models/sets")
    def models_sets(body: dict):
        """Choose which model sets this computer keeps: Linda-Pro, Linda-Pro Lite or both. Removing a set deletes its files, adding one downloads it."""
        sets = updater._valid_sets((body or {}).get("sets"))
        if not sets:
            return err("choose at least one set", 400)
        if core.job.running() or core.move.busy() or (core.engine.lock.locked() and not core.preloading) or core.folder_lock.locked():
            return terr("err_download_running", 409)
        with core.settings_lock:
            cur = load_settings()
            cur["model_sets"] = sets
            save_settings(cur)
        core.engine.unload()
        updater.remove_unselected()
        core.manifest = None
        core.check_updates()
        if core.manifest is not None and (core.update or {}).get("weights_missing"):
            core.job.start(core.manifest, core.manifest_raw)
        return {"status": "ok", "sets": sets}

    @api.post("/api/models/download")
    def download():
        if core.manifest is None:
            core.check_updates()
        if core.manifest is None:
            return err(core.update_error or ui18n.tr("err_cannot_reach", ui18n.resolve_lang(load_settings())), 502)
        if core.update and core.update.get("app_required"):
            return terr("err_app_too_old", 409)
        need = float((core.update or {}).get("bytes_to_download") or 0)
        free = models_location.free_gb(Path(config.models_root()))
        if need and free * 2**30 < need * 1.15 + 1.5 * 2**30:  # models + a safety margin + the ONNX cache
            return terr("err_no_space", 507, need * 1.15 / 2**30 + 1.5, free)
        if not core.job.start(core.manifest, core.manifest_raw):
            return terr("err_download_running", 409)
        return {"status": "started"}

    @api.post("/api/diagnostics")
    def diagnostics_zip():
        """One ZIP for the support e-mail: versions, graphics cards, settings and log tails. Texts and history are not included."""
        from fastapi.responses import Response

        root = config.data_dir()
        info = {"app_version": config.APP_VERSION, "installed_version": updater.installed_version(), "device": core.engine.device, "gpu": core.engine.gpu,
                "gpu_error": core.engine.gpu_error, "models_location": models_location.info(), "settings": load_settings(), "update_error": core.update_error,
                "log_files": [root / "app.log", root / "update_setup.log", root / "update_apply.log", root / "update_launch.log", root / "update_failure.json", Path(config.models_root()) / "update_apply.log"]}
        data = diagnostics.build_zip(info)
        return Response(content=data, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="linda-diagnostics.zip"'})

    @api.post("/api/benchmark")
    async def benchmark():
        """How fast is a check on this computer: one fixed ~300-word text through the whole ensemble (not saved to the history)."""
        if not updater.is_complete():
            return terr("err_models_not_installed", 409)
        words = ("Сегодня мы рассмотрим несколько вопросов, связанных с организацией работы небольшой команды. "
                 "Во-первых, важно заранее договориться о ролях и сроках. Во-вторых, полезно вести общий список задач. ") * 9

        def work():
            t0 = time.time()
            core.engine.run(words, "sensitive", None)
            return {"seconds": round(time.time() - t0, 2), "words": len(words.split()), "device": core.engine.device, "gpu": core.engine.gpu}

        try:
            return await run_in_threadpool(work)
        except Exception as e:  # noqa: BLE001
            return err("%s: %s" % (type(e).__name__, e), 500)

    @api.get("/api/models/location")
    def models_loc():
        return models_location.info()

    @api.post("/api/models/browse")
    async def models_browse(body: dict | None = None):
        """Native folder dialog on this computer (the page cannot open one itself)."""
        path = await run_in_threadpool(models_location.browse, str((body or {}).get("initial") or ""))
        return {"path": path}

    @api.post("/api/models/location")
    def models_set_loc(body: dict):
        """Choose where the models are kept. move=true copies the already downloaded models there first (progress in /api/status models_move)."""
        lang = ui18n.resolve_lang(load_settings())
        if core.job.snapshot().get("phase") in ("checking", "downloading", "verifying", "applying", "finishing") or core.move.busy():
            return terr("err_download_running", 409)
        raw = str(body.get("path") or "").strip()
        new = Path(raw) if raw else Path(config.data_dir())  # empty = back to the default folder
        old = Path(config.models_root())
        if new.resolve() == old.resolve():
            return models_location.info()
        ok, key = models_location.validate(str(new))
        if not ok:
            return err(ui18n.tr(key, lang), 400)
        if body.get("move") and models_location.info()["has_models"]:
            core.move.start(old, new, before=core.engine.unload)
            return {"status": "moving"}
        config.set_models_root(new)
        core.engine.unload()
        core.manifest = None
        core.update = None
        try:
            core.check_updates()
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", **models_location.info()}

    @api.post("/api/models/cancel")
    def cancel():
        core.job.cancel()
        return {"status": "ok"}

    @api.post("/api/upload")
    async def upload(file: UploadFile = File(...)):
        with core.checks_lock:
            if core.installer_job['phase'] == 'launching':
                return err('The application is restarting; wait for the new window.', 409)
            core.active_requests += 1
        try:
            return await _upload(file)
        finally:
            with core.checks_lock:
                core.active_requests -= 1

    async def _upload(file):
        content = await file.read(MAX_UPLOAD + 1)
        return await _extract_payload(file.filename or "file.txt", content)

    async def _extract_payload(filename, content):
        if len(content) > MAX_UPLOAD:
            return terr("err_file_too_large", 413)
        try:
            text = (await run_in_threadpool(extract, filename, content)).replace("\r\n", "\n").replace("\r", "\n").strip()
        except Exception as e:  # noqa: BLE001
            lang = ui18n.resolve_lang(load_settings())
            base = ui18n.tr("err_could_not_read", lang)
            if isinstance(e, ValueError) and str(e) == "not a text file":
                return err(ui18n.tr("err_not_text", lang), 400)
            if isinstance(e, ValueError) and str(e).startswith("Supported formats"):
                return err(base + ": " + ui18n.tr("err_format", lang), 400)
            # не показываем имена внутренних исключений (BadZipFile, KeyError, PdfReadError): понятная причина вместо них
            msg = str(e)
            internal = not isinstance(e, ValueError) or re.fullmatch(r"[A-Za-z_.]*(Error|File|Exception|Warning)", msg) is not None  # BadZipFile, PdfReadError, KeyError...
            return err(base + ": " + (ui18n.tr("err_file_corrupt", lang) if internal else msg))
        if not text:
            return terr("err_no_text")
        return {"status": "ok", "filename": filename, "text": text, "words": len(text.split()), "chars": len(text)}

    @api.get("/api/inbox")
    def inbox_take():
        """Files sent by 'Check in Linda-Pro' (Explorer menu / second start). Returned once; only these paths may be opened by /api/open_path."""
        out = []
        for p in inbox.take():
            core.open_allowed.add(p)
            out.append({"path": p, "name": Path(p).name})
        return {"files": out}

    @api.post("/api/open_path")
    async def open_path(body: dict):
        p = str(body.get("path") or "")
        if p not in core.open_allowed:
            return terr("err_bad_request", 403)
        core.open_allowed.discard(p)
        try:
            content = await run_in_threadpool(Path(p).read_bytes)
        except OSError:
            return terr("err_could_not_read", 400)
        return await _extract_payload(Path(p).name, content)

    @api.get("/api/progress/{job_id}")
    def check_progress(job_id: str):
        """Progress of a running check (job_id is the id the page sent with /api/detect)."""
        if not valid_id(job_id):
            return terr('err_bad_request', 400)
        return core.progress.get(job_id) or {"pct": 0, "phase": "wait"}

    @api.post("/api/detect/cancel")
    def detect_cancel(body: dict | None = None):
        """Отмена идущей проверки из окна одного текста (вставили новый текст, прикрепили файл)."""
        job_id = (body or {}).get('job_id')
        if job_id is not None and not valid_id(job_id):
            return terr('err_bad_request', 400)
        with core.checks_lock:
            count = 0
            if job_id:
                now = time.monotonic()
                core.cancelled_checks = {k: v for k, v in core.cancelled_checks.items() if now - v < 300}
                if len(core.cancelled_checks) >= 1000:
                    core.cancelled_checks.pop(next(iter(core.cancelled_checks)))
                core.cancelled_checks[job_id] = now
            for key, (_, event) in core.active_checks.items():
                if (not job_id or key == job_id) and not event.is_set():
                    event.set()
                    count += 1
        if not job_id:
            count += core.engine.cancel_cancellable()
        return {"status": "ok", "cancelled": count}

    def valid_id(value):
        return isinstance(value, str) and 1 <= len(value) <= 64 and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in value)

    @api.post('/api/batch/start')
    def batch_start():
        core.batch_cancel.clear()
        return {'status': 'ok'}

    @api.post('/api/batch/cancel')
    def batch_cancel():
        core.batch_cancel.set()
        return {'status': 'ok'}

    @api.post("/api/detect")
    async def detect(body: dict, request: Request):
        cancel = core.batch_cancel if body.get('batch') else threading.Event()
        job_id, client_id = body.get('job_id'), body.get('client_id')
        tracked = not body.get('batch') and job_id is not None
        if tracked and (not valid_id(job_id) or not valid_id(client_id)):
            return terr('err_bad_request', 400)
        with core.checks_lock:
            if core.installer_job['phase'] == 'launching':
                return err('The application is restarting; wait for the new window.', 409)
            if tracked:
                if job_id in core.active_checks:
                    return err('duplicate analysis request', 409)
                if body.get('supersede'):
                    for owner, event in core.active_checks.values():
                        if owner == client_id:
                            event.set()
                if job_id in core.cancelled_checks:
                    cancel.set()
                core.active_checks[job_id] = (client_id, cancel)
            core.active_requests += 1
        work = asyncio.create_task(run_in_threadpool(_detect, body, cancel))
        try:
            while not work.done():
                await asyncio.wait({work}, timeout=0.1)
                if not work.done() and await request.is_disconnected():
                    cancel.set()
            return await work
        except asyncio.CancelledError:
            cancel.set()
            raise
        finally:
            with core.checks_lock:
                core.active_requests -= 1
                if tracked:
                    core.active_checks.pop(job_id, None)

    def _detect(body: dict, cancel: threading.Event):
        if cancel.is_set():
            return err('cancelled', 409)
        if not updater.is_complete():
            return terr("err_models_not_installed", 409)
        try:
            text = str(body["text"]).replace("\r\n", "\n").replace("\r", "\n").strip()
            mode = body.get("mode", "sensitive")
            models = body.get("models")
            if mode not in ("sensitive", "precise") or not (models is None or (isinstance(models, list) and all(m in ("linda_essay", "linda_multi_v2", "stylo7c") for m in models))):
                raise ValueError('invalid mode or model')
        except Exception:  # noqa: BLE001
            return terr("err_bad_request")
        if mode == 'precise' and models and len(set(models)) < 3:
            return terr("err_precise_requires_ensemble", 400)
        letters = [c for c in text if c.isalpha()]
        if len(letters) >= 20:
            known = sum(1 for c in letters if c.isascii() or "À" <= c <= "ſ" or "Ѐ" <= c <= "ӿ")
            if known / len(letters) < 0.5:  # арабский, китайский, греческий...: модели не знают этих языков, честный вердикт невозможен
                return terr("err_lang_unsupported", 400)
        n = len(text.split())
        if n < config.MIN_WORDS or (config.MAX_WORDS and n > config.MAX_WORDS):
            return terr("err_text_min", 400, config.MIN_WORDS, n)
        pol = config.enterprise()
        if pol.get("require_license") and not licensing.public_state()["licensed"]:
            return terr("err_license_required", 403)
        sup = bool(body.get("supersede"))  # проверка из окна одного текста: прежняя неоконченная отменяется
        if sup and not body.get('job_id'):
            core.engine.cancel_cancellable()
        try:
            jid = body.get('job_id') if valid_id(body.get('job_id')) else (body.get('progress_id') if valid_id(body.get('progress_id')) else None)

            def report(pct, phase):
                if jid:
                    core.progress[jid] = {"pct": round(pct, 1), "phase": phase, "ts": time.monotonic()}
                    if len(core.progress) > 200:  # stale entries of abandoned jobs
                        for k in sorted(core.progress, key=lambda k: core.progress[k]["ts"])[:100]:
                            core.progress.pop(k, None)

            try:
                try:
                    res = core.engine.run(text, mode, models, cancellable=sup, cancel=cancel, progress=report)
                except TypeError as e:  # an engine without progress support (tests, custom engines)
                    if 'progress' not in str(e):
                        raise
                    res = core.engine.run(text, mode, models, cancellable=sup, cancel=cancel)
            finally:
                if jid:
                    core.progress.pop(jid, None)
            if cancel.is_set():
                raise Cancelled()
        except Cancelled:
            return err("cancelled", 409)
        except Exception as e:  # noqa: BLE001
            base = ui18n.tr("err_analysis_failed", ui18n.resolve_lang(load_settings()))
            return err("%s: %s: %s" % (base, type(e).__name__, e), 500)
        hid = None
        if not pol.get("disable_history") and load_settings().get("save_history", True) and body.get("save", True):
            try:
                hid = history.add(text, res, mode, title=str(body.get("title") or "")[:200] or None, filename=str(body.get("filename") or "")[:200] or None,
                                  folder_id=int(body["folder_id"]) if str(body.get("folder_id") or "").isdigit() else None)
            except Exception:  # noqa: BLE001  # a history problem must never lose the result
                hid = None
        try:
            history.audit("detect", "слов: %d, вердикт: %s%s" % (n, (res or {}).get("verdict"), " (не сохранено)" if hid is None else ""))
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", "result": res, "history_id": hid}

    # ---- local history ("cabinet"), batch results are saved through /api/detect ----
    @api.get("/api/history")
    def hist_list(q: str = "", verdict: str = "", limit: int = 200, offset: int = 0, folder: str = "", sort: str = "date", order: str = "desc"):
        days = int(load_settings().get("history_retention_days", 0) or 0)
        fo = int(folder) if folder.isdigit() else None  # "" = all, "0" = not in a folder
        return history.list_snapshot(q, verdict, min(max(limit, 1), 1000), max(offset, 0), fo, sort, order, days)

    @api.post("/api/history/folders")
    def folder_add(body: dict):
        return {"id": history.folder_add(str(body.get("name", "")), body.get("color"))}

    @api.patch("/api/history/folders/{folder_id}")
    def folder_update(folder_id: int, body: dict):
        return {"status": "ok"} if history.folder_update(folder_id, body.get("name"), body.get("color")) else terr("err_not_found", 404)

    @api.delete("/api/history/folders/{folder_id}")
    def folder_delete(folder_id: int, with_checks: bool = False):
        return {"status": "ok", "deleted": history.folder_delete(folder_id, with_checks)}

    @api.post("/api/history/move")
    def hist_move(body: dict):
        try:
            ids = [int(i) for i in body["ids"]]
            fid = int(body["folder_id"]) if body.get("folder_id") else None
        except Exception:  # noqa: BLE001
            return terr("err_bad_request")
        return {"moved": history.move(ids, fid)}

    @api.post("/api/history/delete")
    def hist_delete_many(body: dict):
        try:
            n = history.delete_many([int(i) for i in body["ids"]])
            try:
                history.audit("history_delete", "удалено проверок: %d" % n)
            except Exception:  # noqa: BLE001
                pass
            return {"deleted": n}
        except Exception:  # noqa: BLE001
            return terr("err_bad_request")

    @api.get("/api/structure/{check_id}")
    def hist_structure(check_id: int):
        c = history.get(check_id)
        return structure.profile(c["text"], c["result"].get("sentences")) if c else terr("err_not_found", 404)

    @api.post("/api/structure")
    def text_structure(body: dict):
        sents = body.get("sentences") if isinstance(body.get("sentences"), list) else None
        return structure.profile(str(body.get("text", "")), sents)

    @api.get("/api/history/{check_id}")
    def hist_get(check_id: int):
        c = history.get(check_id)
        return c if c else terr("err_not_found", 404)

    @api.patch("/api/history/{check_id}")
    def hist_rename(check_id: int, body: dict):
        return {"status": "ok"} if history.rename(check_id, str(body.get("title", ""))) else terr("err_not_found", 404)

    @api.delete("/api/history/{check_id}")
    def hist_delete(check_id: int):
        return {"status": "ok"} if history.delete(check_id) else terr("err_not_found", 404)

    @api.delete("/api/history")
    def hist_clear():
        n = history.clear()
        try:
            history.audit("history_clear", "вся история удалена (%d)" % n)
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", "deleted": n}

    @api.get("/api/analytics/{check_id}")
    def hist_analytics(check_id: int):
        c = history.get(check_id)
        return analytics.analyze(c["text"], c["result"].get("sentences")) if c else terr("err_not_found", 404)

    @api.post("/api/analytics")
    def text_analytics(body: dict):
        return analytics.analyze(str(body.get("text", "")), body.get("sentences") if isinstance(body.get("sentences"), list) else None)

    def _report_lang() -> str:
        """Язык отчёта = язык интерфейса из настроек."""
        try:
            return ui18n.resolve_lang(load_settings())
        except Exception:  # noqa: BLE001
            return ui18n.DEFAULT_LANG

    def _serve_report(rep: dict, fmt: str):
        """Отдать готовый отчёт в нужном формате (html — печатный, pdf — только если есть fpdf)."""
        fmt = (fmt or "json").lower()
        base = "linda_report_%s" % (rep.get("id") or "text")
        if fmt == "html":
            return HTMLResponse(report.to_html(rep, _report_lang()))
        if fmt == "csv":
            return PlainTextResponse(report.to_csv(rep), media_type="text/csv; charset=utf-8",
                                     headers={"Content-Disposition": 'attachment; filename="%s.csv"' % base})
        if fmt == "pdf_short":
            if not report.pdf_available():
                return terr("err_no_pdf", 501)
            from . import report_short

            try:
                data = report_short.to_short_pdf_bytes(rep, ui18n.resolve_lang(load_settings()))
            except RuntimeError as e:
                return err(str(e), 501)
            return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="%s_short.pdf"' % base})
        if fmt == "pdf":
            if not report.pdf_available():
                return terr("err_no_pdf", 501)
            try:
                try:
                    _lang = ui18n.resolve_lang(load_settings())
                except Exception:  # noqa: BLE001
                    _lang = ui18n.DEFAULT_LANG
                data, renderer = report.pdf_export(rep, _lang)
            except RuntimeError as e:
                return err(str(e), 501)
            return Response(data, media_type="application/pdf",
                            headers={"Content-Disposition": 'attachment; filename="%s.pdf"' % base,
                                     'X-Linda-PDF-Renderer': renderer})
        return rep

    @api.get("/api/report/{check_id}")
    def report_saved(check_id: int, fmt: str = "json"):
        """Экспорт отчёта по сохранённой проверке: fmt=html|json|csv|pdf (для корпоративных клиентов)."""
        if config.enterprise().get("disable_export"):
            return terr("err_export_disabled", 403)
        c = history.get(check_id)
        if not c:
            return terr("err_not_found", 404)
        try:
            history.audit("report_export", "проверка №%s, формат: %s" % (check_id, fmt))
        except Exception:  # noqa: BLE001
            pass
        return _serve_report(report.report_for_check(c), fmt)

    @api.post("/api/report")
    def report_adhoc(body: dict, fmt: str = "json"):
        """Отчёт по несохранённому результату: {check_id} или {text, result, title, mode}."""
        if config.enterprise().get("disable_export"):
            return terr("err_export_disabled", 403)
        fmt = (body.get("fmt") or fmt or "json").lower()
        try:
            if body.get("check_id") is not None:
                c = history.get(int(body["check_id"]))
                if not c:
                    return terr("err_not_found", 404)
                rep = report.report_for_check(c)
            else:
                text = str(body.get("text", "")).strip()
                res = body.get("result")
                if not text or not isinstance(res, dict) or not res.get("verdict"):
                    return terr("err_need_check_or_text", 400)
                rep = report.build_report(text, res, {"title": str(body.get("title", ""))[:200], "mode": str(body.get("mode", ""))[:20]})
        except (ValueError, TypeError):
            return terr("err_bad_request", 400)
        try:
            history.audit("report_export", "разовый отчёт, формат: %s" % fmt)
        except Exception:  # noqa: BLE001
            pass
        return _serve_report(rep, fmt)

    @api.get("/api/changelog")
    def changelog():
        """Встроенный changelog: локальный CHANGELOG.json + записи манифеста обновлений."""
        return {"app_version": config.APP_VERSION, "items": report.changelog_merged(core.manifest)}

    @api.get("/api/enterprise")
    def enterprise_policies():
        """Корпоративные политики из enterprise.json и доступность PDF-экспорта."""
        return {"policies": config.enterprise(), "pdf_available": report.pdf_available()}

    @api.get("/api/audit")
    def audit_list(action: str = "", limit: int = 200, offset: int = 0):
        """Журнал аудита (локально): новые события первыми."""
        from . import secure_audit
        days = config.enterprise().get("audit_retention_days", 0) or 0
        try:
            history._migrate_audit()
            secure_audit.retention(days)
            return {"items": history.audit_list(action, limit, offset),
                    "integrity": secure_audit.integrity_info()}
        except secure_audit.AuditIntegrityError:
            return err('Audit integrity verification failed. The journal has not been reset.',409)

    @api.delete("/api/audit")
    def audit_delete():
        """Protected journal has no manual clearing endpoint."""
        return err('The protected audit journal cannot be cleared from the application.',403)

    @api.post("/api/batch_folder")
    def batch_folder(body: dict):
        with core.checks_lock:
            if core.installer_job['phase'] == 'launching':
                return err('The application is restarting; wait for the new window.', 409)
            if not core.folder_lock.acquire(blocking=False):
                return err('a folder check is already running',409)
        core.folder_cancel.clear()
        try:
            return _batch_folder(body)
        finally:
            core.folder_lock.release()

    @api.post('/api/batch_folder/cancel')
    def batch_folder_cancel():
        core.folder_cancel.set()
        return {'status':'ok'}

    def _batch_folder(body: dict):
        """Пакетная проверка папки (рекурсивно): .txt/.md/.docx/.pdf, каждая — через движок, в историю."""
        if not updater.is_complete():
            return terr("err_models_not_installed", 409)
        try:
            folder = str(body.get("path", "")).strip().strip('"')
            mode = body.get("mode", "sensitive")
            assert mode in ("sensitive", "precise") and folder
        except Exception:  # noqa: BLE001
            return terr("err_need_folder", 400)
        if not config.enterprise_allows_path(folder):
            return terr("err_folder_not_allowed", 403)
        root = Path(folder)
        if not root.is_dir():
            return terr("err_folder_not_found", 404)
        pol = config.enterprise()
        exts = {".txt", ".md", ".text", ".docx", ".pdf"}
        if pol.get('require_license') and not licensing.public_state()['licensed']:
            return terr('err_license_required',403)
        try:
            files = []
            for p in root.rglob('*'):
                if core.folder_cancel.is_set():
                    break
                if p.is_file() and p.suffix.lower() in exts and config.enterprise_allows_path(str(p)):
                    files.append(p)
                    if len(files) >= int(pol.get('max_batch_files',200)):
                        break
            files.sort()
        except OSError as e:
            base = ui18n.tr("err_cannot_read_folder", ui18n.resolve_lang(load_settings()))
            return err("%s: %s" % (base, e), 400)
        try:
            folder_id = int(body["folder_id"]) if str(body.get("folder_id") or "").isdigit() else None
        except Exception:  # noqa: BLE001
            folder_id = None
        items, done, errors = [], 0, 0
        for p in files:
            if core.folder_cancel.is_set():
                break
            row: dict = {"file": str(p), "name": p.name}
            try:
                with p.open('rb') as document:
                    data = document.read(MAX_UPLOAD+1)
                if len(data) > MAX_UPLOAD:
                    row.update(status="skipped", error="file is too large (max 20 MB)")
                    items.append(row)
                    continue
                text = extract(p.name, data).replace("\r\n", "\n").replace("\r", "\n").strip()
                n = len(text.split())
                if not text or n < config.MIN_WORDS or (config.MAX_WORDS and n > config.MAX_WORDS):
                    row.update(status="skipped", words=n, error="need at least %d words (now %d)" % (config.MIN_WORDS, n))
                    items.append(row)
                    continue
                res = core.engine.run(text, mode, None, cancel=core.folder_cancel)
                hid = None
                if not pol.get("disable_history") and load_settings().get('save_history', True):
                    try:
                        hid = history.add(text, res, mode, title=p.name[:200], filename=p.name[:200], folder_id=folder_id)
                    except Exception:  # noqa: BLE001
                        hid = None
                row.update(status="ok", words=n, verdict=res.get("verdict"), history_id=hid)
                done += 1
            except Cancelled:
                row.update(status="cancelled")
                items.append(row)
                break
            except Exception as e:  # noqa: BLE001 — один битый файл не останавливает папку
                row.update(status="error", error="%s: %s" % (type(e).__name__, str(e)[:200]))
                errors += 1
            items.append(row)
        try:
            history.audit("batch_folder", "папка: %s, файлов: %d, ok: %d, ошибок: %d" % (folder, len(items), done, errors))
        except Exception:  # noqa: BLE001
            pass
        return {"status": "cancelled" if core.folder_cancel.is_set() else "ok", "folder": str(root), "files": len(items), "done": done, "errors": errors, "items": items}

    @api.post("/api/compare/matrix")
    def compare_matrix(body: dict):
        """Compare any number of saved checks at once: pairwise overlap matrix plus the most similar pairs."""
        try:
            ids = [int(x) for x in body["ids"]][:60]
        except Exception:  # noqa: BLE001
            return terr("err_bad_request")
        checks = history.get_many(ids)
        checks = [c for c in checks if c]
        if len(checks) < 2:
            return terr("err_pick_two", 400)
        m = analytics.similarity_matrix([c["text"] for c in checks])
        pairs = sorted(({"a": checks[i]["id"], "b": checks[j]["id"], "overlap": m[i][j]} for i in range(len(checks)) for j in range(i + 1, len(checks))), key=lambda x: -x["overlap"])
        items = [{"id": c["id"], "title": c["title"], "verdict": c["result"].get("verdict"), "authorship": (c["result"].get("authorship") or {}).get("label"),
                  "words": c["words"], "ai_share": c.get("ai_share")} for c in checks]
        return {"items": items, "matrix": m, "pairs": pairs[:40]}

    @api.post("/api/compare")
    def compare(body: dict):
        try:
            a, b = history.get(int(body["a"])), history.get(int(body["b"]))
        except Exception:  # noqa: BLE001
            return terr("err_bad_request")
        if not a or not b:
            return terr("err_check_not_found", 404)
        return history.compare(a, b)

    @api.post("/api/license/activate")
    def lic_activate(body: dict):
        try:
            st = licensing.activate(str(body.get("key", "")))
            try:
                history.audit("license_activate", "ключ: %s" % st.get("key_hint", ""))
            except Exception:  # noqa: BLE001
                pass
            return {"license": st}
        except licensing.LicenseError as e:
            return err(str(e), 422)

    @api.post("/api/license/remove")
    def lic_remove():
        licensing.deactivate_local()
        try:
            history.audit("license_remove", "ключ удалён с этого компьютера")
        except Exception:  # noqa: BLE001
            pass
        return {"license": licensing.public_state()}

    @api.post("/api/settings")
    def settings(body: dict):
        with core.settings_lock:
            return _settings(body)

    def _settings(body: dict):
        cur = load_settings()
        need_reload = False  # смена устройства/карты требует выгрузки движка — тяжёлая операция, уходит в фон
        if body.get("sentences") in ("auto", "hybrid", "context", "smooth", "full", "windows"):
            cur["sentences"] = body["sentences"]
        if isinstance(body.get("history_retention_days"), int) and not isinstance(body.get("history_retention_days"), bool) and 0 <= body["history_retention_days"] <= 3650:
            cur["history_retention_days"] = body["history_retention_days"]
        if isinstance(body.get("save_history"), bool):
            cur["save_history"] = body["save_history"]
        if isinstance(body.get("preload"), bool):
            cur["preload"] = body["preload"]
        if isinstance(body.get("gpu_index"), int) and not isinstance(body.get("gpu_index"), bool) and 0 <= body["gpu_index"] <= 7:
            if cur.get("gpu_index", 0) != body["gpu_index"]:
                need_reload = True
            cur["gpu_index"] = body["gpu_index"]
        if body.get("quality") in ("auto", "pro", "lite", "full", "speed", "both"):
            if cur.get("quality", "auto") != body["quality"]:
                need_reload = True
            cur["quality"] = body["quality"]
        if body.get("device") in ("auto", "cpu", "cuda"):
            if cur.get("device") != body["device"]:
                need_reload = True
            cur["device"] = body["device"]
        # Персонализация интерфейса (задача D) + язык (задача E): только локально, дефолты в load_settings()
        if body.get("theme") in UI_THEMES:
            cur["theme"] = body["theme"]
        if body.get("accent") in UI_ACCENTS:
            cur["accent"] = body["accent"]
        if body.get("density") in UI_DENSITIES:
            cur["density"] = body["density"]
        if body.get("font_scale") in UI_FONT_SCALES:
            cur["font_scale"] = body["font_scale"]
        if isinstance(body.get("font_scale"), str) and body["font_scale"].isdigit() and int(body["font_scale"]) in UI_FONT_SCALES:
            cur["font_scale"] = int(body["font_scale"])
        if body.get("radius") in UI_RADII:
            cur["radius"] = body["radius"]
        if body.get("sidebar") in UI_SIDEBARS:
            cur["sidebar"] = body["sidebar"]
        if body.get("language") in UI_LANGUAGES:
            cur["language"] = body["language"]
        if body.get("ui_mode") in ("simple", "expert"):
            cur["ui_mode"] = body["ui_mode"]
        if isinstance(body.get("auto_models"), bool):
            cur["auto_models"] = body["auto_models"]
        if isinstance(body.get("tour_done"), bool):
            cur["tour_done"] = body["tour_done"]
        save_settings(cur)
        # Тяжёлое (выгрузка движка, загрузка моделей) — в фоне, ответ сразу; прогресс виден через /api/status (dev_loading)
        preload_on = isinstance(body.get("preload"), bool) and bool(body["preload"])
        if need_reload or preload_on:
            def _bg():
                try:
                    if need_reload:
                        core.engine.unload()
                    core.preload()  # switched on (or the device changed): load now, in a thread
                except Exception:  # noqa: BLE001
                    pass
            threading.Thread(target=_bg, daemon=True).start()
            return {"settings": cur, "reloading": True}
        return {"settings": cur, "reloading": False}

    @api.post("/api/app/update")
    def app_update():
        """Фоновая загрузка инсталлера в staging (проверка хеша). Инсталлер сразу не запускается:
        ставится update_pending, UI показывает баннер «Перезапустите для обновления»."""
        if config.is_store_package():
            return err('Application updates are managed by Microsoft Store.',409)
        ins = (core.manifest or {}).get("installer")
        if not ins or not core.update or not core.update.get("app_new"):
            return terr("err_no_update", 409)
        with core.installer_lock:
            if core.installer_job["phase"] in ("downloading", "launching"):
                return terr("err_already_downloading", 409)
            st = updater.staged_installer()
            if st and st["version"] == str(ins.get("version", "")):
                try:
                    updater.verify_staged_installer(st)
                except updater.UpdateError:
                    st = None
                if st:
                    core.update_pending = {"version": st["version"], "staging": st["staging"]}
                    core.installer_job.update(phase="pending")
                    return {"status": "pending", "action": "restart", "version": st["version"]}
            core.installer_cancel.clear()
            core.installer_job.update(phase="downloading", done=0, total=int(ins.get("size") or 0), error="")
            manifest_raw, signature = core.manifest_raw, core.manifest.get('_signature')

        def work():
            try:
                path = updater.download_installer(ins, lambda d, t: core.installer_job.update(done=d, total=t or core.installer_job["total"]),
                                                  cancel=core.installer_cancel, version=str(ins.get("version", "")), manifest_raw=manifest_raw, signature=signature)
                core.installer_job.update(phase="pending", done=int(ins.get("size") or 0))
                core.update_pending = {"version": str(ins.get("version", "")), "staging": str(path.parent)}
                (config.data_dir() / "update_launch.log").write_text("staged %s, ждёт перезапуска\n" % path, encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                if type(e).__name__ == "_Cancelled":
                    core.installer_job.update(phase="cancelled", error="загрузка отменена")
                else:
                    core.installer_job.update(phase="error", error=str(e))
                    (config.data_dir() / "update_launch.log").write_text("error: %s: %s\n" % (type(e).__name__, e), encoding="utf-8")

        threading.Thread(target=work, daemon=True).start()
        return {"status": "started"}

    @api.post("/api/app/restart")
    def app_restart(body: dict | None = None):
        """Перезапуск с установкой: запускает скачанный инсталлер (он сам закроет и заново откроет приложение) и завершает процесс."""
        if config.is_store_package():
            return err('Application updates are managed by Microsoft Store.',409)
        if os.environ.get("LINDA_DEV") == "1" and not config.DEV_INSTALLER_ENABLED:
            return err("Dev: production installers are disabled; use the isolated update tests.", 409)
        if core.job.running():
            return terr('err_download_running',409)
        if (core.engine.lock.locked() and not core.preloading) or core.folder_lock.locked():
            return err('Finish or cancel the active analysis before restarting.', 409)
        st = updater.staged_installer()
        if not st:
            return terr("err_no_update", 409)

        def go():
            try:
                time.sleep(0.6)  # дать UI получить ответ
                updater.verify_staged_installer(st)
                launch_installer(Path(st["path"]))
                time.sleep(0.5)
                os._exit(0)
            except Exception as e:
                core.installer_job.update(phase="error", error=str(e))

        with core.installer_lock:
            if core.installer_job["phase"] in ("launching", "downloading"):
                return terr("err_already_downloading", 409)
            with core.checks_lock:
                if core.active_requests or (core.engine.lock.locked() and not core.preloading) or core.folder_lock.locked():
                    return err('Finish or cancel the active operation before restarting.', 409)
                if body is not None and 'draft' in body:
                    try:
                        restart_draft.save(body['draft'])
                    except (OSError, ValueError) as error:
                        return err(str(error), 403 if isinstance(error, PermissionError) else 400)
                core.installer_job.update(phase="launching", error="")
        threading.Thread(target=go, daemon=True).start()
        return {"status": "restarting", "version": st["version"]}

    @api.post("/api/models/restart")
    def models_restart(body: dict | None = None):
        """Перезапуск приложения для применения скачанных весов (staging/<версия>/READY применяется при старте). Установщик не нужен."""
        if config.is_store_package() or not getattr(sys, "frozen", False):
            return err("Restart is available in the installed application only.", 409)
        if not updater.pending_status():
            return terr("err_no_update", 409)
        if core.job.running():
            return terr('err_download_running', 409)
        with core.checks_lock:
            if core.active_requests or (core.engine.lock.locked() and not core.preloading) or core.folder_lock.locked():
                return err('Finish or cancel the active operation before restarting.', 409)
            if body is not None and 'draft' in body:
                try:
                    restart_draft.save(body['draft'])
                except (OSError, ValueError) as error:
                    return err(str(error), 403 if isinstance(error, PermissionError) else 400)
        exe = sys.executable
        pid = os.getpid()

        def go():
            time.sleep(0.6)  # let the UI receive the answer
            literal = lambda value: "'" + str(value).replace("'", "''") + "'"  # noqa: E731
            script = (f"$p = {pid}; if (Get-Process -Id $p -ErrorAction SilentlyContinue) {{ Wait-Process -Id $p -Timeout 60 -ErrorAction SilentlyContinue }}; "
                      f"Start-Process -FilePath {literal(exe)}")
            encoded = base64.b64encode(script.encode("utf-16-le")).decode()
            ps = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            try:
                subprocess.Popen([str(ps), "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
                                 creationflags=0x08000000 | 0x00000200, close_fds=True)
            except OSError:
                return  # could not schedule the relaunch: stay open rather than closing the app for good
            time.sleep(0.5)
            os._exit(0)

        threading.Thread(target=go, daemon=True).start()
        return {"status": "restarting"}

    @api.get('/api/draft/resume')
    def resume_draft():
        return {'draft':restart_draft.read()}

    draft_revisions = {}
    @api.post('/api/draft/save')
    def save_session_draft(body: dict):
        client, revision = body.get('client_id'), body.get('revision')
        if not isinstance(client,str) or not 1 <= len(client) <= 80 or type(revision) is not int or revision < 0:
            return err('Invalid draft revision.',400)
        with core.settings_lock:
            if revision <= draft_revisions.get(client,-1):
                return {'status':'stale'}
            try:
                restart_draft.save(body.get('text'))
            except PermissionError as exc:
                return err(str(exc),403)
            except ValueError as exc:
                return err(str(exc),400)
            if len(draft_revisions) >= 128 and client not in draft_revisions:
                draft_revisions.pop(next(iter(draft_revisions)))
            draft_revisions[client] = revision
            return {'status':'ok'}

    @api.post('/api/draft/ack')
    def acknowledge_draft(body: dict):
        restored = restart_draft.acknowledge(body.get('id'))
        if restored:
            history.audit('draft_restore', str(body.get('id'))[:64])
        return {'status':'ok','restored':restored}

    @api.post("/api/app/cancel")
    def app_cancel():
        """Отмена фоновой загрузки инсталлера (без зависаний)."""
        core.installer_cancel.set()
        return {"status": "ok"}

    return api
