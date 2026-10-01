# -*- coding: utf-8 -*-
"""Linda-Pro: local AI text detector (English). See README.md."""
from .core import LindaPro, split_windows, top25, verdict

__version__ = "1.1.0"
__all__ = ["LindaPro", "split_windows", "top25", "verdict", "__version__"]
