"""Build a small dedicated parser without desktop/GPU runtime hooks.

Main PyInstaller build includes this under its existing assets data directory.
"""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'assets' / 'document-parser'


def main():
    env = dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--console',
                    '--name','Linda-Document-Worker','--distpath',str(ROOT/'build'/'parser-dist'),
                    '--workpath',str(ROOT/'build'/'parser-work'),'--specpath',str(ROOT/'build'),
                    '--collect-data','docx','--collect-submodules','pypdf','--exclude-module','torch',
                    '--exclude-module','numpy','--exclude-module','webview','--exclude-module','linda_desktop',
                    str(ROOT/'linda_desktop'/'document_worker.py')],env=env,check=True)
    import shutil
    # python-docx also ships its expanded write template. Its [Content_Types].xml
    # path cannot be included by MakeAppx. Reading documents only needs the
    # library; the packed default.docx remains available for write operations.
    shutil.copytree(ROOT/'build'/'parser-dist'/'Linda-Document-Worker',OUTPUT,
                    dirs_exist_ok=True,ignore=shutil.ignore_patterns('default-docx-template'))
    print(OUTPUT)


if __name__ == '__main__':
    main()
