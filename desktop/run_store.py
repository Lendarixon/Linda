"""Store-only entry: refuse standalone execution before opening any profile."""
import os
import sys

def main(argv=None):
    from linda_desktop import config
    try:
        packaged = config.is_store_package()
    except Exception:
        packaged = False
    if not packaged:
        if sys.stderr is not None:
            print('Linda-Pro Store edition must be launched as an installed Windows package.',file=sys.stderr)
        return 2
    # A Store runtime never adopts the Dev/standalone test profile by inheritance.
    if os.environ.get('LINDA_HOME') or os.environ.get('LINDA_DEV') == '1' or config.APP_NAME != 'Linda-Pro':
        if sys.stderr is not None:
            print('Linda-Pro Store edition requires its package-managed profile; remove Dev/test overrides.',file=sys.stderr)
        return 2
    for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
        os.environ[key] = '6'
    import multiprocessing
    multiprocessing.freeze_support()
    from linda_desktop.__main__ import main as desktop_main
    return desktop_main(argv)

if __name__ == '__main__':
    raise SystemExit(main())
