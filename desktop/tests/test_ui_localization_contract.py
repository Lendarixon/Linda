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


# --- P0-3 (Neon UI audit 2026-11-20): the contract used to look only at the JSON sources,
# --- so a key referenced from desktop-shell.js could be missing from every language.
LANGS=('en','ru','pl')

def _json_keys(text):
 """Keys the pages resolve through window.LINDA_T / data-i18n* -> web/i18n/*.json."""
 keys=set(re.findall(r"""LINDA_T\(\s*['"]([A-Za-z0-9_]+)['"]""",text))
 keys|=set(re.findall(r"""data-i18n(?:-ph|-title|-html)?=['"]([A-Za-z0-9_]+)['"]""",text))
 for call in re.findall(r"""LINDA_T\(([^()]*(?:\([^()]*\)[^()]*)*)\)""",text):
  for m in re.finditer(r"""['"]([A-Za-z0-9_]+)['"]""",call):
   if not call[:m.start()].rstrip().endswith(('===','==','!==','!=')):keys.add(m.group(1))
 return keys

def _ld_text_keys(text):
 return set(re.findall(r"""data-ld-text=['"]([A-Za-z0-9_]+)['"]""",text))

def _copy_table(js,lang):
 """The ru/en/pl COPY object literal inside desktop-shell.js, as {key: value}."""
 start=js.index('const COPY = {')+len('const COPY = ')
 block=js[start:js.index('\n  const LEGACY',start)]
 pos=block.index('{',block.index(lang+':'))+1
 i,depth=pos,1
 while i<len(block):
  ch=block[i]
  if ch in '"\'':
   q=ch;i+=1
   while i<len(block) and block[i]!=q:i+=2 if block[i]=='\\' else 1
  elif ch=='{':depth+=1
  elif ch=='}':
   depth-=1
   if depth==0:return dict(re.findall(r"""([A-Za-z_][A-Za-z0-9_]*)\s*:\s*'((?:[^'\\]|\\.)*)'""",block[pos:i]))
  i+=1
 raise AssertionError('unterminated COPY.'+lang)

def test_every_key_resolved_by_the_shell_and_pages_exists_in_all_languages():
 dicts={l:json.loads((ROOT/f'web/i18n/{l}.json').read_text(encoding='utf-8')) for l in LANGS}
 for name in ('index.html','cabinet.html','desktop-shell.js'):
  keys=_json_keys((ROOT/'web'/name).read_text(encoding='utf-8'))
  assert keys,name
  for lang in LANGS:
   missing=sorted(k for k in keys if not str(dicts[lang].get(k,'') or '').strip())
   assert not missing,f'{name}: {lang}.json is missing {missing}'

def test_desktop_shell_copy_covers_every_data_ld_text_key():
 shell=(ROOT/'web'/'desktop-shell.js').read_text(encoding='utf-8')
 keys=_ld_text_keys(shell)
 assert len(keys)>=15,keys
 for lang in LANGS:
  table=_copy_table(shell,lang)
  missing=sorted(k for k in keys if not str(table.get(k,'') or '').strip())
  assert not missing,f'desktop-shell copy[{lang}] is missing {missing}'
  assert set(_copy_table(shell,'en'))^set(table)==set(),f'copy key sets differ for {lang}'
