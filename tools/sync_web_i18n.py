"""Keep the offline embedded dictionaries identical to their JSON sources."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'web/index.html';s=p.read_text(encoding='utf-8')
start=s.index('window.LINDA_I18N = ')+len('window.LINDA_I18N = ')
_,length=json.JSONDecoder().raw_decode(s[start:])
data={lang:json.loads((ROOT/f'web/i18n/{lang}.json').read_text(encoding='utf-8')) for lang in ('en','pl','ru')}
s=s[:start]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+s[start+length:]
p.write_text(s,encoding='utf-8')
print('Embedded RU/EN/PL synchronized with web/i18n')
