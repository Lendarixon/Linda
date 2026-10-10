"""Collection must not enumerate scratch directories from earlier test runs."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("deny_access", [False, True])
def test_runtime_temp_is_ignored_before_scanning(tmp_path, deny_access):
    suite = tmp_path / "suite"
    suite.mkdir()
    config = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")
    if deny_access:
        # Reproduce WinError 5 without changing ACLs or requiring another user.
        config += '''
import os
_scandir = os.scandir
def _deny_scratch(path):
    if Path(path).name.startswith("runtime_temp_"):
        raise PermissionError("scratch directory belongs to another run account")
    return _scandir(path)
os.scandir = _deny_scratch
'''
    (suite / "conftest.py").write_text(config, encoding="utf-8")
    (suite / "test_real.py").write_text("def test_real(): pass\n", encoding="utf-8")
    scratch = suite / "runtime_temp_lite1"
    scratch.mkdir()
    (scratch / "test_scratch.py").write_text(
        "raise RuntimeError('scratch was collected')\n", encoding="utf-8")
    env = dict(os.environ, PYTEST_ADDOPTS="")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(suite), "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "test_real.py::test_real" in result.stdout
    assert "1 test collected" in result.stdout
