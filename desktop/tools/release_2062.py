"""Build app 2.0.6.2 / Store 2.0.6002.0 without altering previous artifacts.

Usage: python tools/release_2062.py build|manifest
Publication is separate. Existing release_2051 signing code verifies both feeds.
"""
import sys,shutil,re,subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DESK=Path.home()/'Desktop'
BASE=DESK/'Linda_build_2062_review/app'
BASE_STORE=DESK/'Linda_build_2060/store'
BUILD=DESK/'Linda_build_2062_release'
MSIX=DESK/'Linda_Store_upload/Linda-Pro_2.0.6002.0_x64.msix'
VER,STORE_VER='2.0.6.2','2.0.6002.0'

def run(args):subprocess.run(list(map(str,args)),check=True)
def build():
    assert sys.version_info[:2]==(3,12),'Use the frozen payload Python 3.12 runtime'
    assert not BUILD.exists() and not MSIX.exists(),'Preserve existing artifacts'
    assert '__version__ = "2.0.6.2"' in (ROOT/'linda_desktop/__init__.py').read_text(encoding='utf-8')
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
    sys.path.insert(0,str(ROOT))
    import release_2051 as r
    r.VER,r.STORE_VER=VER,STORE_VER
    r.ENTRY=json.loads((ROOT/'CHANGELOG.json').read_text(encoding='utf-8'))[0]
    assert r.ENTRY['version']==VER
    r.URL=f'https://github.com/Lendarixon/Linda/releases/download/v{VER}/Linda-Setup.exe'
    r.OUT=DESK/'Linda_release_2062/repo';r.CHANGED=[]
    stage=BUILD/'manifest_source';(stage/'dist').mkdir(parents=True,exist_ok=True)
    shutil.copy2(BUILD/'Linda-Setup.exe',stage/'dist/Linda-Setup.exe')
    r.ROOT=stage
    r.manifest()
if __name__=='__main__':{'build':build,'manifest':manifest}[sys.argv[1]]()
