# -*- coding: utf-8 -*-
"""Entry point: starts the local server on a free 127.0.0.1 port and opens the app window (pywebview; the default browser if the
window component is missing). Only one copy runs at a time: a second start just opens the running one.

    python -m linda_desktop            # window
    python -m linda_desktop --browser  # force the browser
    python -m linda_desktop --no-ui    # server only (tests)"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

from . import config


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _single_instance() -> bool:
    if os.name != "nt" or os.environ.get("LINDA_ALLOW_MULTI"):  # LINDA_ALLOW_MULTI: tests only
        return True
    import ctypes
    import hashlib
    from ctypes import wintypes
    mutex = ctypes.windll.kernel32.CreateMutexW
    mutex.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    mutex.restype = wintypes.HANDLE
    identity = hashlib.sha256(str(config.data_dir().resolve()).lower().encode()).hexdigest()[:16]
    global _mutex_handle
    _mutex_handle = mutex(None, False, "Local\\LindaProDesktop_" + identity)
    if not _mutex_handle:
        raise ctypes.WinError()
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def _running_url() -> str | None:
    try:
        d = json.loads((config.data_dir() / "instance.json").read_text(encoding="utf-8"))
        url = f"http://127.0.0.1:{d['port']}/"
        urllib.request.urlopen(url, timeout=2).read(10)
        return url
    except Exception:  # noqa: BLE001
        return None


def main(argv: list[str] | None = None) -> int:
    worker_args = sys.argv[1:] if argv is None else argv
    if worker_args and worker_args[0]=='--document-worker':
        from .document_worker import main as document_main
        return document_main(worker_args[1:])
    # Every supported source entry point in this checkout must select Dev data.
    # Importing the runner configures paths without starting a second window.
    argv = sys.argv[1:] if argv is None else argv
    # Повторный запуск не должен заменять файлы работающей первой копии.
    if not _single_instance():
        url = _running_url()
        if url:
            webbrowser.open(url)
        return 0
    # Применение фонового обновления ДО загрузки моделей и FastAPI (как в Claude).
    try:
        from .apply_update import run_if_pending

        run_if_pending()
    except Exception:  # noqa: BLE001 — apply не должен ронять старт
        pass
    if sys.stdout is None or sys.stderr is None:  # windowed build: no console; uvicorn needs real streams, so log to a file
        log = open(config.data_dir() / "app.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    import uvicorn

    from .app import Core, create_app

    port = _free_port()
    core = Core()
    app = create_app(core)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        server.should_exit = True
        print("Linda-Pro: local server did not start", file=sys.stderr)
        return 1
    (config.data_dir() / "instance.json").write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    core.background()
    url = f"http://127.0.0.1:{port}/"
    if "--no-ui" in argv:
        print(url, flush=True)
        while True:
            time.sleep(3600)
    if "--browser" not in argv:
        try:
            import webview

            webview.settings["ALLOW_DOWNLOADS"] = True  # без этого WebView2 молча отменяет скачивание отчётов (PDF/HTML/CSV/JSON/MD)

            webview.create_window(f"{config.APP_NAME} {config.APP_VERSION}", url, width=1360, height=900, min_size=(980, 640), text_select=True)
            webview.start(private_mode=False, storage_path=str(config.data_dir() / "webview"),
                          icon=str(config.resource_dir() / "assets" / "linda-dev.ico"))
            server.should_exit = True
            return 0
        except Exception:  # noqa: BLE001
            pass
    webbrowser.open(url)
    print("Linda-Pro is running at", url, "- close this window to quit")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
