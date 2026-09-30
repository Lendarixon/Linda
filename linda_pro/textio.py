# -*- coding: utf-8 -*-
"""Чтение текста из файлов: .txt/.md (UTF-8), .docx (python-docx, если установлен), .pdf (pypdf, если установлен). Всё локально."""
from __future__ import annotations

from pathlib import Path


def read_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".text", ""):
        return p.read_text(encoding="utf-8", errors="replace")
    if ext == ".docx":
        try:
            import docx  # python-docx
        except ImportError as e:
            raise RuntimeError("install python-docx to read .docx files: pip install python-docx") from e
        d = docx.Document(str(p))
        return "\n\n".join(par.text for par in d.paragraphs if par.text.strip())
    if ext == ".pdf":
        try:
            import pypdf
        except ImportError as e:
            raise RuntimeError("install pypdf to read .pdf files: pip install pypdf") from e
        r = pypdf.PdfReader(str(p))
        return "\n\n".join((pg.extract_text() or "") for pg in r.pages)
    raise ValueError(f"unsupported file type: {ext} (use .txt, .md, .docx or .pdf)")
