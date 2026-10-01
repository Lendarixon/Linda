# -*- coding: utf-8 -*-
import base64
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import make_gift_keys as mg  # noqa: E402

from linda_desktop import config, licensing  # noqa: E402
from linda_desktop.app import Core, create_app  # noqa: E402

TOKEN = "t0k"


@pytest.fixture()
def keys(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(config, "LICENSE_PUBKEY_B64", mg.pub_b64(priv))
    monkeypatch.setattr(config, "POLAR_API", "http://127.0.0.1:9")  # nothing listens: any network call would fail
    return priv


def client():
    return TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})


def test_valid_gift_keys_work_offline(keys):
    c = client()
    for code, tier in (("P", "personal"), ("T", "team")):
        k = mg.make_key(keys, code, 7)
        r = c.post("/api/license/activate", json={"key": k})
        assert r.status_code == 200, r.text
        lic = r.json()["license"]
        assert lic["licensed"] and lic["tier"] == tier and lic["kind"] == "gift"
        assert c.get("/api/status").json()["license"]["tier"] == tier
        assert licensing.revalidate(force=True)["licensed"]  # no network call for gift keys
    assert len(mg.make_key(keys, "P", 1)) < 140


def test_key_is_tolerant_to_case_spaces_and_line_breaks(keys):
    k = mg.make_key(keys, "P", 12)
    messy = "  " + k.lower().replace("-", "-\n", 3) + " "
    assert licensing.verify_gift(messy)["id"] == "P-0012"


def test_tampered_or_foreign_keys_rejected(keys):
    c = client()
    k = mg.make_key(keys, "P", 5)
    assert licensing.verify_gift(k.replace("LINDA-P-0005", "LINDA-T-0005")) is None  # tier changed
    assert licensing.verify_gift(k.replace("0005", "0006")) is None  # number changed
    assert licensing.verify_gift(k[:-3] + ("AAA" if not k.endswith("AAA") else "BBB")) is None  # signature damaged
    other = mg.make_key(Ed25519PrivateKey.generate(), "P", 5)  # signed by somebody else
    r = c.post("/api/license/activate", json={"key": other})
    assert r.status_code == 422 and "not valid" in r.json()["detail"]
    assert not c.get("/api/status").json()["license"]["licensed"]
    assert c.post("/api/license/activate", json={"key": k[:60]}).status_code == 422  # cut in the middle


def test_revocation_through_manifest(keys):
    c = client()
    k = mg.make_key(keys, "T", 3)
    assert c.post("/api/license/activate", json={"key": k}).json()["license"]["licensed"]
    licensing.apply_revocations(["P-0001"])  # another key: nothing happens
    assert c.get("/api/status").json()["license"]["licensed"]
    licensing.apply_revocations(["T-0003"])
    lic = c.get("/api/status").json()["license"]
    assert lic["licensed"] is False and lic["status"] == "revoked"


def test_ids_and_keys_unique(keys):
    ks = {mg.make_key(keys, "P", n) for n in range(1, 101)} | {mg.make_key(keys, "T", n) for n in range(1, 11)}
    assert len(ks) == 110
