"""Check current public licence copies; never change or upload them."""
from pathlib import Path
root=Path(__file__).resolve().parent
canonical=root/'content'
github=root.parent
for name in ['LICENSE','LICENSING.md','COMMERCIAL_LICENSE.md']:
    assert (canonical/name).read_bytes()==(github/name).read_bytes(),name+' differs'
print('Current licence copies agree; no files changed.')
