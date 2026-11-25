# -*- coding: utf-8 -*-
"""Публикация 2.0.5.3 (исправления после переименования), строго по порядку:
    python tools/publish_2052.py github       # релиз v2.0.5.2 с установщиком
    python tools/publish_2052.py hf_manifest  # latest.json + .sig - включает обновление у всех (только после github!)
    python tools/publish_2052.py hf_readme    # баннер в карточки Lindarixon/Linda-Pro и Linda-Pro-Lite
Модели не менялись (1.3.4)."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import publish_2042 as gh  # noqa: E402

REL = Path(r"C:\Users\ninja\Desktop\Linda_release_1_3_4")
BRAND = Path(r"C:\Users\ninja\Desktop\Linda_brand_metro")
VER = "2.0.5.3"
NOTES = ("Linda 2.0.5.3: first-run tips use the interface language; reports show the Linda mark and the short PDF no longer prints the old name; "
         "the installer shows the correct Linda Loupe size (about 0.3 GB). Models (1.3.4), verdicts and licence keys are unchanged.\n\n"
         "SHA-256 of Linda-Setup.exe: %s. Windows may show a SmartScreen notice because the installer is not code-signed yet: choose More info, then Run anyway.")
BANNER = ('<p align="center"><img src="https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/assets/readme_banner.png" '
          'alt="Linda-Pro - local AI-text detector" width="100%"></p>\n\n')


def github():
    gh.TAG = "v" + VER
    tok = gh.gh_token()
    sha = hashlib.sha256(gh.SETUP.read_bytes()).hexdigest()
    code, rel = gh.api(tok, "POST", f"https://api.github.com/repos/{gh.REPO}/releases",
                       {"tag_name": gh.TAG, "target_commitish": "main", "name": f"Linda {VER} (Windows): fixes after the rename",
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


def hf_manifest():
    from huggingface_hub import CommitOperationAdd, HfApi
    m = json.loads((REL / "repo/latest.json").read_text(encoding="utf-8"))
    setup = gh.SETUP.read_bytes()
    assert m["installer"]["version"] == VER and m["installer"]["sha256"] == hashlib.sha256(setup).hexdigest()
    head = urllib.request.Request(m["installer"]["url"], method="HEAD")
    assert urllib.request.urlopen(head, timeout=60).status == 200, "installer not on GitHub yet"
    ops = [CommitOperationAdd(path_in_repo=n, path_or_fileobj=str(REL / "repo" / n)) for n in ("latest.json", "latest.json.sig")]
    print("manifest:", HfApi().create_commit("Lindarixon/Linda-Pro", ops, commit_message=f"Signed update manifest: app {VER}, weights 1.3.4").commit_url)


def hf_readme():
    """Карточки HF с новыми названиями (Linda Assay / Linda Loupe), подготовлены в Linda_brand_metro/hf_cards; баннер и превью."""
    from huggingface_hub import CommitOperationAdd, HfApi
    api = HfApi()
    for rid in ("Lindarixon/Linda-Pro", "Lindarixon/Linda-Pro-Lite", "Lindarixon/Linda-Stylo-Clean"):
        card = (BRAND / "hf_cards" / f"{rid.split('/')[1]}.README.md").read_bytes()
        assert card.startswith(b"---"), "front matter must start the file (no BOM)"
        ops = [CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=card)]
        if rid.endswith("Linda-Pro"):
            ops += [CommitOperationAdd(path_in_repo=f"assets/{n}", path_or_fileobj=str(BRAND / n)) for n in ("readme_banner.png", "og_image.png")]
        print(rid, api.create_commit(rid, ops, commit_message="Card: Linda brand - Linda Assay / Linda Loupe (formerly Linda-Pro / Lite), new logo").commit_url)


def site():
    import subprocess
    subprocess.run(["git", "-C", r"C:\Users\ninja\Desktop\gh_pages_site", "push", "origin", "gh-pages"], check=True)
    subprocess.run(["git", "-C", r"C:\Users\ninja\Desktop\github_public\Linda", "push", "origin", "main"], check=True)


def modal():
    import subprocess
    d = Path(r"C:\Users\ninja\Desktop\modal_demo")
    subprocess.run([str(d / ".venv-modal/Scripts/modal.exe"), "deploy", "modal_app.py"], cwd=d, check=True)


def gh_meta():
    """Описание и домашняя страница репозитория Lendarixon/Linda (старое: «English ... Free for research»)."""
    tok = gh.gh_token()
    code, r = gh.api(tok, "PATCH", f"https://api.github.com/repos/{gh.REPO}",
                     {"description": "Linda - local AI-text detector for English, Russian and Polish: Linda Assay (full ensemble) and "
                                     "Linda Loupe (fast, CPU). Windows app, CLI, models on Hugging Face.",
                      "homepage": "https://lendarixon.github.io/Linda/"})
    print("repo meta:", code, r.get("description"))

def all_steps():
    for f in (site, github, hf_manifest):
        print("==", f.__name__)
        f()

if __name__ == "__main__":
    {"github": github, "hf_manifest": hf_manifest, "hf_readme": hf_readme, "site": site, "modal": modal, "gh_meta": gh_meta, "all": all_steps}[sys.argv[1]]()
