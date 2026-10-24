"""Text-only readers for the disposable document worker; never run embedded code."""
import io
import posixpath
import re
import struct
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

PLAIN_EXTS={'.txt','.text','.md','.markdown','.rst','.log','.csv','.tsv','.json','.yaml','.yml','.tex'}
EXTRA_EXTS={'.doc','.rtf','.odt','.epub','.html','.htm','.xhtml','.fb2'}
SUPPORTED_EXTS=PLAIN_EXTS|EXTRA_EXTS|{'.docx','.pdf'}

def decode(data):
    if data.startswith((b'\xff\xfe',b'\xfe\xff')):return data.decode('utf-16').lstrip('\ufeff')
    for encoding in ('utf-8-sig','cp1251','cp1252'):
        try:return data.decode(encoding)
        except UnicodeDecodeError:pass
    return data.decode('cp1252',errors='replace')

class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.output=[];self.skip=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','template','noscript','head'):self.skip.append(tag)
        if not self.skip and tag in ('p','div','br','li','tr','h1','h2','h3','h4','section','article'):self.output.append('\n')
    def handle_endtag(self,tag):
        if self.skip:
            if tag==self.skip[-1]:self.skip.pop()
        elif tag in ('p','div','li','tr','h1','h2','h3','h4','section','article'):self.output.append('\n')
        elif tag in ('td','th'):self.output.append('\t')
    def handle_data(self,text):
        if not self.skip:self.output.append(text)

def html_text(data):
    raw=decode(data)
    # Honour an explicit legacy charset without visiting links or loading assets.
    m=re.search(rb'charset\s*=\s*["\']?([\w-]+)',data[:4096],re.I)
    if m:
        try:raw=data.decode(m[1].decode('ascii'),errors='replace')
        except (LookupError,UnicodeError):pass
    parser=HTMLText();parser.feed(raw);parser.close()
    return re.sub(r'\n[ \t]*\n+', '\n\n',''.join(parser.output)).strip()

def xml(data):
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',data,re.I):raise ValueError('XML declarations are not supported')
    return ET.fromstring(data)

def archive(data):
    z=zipfile.ZipFile(io.BytesIO(data));entries=z.infolist()
    if len(entries)>2000 or sum(e.file_size for e in entries)>80_000_000:
        z.close();raise ValueError('Document expands beyond the supported limit')
    return z

def local_path(base,href):
    parsed=urlsplit(href)
    if parsed.scheme or parsed.netloc:raise ValueError('External document references are not supported')
    name=posixpath.normpath(posixpath.join(base,unquote(parsed.path)))
    if name.startswith(('../','/')) or name=='..' or '\\' in name:raise ValueError('Invalid document path')
    return name

def epub_text(data):
    with archive(data) as z:
        if 'META-INF/encryption.xml' in z.namelist():raise ValueError('Encrypted EPUB is not supported')
        container=xml(z.read('META-INF/container.xml'))
        rootfile=next((n.attrib.get('full-path') for n in container.iter() if n.tag.endswith('}rootfile')),None)
        if not rootfile:raise ValueError('EPUB reading order is missing')
        rootfile=local_path('',rootfile);package=xml(z.read(rootfile));base=posixpath.dirname(rootfile)
        manifest={n.attrib['id']:n.attrib.get('href','') for n in package.iter() if n.tag.endswith('}item') and 'id' in n.attrib}
        order=[n.attrib.get('idref') for n in package.iter() if n.tag.endswith('}itemref') and n.attrib.get('linear','yes')!='no']
        if not order:raise ValueError('EPUB reading order is missing')
        return '\n\n'.join(html_text(z.read(local_path(base,manifest[key]))) for key in order)

def odt_text(data):
    with archive(data) as z:root=xml(z.read('content.xml'))
    ns='{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
    def content(n):
        out=n.text or ''
        for child in n:
            if child.tag==ns+'s':out+=' '*min(max(int(child.attrib.get(ns+'c','1')),1),10000)
            elif child.tag==ns+'tab':out+='\t'
            elif child.tag==ns+'line-break':out+='\n'
            else:out+=content(child)
            out+=child.tail or ''
        return out
    return '\n\n'.join(content(n) for n in root.iter() if n.tag in (ns+'p',ns+'h'))

def rtf_text(data):
    if not data.lstrip().startswith(b'{\\rtf'):raise ValueError('Invalid RTF document')
    raw=data.decode('latin1');out=[];stack=[];skip=False;uc=1;encoding='cp1252';fallback=0;i=0
    destinations={'fonttbl','colortbl','stylesheet','info','pict','object','objdata','fldinst','header','footer','filetbl','datastore','themedata','xmlnstbl'}
    special={'par':'\n','line':'\n','row':'\n','tab':'\t','cell':'\t','emdash':'—','endash':'–','bullet':'•','lquote':'‘','rquote':'’','ldblquote':'“','rdblquote':'”'}
    while i<len(raw):
        c=raw[i];i+=1
        if c=='{':
            if len(stack)>512:raise ValueError('RTF nesting exceeds the supported limit')
            stack.append((skip,uc,encoding));fallback=0
        elif c=='}':
            if not stack:raise ValueError('Invalid RTF structure')
            skip,uc,encoding=stack.pop();fallback=0
        elif c=='\\':
            if i>=len(raw):break
            c=raw[i];i+=1
            if c=="'":
                value=bytes.fromhex(raw[i:i+2]).decode(encoding,errors='replace');i+=2
                if fallback:fallback-=1
                elif not skip:out.append(value)
            elif c in '\\{}~_-':
                if fallback:fallback-=1
                elif not skip:out.append({'~':' ','_':'-','-':''}.get(c,c))
            elif c=='*':skip=True
            elif c.isalpha():
                start=i-1
                while i<len(raw) and raw[i].isalpha():i+=1
                word=raw[start:i];m=re.match(r'-?\d+',raw[i:]);num=int(m[0]) if m else None
                if m:i+=len(m[0])
                if i<len(raw) and raw[i]==' ':i+=1
                if word=='bin' and num is not None:
                    if num<0 or i+num>len(raw):raise ValueError('Invalid RTF binary data')
                    i+=num
                elif word in destinations:skip=True
                elif word=='ansicpg' and num is not None:
                    encoding='cp'+str(num);b'a'.decode(encoding)
                elif word=='uc' and num is not None:uc=min(max(num,0),16)
                elif word=='u' and num is not None:
                    if not skip:out.append(chr(num & 0xffff))
                    fallback=uc
                elif not skip and word in special:out.append(special[word])
        elif c not in '\r\n':
            if fallback:fallback-=1
            elif not skip:out.append(c.encode('latin1').decode(encoding,errors='replace'))
    if stack:raise ValueError('Invalid RTF structure')
    return ''.join(out).encode('utf-16le',errors='surrogatepass').decode('utf-16le',errors='replace').strip()

def doc_text(data):
    try:from . import linda_olefile as olefile
    except ImportError:import linda_olefile as olefile
    with olefile.OleFileIO(io.BytesIO(data)) as ole:
        word=ole.openstream('WordDocument').read()
        u16=lambda off:struct.unpack_from('<H',word,off)[0]
        u32=lambda off:struct.unpack_from('<I',word,off)[0]
        if len(word)<400 or u16(0)!=0xa5ec or u16(2)<0xc1:raise ValueError('This legacy Word version is not supported; save it as DOCX')
        flags=u16(10)
        if flags&0x8100:raise ValueError('Encrypted Word documents are not supported')
        table=ole.openstream('1Table' if flags&0x200 else '0Table').read()
        offset=34+u16(32)*2;cslw=u16(offset);body_chars=u32(offset+2+3*4)
        pairs=offset+2+cslw*4
        if u16(pairs)<=33:raise ValueError('Word piece table is missing')
        fc,size=struct.unpack_from('<II',word,pairs+2+33*8)
        if fc+size>len(table):raise ValueError('Invalid Word piece table')
        clx=table[fc:fc+size];p=0
        while p<len(clx) and clx[p]==1:p+=3+struct.unpack_from('<H',clx,p+1)[0]
        if p+5>len(clx) or clx[p]!=2:raise ValueError('Invalid Word piece table')
        length=struct.unpack_from('<I',clx,p+1)[0];plc=clx[p+5:p+5+length]
        if len(plc)!=length or length<16 or (length-4)%12:raise ValueError('Invalid Word piece table')
        count=(length-4)//12;out=[];last=0
        for i in range(count):
            start,end=struct.unpack_from('<II',plc,i*4)
            if start<last or end<start:raise ValueError('Invalid Word text order')
            last=end
            if start>=body_chars:break
            chars=min(end,body_chars)-start;raw=struct.unpack_from('<I',plc,4*(count+1)+i*8+2)[0]
            compressed=bool(raw&0x40000000);offset=raw&0x3fffffff
            if compressed:offset//=2
            size=chars*(1 if compressed else 2)
            if offset+size>len(word):raise ValueError('Invalid Word text range')
            out.append(word[offset:offset+size].decode('cp1252' if compressed else 'utf-16le',errors='replace'))
        text=''.join(out).replace('\r','\n').replace('\x07','\t').replace('\x0b','\n').replace('\x0c','\n')
        # Drop field instructions while keeping their displayed results.
        text=re.sub('\x13[^\x14\x15]*\x14','',text).replace('\x15','')
        return re.sub(r'[\x00-\x08\x0e-\x1f]','',text).strip()

def extract_extended(ext,data):
    if ext in ('.html','.htm','.xhtml'):return html_text(data)
    if ext=='.rtf':return rtf_text(data)
    if ext=='.odt':return odt_text(data)
    if ext=='.epub':return epub_text(data)
    if ext=='.doc':return doc_text(data)
    if ext=='.fb2':
        root=xml(data)
        return '\n\n'.join(''.join(n.itertext()) for body in root.iter() if body.tag.endswith('}body') for n in body.iter() if n.tag.endswith('}p'))
    raise ValueError('Unsupported document format')
