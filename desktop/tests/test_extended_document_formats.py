import io
from pathlib import Path
import zipfile
import pytest
from linda_desktop.document_formats import extract_extended, SUPPORTED_EXTS
from linda_desktop.document_worker import parse

def zipped(items):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,text in items.items():z.writestr(name,text)
    return out.getvalue()

def test_html_keeps_visible_words_without_executing_or_fetching():
    text=parse('a.html',b'<html><head><title>Hidden title</title></head><body><h1>Hello</h1><p>One <b>two</b> &amp; three.</p><script>secret()</script><style>.x{}</style><img src="https://invalid.local/private"></body></html>')
    assert text=='Hello\n\nOne two & three.'

def test_rtf_unicode_nested_ignored_destinations_and_hex():
    text=parse('a.rtf',br"{\rtf1\ansi\ansicpg1251 {\fonttbl{\f0 Secret Font;}}Hello \u1046? \'cf\'f0\'e8\'e2\'e5\'f2\par Second {\b bold} line.}")
    assert text=='Hello Ж Привет\nSecond bold line.'

def test_odt_paragraph_order_spaces_and_tables():
    data=zipped({'content.xml':'<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><text:p>First<text:s text:c="2"/>row</text:p><text:p>Русский żółć</text:p></office:body></office:document-content>'})
    assert parse('a.odt',data)=='First  row\n\nРусский żółć'

def epub(href='b.xhtml'):
    return zipped({'META-INF/container.xml':'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>',
    'OPS/book.opf':f'<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml"/><item id="b" href="{href}"/></manifest><spine><itemref idref="b"/><itemref idref="a"/></spine></package>',
    'OPS/a.xhtml':'<p>Second chapter</p>','OPS/b.xhtml':'<p>First chapter</p>'})

def test_epub_uses_reading_order_not_zip_order():
    assert parse('a.epub',epub())=='First chapter\n\nSecond chapter'

@pytest.mark.parametrize('href',['https://example.org/x','../../secret.xhtml','/secret.xhtml'])
def test_epub_rejects_external_or_traversing_references(href):
    with pytest.raises(ValueError):parse('a.epub',epub(href))

def test_fb2_only_body_paragraphs():
    assert parse('a.fb2','<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"><description><p>Metadata</p></description><body><section><p>Book text</p></section></body></FictionBook>'.encode())=='Book text'

def test_xml_entities_rejected():
    with pytest.raises(ValueError):parse('a.fb2',b'<!DOCTYPE x [<!ENTITY a "boom">]><x>&a;</x>')

def test_real_word97_doc_unicode_fixture():
    data=Path(__file__).with_name('fixtures').joinpath('legacy-word97.doc').read_bytes()
    assert parse('a.doc',data)=='Linda document test. Русский текст. Polski tekst: żółć. Second paragraph.'

@pytest.mark.parametrize('ext',['doc','rtf','odt','epub'])
def test_malformed_structured_documents_fail(ext):
    with pytest.raises(Exception):parse('a.'+ext,b'not a document')

def test_advertised_required_formats():
    assert {'.doc','.docx','.rtf','.odt','.epub','.html','.pdf','.txt','.fb2'}<=SUPPORTED_EXTS
