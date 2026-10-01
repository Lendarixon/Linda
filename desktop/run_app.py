# -*- coding: utf-8 -*-
"""PyInstaller entry point."""
import multiprocessing

from linda_desktop.__main__ import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
