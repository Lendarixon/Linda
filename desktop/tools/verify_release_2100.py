"""Verify source bytecode, bundled resources, MSIX and unchanged model hashes."""
import difflib
import hashlib
import json
import marshal
import os
import struct
import sys
import zipfile
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import repack_exe as repack

ROOT=Path(__file__).resolve().parents[1]
BUILD=Path(os.environ.get('LINDA_BUILD_DIR',str(Path.home()/'Desktop/Linda_2.1.0.0')))
OUT=Path(os.environ.get('LINDA_VERIFY_OUT',str(ROOT/'evidence')))
OUT.mkdir(parents=True,exist_ok=True)


def check_bytecode(exe):
    raw=exe.read_bytes()
    pos=raw.rfind(repack.COOKIE)
    _,length,off,size,pyvers,_=struct.unpack(repack.COOKIE_FMT,raw[pos:pos+struct.calcsize(repack.COOKIE_FMT)])
    assert pyvers==312
    start=pos+struct.calcsize(repack.COOKIE_FMT)-length
    toc=raw[start+off:start+off+size]
    pos=0
    while pos<len(toc):
        length,off,size,_,compressed,kind=struct.unpack(repack.TOC_FMT,toc[pos:pos+struct.calcsize(repack.TOC_FMT)])
        name=toc[pos+struct.calcsize(repack.TOC_FMT):pos+length].rstrip(b'\0').decode()
        if kind==b'z':
            pyz=raw[start+off:start+off+size]
            break
        pos+=length
    assert pyz[:4]==b'PYZ\0'
    pos=struct.unpack('!i',pyz[8:12])[0]
    entries=dict(marshal.loads(pyz[pos:]))
    checked=[]
    for name,(typ,code) in repack.our_modules().items():
        if name not in entries:
            continue
        _,off,size=entries[name]
        actual=zlib.decompress(pyz[off:off+size])
        assert actual==marshal.dumps(code),f'stale module {name}'
        checked.append(name)
    for name in ['linda_desktop','linda_desktop.app','linda_desktop.engine','linda_desktop.i18n']:
        assert name in checked
    return checked


def main():
    result={'bytecode':check_bytecode(BUILD/'app/Linda-Pro.exe'),'resource_files':0}
    for name in ('web','assets'):
        for p in (ROOT/name).rglob('*'):
            if p.is_file():
                dest=BUILD/'app/_internal'/p.relative_to(ROOT)
                assert p.read_bytes()==dest.read_bytes(),str(p)
                result['resource_files']+=1
    models=ROOT/'qa_models'
    manifest=json.loads((models/'manifest.json').read_text(encoding='utf-8'))
    checked=[]
    for entry in manifest.get('all_files',manifest['files']):
        p=models/entry['path']
        assert p.stat().st_size==entry['size'],entry['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],entry['path']
        checked.append(entry['path'])
    result['model_files_hash_verified']=checked
    with zipfile.ZipFile(BUILD/'Linda-Pro_2.1.0.0_x64.msix') as z:
        assert z.testzip() is None
        assert b'Version="2.1.0.0"' in z.read('AppxManifest.xml')
        assert z.read('app/_internal/web/startup.html')==(ROOT/'web/startup.html').read_bytes()
        assert z.read('app/_internal/web/index.html')==(ROOT/'web/index.html').read_bytes()
        result['msix_entries']=len(z.infolist())
    result['pass']=True
    (OUT/'payload-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS',len(result['bytecode']),'source modules,',result['resource_files'],'resource files,',len(checked),'model hashes; MSIX CRC and version')
    archive=Path('G:/Мой диск/Linda_archive/releases/Linda_src_2041.zip')
    diff=[]
    with zipfile.ZipFile(archive) as z:
        for rel in ['linda_desktop/__init__.py','linda_desktop/i18n.py','linda_desktop/engine.py','linda_desktop/app.py','installer/linda.iss']:
            old=z.read('Linda_src_2041/'+rel).decode('utf-8').replace('\r\n','\n')
            new=(ROOT/rel).read_text(encoding='utf-8')
            diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='2.0.7.0/'+rel,tofile='2.1.0.0/'+rel))
    (OUT/'source-changes.diff').write_text(''.join(diff),encoding='utf-8')


if __name__=='__main__':
    main()
