# -*- coding: utf-8 -*-
"""Регрессия: встроенные скрипты web/*.html обязаны проходить `node --check` (раньше лишняя скобка роняла весь интерфейс)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent / "web"


@pytest.mark.skipif(shutil.which("node") is None, reason="нет node")
@pytest.mark.parametrize("name", ["index.html", "cabinet.html"])
def test_inline_scripts_parse(name, tmp_path):
    html = (WEB / name).read_text(encoding="utf-8")
    for i, body in enumerate(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, flags=re.S)):
        f = tmp_path / f"s{i}.js"
        f.write_text(body, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{name} script #{i}: {r.stderr[:300]}"
