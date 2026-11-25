from pathlib import Path
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from linda_desktop.document_formats import SUPPORTED_EXTS
accept=','.join(sorted(SUPPORTED_EXTS));pattern='(?:'+ '|'.join(x[1:] for x in sorted(SUPPORTED_EXTS))+')'
for name in ['web/index.html','web/cabinet.html']:
 p=ROOT/name;s=p.read_text(encoding='utf-8');s=re.sub(r'accept="[^"]+"',lambda m:'accept="'+accept+'"' if '.pdf' in m[0] else m[0],s)
 s=s.replace('(?:pdf|docx|txt|text|md)',pattern).replace('(txt|text|md|docx|pdf)',pattern)
 p.write_text(s,encoding='utf-8')
for lang in ('ru','en','pl'):
 p=ROOT/f'web/i18n/{lang}.json';data=json.loads(p.read_text(encoding='utf-8'))
 data['hu_formats']={'ru':'Документы: DOC, DOCX, RTF, ODT, PDF · книги: EPUB, FB2 · HTML и текстовые файлы','en':'Documents: DOC, DOCX, RTF, ODT, PDF · books: EPUB, FB2 · HTML and text files','pl':'Dokumenty: DOC, DOCX, RTF, ODT, PDF · książki: EPUB, FB2 · HTML i pliki tekstowe'}[lang]
 data['hu_file_error']={'ru':'Не удалось извлечь текст. Файл может быть повреждён, защищён паролем или содержать только сканы. Поддерживаемые форматы указаны над полем. Исходный текст сохранён.','en':'Could not extract text. The document may be damaged, password-protected or contain only scans. Supported formats are listed above. Your original text is preserved.','pl':'Nie udało się odczytać tekstu. Plik może być uszkodzony, chroniony hasłem albo zawierać tylko skany. Formaty są podane powyżej. Tekst źródłowy został zachowany.'}[lang]
 for key,value in list(data.items()):
  if isinstance(value,str):
   value=value.replace('TXT, MD, DOCX, PDF','TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML, PDF').replace('.txt, .md, .docx, .pdf',accept).replace('.txt/.md/.docx/.pdf',accept)
   data[key]=value
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'linda_desktop/app.py';s=p.read_text(encoding='utf-8');s=s.replace('exts = {".txt", ".md", ".text", ".docx", ".pdf"}','from .document_formats import SUPPORTED_EXTS\n        exts = SUPPORTED_EXTS');p.write_text(s,encoding='utf-8')
p=ROOT/'web/desktop-shell.js';s=p.read_text(encoding='utf-8');s=s.replace('TXT, MD, DOCX, PDF','TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML, PDF').replace('TXT, MD, DOCX or PDF','TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML or PDF').replace('TXT, MD, DOCX albo PDF','TXT, DOC, DOCX, RTF, ODT, EPUB, FB2, HTML albo PDF');p.write_text(s,encoding='utf-8')
print(accept)
