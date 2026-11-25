"""Build unsigned Microsoft Store MSIX package for Linda 2.5.0.4 (manifest 2.5.4.0)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VSVersionInfo,
    VarFileInfo,
    VarStruct,
    write_version_info_to_executable,
)

VER = "2.5.0.4"
V4 = (2, 5, 0, 4)
MANIFEST_VER = "2.5.4.0"

ROOT = Path("D:/Linda_2100_Dev")
DESK = Path.home() / "Desktop"
APP = DESK / f"Linda_{VER}" / "app"
BUILD = DESK / f"Linda_{VER}_Store"

OLD_CANDIDATES = [
    ROOT / "release_prep_20261120" / "store_package" / "Linda_2.4.0.0_Store" / "store",
    Path("D:/Linda_2.3.0.2_Store/store"),
]
MAKEAPPX = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"


def run(cmd: list[object], cwd: Path | None = None) -> None:
    """Run a command and fail fast on non-zero exit code."""
    subprocess.run([str(x) for x in cmd], cwd=str(cwd) if cwd else None, check=True)


def stamp(exe_path: Path) -> None:
    """Stamp PE version resources on Linda-Pro.exe to 2.5.0.4."""
    info = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=V4,
            prodvers=V4,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", "Lindarixon"),
                            StringStruct("FileDescription", "Linda-Pro"),
                            StringStruct("FileVersion", VER),
                            StringStruct("InternalName", "Linda-Pro"),
                            StringStruct("OriginalFilename", "Linda-Pro.exe"),
                            StringStruct("ProductName", "Linda-Pro"),
                            StringStruct("ProductVersion", VER),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
    write_version_info_to_executable(str(exe_path), info)


def sha256_file(path: Path) -> str:
    """Return lowercase hex SHA-256 digest for a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    assert sys.version_info[:2] == (3, 12), f"need Python 3.12, got {sys.version}"
    assert not BUILD.exists(), f"never overwrite a previous build: {BUILD}"
    assert APP.is_dir(), f"missing app payload: {APP}"
    assert Path(MAKEAPPX).is_file(), f"missing makeappx.exe: {MAKEAPPX}"

    old = next((p for p in OLD_CANDIDATES if p.is_dir()), None)
    assert old is not None, f"no donor store folder found in {OLD_CANDIDATES}"

    store = BUILD / "store"
    store.mkdir(parents=True)
    shutil.copy2(old / "AppxManifest.xml", store / "AppxManifest.xml")
    shutil.copytree(old / "Assets", store / "Assets")

    manifest_path = store / "AppxManifest.xml"
    xml = manifest_path.read_text(encoding="utf-8")
    xml, count = re.subn(
        r'Version="\d+\.\d+\.\d+\.\d+"',
        f'Version="{MANIFEST_VER}"',
        xml,
        count=1,
    )
    assert count == 1, "Identity Version attribute not found"
    manifest_path.write_text(xml, encoding="utf-8", newline="")

    (store / "app").mkdir()
    shutil.copytree(APP / "_internal", store / "app" / "_internal")
    for dll in ("tcl86t.dll", "tk86t.dll", "zlib1.dll"):
        src = APP / dll
        if src.is_file():
            shutil.copy2(src, store / "app" / dll)

    exe_out = store / "app" / "Linda-Pro.exe"
    run(
        [
            sys.executable,
            ROOT / "tools" / "repack_exe.py",
            old / "app" / "Linda-Pro.exe",
            exe_out,
            "--entry",
            "run_store",
        ],
        cwd=ROOT,
    )
    stamp(exe_out)

    changelog_src = ROOT / "CHANGELOG.json"
    if changelog_src.is_file():
        shutil.copy2(
            changelog_src,
            store / "app" / "_internal" / "linda_desktop" / "data" / "CHANGELOG.json",
        )
        shutil.copy2(changelog_src, store / "app" / "_internal" / "CHANGELOG.json")

    excl = BUILD / "excluded_store_assets"
    for i, t in enumerate(list(store.rglob("default-docx-template"))):
        if t.is_dir():
            excl.mkdir(exist_ok=True)
            shutil.move(str(t), str(excl / f"{i}-default-docx-template"))

    msix = BUILD / f"Linda-Pro_{MANIFEST_VER}_x64.msix"
    run([MAKEAPPX, "pack", "/d", store, "/p", msix])

    with zipfile.ZipFile(msix, "r") as zf:
        bad = zf.testzip()
        assert bad is None, f"corrupt zip entry: {bad}"
        names = set(zf.namelist())
        assert "AppxManifest.xml" in names, "missing AppxManifest.xml in MSIX"
        assert "app/Linda-Pro.exe" in names, "missing app/Linda-Pro.exe in MSIX"
        packed_manifest = zf.read("AppxManifest.xml").decode("utf-8")
        assert f'Version="{MANIFEST_VER}"' in packed_manifest, "manifest version mismatch in MSIX"

    msix_sha = sha256_file(msix)
    exe_sha = sha256_file(exe_out)
    (BUILD / f"{msix.name}.sha256").write_text(f"{msix_sha}  {msix.name}\n", encoding="utf-8")

    summary = {
        "app_version": VER,
        "manifest_version": MANIFEST_VER,
        "signed": False,
        "msix": {
            "name": msix.name,
            "path": str(msix),
            "size_bytes": msix.stat().st_size,
            "sha256": msix_sha,
        },
        "exe": {
            "name": exe_out.name,
            "path": str(exe_out),
            "size_bytes": exe_out.stat().st_size,
            "sha256": exe_sha,
        },
    }
    (BUILD / "SHA256.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {msix} ({msix.stat().st_size} bytes) sha256={msix_sha}")


if __name__ == "__main__":
    main()
