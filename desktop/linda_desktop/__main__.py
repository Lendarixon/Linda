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


def _take_over_stale() -> bool:
    """The copy that holds the mutex is older than this one (left over from before an update) or has lost its window (hung after the window was closed):
    end it, so that the new launch does not just open the old copy's page in a browser or do nothing."""
    if os.name != "nt":
        return False
    try:
        d = json.loads((config.data_dir() / "instance.json").read_text(encoding="utf-8"))
        pid = int(d.get("pid") or 0)
    except Exception:
        return False
    if not pid or pid == os.getpid():
        return False
    stale = d.get("version") != config.APP_VERSION
    if not stale and d.get("mode") == "window" and not _focus_window():
        stale = True
    if not stale:
        return False
    import ctypes
    import subprocess
    # Завершаем устаревший экземпляр.
    subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True, timeout=20, creationflags=134217728)
    time.sleep(1.0)
    try:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
    except Exception:
        pass
    for _ in range(25):
        if _single_instance():
            return True
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        time.sleep(0.4)
    return False


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


def _focus_window() -> bool:
    """Повторный запуск: вывести окно работающей копии на передний план. False — окна нет (режим браузера)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        pid = json.loads((config.data_dir() / "instance.json").read_text(encoding="utf-8")).get("pid")
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _):
            p = wintypes.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and u.IsWindowVisible(h) and u.GetWindowTextLengthW(h) > 0:
                buf = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(h, buf, 256)
                if buf.value.startswith(config.APP_NAME):
                    found.append(h)
            return True

        u.EnumWindows(cb, 0)
        if not found:
            return False
        if u.IsIconic(found[0]):
            u.ShowWindow(found[0], 9)
        u.SetForegroundWindow(found[0])
        return True
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    worker_args = sys.argv[1:] if argv is None else argv
    if worker_args and worker_args[0]=='--document-worker':
        from .document_worker import main as document_main
        return document_main(worker_args[1:])
    # Every supported source entry point in this checkout must select Dev data.
    # Importing the runner configures paths without starting a second window.
    if config.APP_NAME != 'Linda-Pro Dev' and not config.is_store_package() and (config.resource_dir() / 'run_dev.py').is_file():
        import run_dev  # noqa: F401
    argv = sys.argv[1:] if argv is None else argv
    def _file_arg() -> str | None:
        for a in argv:
            if not a.startswith("-") and os.path.splitext(a)[1].lower() in (".docx", ".pdf", ".txt", ".md") and os.path.isfile(a):
                return a
        return None

    # Повторный запуск не должен заменять файлы работающей первой копии.
    try:
        lk = config.data_dir() / "installing.lock"
        if lk.is_file() and time.time() - int(lk.read_text().strip() or 0) < 900:
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, "Linda-Pro обновляется. Программа откроется сама через минуту.\nLinda-Pro is updating and will open by itself in a minute.", config.APP_NAME, 64)
            return 0
    except Exception:
        pass

    if not _single_instance() and not _take_over_stale():
        if _file_arg():
            try:
                from . import inbox

                inbox.push(_file_arg())  # «Проверить в Linda-Pro» из проводника: работающая копия сама откроет файл
            except Exception:  # noqa: BLE001
                pass
        url = _running_url()
        if url and not _focus_window():
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
    def recover_document_jobs():
        try:
            from .document_sandbox import cleanup_stale
            cleanup_stale(config.data_dir() / '_document_spool')
        except OSError:
            print('Document scratch recovery deferred; retry on next document import.', file=sys.stderr)
    threading.Thread(target=recover_document_jobs, daemon=True).start()
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
    (config.data_dir() / "instance.json").write_text(json.dumps({"port": port, "pid": os.getpid(), "version": config.APP_VERSION, "mode": "browser" if "--browser" in argv or "--no-ui" in argv else "window"}), encoding="utf-8")
    core.background()
    if _file_arg():
        try:
            from . import inbox

            inbox.push(_file_arg())
        except Exception:  # noqa: BLE001
            pass
    url = f"http://127.0.0.1:{port}/"
    if "--no-ui" in argv:
        print(url, flush=True)
        while True:
            time.sleep(3600)
    if "--browser" not in argv:
        try:
            import webview

            webview.settings["ALLOW_DOWNLOADS"] = True  # без этого WebView2 молча отменяет скачивание отчётов (PDF/HTML/CSV/JSON/MD)

            window = webview.create_window(f"{config.APP_NAME} {config.APP_VERSION}", url, width=1360, height=900, min_size=(980, 640), text_select=True, background_color='#0d0f14')
            if os.name == 'nt':
                from .window_recovery import install
                install(window)
            webview.start(private_mode=False, storage_path=str(config.data_dir() / "webview"),
                          icon=str(config.resource_dir() / "assets" / ("linda-dev.ico" if config.APP_NAME == 'Linda-Pro Dev' else "linda.ico")))
            server.should_exit = True
            time.sleep(0.5)
            os._exit(0)
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
