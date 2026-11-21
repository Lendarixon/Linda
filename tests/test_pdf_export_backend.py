import io
import pytest
from pypdf import PdfReader
from linda_desktop import report, report_pdf

@pytest.mark.parametrize('lang,heading',[('en','Text'),('ru','Отчёт'),('pl','Raport')])
def test_native_pdf_without_any_browser(lang,heading,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('PDF must not use browser subprocesses')
    monkeypatch.setattr(report_pdf,'find_browser',forbidden,raising=False)
    monkeypatch.setattr(report_pdf.subprocess,'run',forbidden)
    text='Synthetic local report with no external browser. '*12
    rep=report.build_report(text,{'verdict':'human','p_ai':.1,'sentences':[],'models_executed':['stylo7c'],'analysis_scope':'single'}, {})
    data,backend=report.pdf_export(rep,lang)
    reader=PdfReader(io.BytesIO(data));content=' '.join(p.extract_text() or '' for p in reader.pages)
    assert backend=='native' and data.startswith(b'%PDF') and heading in content
    assert 'Synthetic local report' in content
