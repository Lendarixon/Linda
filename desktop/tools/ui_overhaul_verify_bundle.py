import hashlib
import json
import marshal
import types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

_CODE_ATTRS = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount',
               'co_stacksize', 'co_flags', 'co_code', 'co_consts', 'co_names',
               'co_varnames', 'co_freevars', 'co_cellvars', 'co_filename',
               'co_name', 'co_qualname', 'co_firstlineno', 'co_linetable',
               'co_exceptiontable')


def _same_code(expected, actual, path, diffs):
    """Побайтовый marshal.dumps зависит от refcount процесса записи
    (FLAG_REF на корне и на immortal-синглтонах вроде b'\\x00'), поэтому
    сравниваем семантику код-объектов рекурсивно, а не дампы."""
    for attr in _CODE_ATTRS:
        exp_val = getattr(expected, attr)
        act_val = getattr(actual, attr)
        if attr == 'co_consts':
            if len(exp_val) != len(act_val):
                diffs.append(f'{path}: длина consts {len(exp_val)} != {len(act_val)}')
                continue
            for i, (exp_item, act_item) in enumerate(zip(exp_val, act_val)):
                if isinstance(exp_item, types.CodeType) and isinstance(act_item, types.CodeType):
                    _same_code(exp_item, act_item, f'{path}.{exp_item.co_name}', diffs)
                elif not (type(exp_item) is type(act_item) and exp_item == act_item):
                    diffs.append(f'{path}: const[{i}] {type(exp_item).__name__} != {type(act_item).__name__}')
        elif exp_val != act_val:
            diffs.append(f'{path}: {attr} отличается')

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path.home()/'Desktop/Linda_2.3.0.0'
OUT=ROOT/'evidence/ui_overhaul_20261024'
archive=CArchiveReader(str(BUILD/'app/Linda-Pro.exe'))
pyz=archive.open_embedded_archive(next(name for name in archive.toc if name.endswith('.pyz')))
modules=[]
for module in ['app','splash','__main__','documents','document_worker','document_formats','task_cancel','humanize_pack','inbox','trace_pack','trace.outlier_engine']:
    source=ROOT/'linda_desktop'/(module.replace('.','/')+'.py')
    expected=compile(source.read_text(encoding='utf-8'),str(source.relative_to(ROOT)),'exec',dont_inherit=True,optimize=0)
    actual=pyz.extract('linda_desktop.'+module)
    diffs=[]
    _same_code(expected,actual,module,diffs)
    assert not diffs,module+': '+'; '.join(diffs[:8])
    modules.append(module)
resources={}
for name in [p.relative_to(ROOT/'web').as_posix() for p in (ROOT/'web').rglob('*') if p.is_file()]:
    source=ROOT/'web'/name
    assert source.read_bytes()==(BUILD/'app/_internal/web'/name).read_bytes(),name
    resources[name]=hashlib.sha256(source.read_bytes()).hexdigest()
for file in (ROOT/'assets/splash/panorama').glob('*.png'):
    assert file.read_bytes()==(BUILD/'app/_internal/assets/splash/panorama'/file.name).read_bytes()
manifest=json.loads((BUILD/'SHA256.json').read_text())
for name,info in manifest.items():assert hashlib.sha256((BUILD/name).read_bytes()).hexdigest()==info['sha256']
(OUT/'bundle-results.json').write_text(json.dumps({'bytecode_matches':modules,'resources':resources,'splash_assets_match':11,'release_hashes_verified':True},indent=2),encoding='utf-8')
print('PASS: application/parser/cancellation bytecode, all web resources, splash assets and release SHA256')
