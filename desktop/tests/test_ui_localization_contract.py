"""The offline UI must ship current dictionaries and the complete import filter."""
import json
from pathlib import Path
import re
from linda_desktop.document_formats import SUPPORTED_EXTS
ROOT=Path(__file__).resolve().parents[1]

def test_embedded_offline_dictionaries_match_json_sources():
 html=(ROOT/'web/index.html').read_text(encoding='utf-8')
 start=html.index('window.LINDA_I18N = ')+len('window.LINDA_I18N = ')
 embedded,_=json.JSONDecoder().raw_decode(html[start:])
 for lang in ('ru','en','pl'):
  source=json.loads((ROOT/f'web/i18n/{lang}.json').read_text(encoding='utf-8'))
  assert embedded[lang]==source
  for key in ('hu_file','hu_input','hu_output','hu_formats','task_stop','task_stopping','rewrite_current'):
   assert source[key].strip() and source[key]!=key

def test_all_file_pickers_advertise_the_same_supported_extensions():
 for name in ('index.html','cabinet.html'):
  source=(ROOT/'web'/name).read_text(encoding='utf-8')
  accepts=re.findall(r'<input[^>]+type="file"[^>]+accept="([^"]+)"',source)
  assert accepts
  for value in accepts:assert set(value.split(','))==SUPPORTED_EXTS
