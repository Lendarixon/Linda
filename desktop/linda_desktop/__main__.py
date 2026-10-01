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

    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\LindaProDesktopSingleInstance")
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
    argv = sys.argv[1:] if argv is None else argv
    if sys.stdout is None or sys.stderr is None:  # windowed build: no console; uvicorn needs real streams, so log to a file
        log = open(config.data_dir() / "app.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    import uvicorn

    from .app import Core, create_app

    if not _single_instance():
        url = _running_url()
        if url:
            webbrowser.open(url)
        return 0
    port = _free_port()
    core = Core()
    app = create_app(core)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
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

            webview.create_window(f"Linda-Pro {config.APP_VERSION}", url, width=1360, height=900, min_size=(980, 640), text_select=True)
            webview.start(private_mode=False, storage_path=str(config.data_dir() / "webview"))
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
