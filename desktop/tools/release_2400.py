# -*- coding: utf-8 -*-
"""Локальная сборка 2.4.0.0 (без публикации): база — готовое приложение 2.3.0.2.

Копирует _internal и верхние DLL базы, проверяет импорт бандла, пересобирает PYZ
(новый __version__ + новые модули 2.4.0.0 из tools/repack_exe.py EXTRA_MODULES),
штампует версию в exe, кладёт CHANGELOG.json и собирает установщик через ISCC.

    python tools/release_2400.py

Ничего не публикует: no push, no Store, no manifest signing.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = Path.home() / 'Desktop'
BASE = Path(os.environ.get('LINDA_BUILD_BASE', str(DESK / 'Linda_2.3.0.2' / 'app')))
BUILD = Path(os.environ.get('LINDA_BUILD_DIR', str(DESK / 'Linda_2.4.0.0')))
VER = '2.4.0.0'
V4 = tuple(int(x) for x in VER.split('.'))


def run(args, **kw):
    subprocess.run(list(map(str, args)), check=True, **kw)


def stamp(exe):
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
        StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
        write_version_info_to_executable)
    info = VSVersionInfo(ffi=FixedFileInfo(filevers=V4, prodvers=V4,
        mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable('040904B0', [StringStruct(k, v) for k, v in {
            'CompanyName': 'Linda', 'FileDescription': 'Linda AI text detector',
            'FileVersion': VER, 'ProductName': 'Linda', 'ProductVersion': VER,
            'OriginalFilename': 'Linda-Pro.exe'}.items()])]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])])
    write_version_info_to_executable(str(exe), info)


def _verify_bundle(internal: Path) -> None:
    """Импортная проверка бандла тем же Python 3.12 до упаковки: роняет сборку при регрессе."""
    code = ("import sys; sys.path.insert(0, %r); "
            "import transformers, peft, torch, requests, huggingface_hub, tokenizers, jinja2, "
            "tqdm, filelock, idna, certifi; "
            "print('bundle-check:', transformers.__version__, peft.__version__, torch.__version__)") % str(internal)
    # -I -S: изолированно, без глобального site-packages. Иначе глобальный torchvision
    # цепляется к бандл-торчу и роняет проверку (RuntimeError: operator torchvision::nms).
    run([sys.executable, '-I', '-S', '-c', code])


def _find_iscc() -> Path:
    env = os.environ.get('LINDA_ISCC')
    if env and Path(env).is_file():
        return Path(env)
    cands = [
        Path.home() / 'AppData/Local/Programs/Inno Setup 6/ISCC.exe',
        Path.home() / 'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe',
        Path(r'C:\Users\ninja\Desktop\LocalDocs\work\release_1410\toolchain\extracted\{app}\ISCC.exe'),
    ]
    for c in cands:
        if c.is_file():
            return c
    raise SystemExit('ISCC не найден; задайте LINDA_ISCC')


def make_installer(app: Path) -> None:
    inst = BUILD / 'installer'
    inst.mkdir(parents=True, exist_ok=True)
    iss = (ROOT / 'installer/linda.iss').read_text(encoding='utf-8')
    iss = iss.replace('..\\dist\\Linda-Pro\\*', str(app / '*'))
    iss = iss.replace('OutputDir=..\\dist', f'OutputDir={BUILD}')
    for name in ['SetupIconFile', 'WizardImageFile', 'WizardSmallImageFile', 'LicenseFile']:
        iss = re.sub(rf'(?m)^{name}=(.+)$',
                     lambda m: f'{name}=' + str((ROOT / 'installer' / m.group(1).strip().replace('\\', '/')).resolve()),
                     iss)
    (inst / 'linda.iss').write_text(iss, encoding='utf-8-sig')
    shutil.copy2(ROOT / 'installer/EULA.txt', inst / 'EULA.txt')
    run([_find_iscc(), inst / 'linda.iss'])


def finalize() -> None:
    app = BUILD / 'app'
    hashes = {}
    for p in [app / 'Linda-Pro.exe', BUILD / 'Linda-Setup.exe']:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[str(p.relative_to(BUILD)).replace('\\', '/')] = {'size': p.stat().st_size, 'sha256': digest}
        p.with_suffix(p.suffix + '.sha256').write_text(digest + '  ' + p.name + '\n', encoding='ascii')
    (BUILD / 'SHA256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print('BUILD COMPLETE', json.dumps(hashes), flush=True)


def build() -> None:
    assert sys.version_info[:2] == (3, 12), 'сборка только под Python 3.12'
    assert not BUILD.exists(), 'Never overwrite a previous candidate'
    assert BASE.is_dir(), f'нет базового приложения: {BASE}'
    assert f'__version__ = "{VER}"' in (ROOT / 'linda_desktop/__init__.py').read_text(encoding='utf-8')
    BUILD.mkdir()
    app = BUILD / 'app'
    app.mkdir()
    shutil.copytree(BASE / '_internal', app / '_internal')
    for dll in ('tcl86t.dll', 'tk86t.dll', 'zlib1.dll'):
        s = BASE / dll
        if s.is_file():
            shutil.copy2(s, app / dll)
    _verify_bundle(app / '_internal')
    run([sys.executable, ROOT / 'tools/repack_exe.py', BASE / 'Linda-Pro.exe', app / 'Linda-Pro.exe',
         '--entry', 'run_app'])
    stamp(app / 'Linda-Pro.exe')
    shutil.copy2(ROOT / 'CHANGELOG.json', app / '_internal/linda_desktop/data/CHANGELOG.json')
    shutil.copy2(ROOT / 'CHANGELOG.json', app / '_internal/CHANGELOG.json')
    make_installer(app)
    finalize()


if __name__ == '__main__':
    if sys.argv[1:] == ['resume']:
        make_installer(BUILD / 'app')
        finalize()
    else:
        build()
