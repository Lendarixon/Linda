"""Embed the five supplied Linda illustrations, without baked-in labels."""
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ART=Path.home()/'Desktop/дизайн/иллюстрации/1_linda_детектор/без_текста'
p=ROOT/'web/startup.html'
s=p.read_text(encoding='utf-8')
assert 'startup-frame' not in s
frames=[]
for i,asset in enumerate(sorted(ART.glob('*.svg'))):
    active=' is-active' if i==0 else ''
    artwork=re.sub(r'<text\b[^>]*>.*?</text>','',asset.read_text(encoding='utf-8'),flags=re.S)
    if i==1:
        glyph='<g fill="#fff"><rect x="416" y="130" width="148" height="20"/><rect x="416" y="166" width="65" height="20"/><rect x="493" y="166" width="71" height="20" fill="#e51400"/><rect x="416" y="202" width="106" height="20"/></g>'
        artwork=artwork.replace('</svg>',glyph+'</svg>')
    frames.append(f'<div class="startup-frame{active}" data-frame="{i}">'+artwork+'</div>')
assert len(frames)==5
s,n=re.subn(r'(<div class="startup-art" aria-hidden="true">).*?(</div>)',lambda m:m[1]+''.join(frames)+m[2],s,count=1,flags=re.S)
assert n==1
css='''
.startup-frame{position:absolute;inset:0;opacity:0;transition:opacity .8s ease}
.startup-frame.is-active{opacity:1}
@media(prefers-reduced-motion:reduce){.startup-frame{transition:none}}
'''
s=s.replace('</style>',css+'</style>',1)
anchor=' const timer=setInterval('
assert s.count(anchor)==1
script=''' const frames=Array.from(el.querySelectorAll('.startup-frame'));
 let frameIndex=0;
 const artworkTimer=setInterval(function(){
  if(el.hidden){clearInterval(artworkTimer);return;}
  frames[frameIndex].classList.remove('is-active');
  frameIndex=(frameIndex+1)%frames.length;
  frames[frameIndex].classList.add('is-active');
 },6000);
'''
s=s.replace(anchor,script+anchor,1)
p.write_text(s,encoding='utf-8')
print('Five artwork frames embedded; 6 second cycle with reduced-motion support')
