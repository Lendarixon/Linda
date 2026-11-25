"""Prepare localized editor import controls and bounded native test documents."""
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/ui_overhaul_20261024'
strings={
 'ru':dict(hu_file='Открыть файл',hu_formats='TXT, TEXT, MD, DOCX, PDF · извлечение текста из документа',hu_input='Исходный текст',hu_output='Переписанный текст',hu_reading='Извлекаем текст из документа…',hu_file_loaded='Текст из «{name}» загружен. Проверьте его перед переписыванием.',hu_file_error='Не удалось прочитать документ. Поддерживаются TXT, TEXT, MD, DOCX и PDF с текстовым слоем. Исходный текст сохранён.',hu_input_changed='Вы изменили текст во время чтения файла. Ваши правки сохранены; откройте файл повторно, если хотите заменить их.'),
 'en':dict(hu_file='Open file',hu_formats='TXT, TEXT, MD, DOCX, PDF · extract document text',hu_input='Original text',hu_output='Rewritten text',hu_reading='Extracting document text…',hu_file_loaded='Text from “{name}” loaded. Review it before rewriting.',hu_file_error='Could not read this document. Supported: TXT, TEXT, MD, DOCX and PDFs with a text layer. Your original text is preserved.',hu_input_changed='You edited the text while the file was loading. Your changes were preserved; reopen the file to replace them.'),
 'pl':dict(hu_file='Otwórz plik',hu_formats='TXT, TEXT, MD, DOCX, PDF · odczyt tekstu dokumentu',hu_input='Tekst źródłowy',hu_output='Przeredagowany tekst',hu_reading='Odczytywanie tekstu dokumentu…',hu_file_loaded='Wczytano tekst z pliku „{name}”. Sprawdź go przed przeredagowaniem.',hu_file_error='Nie udało się odczytać dokumentu. Obsługiwane: TXT, TEXT, MD, DOCX i PDF z warstwą tekstową. Tekst źródłowy został zachowany.',hu_input_changed='Tekst zmienił się podczas odczytywania pliku. Zachowano Twoje zmiany; otwórz plik ponownie, aby je zastąpić.')}
for lang,values in strings.items():
 p=ROOT/f'web/i18n/{lang}.json';data=json.loads(p.read_text(encoding='utf-8'));data.update(values);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['web/index.html','web/cabinet.html']:
 p=ROOT/name;s=p.read_text(encoding='utf-8');s=s.replace('accept=".pdf,.docx,.txt,.md"','accept=".pdf,.docx,.txt,.text,.md"').replace('accept=".txt,.md,.docx,.pdf"','accept=".txt,.text,.md,.docx,.pdf"').replace('(?:pdf|docx|txt|md)','(?:pdf|docx|txt|text|md)').replace('(txt|md|docx|pdf)','(txt|text|md|docx|pdf)');p.write_text(s,encoding='utf-8')
sample='Linda input test. This document is used to verify local text extraction and editing. No rewriting starts when a file is opened.'
(OUT/'input-test.txt').write_text(sample,encoding='utf-8')
(OUT/'input-test.text').write_text(sample,encoding='utf-8')
(OUT/'input-test.md').write_text('# Local test\n\n'+sample,encoding='utf-8')
with zipfile.ZipFile(OUT/'input-test.docx','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
 z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+sample+'</w:t></w:r></w:p></w:body></w:document>')
print('Localized controls and test documents prepared')
