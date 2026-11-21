"""Build app 2.0.7.0 / Store 2.0.7000.0 without altering previous artifacts.

Usage: python tools/release_2070.py build|manifest
Publication is separate. Existing release_2051 signing code verifies both feeds.
"""
import sys,shutil,re,subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DESK=Path.home()/'Desktop'
BASE=DESK/'Linda_build_2062_review/app'
BASE_STORE=DESK/'Linda_build_2060/store'
BUILD=DESK/'Linda_build_2070_release'
MSIX=DESK/'Linda_Store_upload/Linda-Pro_2.0.7000.0_x64.msix'
VER,STORE_VER='2.0.7.0','2.0.7000.0'

def run(args):subprocess.run(list(map(str,args)),check=True)
def build():
    assert sys.version_info[:2]==(3,12),'Use the frozen payload Python 3.12 runtime'
    assert not BUILD.exists() and not MSIX.exists(),'Preserve existing artifacts'
    assert '__version__ = "2.0.7.0"' in (ROOT/'linda_desktop/__init__.py').read_text(encoding='utf-8')
    BUILD.mkdir()
    for dst,entry in [(BUILD/'app','run_app'),(BUILD/'store/app','run_store')]:
        shutil.copytree(BASE,dst)
        run([sys.executable,ROOT/'tools/repack_exe.py',BASE/'Linda-Pro.exe',dst/'Linda-Pro.exe','--entry',entry])
        shutil.copy2(ROOT/'CHANGELOG.json',dst/'_internal/linda_desktop/data/CHANGELOG.json')
    shutil.copytree(BASE_STORE/'Assets',BUILD/'store/Assets')
    xml=(BASE_STORE/'AppxManifest.xml').read_text(encoding='utf-8')
    xml,n=re.subn(r'Version="2\.0\.6000\.0"',f'Version="{STORE_VER}"',xml,count=1);assert n==1
    (BUILD/'store/AppxManifest.xml').write_text(xml,encoding='utf-8')
    template=BUILD/'store/app/_internal/assets/document-parser/_internal/docx/templates/default-docx-template'
    if template.exists():
        excluded=BUILD/'excluded_store_assets';excluded.mkdir()
        # Unused document-writing template contains an OPC-reserved filename.
        shutil.move(str(template),str(excluded/template.name))
    inst=BUILD/'installer';inst.mkdir()
    iss=(ROOT/'installer/linda.iss').read_text(encoding='utf-8')
    iss=iss.replace('..\\dist\\Linda-Pro\\*',str(BUILD/'app/*'));assert str(BUILD/'app/*') in iss
    iss=iss.replace('OutputDir=..\\dist',f'OutputDir={BUILD}')
    for name in ['SetupIconFile','WizardImageFile','WizardSmallImageFile','LicenseFile']:
        iss=re.sub(rf'(?m)^{name}=(.+)$',lambda m:f'{name}='+str((ROOT/'installer'/m.group(1).strip().replace('\\','/')).resolve()),iss)
    (inst/'linda.iss').write_text(iss,encoding='utf-8-sig')
    shutil.copy2(ROOT/'installer/EULA.txt',inst/'EULA.txt')
    run([Path.home()/'AppData/Local/Programs/Antigravity IDE/resources/app/node_modules/innosetup/bin/ISCC.exe',inst/'linda.iss'])
    run([r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe','pack','/d',BUILD/'store','/p',MSIX])
    for p in [BUILD/'Linda-Setup.exe',MSIX]:
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        p.with_suffix(p.suffix+'.sha256').write_text(digest+'  '+p.name+'\n',encoding='ascii')
        print('BUILT',p,p.stat().st_size,digest,flush=True)

def manifest():
    """Signed feed: app 2.0.7.0 + model pack label 1.3.4.1 (weights/thresholds identical to 1.3.4, per owner)."""
    sys.path.insert(0,str(ROOT))
    import base64,urllib.request
    from cryptography.hazmat.primitives import serialization
    from linda_desktop.updater import verify_signature
    base="https://huggingface.co/Lindarixon/Linda-Pro/resolve/main/"
    raw=urllib.request.urlopen(base+'latest.json',timeout=60).read()
    verify_signature(raw,urllib.request.urlopen(base+'latest.json.sig',timeout=60).read())
    m=json.loads(raw)
    assert m['version']=='1.3.4'
    entry=json.loads((ROOT/'CHANGELOG.json').read_text(encoding='utf-8'))[0]
    assert entry['version']==VER
    wn={'en':'• Models 1.3.4.1: minor refresh of the model pack label; weights, thresholds and verdicts are unchanged.',
        'ru':'• Модели 1.3.4.1: небольшое обновление метки пакета моделей; веса, пороги и вердикты не изменены.',
        'pl':'• Modele 1.3.4.1: drobne odświeżenie etykiety pakietu modeli; wagi, progi i werdykty bez zmian.'}
    wentry={'version':'1.3.4.1','date':'2026-10-18','notes':wn['en'],'notes_ru':wn['ru'],'notes_pl':wn['pl'],'notes_en':wn['en'],'notes_i18n':wn,
            'title_i18n':{'ru':'Модели 1.3.4.1: без изменений весов','en':'Models 1.3.4.1: weights unchanged','pl':'Modele 1.3.4.1: wagi bez zmian'}}
    m['version'],m['released']='1.3.4.1','2026-10-18'
    m['notes'],m['notes_i18n']=wn['en'],wn
    setup=(BUILD/'Linda-Setup.exe').read_bytes()
    m['installer'].update(version=VER,url=f'https://github.com/Lendarixon/Linda/releases/download/v{VER}/Linda-Setup.exe',size=len(setup),sha256=hashlib.sha256(setup).hexdigest())
    cl=[e for e in m.get('changelog',[]) if e.get('version') not in (VER,'1.3.4.1')]
    m['changelog']=[entry,wentry]+cl
    new=json.dumps(m,indent=1,ensure_ascii=False).encode('utf-8')
    key=serialization.load_pem_private_key((DESK/'Linda_desktop/keys/linda_signing.key').read_bytes(),password=None)
    sig=base64.b64encode(key.sign(new));verify_signature(new,sig)
    out=DESK/'Linda_release_2070/repo';out.mkdir(parents=True,exist_ok=True)
    (out/'latest.json').write_bytes(new);(out/'latest.json.sig').write_bytes(sig)
    print('manifest signed: pack 1.3.4.1 app',VER,'files',len(m['files']))
if __name__=='__main__':{'build':build,'manifest':manifest}[sys.argv[1]]()
