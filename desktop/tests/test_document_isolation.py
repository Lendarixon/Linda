import io
import json
import subprocess
import sys
import time

import pytest
from linda_desktop import documents


def test_docx_real_worker_unicode():
    import docx
    doc = docx.Document()
    doc.add_paragraph('Тестowy документ — Unicode.')
    stream = io.BytesIO()
    doc.save(stream)
    assert documents.extract('test.docx',stream.getvalue())=='Тестowy документ — Unicode.'


def test_pdf_real_worker_and_empty_pdf():
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica',size=12)
    pdf.cell(text='Isolated PDF test')
    assert 'Isolated PDF test' in documents.extract('test.pdf',bytes(pdf.output()))
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72,height=72)
    stream = io.BytesIO()
    writer.write(stream)
    assert documents.extract('empty.pdf',stream.getvalue())==''


def test_timeout_kills_owned_worker_and_releases_slot(monkeypatch):
    monkeypatch.setattr(documents,'TIMEOUT',.15)
    monkeypatch.setattr(documents,'_command',lambda *args:[sys.executable,'-c','import time;time.sleep(30)'])
    real = subprocess.Popen
    children = []
    def launch(*args,**kwargs):
        process = real(*args,**kwargs)
        children.append(process)
        return process
    monkeypatch.setattr(documents.subprocess,'Popen',launch)
    start = time.monotonic()
    with pytest.raises(ValueError,match='timed out'):
        documents.extract('slow.pdf',b'test')
    assert time.monotonic()-start<3 and children[0].poll() is not None
    assert documents._slots.acquire(blocking=False)
    documents._slots.release()


def test_worker_errors_do_not_leak_paths():
    with pytest.raises(ValueError):
        documents.extract('bad.docx',b'not a zip')
    assert documents.extract('ok.txt','hello'.encode())=='hello'


def test_oversized_pdf_and_output_are_rejected(monkeypatch):
    from linda_desktop import document_worker as worker
    from pypdf import PdfWriter
    monkeypatch.setattr(worker,'MAX_PAGES',1)
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=72,height=72)
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(ValueError,match='page limit'):
        worker.parse('test.pdf',stream.getvalue())
    monkeypatch.setattr(documents,'MAX_INPUT',4)
    with pytest.raises(ValueError,match='input limit'):
        documents.extract('large.pdf',b'12345')


def test_windowed_frozen_command_has_worker_dispatch(monkeypatch,tmp_path):
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    assert documents._command('a.pdf',tmp_path/'in',tmp_path/'out')[1]=='--document-worker'
    # run_dev's early dispatch must avoid importing the app or configuring profiles.
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1]/'run_dev.py').read_text(encoding='utf-8')
    assert source.index('document_main(sys.argv[2:])')<source.index('ROOT =')
