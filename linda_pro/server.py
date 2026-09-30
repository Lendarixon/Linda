# -*- coding: utf-8 -*-
"""Локальный HTTP-сервис Linda-Pro (только стандартная библиотека): для встраивания в ваш продукт ВНУТРИ вашей инфраструктуры.
Модели загружаются один раз и остаются в памяти. Тексты не пишутся в журнал и не отправляются наружу.

    python -m linda_pro.server --port 8080 [--host 127.0.0.1] [--mode sensitive|precise] [--token SECRET] [--device cuda|cpu]

Запросы (JSON):
    GET  /health                       -> {"status": "ok", "mode": ...}
    POST /v1/detect  {"texts": ["..."], "mode": "sensitive"|"precise", "windows": true|false}
                     -> {"results": [{"verdict", "essay", "ens_z", "ai_share", "n_windows", "windows": [...]}]}
Если задан --token, нужен заголовок  Authorization: Bearer SECRET. По умолчанию слушает только 127.0.0.1.
Это локальная обёртка для интеграции (например, шлюз для LTI-инструмента), а не облачный API; модели одни на процесс,
запросы обрабатываются строго по очереди.
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import LindaPro

MAX_BODY = 20 * 1024 * 1024  # 20 МБ на запрос
MAX_TEXTS = 64
LOCK = threading.Lock()  # голоса строго последовательно


class _Resident:
    """Обёртка голоса: close() ничего не выгружает, модель остаётся в памяти между запросами."""

    def __init__(self, voter):
        self._v = voter

    def margins(self, texts):
        return self._v.margins(texts)

    def close(self) -> None:
        return None


def make_detectors(device: str | None = None) -> dict[str, LindaPro]:
    cache: dict[str, _Resident] = {}
    base = LindaPro(mode="sensitive", device=device)

    def factory(key: str) -> _Resident:
        if key not in cache:
            cache[key] = _Resident(base._default_factory(key))
        return cache[key]

    base._factory = factory
    precise = LindaPro(mode="precise", device=device, voter_factory=factory)
    return {"sensitive": base, "precise": precise}


def make_handler(detectors: dict, token: str | None, default_mode: str):
    class H(BaseHTTPRequestHandler):
        server_version = "LindaPro"

        def log_message(self, *a):  # ничего не пишем: в запросах чужие тексты
            return

        def _send(self, code: int, obj: dict) -> None:
            b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _auth(self) -> bool:
            return token is None or self.headers.get("Authorization", "") == "Bearer " + token

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"status": "ok", "mode": default_mode})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/detect":
                return self._send(404, {"error": "not found"})
            if not self._auth():
                return self._send(401, {"error": "unauthorized"})
            n = int(self.headers.get("Content-Length", "0") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._send(413, {"error": "body size must be 1..%d bytes" % MAX_BODY})
            try:
                req = json.loads(self.rfile.read(n).decode("utf-8"))
                texts = req["texts"]
                if not (isinstance(texts, list) and 0 < len(texts) <= MAX_TEXTS and all(isinstance(t, str) for t in texts)):
                    raise ValueError("texts")
                det = detectors[req.get("mode", default_mode)]
            except Exception:  # noqa: BLE001
                return self._send(400, {"error": 'expected JSON {"texts": [1..%d strings], "mode": "sensitive"|"precise"}' % MAX_TEXTS})
            try:
                with LOCK:
                    res = det.detect(texts)
            except Exception as e:  # noqa: BLE001
                return self._send(500, {"error": "detector failed: " + type(e).__name__})
            if not req.get("windows", True):
                for r in res:
                    r.pop("windows", None)
            self._send(200, {"results": res})

    return H


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Linda-Pro local HTTP service")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--mode", choices=["sensitive", "precise"], default="sensitive")
    ap.add_argument("--token", default=None)
    ap.add_argument("--device", default=None, help="cuda or cpu (default: auto)")
    a = ap.parse_args(argv)
    dets = make_detectors(a.device)
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(dets, a.token, a.mode))
    print(f"Linda-Pro service on http://{a.host}:{a.port} (mode {a.mode}); request texts are never logged", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
