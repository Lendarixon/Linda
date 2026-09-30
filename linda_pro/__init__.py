# -*- coding: utf-8 -*-
"""Linda-Pro: локальный детектор ИИ-текста (английский). См. README.md."""
from .core import LindaPro, split_windows, top25, verdict

__version__ = "1.0.0"
__all__ = ["LindaPro", "split_windows", "top25", "verdict", "__version__"]
