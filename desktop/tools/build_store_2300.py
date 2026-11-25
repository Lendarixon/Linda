"""Build Microsoft Store MSIX 2.3.0.0 (local, nothing is published). Run with Python 3.12 that has PyInstaller."""
import hashlib, re, shutil, subprocess, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DESK = Path.home() / 'Desktop'
VER = '2.3.0.0'
APP = DESK / 'Linda_2.3.0.0' / 'app'                 # finished 2.3.0.0 app (run_app entry)
OLD = DESK / 'Linda_2.1.0.0'                          # donor: Store manifest, Assets, frozen base exe
BUILD = DESK / 'Linda_2.3.0.0_Store'
MAKEAPPX = r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe'

def run(a, cwd=None): subprocess.run([str(x) for x in a], check=True, cwd=cwd)

def stamp(exe):
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
        StringStruct, VarFileInfo, VarStruct, write_version_info_to_executable)
    info = VSVersionInfo(ffi=FixedFileInfo(filevers=(2,3,0,0), prodvers=(2,3,0,0), mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
        kids=[StringFileInfo([StringTable('040904B0', [StringStruct(k, v) for k, v in {
            'CompanyName':'Linda', 'FileDescription':'Linda AI text detector', 'FileVersion':VER, 'ProductName':'Linda',
            'ProductVersion':VER, 'OriginalFilename':'Linda-Pro.exe'}.items()])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
    write_version_info_to_executable(str(exe), info)

assert sys.version_info[:2] == (3, 12), 'need Python 3.12'
assert not BUILD.exists(), 'never overwrite a previous build'
store = BUILD / 'store'; store.mkdir(parents=True)
shutil.copy2(OLD / 'store' / 'AppxManifest.xml', store / 'AppxManifest.xml')
shutil.copytree(OLD / 'store' / 'Assets', store / 'Assets')
m = store / 'AppxManifest.xml'
xml = m.read_text(encoding='utf-8')
xml, n = re.subn(r'Version="2\.1\.0\.0"', f'Version="{VER}"', xml, count=1); assert n == 1
m.write_text(xml, encoding='utf-8')
(store / 'app').mkdir()
shutil.copytree(APP / '_internal', store / 'app' / '_internal')
for dll in ('tcl86t.dll', 'tk86t.dll', 'zlib1.dll'): shutil.copy2(APP / dll, store / 'app' / dll)
run([sys.executable, ROOT / 'tools' / 'repack_exe.py', OLD / 'app' / 'Linda-Pro.exe', store / 'app' / 'Linda-Pro.exe', '--entry', 'run_store'], cwd=ROOT)
stamp(store / 'app' / 'Linda-Pro.exe')
excl = BUILD / 'excluded_store_assets'
for i, t in enumerate(list(store.rglob('default-docx-template'))):
    if t.is_dir():
        excl.mkdir(exist_ok=True); shutil.move(str(t), str(excl / f'{i}-default-docx-template'))
msix = BUILD / f'Linda-Pro_{VER}_x64.msix'
run([MAKEAPPX, 'pack', '/d', store, '/p', msix])
sha = hashlib.sha256(msix.read_bytes()).hexdigest()
(BUILD / f'{msix.name}.sha256').write_text(f'{sha}  {msix.name}\n')
with zipfile.ZipFile(msix) as z:
    bad = z.testzip(); mf = z.read('AppxManifest.xml').decode('utf-8')
    print('entries', len(z.namelist()), 'testzip', bad, 'version ok', f'Version="{VER}"' in mf)
print('MSIX', msix, msix.stat().st_size, 'bytes sha256', sha)
