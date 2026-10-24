"""Identify implementation and static artifacts used in an analysis."""
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import sys

FILES = ('local_app.py', 'analysis_jobs.py', 'outlier_engine.py', 'authorship_engine.py', 'input_quality.py', 'stylometric_engine.py', 'core.py',
         'feature_labels.py', 'vendor/linda_stylometry.py', 'char_ngrams_model.json',
         'trace_config.py', 'trace_updater.py', 'update_api.py')


def source_manifest(root):
    root = Path(root)
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
            for name in FILES if (root/name).is_file()}


@lru_cache(maxsize=1)
def _base_manifest():
    root = Path(__file__).resolve().parent
    if getattr(sys, 'frozen', False):
        path = root/'build_metadata.json'
        return {'kind': 'packaged_build', **(json.loads(path.read_text(encoding='utf-8'))
                                            if path.is_file() else {'source_hashes': {}, 'status': 'unrecorded'})}
    return {'kind': 'source', 'source_hashes': source_manifest(root)}


def runtime_manifest():
    """Build/source identity plus the model pack that is actually used now (it can change while the app runs)."""
    manifest = dict(_base_manifest())
    try:
        import trace_updater
        bundled = Path(__file__).resolve().parent/'char_ngrams_model.json'
        manifest['active_model'] = trace_updater.active_model_info(bundled.name, bundled)
    except Exception:
        pass
    return manifest
