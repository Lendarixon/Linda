# -*- coding: utf-8 -*-
"""Linda-Pro: local AI text detector (English, Polish, Russian). See README.md."""
from .core import LindaPro, split_windows, top25, verdict
from .loader import load_detector, load_detectors

__version__ = "1.3.1"
__all__ = ["LindaPro", "load_detector", "load_detectors", "split_windows", "top25", "verdict", "__version__"]
