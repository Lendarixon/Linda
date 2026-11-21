"""Exercise the installed parser with synthetic documents through its local API."""
import io,json,re,uuid,zipfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/ui_overhaul_20261024'
info=json.loads((Path.home()/'AppData/Local/Linda-Pro/instance.json').read_text());BASE=f'http://127.0.0.1:{info["port"]}'
html=urlopen(BASE+'/').read().decode();TOKEN=re.search(r'''window\.__lindaToken\s*=\s*['"]([^'"]+)''',html)[1]
def zipped(items):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for name,text in items.items():z.writestr(name,text)
 return out.getvalue()
sample='Linda local extraction test. Full document body.'
files={x:sample.encode() for x in ['txt','text','md','csv','tsv','json','yaml','yml','log','rst','tex','markdown']}
files['doc']=(OUT/'input-test.doc').read_bytes();files['docx']=(OUT/'input-test.docx').read_bytes()
files['rtf']=br'{\rtf1\ansi Linda local extraction test. Full document body.}'
for ext in ('html','htm','xhtml'):files[ext]=b'<html><body><p>Linda local extraction test.</p><script>hidden_secret</script><p>Full document body.</p></body></html>'
files['odt']=zipped({'content.xml':'<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><text:p>'+sample+'</text:p></office:body></office:document-content>'})
files['epub']=zipped({'META-INF/container.xml':'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>','book.opf':'<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="a" href="a.xhtml"/></manifest><spine><itemref idref="a"/></spine></package>','a.xhtml':'<p>'+sample+'</p>'})
files['fb2']=('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"><body><section><p>'+sample+'</p></section></body></FictionBook>').encode()
from fpdf import FPDF
pdf=FPDF();pdf.add_page();pdf.set_font('Helvetica',size=12);pdf.cell(text=sample);files['pdf']=bytes(pdf.output())
results=[]
for ext,content in files.items():
 path=OUT/('import-sample.'+ext);path.write_bytes(content)
 boundary=uuid.uuid4().hex;payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="import-sample.{ext}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode())
 request=Request(BASE+'/api/upload',data=payload,headers={'x-linda-token':TOKEN,'Content-Type':'multipart/form-data; boundary='+boundary})
 try:
  with urlopen(request,timeout=60) as r:data=json.loads(r.read())
  assert 'Linda' in data['text'] and 'hidden_secret' not in data['text']
  results.append({'format':ext,'ok':True,'words':data['words']})
 except HTTPError as e:results.append({'format':ext,'ok':False,'code':e.code,'error':e.read().decode()})
(OUT/'native-format-imports.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results));assert all(r['ok'] for r in results)
