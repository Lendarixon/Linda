# -*- coding: utf-8 -*-
"""Публикация 2.0.5.0 + веса 1.3.4, по шагам и строго в этом порядке:
    python tools/publish_2050.py github       # релиз v2.0.5.1 с установщиком
    python tools/publish_2050.py hf_models    # 3 изменённых файла моделей в Lindarixon/Linda-Pro (пользователи пока ничего не видят)
    python tools/publish_2050.py hf_manifest  # переключатель: latest.json + .sig (после github и hf_models!)
    python tools/publish_2050.py hf_lite      # Lindarixon/Linda-Pro-Lite: model.onnx, voters.py, VERSION, CHECKSUMS
Токены: GitHub - git credential manager, Hugging Face - huggingface-cli login."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import publish_2042 as gh  # noqa: E402

REL = Path(r"C:\Users\ninja\Desktop\Linda_release_1_3_4")
CHANGED = ["models/linda_speed_131/model.onnx", "models/essay_dhi_131_20261008/tok_head.npz", "models/multi_dhi_131_20261008/tok_head.npz"]
NOTES = ("Linda-Pro 2.0.5.1: Linda-Pro Lite now takes the token scores for sentence highlighting from the same model passes that compute the verdict "
         "and reads only the rest of the text - highlighting about 2x faster (2.1 -> 1.0 s per 1,000 words on 4 threads in our measurement), "
         "highlighting accuracy not lower, verdicts unchanged. Models unchanged (1.3.4).\n\n"
         "SHA-256 of Linda-Setup.exe: %s. Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.")


def github():
    gh.TAG = "v2.0.5.1"
    gh.NOTES = NOTES
    tok = gh.gh_token()
    sha = hashlib.sha256(gh.SETUP.read_bytes()).hexdigest()
    code, rel = gh.api(tok, "POST", f"https://api.github.com/repos/{gh.REPO}/releases",
                       {"tag_name": gh.TAG, "target_commitish": "main", "name": "Linda-Pro 2.0.5.1 (Windows): Lite highlighting twice as fast",
                        "body": NOTES % sha, "draft": False, "prerelease": False, "make_latest": "true"})
    if code == 422:
        code, rel = gh.api(tok, "GET", f"https://api.github.com/repos/{gh.REPO}/releases/tags/{gh.TAG}")
    print("release:", code, rel.get("html_url"))
    for a in rel.get("assets", []):
        if a["name"] == "Linda-Setup.exe":
            gh.api(tok, "DELETE", f"https://api.github.com/repos/{gh.REPO}/releases/assets/{a['id']}")
    with open(gh.SETUP, "rb") as f:
        code, asset = gh.api(tok, "POST", f"https://uploads.github.com/repos/{gh.REPO}/releases/{rel['id']}/assets?name=Linda-Setup.exe",
                             raw=f, ctype="application/octet-stream")
    print("asset:", code, asset.get("browser_download_url"), asset.get("size"), "sha256", sha)


def hf_models():
    from huggingface_hub import CommitOperationAdd, HfApi
    ops = [CommitOperationAdd(path_in_repo=r, path_or_fileobj=str(REL / "pack" / r)) for r in CHANGED]
    print("committed:", HfApi().create_commit("Lindarixon/Linda-Pro", ops, commit_message="Models 1.3.4: per-token output (Lite) and token heads (Pro); manifest follows").commit_url)


def hf_manifest():
    from huggingface_hub import CommitOperationAdd, HfApi
    m = json.loads((REL / "repo/latest.json").read_text(encoding="utf-8"))
    assert m["installer"]["version"] == "2.0.5.1" and m["installer"]["sha256"] == hashlib.sha256(gh.SETUP.read_bytes()).hexdigest()
    ops = [CommitOperationAdd(path_in_repo=n, path_or_fileobj=str(REL / "repo" / n)) for n in ("latest.json", "latest.json.sig")]
    print("manifest:", HfApi().create_commit("Lindarixon/Linda-Pro", ops, commit_message="Signed update manifest: app 2.0.5.1, weights 1.3.4").commit_url)


def hf_lite():
    from huggingface_hub import CommitOperationAdd, HfApi
    rid = "Lindarixon/Linda-Pro-Lite"
    onnx = REL / "pack/models/linda_speed_131/model.onnx"
    sums = urllib.request.urlopen(f"https://huggingface.co/{rid}/resolve/main/CHECKSUMS.sha256", timeout=60).read().decode("utf-8").splitlines()
    new_sum = hashlib.sha256(onnx.read_bytes()).hexdigest()
    sums = [(f"{new_sum}  models/linda_speed_131/model.onnx" if l.rstrip().endswith("models/linda_speed_131/model.onnx") else l) for l in sums]
    ops = [CommitOperationAdd(path_in_repo="models/linda_speed_131/model.onnx", path_or_fileobj=str(onnx)),
           CommitOperationAdd(path_in_repo="linda_pro/voters.py", path_or_fileobj=str(ROOT / "linda_pro/voters.py")),
           CommitOperationAdd(path_in_repo="VERSION", path_or_fileobj=b"1.3.4\n"),
           CommitOperationAdd(path_in_repo="CHECKSUMS.sha256", path_or_fileobj=("\n".join(sums) + "\n").encode("utf-8"))]
    print("lite:", HfApi().create_commit(rid, ops, commit_message="Linda-Pro Lite 1.3.4: per-token output for sentence highlighting (verdict output unchanged)").commit_url)


if __name__ == "__main__":
    {"github": github, "hf_models": hf_models, "hf_manifest": hf_manifest, "hf_lite": hf_lite}[sys.argv[1]]()
