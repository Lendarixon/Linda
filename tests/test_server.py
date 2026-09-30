# -*- coding: utf-8 -*-
"""Тесты HTTP-сервиса без реальных моделей: авторизация, лимиты, форма ответа, адрес по умолчанию."""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linda_pro import server  # noqa: E402


class FakeDet:
    def __init__(self, mode):
        self.mode = mode

    def detect(self, texts):
        return [{"verdict": "human", "mode": self.mode, "essay": 0.0, "ens_z": 0.0, "ai_share": 0.0, "n_windows": 1,
                 "windows": [{"first_word": 0, "last_word": 1, "essay": 0.0, "flag": False}]} for _ in texts]


@pytest.fixture()
def url():
    dets = {"sensitive": FakeDet("sensitive"), "precise": FakeDet("precise")}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(dets, "tok", "sensitive"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()


def call(base, path, body=None, token="tok", raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    rq = urllib.request.Request(base + path, data=data, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(rq) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health(url):
    assert call(url, "/health") == (200, {"status": "ok", "mode": "sensitive"})


def test_detect_and_modes(url):
    s, j = call(url, "/v1/detect", {"texts": ["a b c"]})
    assert s == 200 and j["results"][0]["mode"] == "sensitive" and "windows" in j["results"][0]
    s, j = call(url, "/v1/detect", {"texts": ["a"], "mode": "precise", "windows": False})
    assert s == 200 and j["results"][0]["mode"] == "precise" and "windows" not in j["results"][0]


def test_auth_required(url):
    assert call(url, "/v1/detect", {"texts": ["a"]}, token="wrong")[0] == 401


@pytest.mark.parametrize("body", [{"texts": []}, {"texts": "x"}, {"texts": [1]}, {"texts": ["a"] * (server.MAX_TEXTS + 1)}, {}, {"texts": ["a"], "mode": "x"}])
def test_bad_requests(url, body):
    assert call(url, "/v1/detect", body)[0] == 400


def test_not_json_and_unknown_path(url):
    assert call(url, "/v1/detect", raw=b"not json")[0] == 400
    assert call(url, "/etc/passwd")[0] == 404
    assert call(url, "/v1/detect")[0] == 404  # GET на POST-маршруте не поддерживается


def test_default_bind_is_localhost():
    src = Path(server.__file__).read_text(encoding="utf-8")
    assert 'add_argument("--host", default="127.0.0.1")' in src
