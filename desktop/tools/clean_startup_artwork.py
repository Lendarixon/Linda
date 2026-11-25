"""Remove historical model labels and decorative scores from the inline art."""
import re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'web/startup.html'
s=p.read_text(encoding='utf-8')
s=re.sub(r'<text\b[^>]*>.*?</text>','',s,flags=re.S)
pattern=r'(<div class="startup-frame" data-frame="1">)(.*?)(</svg></div>)'
glyph='<g fill="#fff"><rect x="416" y="130" width="148" height="20"/><rect x="416" y="166" width="65" height="20"/><rect x="493" y="166" width="71" height="20" fill="#e51400"/><rect x="416" y="202" width="106" height="20"/></g>'
s,n=re.subn(pattern,lambda m:m[1]+m[2]+glyph+m[3],s,count=1,flags=re.S)
assert n==1
p.write_text(s,encoding='utf-8')
print('Historical model names and decorative scores removed from startup artwork')
