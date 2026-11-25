# -*- coding: utf-8 -*-
"""Публикация 2.3.0.1: GitHub-релиз с установщиком, подписанный манифест HF, сайт.
Модели не менялись (пакет 1.3.4.1).

    python tools/publish_2301.py github      # релиз v2.3.0.1 + Linda-Setup.exe
    python tools/publish_2301.py hf_manifest  # latest.json + .sig (только после github!)
    python tools/publish_2301.py site         # push gh-pages + public main
"""
import base64
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import publish_2042 as gh  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

from linda_desktop.updater import verify_signature  # noqa: E402

VER = "2.3.0.1"
SETUP = Path(r"C:\Users\ninja\Desktop\Linda_2.3.0.1\Linda-Setup.exe")
NOTES = ("Linda 2.3.0.1: humanizer reliability, no detector changes (model pack 1.3.4.1, thresholds unchanged).\n\n"
         "- Pack downloads now show a live byte bar (downloaded of total) plus a one-click \"whole humanizer (Lite + Full)\" button; the \"everything\" choice no longer covers only the detector.\n"
         "- Applied detector updates no longer leave a ~3 GB staging duplicate behind.\n"
         "- Auto mode reports which tier it picked and why; out-of-memory or missing-GPU situations end with a clear message (pick Lite) instead of a crash.\n"
         "- One-sentence rewrites no longer hang the PC: the full 4B model is blocked on GPU-less machines and refinement shows live progress.\n"
         "- The humanizer gained a word counter, a below-300-words warning and a log export (Markdown), like the detector already had.\n\n"
         "SHA-256 of Linda-Setup.exe: %s. Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.")


def github():
    gh.TAG = "v" + VER
    tok = gh.gh_token()
    sha = hashlib.sha256(SETUP.read_bytes()).hexdigest()
    code, rel = gh.api(tok, "POST", f"https://api.github.com/repos/{gh.REPO}/releases",
                       {"tag_name": gh.TAG, "target_commitish": "main", "name": f"Linda {VER} (Windows): humanizer reliability, no detector changes",
                        "body": NOTES % sha, "draft": False, "prerelease": False, "make_latest": "true"})
    if code == 422:
        code, rel = gh.api(tok, "GET", f"https://api.github.com/repos/{gh.REPO}/releases/tags/{gh.TAG}")
    print("release:", code, rel.get("html_url"))
    for a in rel.get("assets", []):
        if a["name"] == "Linda-Setup.exe":
            print("delete old asset:", gh.api(tok, "DELETE", f"https://api.github.com/repos/{gh.REPO}/releases/assets/{a['id']}")[0])
    with open(SETUP, "rb") as f:
        code, asset = gh.api(tok, "POST", f"https://uploads.github.com/repos/{gh.REPO}/releases/{rel['id']}/assets?name=Linda-Setup.exe",
                             raw=f, ctype="application/octet-stream")
    print("asset:", code, asset.get("browser_download_url"), asset.get("size"), "sha256", sha)


def hf_manifest():
    base = "https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/"
    raw = urllib.request.urlopen(base + "latest.json", timeout=60).read()
    verify_signature(raw, urllib.request.urlopen(base + "latest.json.sig", timeout=60).read())
    m = json.loads(raw)
    assert m["version"] == "1.3.4.1", m.get("version")
    assert m["installer"]["version"] == "2.3.0.0", m["installer"].get("version")
    entry = json.loads((ROOT / "CHANGELOG.json").read_text(encoding="utf-8"))[0]
    assert entry["version"] == VER
    setup = SETUP.read_bytes()
    m["installer"].update(version=VER, url=f"https://github.com/Lendarixon/Linda/releases/download/v{VER}/Linda-Setup.exe",
                          size=len(setup), sha256=hashlib.sha256(setup).hexdigest())
    head = urllib.request.Request(m["installer"]["url"], method="HEAD")
    assert urllib.request.urlopen(head, timeout=60).status == 200, "installer not on GitHub yet"
    cl = [e for e in m.get("changelog", []) if e.get("version") != VER]
    m["changelog"] = [entry] + cl
    new = json.dumps(m, indent=1, ensure_ascii=False).encode("utf-8")
    key = serialization.load_pem_private_key(Path(r"C:\Users\ninja\Desktop\Linda_desktop\keys\linda_signing.key").read_bytes(), password=None)
    sig = base64.b64encode(key.sign(new))
    verify_signature(new, sig)
    out = Path(r"C:\Users\ninja\Desktop\Linda_release_2301\repo")
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_bytes(new)
    (out / "latest.json.sig").write_bytes(sig)
    print("manifest signed: pack 1.3.4.1 app", VER, "files", len(m["files"]))
    return out


def hf_commit(repo_dir):
    from huggingface_hub import CommitOperationAdd, HfApi
    ops = [CommitOperationAdd(path_in_repo=n, path_or_fileobj=str(Path(repo_dir) / n)) for n in ("latest.json", "latest.json.sig")]
    print("manifest:", HfApi().create_commit("Lindarixon/Linda-Pro", ops, commit_message=f"Signed update manifest: app {VER}, model pack 1.3.4.1 (weights unchanged)").commit_url)


def site():
    import subprocess
    subprocess.run(["git", "-C", r"C:\Users\ninja\Desktop\gh_pages_site", "push", "origin", "gh-pages"], check=True)
    subprocess.run(["git", "-C", r"C:\Users\ninja\Desktop\github_public\Linda", "push", "origin", "main"], check=True)


if __name__ == "__main__":
    {"github": github, "hf_manifest": lambda: hf_commit(hf_manifest()), "site": site}[sys.argv[1]]()
