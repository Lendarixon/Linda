"""Build 2.0.6.0 in a fresh directory; publication is a separate explicit step."""
import sys,shutil,re,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import release_2052
import release_2051 as r
r.VER,r.STORE_VER='2.0.6.0','2.0.6000.0'
r.BUILD=r.DESK/'Linda_build_2060'
r.OUT=r.DESK/'Linda_release_2060/repo'
r.URL=f'https://github.com/Lendarixon/Linda/releases/download/v{r.VER}/Linda-Setup.exe'
r.CHANGED=[]
r.ENTRY={'version':r.VER,'date':'2026-10-11','title':{'en':'Consistent GPU inference and local highlighting','ru':'Согласованные GPU-оценки и локальная разметка','pl':'Spójne oceny GPU i lokalne oznaczenia'},'notes':{
'en':'• Assay uses FP32 stable DirectML on Windows to reduce CPU/GPU score drift; Loupe remains on CPU. GPU memory use is higher than FP16; 4 GB compatibility is not certified.\n• Assay samples the same context anchors on CPU/GPU.\n• Model identity, independent Essay/Multi evidence, Unicode offsets and document extraction are corrected.\n• Selected highlighting, counters, word shares and exports stay synchronized. Document confidence and local coverage are separate.\n• Weights remain 1.3.4. Short AI inserts and edited texts may still be missed; these fixes do not certify detection accuracy.',
'ru':'• Assay использует стабильный FP32 DirectML в Windows для уменьшения расхождений CPU/GPU; Loupe работает на CPU. Расход видеопамяти выше FP16; совместимость с 4 ГБ не сертифицирована.\n• Assay использует одинаковые опорные контексты на CPU/GPU.\n• Исправлены имя модели, независимые данные Essay/Multi, Unicode-смещения и извлечение документов.\n• Выбранная подсветка, счётчики, доли слов и экспорт синхронизированы. Оценка документа и локальное покрытие — разные показатели.\n• Веса остаются 1.3.4. Короткие ИИ-вставки и редактированные тексты могут быть пропущены; эти исправления не сертифицируют точность детекции.',
'pl':'• Assay używa stabilnego FP32 DirectML w Windows, aby ograniczyć różnice CPU/GPU; Loupe pozostaje na CPU. Zużycie VRAM jest wyższe niż FP16; zgodność z 4 GB nie została potwierdzona.\n• Assay wybiera te same konteksty na CPU/GPU.\n• Poprawiono identyfikację modelu, niezależne dane Essay/Multi, przesunięcia Unicode i odczyt dokumentów.\n• Podświetlenie, liczniki, udziały słów i eksport są zsynchronizowane. Ocena dokumentu i lokalne pokrycie to oddzielne wskaźniki.\n• Wagi pozostają 1.3.4. Krótkie wstawki AI i edytowane teksty mogą pozostać niewykryte; poprawki nie certyfikują dokładności.'}}

def build():
    assert not r.BUILD.exists(), 'Preserve previous builds; fresh output required'
    base=r.DESK/'Linda_build_2053'
    app=r.BUILD/'app';store=r.BUILD/'store'
    shutil.copytree(base/'app',app)
    shutil.copytree(base/'store',store)
    for dst,entry in [(app,'run_app'),(store/'app','run_store')]:
        subprocess.run([sys.executable,str(ROOT/'tools/repack_exe.py'),str(base/('app' if entry=='run_app' else 'store/app')/'Linda-Pro.exe'),str(dst/'Linda-Pro.exe'),'--entry',entry],check=True)
        release_2052.set_icon(dst/'Linda-Pro.exe')
        shutil.copy2(ROOT/'CHANGELOG.json',dst/'_internal/linda_desktop/data/CHANGELOG.json')
    p=store/'AppxManifest.xml';s=p.read_text(encoding='utf-8')
    s,n=re.subn(r'Version="2\.0\.\d+\.0"',f'Version="{r.STORE_VER}"',s,count=1);assert n==1
    p.write_text(s,encoding='utf-8')
    # Existing installer dist and installed application are not changed.
    inst=r.BUILD/'installer';inst.mkdir()
    iss=(ROOT/'installer/linda.iss').read_text(encoding='utf-8')
    iss=iss.replace('..\\dist\\Linda-Pro\\*',str(app/'*'))
    assert str(app/'*') in iss
    iss=iss.replace('OutputDir=..\\dist',f'OutputDir={r.BUILD}')
    for name in ['SetupIconFile','WizardImageFile','WizardSmallImageFile','LicenseFile']:
        iss=re.sub(rf'(?m)^{name}=(.+)$',lambda m:f'{name}='+str((ROOT/'installer'/m.group(1).strip().replace('\\','/')).resolve()),iss)
    (inst/'linda.iss').write_text(iss,encoding='utf-8-sig')
    shutil.copy2(ROOT/'installer/EULA.txt',inst/'EULA.txt')
    subprocess.run([r'C:\Users\ninja\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe',str(inst/'linda.iss')],check=True)
    msix=r.DESK/'Linda_Store_upload'/f'Linda-Pro_{r.STORE_VER}_x64.msix'
    # Expanded python-docx write template contains an OPC-reserved filename;
    # preserve it outside the MSIX payload. The parser reads supplied files.
    template=store/'app/_internal/assets/document-parser/_internal/docx/templates/default-docx-template'
    if template.exists():
        excluded=r.BUILD/'excluded_store_assets';excluded.mkdir(exist_ok=True)
        shutil.move(str(template),str(excluded/'default-docx-template'))
    assert not msix.exists()
    subprocess.run([r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\makeappx.exe','pack','/d',str(store),'/p',str(msix)],check=True)
    print('BUILT',r.BUILD,msix)

def manifest():
    # r.manifest only reads the installer from ROOT/dist; use a private staging
    # root for this path while retaining tested verification and signing code.
    sys.path.insert(0,str(ROOT))
    original=r.ROOT
    staged=r.BUILD/'manifest_source';(staged/'dist').mkdir(parents=True,exist_ok=True)
    shutil.copy2(r.BUILD/'Linda-Setup.exe',staged/'dist/Linda-Setup.exe')
    r.ROOT=staged
    try:r.manifest()
    finally:r.ROOT=original

if __name__=='__main__': {'bump':r.bump,'build':build,'manifest':manifest}[sys.argv[1]]()
