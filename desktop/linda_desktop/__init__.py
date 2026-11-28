# -*- coding: utf-8 -*-
__version__ = "2.6.0.0"


def _bootstrap_cuda_lib() -> None:
    """Prepend downloaded CUDA torch runtime (if present) before torch+cpu is imported."""
    import os
    import sys

    if "torch" in sys.modules:
        return
    try:
        from . import config  # noqa: PLC0415

        cuda_lib = config.models_root() / "packs" / "humanizer" / "cuda_lib"
        if not (cuda_lib / "READY.json").is_file() or not (cuda_lib / "torch" / "__init__.py").is_file():
            return
        s = str(cuda_lib)
        if s not in sys.path:
            sys.path.insert(0, s)
        torch_dlls = cuda_lib / "torch" / "lib"
        if os.name == "nt" and torch_dlls.is_dir() and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(torch_dlls))
    except Exception:  # noqa: BLE001
        pass


_bootstrap_cuda_lib()
