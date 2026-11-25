"""Build Microsoft Store MSIX 2.4.0.0 (local only: nothing is signed with a real cert, nothing is submitted).

Adapted from tools/build_store_2302.py. Differences:
  * app payload = C:/Users/ninja/Desktop/Linda_2.4.0.0_final/app (the release build);
  * donor (AppxManifest, Assets, frozen base exe) = D:/Linda_2.3.0.2_Store/store;
  * package version = 2.4.0.0 (Store accepts only revision 0, and 2.4.0.0 already is);
  * output tree = D:/Linda_2100_Dev/release_prep_20261120/store_package.

Run with Python 3.12 that has PyInstaller:
    C:/Users/ninja/AppData/Local/Programs/Python/Python312/python.exe tools/build_store_2400.py
"""
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREP = Path("D:/Linda_2100_Dev/release_prep_20261120")
VER = "2.4.0.0"
MANIFEST_VER = "2.4.0.0"          # Store: revision must be 0
APP = Path.home() / "Desktop" / "Linda_2.4.0.0_final" / "app"
OLD = Path("D:/Linda_2.3.0.2_Store") / "store"   # donor: AppxManifest, Assets, frozen base exe (same Identity)
BUILD = PREP / "store_package" / f"Linda_2.4.0.0_Store"
MAKEAPPX = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe"


def run(a, cwd=None):
    subprocess.run([str(x) for x in a], check=True, cwd=cwd)


def stamp(exe):
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
        StringStruct, VarFileInfo, VarStruct, write_version_info_to_executable,
    )
    info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=(2, 4, 0, 0), prodvers=(2, 4, 0, 0), mask=0x3F, flags=0,
                          OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable("040904B0", [StringStruct(k, v) for k, v in {
            "CompanyName": "Linda", "FileDescription": "Linda AI text detector",
            "FileVersion": VER, "ProductName": "Linda",
            "ProductVersion": VER, "OriginalFilename": "Linda-Pro.exe"}.items()])]),
              VarFileInfo([VarStruct("Translation", [1033, 1200])])])
    write_version_info_to_executable(str(exe), info)


assert sys.version_info[:2] == (3, 12), "need Python 3.12"
assert not BUILD.exists(), "never overwrite a previous build"
assert APP.is_dir(), APP

store = BUILD / "store"
store.mkdir(parents=True)
shutil.copy2(OLD / "AppxManifest.xml", store / "AppxManifest.xml")
shutil.copytree(OLD / "Assets", store / "Assets")

m = store / "AppxManifest.xml"
xml = m.read_text(encoding="utf-8")
xml, n = re.subn(r'Version="\d+\.\d+\.\d+\.\d+"', f'Version="{MANIFEST_VER}"', xml, count=1)
assert n == 1, "Identity Version attribute not found"
m.write_text(xml, encoding="utf-8", newline="")

(store / "app").mkdir()
shutil.copytree(APP / "_internal", store / "app" / "_internal")
for dll in ("tcl86t.dll", "tk86t.dll", "zlib1.dll"):
    shutil.copy2(APP / dll, store / "app" / dll)

# The launcher script is swapped to run_store; the rest of the frozen base (loader, libs,
# every non-linda module) is carried over byte-for-byte from the donor exe.
run([sys.executable, ROOT / "tools" / "repack_exe.py", OLD / "app" / "Linda-Pro.exe",
     store / "app" / "Linda-Pro.exe", "--entry", "run_store"], cwd=ROOT)
stamp(store / "app" / "Linda-Pro.exe")

# makeappx refuses these symlinked template dirs; the app regenerates them at runtime.
excl = BUILD / "excluded_store_assets"
for i, t in enumerate(list(store.rglob("default-docx-template"))):
    if t.is_dir():
        excl.mkdir(exist_ok=True)
        shutil.move(str(t), str(excl / f"{i}-default-docx-template"))

msix = BUILD / f"Linda-Pro_{MANIFEST_VER}_x64.msix"
run([MAKEAPPX, "pack", "/d", store, "/p", msix])
sha = hashlib.sha256(msix.read_bytes()).hexdigest()
(BUILD / f"{msix.name}.sha256").write_text(f"{sha}  {msix.name}\n", encoding="utf-8", newline="")

with zipfile.ZipFile(msix) as z:
    bad = z.testzip()
    names = z.namelist()
    mf = z.read("AppxManifest.xml").decode("utf-8")
print("entries", len(names), "testzip", bad,
      "manifest version ok", f'Version="{MANIFEST_VER}"' in mf,
      "entry run_store present", any(n.endswith("Linda-Pro.exe") for n in names))
print("MSIX", msix, msix.stat().st_size, "bytes sha256", sha)
print("UNSIGNED: no certificate is applied; signing and Store submission are owner steps.")
