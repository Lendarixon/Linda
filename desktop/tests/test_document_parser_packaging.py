from pathlib import Path
import sys
import pytest
from linda_desktop import document_sandbox as sandbox


def test_frozen_parser_uses_bundled_assets_only(tmp_path, monkeypatch):
    bundled = tmp_path/'bundle'/'assets'/'document-parser'
    bundled.mkdir(parents=True)
    (bundled/'Linda-Document-Worker.exe').write_bytes(b'synthetic trusted worker')
    output = tmp_path/'runtime'
    output.mkdir()
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(tmp_path/'bundle'),raising=False)
    assert sandbox.stage_runtime(output) == [str(output/'Linda-Document-Worker.exe')]
    assert (output/'Linda-Document-Worker.exe').read_bytes() == b'synthetic trusted worker'
    (bundled/'Linda-Document-Worker.exe').unlink()
    with pytest.raises(ValueError,match='runtime is missing'):
        sandbox.stage_runtime(output)
