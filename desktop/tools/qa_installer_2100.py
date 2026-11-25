"""Install an identical TestInstall payload with a separate AppId/data folder."""
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/installer'
DEST=OUT/'installed-test'
SETUP=OUT/'Linda-Setup-test.exe'
BASE=Path.home()/'Desktop/Linda_2.1.0.0/app'
results=[]
for language in ['english','polish','russian']:
    args=[str(SETUP),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/TASKS=',
          f'/LANG={language}',f'/DIR={DEST}',f'/LOG={OUT/(language+".log")}', '/MODELSET=lite']
    run=subprocess.run(args,timeout=120,check=True)
    assert (DEST/'Linda-Pro.exe').read_bytes()==(BASE/'Linda-Pro.exe').read_bytes()
    for rel in ['web/index.html','web/startup.html','web/i18n/en.json','web/i18n/pl.json','web/i18n/ru.json']:
        assert (DEST/'_internal'/rel).read_bytes()==(BASE/'_internal'/rel).read_bytes()
    chosen=json.loads((Path.home()/'AppData/Local/Linda-Pro (test)/installer_choice.json').read_text(encoding='utf-8'))
    assert chosen['language']=={'english':'en','polish':'pl','russian':'ru'}[language],chosen
    results.append({'language':language,'pass':True,'installer_choice':chosen})
    print('INSTALL PASS',language,flush=True)
subprocess.run([str(DEST/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],timeout=90,check=True)
assert not (DEST/'Linda-Pro.exe').exists()
(OUT/'results.json').write_text(json.dumps({'installations':results,'uninstall_pass':True},indent=2),encoding='utf-8')
print('PASS: 3 isolated installer languages; exact EXE/UI payload; uninstalled test app',flush=True)
