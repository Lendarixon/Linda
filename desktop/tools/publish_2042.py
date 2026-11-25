# -*- coding: utf-8 -*-
"""Публикация приложения 2.0.4.2 на GitHub (релиз v2.0.4.2 с установщиком) - запускает владелец сам:
    python tools/publish_2042.py github
Токен GitHub берётся из git credential manager; в чат не вставляется. Модели не менялись (1.3.3), манифест HF этим скриптом не трогается."""
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO, TAG = "Lendarixon/Linda", "v2.0.4.2"
SETUP = Path(__file__).resolve().parents[1] / "dist" / "Linda-Setup.exe"
NOTES = ("Linda-Pro 2.0.4.2: a more honest verdict and sentence highlighting.\n\n"
         "- Linda-Pro Lite: sentence highlighting is fixed. Before, almost the whole text was coloured \"possibly AI\" for human and AI texts alike, "
         "and no sentence was ever marked \"AI\". Now about 9 in 10 words of AI texts are marked \"AI\", and 0-3%% of words in human texts (our dev sets, EN/PL/RU).\n"
         "- The verdict no longer contradicts the highlighting: \"written by a human\" with a quarter or more of the words marked AI becomes \"unclear\".\n"
         "- Linda-Pro Lite is more careful: when the Lite model alone is above its threshold but the combined score is lower, the verdict is \"unclear\" "
         "instead of \"human\" (an AI text edited by hand is no longer passed off as human).\n\n"
         "SHA-256 of Linda-Setup.exe: %s. Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.")


def gh_token() -> str:
    r = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("no GitHub credential found")


def api(tok, method, url, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    hdr = {"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "Content-Type": ctype, "User-Agent": "linda-publish"}
    if raw is not None and hasattr(raw, "fileno"):
        hdr["Content-Length"] = str(os.fstat(raw.fileno()).st_size)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=hdr), timeout=900) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def github():
    tok = gh_token()
    sha = hashlib.sha256(SETUP.read_bytes()).hexdigest()
    code, rel = api(tok, "POST", f"https://api.github.com/repos/{REPO}/releases",
                    {"tag_name": TAG, "target_commitish": "main", "name": "Linda-Pro 2.0.4.2 (Windows): honest verdict and sentence highlighting",
                     "body": NOTES % sha, "draft": False, "prerelease": False, "make_latest": "true"})
    if code == 422:
        code, rel = api(tok, "GET", f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
    print("release:", code, rel.get("html_url"))
    for a in rel.get("assets", []):
        if a["name"] == "Linda-Setup.exe":
            print("delete old asset:", api(tok, "DELETE", f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}")[0])
    with open(SETUP, "rb") as f:
        code, asset = api(tok, "POST", f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name=Linda-Setup.exe", raw=f, ctype="application/octet-stream")
    print("asset upload:", code, asset.get("browser_download_url"), asset.get("size"))
    print("sha256:", sha)


def hf_manifest():
    """Переключатель обновления: latest.json + latest.json.sig (из tools/make_manifest_2042.py) одним коммитом в Lindarixon/Linda-Pro."""
    from huggingface_hub import CommitOperationAdd, HfApi
    d = Path(__file__).resolve().parents[1] / "manifest_2042"
    m = json.loads((d / "latest.json").read_text(encoding="utf-8"))
    assert m["installer"]["version"] == "2.0.4.2" and m["installer"]["sha256"] == hashlib.sha256(SETUP.read_bytes()).hexdigest()
    ops = [CommitOperationAdd(path_in_repo="latest.json", path_or_fileobj=str(d / "latest.json")),
           CommitOperationAdd(path_in_repo="latest.json.sig", path_or_fileobj=str(d / "latest.json.sig"))]
    c = HfApi().create_commit("Lindarixon/Linda-Pro", ops, commit_message="Signed update manifest: app 2.0.4.2 (weights 1.3.3 unchanged)")
    print("manifest committed:", c.commit_url)


if __name__ == "__main__":
    if sys.argv[1:] == ["github"]:
        github()
    elif sys.argv[1:] == ["hf_manifest"]:
        hf_manifest()
    else:
        print(__doc__)
