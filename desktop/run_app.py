import os,sys
if __name__ == '__main__' and len(sys.argv)>1 and sys.argv[1]=='--document-worker':
    from linda_desktop.document_worker import main
    raise SystemExit(main(sys.argv[2:]))
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
    os.environ[key]='6'
from linda_desktop.__main__ import main
if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
