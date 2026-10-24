"""Build a local 2.1.0.0 candidate; publishing/installing is a separate operation."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = Path.home() / 'Desktop'
BASE = Path(os.environ.get('LINDA_BUILD_BASE', str(Path.home() / 'AppData/Local/Programs/Linda-Pro')))
BUILD = Path(os.environ.get('LINDA_BUILD_DIR', str(DESK / 'Linda_2.1.0.0')))
VER = '2.1.0.0'


def run(args):
    subprocess.run(list(map(str, args)), check=True)


def stamp(exe):
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
        StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
        write_version_info_to_executable)
    info = VSVersionInfo(ffi=FixedFileInfo(filevers=(2,1,0,0), prodvers=(2,1,0,0),
        mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
        kids=[StringFileInfo([StringTable('040904B0', [StringStruct(k,v) for k,v in {
            'CompanyName':'Linda', 'FileDescription':'Linda AI text detector',
            'FileVersion':VER, 'ProductName':'Linda', 'ProductVersion':VER,
            'OriginalFilename':'Linda-Pro.exe'}.items()])]),
            VarFileInfo([VarStruct('Translation',[1033,1200])])])
    write_version_info_to_executable(str(exe), info)


def build():
    assert sys.version_info[:2] == (3,12)
    assert not BUILD.exists(), 'Never overwrite a previous candidate'
    assert f'__version__ = "{VER}"' in (ROOT/'linda_desktop/__init__.py').read_text(encoding='utf-8')
    BUILD.mkdir()
    app = BUILD/'app'
    app.mkdir()
    shutil.copytree(BASE/'_internal', app/'_internal')
    run([sys.executable, ROOT/'tools/repack_exe.py', BASE/'Linda-Pro.exe', app/'Linda-Pro.exe', '--entry', 'run_app'])
    stamp(app/'Linda-Pro.exe')
    shutil.copy2(ROOT/'CHANGELOG.json', app/'_internal/linda_desktop/data/CHANGELOG.json')
    inst = BUILD/'installer'
    inst.mkdir()
    iss = (ROOT/'installer/linda.iss').read_text(encoding='utf-8')
    iss = iss.replace('..\\dist\\Linda-Pro\\*',str(app/'*'))
    iss = iss.replace('OutputDir=..\\dist',f'OutputDir={BUILD}')
    for name in ['SetupIconFile','WizardImageFile','WizardSmallImageFile','LicenseFile']:
        iss = re.sub(rf'(?m)^{name}=(.+)$',lambda m:f'{name}='+str((ROOT/'installer'/m.group(1).strip().replace('\\','/')).resolve()),iss)
    (inst/'linda.iss').write_text(iss,encoding='utf-8-sig')
    shutil.copy2(ROOT/'installer/EULA.txt',inst/'EULA.txt')
    run([Path.home()/'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe',inst/'linda.iss'])
    store = BUILD/'store'
    archive = Path('G:/Мой диск/Linda_archive/builds/Linda_build_2070_release.zip')
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            prefix = 'Linda_build_2070_release/store/'
            if entry.filename == prefix+'AppxManifest.xml' or entry.filename.startswith(prefix+'Assets/'):
                rel = entry.filename[len(prefix):]
                if not rel or entry.is_dir():
                    continue
                dest = store/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read(entry))
    manifest = store/'AppxManifest.xml'
    xml = manifest.read_text(encoding='utf-8')
    xml,n = re.subn(r'Version="2\.0\.7000\.0"',f'Version="{VER}"',xml,count=1)
    assert n == 1
    manifest.write_text(xml,encoding='utf-8')
    shutil.copytree(app,store/'app')
    run([sys.executable,ROOT/'tools/repack_exe.py',BASE/'Linda-Pro.exe',store/'app/Linda-Pro.exe','--entry','run_store'])
    stamp(store/'app/Linda-Pro.exe')
    exclude_store_templates(store)
    msix=BUILD/f'Linda-Pro_{VER}_x64.msix'
    run([r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe','pack','/d',store,'/p',msix])
    finalize()


def exclude_store_templates(store):
    # Both the main runtime and the isolated parser may carry this unused
    # document-writing template; its OPC-reserved name is invalid in an MSIX.
    for index,template in enumerate(store.rglob('default-docx-template')):
        if template.is_dir():
            excluded=BUILD/'excluded_store_assets'
            excluded.mkdir(exist_ok=True)
            shutil.move(str(template),str(excluded/f'{index}-default-docx-template'))


def finalize():
    app=BUILD/'app'
    msix=BUILD/f'Linda-Pro_{VER}_x64.msix'
    hashes={}
    for p in [app/'Linda-Pro.exe',BUILD/'Linda-Setup.exe',msix]:
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[str(p.relative_to(BUILD))]={'size':p.stat().st_size,'sha256':digest}
        p.with_suffix(p.suffix+'.sha256').write_text(digest+'  '+p.name+'\n',encoding='ascii')
    (BUILD/'SHA256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    print('BUILD COMPLETE',json.dumps(hashes),flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['refresh-web']:
        for dest in [BUILD/'app/_internal/web',BUILD/'store/app/_internal/web']:
            shutil.copytree(ROOT/'web',dest,dirs_exist_ok=True)
        run([Path.home()/'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe',BUILD/'installer/linda.iss'])
        run([r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe','pack','/o','/d',BUILD/'store','/p',BUILD/f'Linda-Pro_{VER}_x64.msix'])
        finalize()
    elif sys.argv[1:] == ['resume-store']:
        exclude_store_templates(BUILD/'store')
        run([r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe','pack','/d',BUILD/'store','/p',BUILD/f'Linda-Pro_{VER}_x64.msix'])
        finalize()
    else:
        build()
