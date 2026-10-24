# -*- coding: utf-8 -*-
"""Сборка коммерческого 2.2.0.0: инкрементальная (база — проверенная app 2.1.0.0),
плюс Trace-данные, tcl/tk для сплэша и torch-стек cp312 для гуманайзера.

    python tools/release_2200.py            # полная сборка + установщик
    python tools/release_2200.py refresh-web  # только web/ + пересборка установщика

Требования: ISCC (Inno), интернет для pip download, ~5 ГБ свободно.
"""
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
BASE = Path(os.environ.get('LINDA_BUILD_BASE', str(DESK / 'Linda_2.1.0.0' / 'app')))
BUILD = Path(os.environ.get('LINDA_BUILD_DIR', str(DESK / 'Linda_2.3.0.0')))
VER = '2.3.0.0'
PY312 = Path(r'C:\Users\ninja\AppData\Local\Programs\Python\Python312')

TORCH_INDEX = 'https://download.pytorch.org/whl/cpu'
TORCH_STACK = ['torch', 'transformers', 'peft', 'accelerate', 'tokenizers', 'tqdm',
               'fsspec', 'sympy', 'networkx', 'jinja2', 'mpmath', 'typing_extensions',
               'psutil', 'sentencepiece']


def run(args, **kw):
    subprocess.run(list(map(str, args)), check=True, **kw)


def stamp(exe):
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
        StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
        write_version_info_to_executable)
    info = VSVersionInfo(ffi=FixedFileInfo(filevers=(2,3,0,0), prodvers=(2,3,0,0),
        mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)),
        kids=[StringFileInfo([StringTable('040904B0', [StringStruct(k,v) for k,v in {
            'CompanyName':'Linda', 'FileDescription':'Linda AI text detector',
            'FileVersion':VER, 'ProductName':'Linda', 'ProductVersion':VER,
            'OriginalFilename':'Linda-Pro.exe'}.items()])]),
            VarFileInfo([VarStruct('Translation',[1033,1200])])])
    write_version_info_to_executable(str(exe), info)


def sync_splash_assets(internal: Path) -> None:
    """Панорамы-гифки сплэша (assets/splash/<lang>/detector.gif) в бандл."""
    src = ROOT / 'assets' / 'splash'
    if src.is_dir():
        shutil.copytree(src, internal / 'assets' / 'splash', dirs_exist_ok=True)
    print('splash-панорама: готово')


def sync_trace_data(internal: Path) -> None:
    """Trace payload + адаптеры гуманайзера как файлы (нужны и dev-импорту через sys.path, и frozen)."""
    # Базовый бандл несёт dist-info-заглушки ФАЙЛАМИ (ломают importlib.metadata -> Invalid version: None):
    # сносим все, настоящие приедут из колёс ниже.
    for stub in list(internal.glob('*.dist-info')) + list(internal.glob('*.egg-info')):
        if not stub.is_dir():
            _force_remove(stub)
    dest = internal / 'linda_desktop' / 'trace'
    dest.mkdir(parents=True, exist_ok=True)
    src = ROOT / 'linda_desktop' / 'trace'
    for name in ('char_ngrams_model.json', 'humanizer_adapter_lite.safetensors',
                 'humanizer_adapter_lite_config.json', 'humanizer_adapter_full.safetensors',
                 'humanizer_adapter_full_config.json'):
        s = src / name
        if s.is_file():
            shutil.copy2(s, dest / name)
    vendor = dest / 'vendor'
    vendor.mkdir(exist_ok=True)
    print(f'trace-данные: {sum(1 for _ in dest.rglob("*") if _.is_file())} файлов')


def sync_tk(internal: Path) -> None:
    """tcl/tk + _tkinter + пакет tkinter для сплэша в упакованном приложении (Python 3.12)."""
    tcl = PY312 / 'tcl'
    for sub in ('tcl8.6', 'tk8.6'):
        s = tcl / sub
        if s.is_dir():
            shutil.copytree(s, internal / sub, dirs_exist_ok=True)
    for dll in ('tcl86t.dll', 'tk86t.dll', 'zlib1.dll'):  # zlib1: зависимость tcl86t
        s = PY312 / 'DLLs' / dll
        if s.is_file():
            shutil.copy2(s, internal / dll)
    pyd = PY312 / 'DLLs' / '_tkinter.pyd'
    if pyd.is_file():
        shutil.copy2(pyd, internal / '_tkinter.pyd')
    for dll in ('tcl86t.dll', 'tk86t.dll', 'zlib1.dll'):
        s = PY312 / 'DLLs' / dll
        if s.is_file():
            shutil.copy2(s, internal.parent / dll)
    tkpkg = Path(sys.base_prefix) / 'Lib' / 'tkinter'
    if tkpkg.is_dir():
        shutil.copytree(tkpkg, internal / 'tkinter', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'), dirs_exist_ok=True)
    print('tcl/tk + tkinter для сплэша: готово')


# Точный рантайм гуманайзера: пары с transformers 4.57.6 (пакет детектора).
# Всё ставится принудительно поверх обрезанных копий базового бандла.
HF_STACK = {
    'huggingface_hub': 'huggingface_hub==0.36.2',
    'peft': 'peft==0.17.1',
    'tokenizers': 'tokenizers==0.22.1',
    'requests': 'requests==2.34.2',
    'urllib3': 'urllib3==2.8.0',
    'idna': 'idna==3.20',
    'tqdm': 'tqdm==4.70.1',
    'filelock': 'filelock==4.2.4',
    'jinja2': 'jinja2==3.1.6',
    'certifi': 'certifi==2026.10.23',
    'markupsafe': 'markupsafe==3.0.4',
    'safetensors': 'safetensors==0.8.0',
    'pillow': 'pillow==12.3.0',
    'charset-normalizer': 'charset-normalizer==3.5.2',
    'typing_extensions': 'typing_extensions==4.16.0',
    'packaging': 'packaging==26.3',
    'pyyaml': 'pyyaml==6.0.3',
    'narwhals': 'narwhals==2.27.1',
    'joblib': 'joblib==1.4.2',
    'threadpoolctl': 'threadpoolctl==3.5.0',
    'scikit-learn': 'scikit-learn==1.9.1',
    'scipy': 'scipy==1.18.1',
    'regex': 'regex==2026.9.29',
}


def _unpack_wheel(internal: Path, whl: Path, skip_tests: bool = False) -> None:
    """Распаковать wheel, переживая записи каталогов без слэша и read-only файлы."""
    with zipfile.ZipFile(whl) as z:
        for entry in z.infolist():
            name = entry.filename
            no_slash = '/' not in name.rstrip('/')
            looks_dir = entry.is_dir() or (no_slash and (name.endswith(('.dist-info', '.egg-info')) or '.' not in name))
            if looks_dir:
                p = internal / name
                if p.exists() and not p.is_dir():
                    _force_remove(p)
                p.mkdir(parents=True, exist_ok=True)
                continue
            if skip_tests and '/tests/' in name.replace('\\', '/'):
                continue
            dest = internal / name
            if dest.exists() and not dest.is_dir():
                _force_remove(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(entry) as src, open(dest, 'wb') as out:
                shutil.copyfileobj(src, out)


def sync_hf_stack(internal: Path) -> None:
    """Полный стек transformers/peft/hf_hub/зависимости: скачать пины и ПЕРЕЗАПИСАТЬ стабы бандла."""
    stage = Path(os.environ.get('TEMP', str(Path.home()))) / 'linda2200_wheels'
    stage.mkdir(parents=True, exist_ok=True)
    specs = sorted(set(HF_STACK.values()))
    run([sys.executable, '-m', 'pip', 'download', '--dest', str(stage), '--only-binary=:all:',
         '--python-version', '3.12', '--platform', 'win_amd64', '--abi', 'cp312', *specs])
    def _pick(dist: str, ver: str) -> Path | None:
        prefix = (dist.replace('-', '_') + '-' + ver).lower()
        cands = [w for w in stage.glob('*.whl') if w.name.lower().startswith(prefix + '-') or w.name.lower().startswith(prefix + '.')]
        cands.sort(key=lambda w: (len(w.name), w.name))
        return cands[0] if cands else None
    wanted: dict[str, Path] = {}
    for top, spec in HF_STACK.items():
        ver = spec.split('==')[1]
        whl = _pick(top, ver)
        if whl is None:
            raise RuntimeError('no wheel downloaded for %s' % spec)
        wanted[top] = whl
    for top, whl in sorted(wanted.items()):
        real_top = {'charset_normalizer': 'charset_normalizer', 'typing_extensions': 'typing_extensions'}.get(top, top)
        target = internal / real_top
        _force_remove(internal / (real_top + chr(46)+chr(112)+chr(121)))
        if target.is_dir() or target.is_file():
            if target.is_dir() and not target.is_symlink():
                _force_remove(target)
            else:
                try:
                    _force_remove(target)
                except OSError:
                    pass
        dash = top.replace('_', '-')
        stale = [d for d in internal.iterdir() if d.name.replace('_', '-').startswith(dash + '-') and (d.name.endswith('.dist-info') or d.name.endswith('.egg-info'))]
        for d in stale:
            if d.is_dir() and not d.is_symlink():
                _force_remove(d)
            else:
                try:
                    _force_remove(d)
                except OSError:
                    pass
        _unpack_wheel(internal, whl)
        print('hf-стек: обновлён', whl.name, flush=True)
    print('hf-стек: готово')


def sync_torch_stack(internal: Path) -> None:
    """torch CPU + transformers/peft/зависимости (cp312) в _internal. Пропускает то, что уже есть."""
    stage = Path(os.environ.get('TEMP', str(Path.home()))) / 'linda2200_wheels'
    stage.mkdir(parents=True, exist_ok=True)
    def _present(p: str) -> bool:
        if (internal / p).is_dir() or (internal / f'{p}.py').is_file():
            return True
        return any(d.is_dir() and d.name.startswith(p + '-') for d in internal.iterdir())
    missing = [p for p in TORCH_STACK if not _present(p)]
    if not missing:
        print('torch-стек: всё уже в бандле')
        return
    print('torch-стек: качаю', ', '.join(missing))
    cmd = [sys.executable, '-m', 'pip', 'download', '--dest', str(stage), '--only-binary=:all:',
           '--python-version', '3.12', '--platform', 'win_amd64', '--abi', 'cp312']
    torch_only = [p for p in missing if p in ('torch',)]
    other = [p for p in missing if p not in ('torch',)]
    if torch_only:
        run(cmd + ['--index-url', TORCH_INDEX] + torch_only)
    if other:
        run(cmd + other)
    for whl in stage.glob('*.whl'):
        with zipfile.ZipFile(whl) as z:
            for entry in z.infolist():
                if entry.is_dir() or '/tests/' in entry.filename.replace('\\', '/'):
                    continue
                top = entry.filename.split('/')[0]
                if '-' in top and top.endswith(('.dist-info', '.egg-info')):
                    dest = internal / top
                else:
                    # пропускаем то, что уже есть в бандле (numpy и т.п.), кроме наших целей
                    if (internal / top).exists() and top not in missing:
                        continue
                    dest = internal / entry.filename
                if not dest.parent.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    with z.open(entry) as src, open(dest, 'wb') as out:
                        shutil.copyfileobj(src, out)
    print('torch-стек: распакован в _internal')


def _force_remove(path: Path) -> None:
    try:
        if path.is_dir() and not path.is_symlink():
            import stat as _stat

            for root, dirs, files in os.walk(path):
                for n in dirs + files:
                    try:
                        os.chmod(os.path.join(root, n), _stat.S_IWRITE)
                    except OSError:
                        pass
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                import stat as _stat

                os.chmod(path, _stat.S_IWRITE)
            except OSError:
                pass
            try:
                path.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _verify_bundle(internal: Path) -> None:
    """Импортная проверка бандла тем же Python 3.12 до упаковки: роняет сборку при регрессе."""
    code = ("import sys; sys.path.insert(0, %r); "
            "import transformers, peft, torch, requests, huggingface_hub, tokenizers, jinja2, tqdm, filelock, idna, certifi; "
            "print('bundle-check:', transformers.__version__, peft.__version__, torch.__version__)") % str(internal)
    run([sys.executable, "-c", code])


def build():
    assert sys.version_info[:2] == (3, 12), 'сборка только под Python 3.12'
    assert not BUILD.exists(), 'Never overwrite a previous candidate'
    assert f'__version__ = "{VER}"' in (ROOT / 'linda_desktop/__init__.py').read_text(encoding='utf-8')
    BUILD.mkdir()
    app = BUILD / 'app'
    app.mkdir()
    shutil.copytree(BASE / '_internal', app / '_internal')
    sync_trace_data(app / '_internal')
    sync_splash_assets(app / '_internal')
    sync_tk(app / '_internal')
    sync_hf_stack(app / '_internal')
    sync_torch_stack(app / '_internal')
    _verify_bundle(app / '_internal')
    run([sys.executable, ROOT / 'tools/repack_exe.py', BASE / 'Linda-Pro.exe', app / 'Linda-Pro.exe', '--entry', 'run_app'])
    stamp(app / 'Linda-Pro.exe')
    shutil.copy2(ROOT / 'CHANGELOG.json', app / '_internal/linda_desktop/data/CHANGELOG.json')
    inst = BUILD / 'installer'
    inst.mkdir()
    iss = (ROOT / 'installer/linda.iss').read_text(encoding='utf-8')
    iss = iss.replace('..\\dist\\Linda-Pro\\*', str(app / '*'))
    iss = iss.replace('OutputDir=..\\dist', f'OutputDir={BUILD}')
    for name in ['SetupIconFile', 'WizardImageFile', 'WizardSmallImageFile', 'LicenseFile']:
        iss = re.sub(rf'(?m)^{name}=(.+)$', lambda m: f'{name}=' + str((ROOT / 'installer' / m.group(1).strip().replace('\\', '/')).resolve()), iss)
    (inst / 'linda.iss').write_text(iss, encoding='utf-8-sig')
    shutil.copy2(ROOT / 'installer/EULA.txt', inst / 'EULA.txt')
    iscc = Path.home() / 'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe'
    run([iscc, inst / 'linda.iss'])
    finalize()


def finalize():
    app = BUILD / 'app'
    hashes = {}
    for p in [app / 'Linda-Pro.exe', BUILD / 'Linda-Setup.exe']:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[str(p.relative_to(BUILD))] = {'size': p.stat().st_size, 'sha256': digest}
        p.with_suffix(p.suffix + '.sha256').write_text(digest + '  ' + p.name + '\n', encoding='ascii')
    (BUILD / 'SHA256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print('BUILD COMPLETE', json.dumps(hashes), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['refresh-web']:
        for dest in [BUILD / 'app/_internal/web']:
            shutil.copytree(ROOT / 'web', dest, dirs_exist_ok=True)
        iscc = Path.home() / 'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe'
        run([iscc, BUILD / 'installer/linda.iss'])
        finalize()
    elif sys.argv[1:] == ['resume']:
        # продолжить после упавшего шага: штамп + установщик + финал
        app = BUILD / 'app'
        stamp(app / 'Linda-Pro.exe')
        shutil.copy2(ROOT / 'CHANGELOG.json', app / '_internal/linda_desktop/data/CHANGELOG.json')
        inst = BUILD / 'installer'
        inst.mkdir(exist_ok=True)
        iss = (ROOT / 'installer/linda.iss').read_text(encoding='utf-8')
        iss = iss.replace('..\\dist\\Linda-Pro\\*', str(app / '*'))
        iss = iss.replace('OutputDir=..\\dist', f'OutputDir={BUILD}')
        for name in ['SetupIconFile', 'WizardImageFile', 'WizardSmallImageFile', 'LicenseFile']:
            iss = re.sub(rf'(?m)^{name}=(.+)$', lambda m: f'{name}=' + str((ROOT / 'installer' / m.group(1).strip().replace('\\', '/')).resolve()), iss)
        (inst / 'linda.iss').write_text(iss, encoding='utf-8-sig')
        shutil.copy2(ROOT / 'installer/EULA.txt', inst / 'EULA.txt')
        iscc = Path.home() / 'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe'
        run([iscc, inst / 'linda.iss'])
        finalize()
    else:
        build()
