# -*- coding: utf-8 -*-
"""Linda-Pro: local AI text detector (English, Polish, Russian). See README.md.

    from linda_pro import load_detector
    load_detector("sensitive").detect([text])            # best installed weights
    load_detector("sensitive", tier="lite").detect([text])
"""
from .core import LindaPro, split_windows, top25, verdict
from .loader import TIERS, installed_tiers, load_detector, load_detectors

__version__ = "1.1.0"
__all__ = ["LindaPro", "split_windows", "top25", "verdict", "load_detector", "load_detectors", "installed_tiers", "TIERS", "__version__"]
