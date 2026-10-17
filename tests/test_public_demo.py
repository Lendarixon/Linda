"""Public API contract: real async callbacks/SQLite, synthetic Engine results."""
import importlib.util
import inspect
import io
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest
import asyncio
from concurrent.futures import CancelledError as FutureCancelledError
from fastapi.testclient import TestClient


def load(name):
    path = Path(__file__).resolve().parents[1] / "modal" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modal"))
quota_module, api_module = load("demo_quota"), load("demo_api")
TEXT = "\u017b\u00f3\u0142w \U0001f680 " + "word " * 18 + ". Second sentence."
NOW = 20_000 * 86400 + 3600
HAS_CLIENT_IP = "client" in inspect.signature(TestClient).parameters


def engine_result(text, detector):
    sentences = []
    for match in re.finditer(r"[^.!?]+[.!?]?", text):
        start = match.start()
        while start < match.end() and text[start].isspace():
            start += 1
        if start < match.end():
            sentences.append({"start": start, "end": match.end(),
                              "text": text[start:match.end()], "p_ai": 0.25, "label": "human"})
    return dict(detector_id=detector, app_version="2.0.6.2", model_version="1.3.4",
                model_pack_version="1.3.4", markup_version="2.0.6.2", text=text,
                status="human", ai_share=0.0, sentences=sentences)


@pytest.fixture
def demo(tmp_path):
    state = SimpleNamespace(db=tmp_path / "quota.sqlite", now=NOW, failure=None,
                            calls=[], runs=[], results=[])

    async def quota_call(op, visitor, network, rid):
        state.calls.append((op, visitor, network, rid))
        if op == "finish" and state.failure in (
                "cancel_finish_before_commit", "cancel_finish_refund_failure"):
            raise asyncio.CancelledError()
        if op == "refund" and state.failure == "cancel_finish_refund_failure":
            raise RuntimeError("synthetic refund failure")
        if (state.failure == op
                or (state.failure in ("model+refund", "finish+refund") and op == "refund")
                or (state.failure == "finish+refund" and op == "finish")):
            raise RuntimeError("synthetic quota failure")
        result = quota_module.quota(state.db, op, visitor, network, rid, now=state.now)
        if op == "finish" and state.failure == "cancel_finish_after_commit":
            raise asyncio.CancelledError()
        if state.failure == "finish_after_commit" and op == "finish":
            raise RuntimeError("finish committed but response was lost")
        return result

    async def run_call(text, mode, detector):
        state.runs.append((text, mode, detector))
        if state.failure == 'cancelled':
            raise asyncio.CancelledError()
        if state.failure in ("model", "model+refund"):
            raise RuntimeError("synthetic model failure")
        result = engine_result(text, detector)
        if state.failure == "identity":
            result["detector_id"] = "assay" if detector == "loupe" else "loupe"
        state.results.append(result)
        return result

    api = api_module.create_api(page=b"<html>test</html>", quota_call=quota_call,
                                 run_call=run_call, secret="synthetic-test-secret-" * 2)
    with ExitStack() as stack:
        def client(ip="192.0.2.1"):
            kwargs = {"client": (ip, 12345)} if HAS_CLIENT_IP else {}
            return stack.enter_context(TestClient(api, base_url="https://testserver/", **kwargs))
        state.client = client
        yield state


def detect(client, detector="loupe", text=TEXT, mode="sensitive", **kwargs):
    return client.post("/api/detect", json=dict(text=text, mode=mode, detector=detector), **kwargs)


def remaining(client):
    response = client.get("/api/session")
    assert response.status_code == 200, response.text
    return response.json()["remaining"]


def test_quota_closes_connection_before_return(tmp_path, monkeypatch):
    original = sqlite3.connect
    closed = []
    class Connection(sqlite3.Connection):
        def close(self):
            closed.append(True)
            return super().close()
    def tracked(*args, **kwargs):
        return original(*args, factory=Connection, **kwargs)
    monkeypatch.setattr(quota_module.sqlite3, 'connect', tracked)
    result = quota_module.quota(tmp_path / 'closed.sqlite', 'status', 'v', 'n', now=NOW)
    assert result['remaining'] == 12
    assert closed == [True]


def test_non_ascii_cookie_signature_is_replaced_not_server_error(demo):
    client = demo.client()
    cookie = (api_module.COOKIE + '=' + 'a' * 32 + '.').encode('ascii') + b'\xe9'
    response = client.get('/api/session', headers=[(b'cookie', cookie)])
    assert response.status_code == 200
    assert response.json()['remaining'] == 12
    assert re.fullmatch(r'[0-9a-f]{32}\.[0-9a-f]{64}', client.cookies.get(api_module.COOKIE))


def test_cancelled_inference_releases_pending_reservation(demo):
    client = demo.client()
    demo.failure = 'cancelled'
    # BaseHTTPMiddleware may translate a cancelled endpoint into this transport
    # error; in either case the reservation must already have been released.
    with pytest.raises((asyncio.CancelledError, FutureCancelledError, RuntimeError)) as caught:
        detect(client)
    if isinstance(caught.value, RuntimeError):
        assert str(caught.value) == 'No response returned.'
    assert remaining(client) == 12
    assert rows(demo) == []
    assert any(op == 'refund' for op, *_ in demo.calls)


@pytest.mark.parametrize("failure, expected_remaining, expected_states", [
    ("cancel_finish_before_commit", 12, []),
    ("cancel_finish_after_commit", 11, ["done"]),
])
def test_cancelled_finish_refunds_only_if_finish_did_not_commit(
        demo, failure, expected_remaining, expected_states):
    client = demo.client()
    demo.failure = failure
    with pytest.raises((asyncio.CancelledError, FutureCancelledError, RuntimeError)) as caught:
        detect(client)
    if isinstance(caught.value, RuntimeError):
        assert str(caught.value) == "No response returned."
    assert [call[0] for call in demo.calls[-2:]] == ["finish", "refund"]
    assert [row[4] for row in rows(demo)] == expected_states
    assert remaining(client) == expected_remaining


def test_cancelled_finish_with_failed_refund_recovers_pending_lease(demo):
    client = demo.client()
    demo.failure = "cancel_finish_refund_failure"
    with pytest.raises((asyncio.CancelledError, FutureCancelledError, RuntimeError)) as caught:
        detect(client)
    if isinstance(caught.value, RuntimeError):
        assert str(caught.value) == "No response returned."
    assert [call[0] for call in demo.calls[-2:]] == ["finish", "refund"]
    assert [row[4] for row in rows(demo)] == ["pending"]
    assert remaining(client) == 11
    demo.now += quota_module.LEASE_SECONDS + 1
    assert remaining(client) == 12
    assert rows(demo) == []


def rows(demo):
    with sqlite3.connect(demo.db) as db:
        return db.execute("SELECT id,visitor,network,day,state,created FROM checks ORDER BY id").fetchall()


def no_charge(demo, client, send, status):
    starting_remaining = remaining(client)
    before = rows(demo)
    calls, runs = len(demo.calls), len(demo.runs)
    response = send()
    assert response.status_code == status, response.text
    assert "result" not in response.json()
    assert len(demo.runs) == runs
    assert not any(op == "reserve" for op, *_ in demo.calls[calls:])
    assert remaining(client) == starting_remaining
    assert rows(demo) == before
    return response


def test_health_and_https_session(demo):
    client = demo.client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["detectors"] == ["loupe", "assay"]
    assert data["app_version"] == data["markup_version"] == "2.0.6.2"
    assert data["model_version"] == data["model_pack_version"] == "1.3.4"
    assert (data["max_chars"], data["max_uses"], data["access_code_required"]) == (6000, 12, False)
    assert data["supported_formats"] == ["txt", "md", "docx"]
    assert data["recommended_words"] == 300
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json()["remaining"] == 12
    assert response.json()["min_words"] == 20
    assert response.json()["max_chars"] == 6000
    assert "signed browser cookie" in response.json()["quota_identity"]
    assert all(flag in response.headers["set-cookie"].lower() for flag in ("secure", "httponly", "samesite=lax"))
    token = client.cookies.get(api_module.COOKIE)
    assert re.fullmatch(r"[0-9a-f]{32}\.[0-9a-f]{64}", token)
    assert remaining(client) == 12
    assert client.cookies.get(api_module.COOKIE) == token
    assert rows(demo) == []


def exhaust(demo, client):
    for index in range(12):
        detector = ("loupe", "assay")[index % 2]
        response = detect(client, detector, mode="precise" if detector == "assay" else "sensitive")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ok"
        assert data["remaining"] == remaining(client) == 11 - index
        assert data["result"] == demo.results[-1]
        assert data["result"]["detector_id"] == detector
        assert len(data["result"]["sentences"]) == 2
        for sentence in data["result"]["sentences"]:
            assert TEXT[sentence["start"]:sentence["end"]] == sentence["text"]


def test_twelve_alternating_successes_then_429(demo):
    client = demo.client()
    exhaust(demo, client)
    response = detect(client, "assay")
    assert response.status_code == 429
    assert response.json()["remaining"] == remaining(client) == 0
    assert len(demo.runs) == 12
    assert [row[4] for row in rows(demo)] == ["done"] * 12


def test_same_cookie_after_eight_days_still_zero(demo):
    client = demo.client()
    exhaust(demo, client)
    token = client.cookies.get(api_module.COOKIE)
    demo.now += 8 * 86400
    assert remaining(client) == 0
    assert client.cookies.get(api_module.COOKIE) == token
    response = detect(client)
    assert response.status_code == 429 and response.json()["remaining"] == 0
    assert len(demo.runs) == 12
    fresh = demo.client()
    assert remaining(fresh) == 12  # Network daily count really reset.
    assert detect(fresh).status_code == 200
    assert {row[3] for row in rows(demo)} == {int(NOW // 86400), int(demo.now // 86400)}


@pytest.mark.parametrize("cookie", [None, "f" * 32 + "." + "0" * 64])
def test_cleared_forged_cookies_and_forwarded_ip_cannot_bypass_network(demo, cookie):
    client = demo.client()
    exhaust(demo, client)
    old = client.cookies.get(api_module.COOKIE)
    client.cookies.clear()
    headers = {"X-Forwarded-For": "198.51.100.99"}
    if cookie:
        headers["Cookie"] = api_module.COOKIE + "=" + cookie
    response = detect(client, headers=headers)
    assert response.status_code == 429
    assert response.json()["remaining"] == remaining(client) == 0
    assert client.cookies.get(api_module.COOKIE) not in (old, cookie)
    assert len(demo.runs) == len(rows(demo)) == 12
    assert len({network for _, _, network, _ in demo.calls}) == 1


def test_independent_client_ip_isolated(demo):
    if HAS_CLIENT_IP:
        first, second = demo.client("192.0.2.1"), demo.client("192.0.2.2")
        exhaust(demo, first)
        assert remaining(second) == 12
        response = detect(second)
        assert response.status_code == 200 and response.json()["remaining"] == 11
        assert remaining(first) == 0
        assert len({row[2] for row in rows(demo)}) == 2
    else:
        for i in range(3):
            assert quota_module.quota(demo.db, "reserve", "a", "network-a", str(i), now=NOW)["ok"]
        assert quota_module.quota(demo.db, "status", "b", "network-b", now=NOW)["remaining"] == 12
        assert quota_module.quota(demo.db, "reserve", "b", "network-b", "b1", now=NOW)["remaining"] == 11
        assert quota_module.quota(demo.db, "status", "a", "network-a", now=NOW)["remaining"] == 0


def test_forty_eight_concurrent_sqlite_reserves_only_twelve_accepted(tmp_path):
    db = tmp_path / "concurrent.sqlite"
    barrier = Barrier(48)
    def reserve(index):
        barrier.wait(timeout=10)
        return quota_module.quota(db, "reserve", "visitor-" + str(index), "shared", str(index), now=NOW)
    with ThreadPoolExecutor(max_workers=48) as pool:
        results = list(pool.map(reserve, range(48)))
    assert sum(result["ok"] for result in results) == 12
    assert all(result["remaining"] == 0 for result in results if not result["ok"])
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM checks WHERE state='pending'").fetchone()[0] == 12


def test_three_existing_uses_are_retained_and_leave_nine(demo):
    for index in range(3):
        rid = f"old-{index}"
        assert quota_module.quota(demo.db, "reserve", "legacy-visitor", "legacy-network", rid, now=NOW)["ok"]
        quota_module.quota(demo.db, "finish", "legacy-visitor", "legacy-network", rid, now=NOW)
    status = quota_module.quota(demo.db, "status", "legacy-visitor", "legacy-network", now=NOW)
    assert status["remaining"] == 9 and status["max_uses"] == 12
    with sqlite3.connect(demo.db) as connection:
        assert connection.execute("SELECT state,count(*) FROM checks GROUP BY state").fetchall() == [("done", 3)]


def test_global_daily_capacity_remains_three_hundred(tmp_path):
    db = tmp_path / "daily-cap.sqlite"
    for index in range(quota_module.DAY_LIMIT):
        result = quota_module.quota(db, "reserve", f"visitor-{index}", f"network-{index}", str(index), now=NOW)
        assert result["ok"]
    blocked = quota_module.quota(db, "reserve", "visitor-last", "network-last", "last", now=NOW)
    assert blocked == {"ok": False, "remaining": 12, "reason": "demo_capacity"}


def test_repeated_finish_idempotent_and_expired_pending_finish_fails(tmp_path):
    db = tmp_path / "leases.sqlite"
    def call(op, rid, now=NOW):
        return quota_module.quota(db, op, "visitor", "network", rid, now=now)
    assert call("reserve", "done")["remaining"] == 11
    first = call("finish", "done")
    assert first["ok"] and first["remaining"] == 11
    assert call("finish", "done") == first
    assert call("reserve", "expired")["remaining"] == 10
    late = NOW + quota_module.LEASE_SECONDS + 1
    assert call("finish", "expired", late) == {"ok": False, "remaining": 11, "reason": "expired"}
    assert call("status", None, late)["remaining"] == 11
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT id,state FROM checks").fetchall() == [("done", "done")]


@pytest.mark.parametrize("failure", ["model", "identity"])
def test_model_exception_or_identity_mismatch_refunds(demo, failure):
    client = demo.client()
    demo.failure = failure
    response = detect(client)
    assert response.status_code == 503
    assert "result" not in response.json()
    assert response.json()["remaining"] == remaining(client) == 12
    assert [call[0] for call in demo.calls[:2]] == ["reserve", "refund"]
    assert rows(demo) == []
    demo.failure = None
    response = detect(client)
    assert response.status_code == 200 and response.json()["remaining"] == 11


def test_quota_finalization_exception_withholds_computed_result(demo):
    client = demo.client()
    demo.failure = "finish"
    response = detect(client)
    assert response.status_code == 503 and "result" not in response.json()
    assert len(demo.results) == 1
    assert response.json()["remaining"] == remaining(client) == 12
    assert [call[0] for call in demo.calls[-3:-1]] == ["finish", "refund"]
    assert rows(demo) == []


def test_ambiguous_successful_finish_withholds_result_and_keeps_charge(demo):
    client = demo.client()
    demo.failure = "finish_after_commit"
    response = detect(client)
    assert response.status_code == 503 and "result" not in response.json()
    assert response.json()["remaining"] == 11
    assert remaining(client) == 11
    assert [call[0] for call in demo.calls[-3:-1]] == ["finish", "refund"]
    assert [row[4] for row in rows(demo)] == ["done"]


def test_failed_finish_and_refund_recover_by_pending_lease(demo):
    client = demo.client()
    demo.failure = "finish+refund"
    response = detect(client)
    assert response.status_code == 503 and "result" not in response.json()
    assert response.json()["remaining"] == remaining(client) == 11
    assert [call[0] for call in demo.calls[-3:-1]] == ["finish", "refund"]
    assert [row[4] for row in rows(demo)] == ["pending"]
    demo.now += quota_module.LEASE_SECONDS + 1
    assert remaining(client) == 12 and rows(demo) == []


def test_failed_refund_is_recovered_by_pending_lease(demo):
    client = demo.client()
    demo.failure = "model+refund"
    response = detect(client)
    assert response.status_code == 503 and "result" not in response.json()
    assert "reservation will be released" not in response.json()["detail"]
    assert response.json()["remaining"] == remaining(client) == 11
    assert [row[4] for row in rows(demo)] == ["pending"]
    demo.now += quota_module.LEASE_SECONDS + 1
    assert remaining(client) == 12 and rows(demo) == []


@pytest.mark.parametrize("payload", [
    {"text": "\U0001f680" * 6001}, {"text": "word " * 19}, {},
    {"text": None}, {"text": 42}, {"text": []},
    {"text": TEXT, "mode": "invalid"}, {"text": TEXT, "mode": []},
    {"text": TEXT, "detector": "invalid"}, {"text": TEXT, "detector": {}},
    [], "string", None,
])
def test_invalid_json_fields_no_charge(demo, payload):
    client = demo.client()
    no_charge(demo, client, lambda: client.post("/api/detect", content=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
              headers={"Content-Type": "application/json"}), 400)


@pytest.mark.parametrize("content,status,headers", [
    (b'{"text":', 400, {"Content-Type": "application/json"}),
    (b"\xff", 400, {"Content-Type": "application/json"}),
    (b"x" * (api_module.MAX_REQUEST_BYTES + 1), 413, {"Content-Type": "application/json"}),
    (b"{}", 415, {"Content-Type": "text/plain"}),
], ids=['malformed-json','invalid-utf8','body-too-large','wrong-content-type'])
def test_malformed_or_oversize_body_no_charge(demo, content, status, headers):
    client = demo.client()
    no_charge(demo, client, lambda: client.post("/api/detect", content=content, headers=headers), status)


def test_wrong_origin_no_charge(demo):
    client = demo.client()
    no_charge(demo, client, lambda: detect(client, headers={"Origin": "https://evil.example"}), 403)


def test_exactly_6000_unicode_codepoints_and_json_high_surrogate_pairs(demo):
    client = demo.client()
    prefix = "word " * 19
    text = prefix + "\U0001f680" * (6000 - len(prefix))
    assert len(text) == 6000 and len(text.split()) == 20
    # UTF-8 fits the body cap; UTF-16 would count each rocket as two units.
    body = json.dumps(dict(text=text, detector="assay", mode="precise"), ensure_ascii=False).encode("utf-8")
    response = client.post("/api/detect", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 200, response.text
    assert response.json()["result"] == engine_result(text, "assay")
    assert response.json()["remaining"] == remaining(client) == 11
    # Also test exactly 6000 codepoints with escaped high/low surrogate pairs.
    # ASCII padding keeps the escaped JSON itself below the request byte cap.
    escaped_text = prefix + "\U0001f680" + "x" * (6000 - len(prefix) - 1)
    assert len(escaped_text) == 6000 and len(escaped_text.split()) == 20
    escaped = json.dumps({"text": escaped_text}, ensure_ascii=True)
    assert "\\ud83d\\ude80" in escaped
    response = client.post("/api/detect", content=escaped, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert response.json()["result"] == engine_result(escaped_text, "loupe")
    assert response.json()["remaining"] == remaining(client) == 10


@pytest.mark.parametrize("content,status", [
    (b"x" * (api_module.MAX_UPLOAD_BYTES + 1), 413),
    (("\U0001f680" * 6001).encode("utf-8"), 400),
], ids=['file-too-large','extracted-text-too-long'])
def test_upload_over_2mb_or_long_extracted_text_no_charge(demo, content, status):
    client = demo.client()
    no_charge(demo, client, lambda: client.post("/api/upload", files={"file": ("text.txt", content, "text/plain")}), status)


def test_valid_utf8_txt_upload_no_charge(demo):
    client = demo.client()
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": ("sample.txt", ("\ufeff" + TEXT + "\r\n").encode("utf-8"), "text/plain")}), 200)
    assert response.json() == dict(status="ok", filename="sample.txt", text=TEXT,
                                   words=len(TEXT.split()), chars=len(TEXT))


def test_valid_docx_upload_no_charge_if_available(demo):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph(TEXT)
    stream = io.BytesIO()
    document.save(stream)
    client = demo.client()
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": ("sample.docx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}), 200)
    assert response.json()["text"] == TEXT
    assert response.json()["chars"] == len(TEXT)
    assert response.json()["words"] == len(TEXT.split())


@pytest.mark.parametrize("filename,content,error_code", [
    ("slides.pptx", b"not a pptx", "unsupported_format"),
    ("slides.ppt", b"not a ppt", "unsupported_format"),
    ("paper.pdf", b"%PDF-1.7", "unsupported_format"),
    ("broken.docx", b"not a zip file", "invalid_file"),
    ("binary.txt", b"one\x00two", "invalid_file"),
    ("bad-encoding.txt", b"\xff\xfe", "invalid_encoding"),
])
def test_unsupported_or_malformed_upload_no_charge_after_success(demo, filename, content, error_code):
    client = demo.client()
    assert detect(client).status_code == 200
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": (filename, content, "application/octet-stream")}), 400)
    assert response.json()["error_code"] == error_code


def test_docx_table_text_is_extracted(demo):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = TEXT
    stream = io.BytesIO()
    document.save(stream)
    client = demo.client()
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": ("table.docx", stream.getvalue(), "application/octet-stream")}), 200)
    assert response.json()["text"] == TEXT


def test_docx_body_order_nested_tables_and_merged_cells(demo):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Before")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Left"
    table.cell(0, 1).text = "Right"
    merged = table.cell(1, 0).merge(table.cell(1, 1))
    merged.text = "Merged"
    nested = merged.add_table(rows=1, cols=2)
    nested.cell(0, 0).text = "Nested left"
    nested.cell(0, 1).text = "Nested right"
    merged.add_paragraph("After nested")
    document.add_paragraph("After")
    stream = io.BytesIO()
    document.save(stream)
    client = demo.client()
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": ("nested.docx", stream.getvalue(), "application/octet-stream")}), 200)
    assert response.json()["text"] == "\n\n".join([
        "Before", "Left", "Right", "Merged", "Nested left",
        "Nested right", "After nested", "After",
    ])


def test_docx_zip_entry_cap_is_checked_before_document_parse(demo, monkeypatch):
    import zipfile
    docx = pytest.importorskip("docx")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index in range(2001):
            archive.writestr(f"entry-{index}", b"")
    monkeypatch.setattr(docx, "Document", lambda *args, **kwargs: pytest.fail("DOCX parsed before ZIP entry cap"))
    client = demo.client()
    response = no_charge(demo, client, lambda: client.post("/api/upload", files={
        "file": ("many-entries.docx", stream.getvalue(), "application/octet-stream")}), 400)
    assert response.json()["error_code"] == "invalid_file"


def test_short_detection_text_is_rejected_after_success_without_charge(demo):
    client = demo.client()
    assert detect(client).status_code == 200
    response = no_charge(demo, client, lambda: detect(client, text="word " * 19), 400)
    assert "at least 20 words" in response.json()["detail"]
