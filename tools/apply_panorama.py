"""One-time switch from Studio to the supplied Panorama layout."""
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'web/startup.html'
s=p.read_text(encoding='utf-8')
backup=ROOT/'evidence/panorama'
backup.mkdir(exist_ok=True)
assert not (backup/'startup-studio.html').exists()
(backup/'startup-studio.html').write_text(s,encoding='utf-8')
css=(ROOT/'web/startup-panorama.css').read_text(encoding='utf-8')
s,n=re.subn(r'<style>.*?</style>',lambda m:'<style>\n'+css+'</style>',s,count=1,flags=re.S)
assert n==1
old='   <div class="startup-status"'
assert s.count(old)==1
s=s.replace(old,'   <div class="startup-foot">\n'+old,1)
old='   <button id="startupContinue" type="button" hidden></button>'
assert s.count(old)==1
s=s.replace(old,old+'\n   </div>',1)
p.write_text(s,encoding='utf-8')
print('Panorama applied; Studio backup saved')
