# -*- coding: utf-8 -*-
"""Builds a stand-in "repository v1.1.1" for the update test: models/ is a junction to the real staged weights (nothing is copied), calibration/ is a copy plus one
new file, plus the signed latest.json that announces version 1.1.1, the new installer and a note. ASCII output.
    python tools/make_test_repo.py SRC_DIR OUT_DIR INSTALLER_EXE INSTALLER_URL [--bad-hash]"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_manifest as mm  # noqa: E402

src, out, inst, url = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
if out.exists():
    subprocess.run(["cmd", "/c", "rmdir", str(out / "models")], capture_output=True)  # removes the junction only, not the target
    shutil.rmtree(out)
out.mkdir(parents=True)
subprocess.run(["cmd", "/c", "mklink", "/J", str(out / "models"), str(src / "models")], check=True, capture_output=True)
shutil.copytree(src / "calibration", out / "calibration")
(out / "calibration" / "release_notes.txt").write_text("test file added in 1.1.1\n")
shutil.copy2(inst, out / inst.name)


class A:
    src = str(out)
    version = "1.1.1"
    min_app = "1.1.0"
    notes = "Test update: new calibration notes"
    installer_url = url
    installer_file = str(inst)
    installer_version = "1.1.1"
    out = str(out)


mm.build(A)
if "--bad-hash" in sys.argv:
    p = out / "latest.json"
    m = json.loads(p.read_text())
    m["installer"]["sha256"] = "0" * 64
    raw = json.dumps(m, indent=1).encode()
    p.write_bytes(raw)
    import base64
    (out / "latest.json.sig").write_bytes(base64.b64encode(mm.load_key().sign(raw)))
    print("manifest re-signed with a WRONG installer hash")
