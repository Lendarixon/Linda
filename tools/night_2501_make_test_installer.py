# -*- coding: utf-8 -*-
"""Build a TestInstall variant of the 2.5.0.1 installer for E2E scenario runs.

Uses the already-built app payload at Desktop/Linda_2.5.0.1/app and a separate
AppId (TestInstall) so scenarios never touch a real Linda installation.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r'D:/Linda_2100_Dev')
BUILD = Path(r'C:/Users/ninja/Desktop/Linda_2.5.0.1')
INST = ROOT / 'work/night_2501/inst'
ISCC = Path.home() / 'AppData/Local/Programs/Inno Setup 6/ISCC.exe'

INST.mkdir(parents=True, exist_ok=True)
iss = (ROOT / 'installer/linda.iss').read_text(encoding='utf-8')
iss = iss.replace('..\\dist\\Linda-Pro\\*', str(BUILD / 'app' / '*'))
iss = iss.replace('OutputDir=..\\dist', 'OutputDir=' + str(INST).replace('\\', '/'))
for name in ['SetupIconFile', 'WizardImageFile', 'WizardSmallImageFile', 'LicenseFile']:
    iss = re.sub(rf'(?m)^{name}=(.+)$',
                 lambda m: f'{name}=' + str((ROOT / 'installer' / m.group(1).strip().replace('\\', '/')).resolve()),
                 iss)
(INST / 'linda_test.iss').write_text('#define TestInstall 1\n' + iss, encoding='utf-8-sig')
shutil.copy2(ROOT / 'installer/EULA.txt', INST / 'EULA.txt')
r = subprocess.run([str(ISCC), str(INST / 'linda_test.iss')], text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(r.stdout[-3000:])
sys.exit(r.returncode)
