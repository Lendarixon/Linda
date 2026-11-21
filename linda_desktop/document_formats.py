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


_HYPHEN_END=re.compile(r'[A-Za-z\u00c0-\u024f\u0400-\u04ff][-\u00ad\u2010]$')
_LOWER_START=re.compile(r'^[a-z\u00df-\u024f\u0430-\u044f\u0451]')
_NO_SPACE_BEFORE=re.compile(r'^[.,;:!?\)\]\}%\u00bb\u201d\u2019]')
_SENT_END=re.compile(r'[.!?\u2026\u00bb\u201d\)]$')


def _join_line_frags(frags):
    frags.sort(key=lambda f: f[0])
    out=[]
    for x, y, fs, txt in frags:
        s=txt.strip()
        if not s:
            continue
        if not out:
            out.append(s)
        elif out[-1].endswith(('-', '\u00ad', '\u2010', '(', '[', '\u00ab', '\u201c')) or _NO_SPACE_BEFORE.match(s):
            out.append(s)
        else:
            out.append(' ' + s)
    return re.sub(r'[ \t]{2,}', ' ', ''.join(out)).strip()


def _cluster_lines(frags):
    if not frags:
        return []
    ordered=sorted(frags, key=lambda f: (-f[1], f[0]))
    lines=[]
    cur=[ordered[0]]
    cur_y=ordered[0][1]
    cur_fs=ordered[0][2]
    for f in ordered[1:]:
        tol=max(2.0, 0.35 * max(cur_fs, f[2]))
        if abs(f[1] - cur_y) <= tol:
            cur.append(f)
            cur_fs=max(cur_fs, f[2])
        else:
            txt=_join_line_frags(cur)
            if txt:
                lines.append((cur_y, min(p[0] for p in cur), cur_fs, txt))
            cur=[f]
            cur_y=f[1]
            cur_fs=f[2]
    txt=_join_line_frags(cur)
    if txt:
        lines.append((cur_y, min(p[0] for p in cur), cur_fs, txt))
    return lines


def _split_two_columns(frags, page_width):
    if len(frags) < 8 or page_width < 300:
        return [frags]
    xs=sorted(f[0] for f in frags)
    lo, hi=page_width * 0.25, page_width * 0.75
    best_gap, mid_x=0.0, 0.0
    for a, b in zip(xs, xs[1:]):
        if lo <= (a + b) / 2.0 <= hi and (b - a) > best_gap:
            best_gap=b - a
            mid_x=(a + b) / 2.0
    if best_gap < 14.0:
        return [frags]
    left=[f for f in frags if f[0] < mid_x]
    right=[f for f in frags if f[0] >= mid_x]
    if len(left) < 4 or len(right) < 4:
        return [frags]
    left_ys={round(f[1] / 6.0) for f in left}
    right_ys={round(f[1] / 6.0) for f in right}
    if len(left_ys) < 4 or len(right_ys) < 4:
        return [frags]
    return [left, right]


def _lines_to_paragraphs(lines):
    if not lines:
        return ''
    dys=[lines[i - 1][0] - lines[i][0] for i in range(1, len(lines)) if 0 < lines[i - 1][0] - lines[i][0] < max(lines[i - 1][2], 10.0) * 4.0]
    med_dy=sorted(dys)[len(dys) // 2] if dys else max(lines[0][2] * 1.2, 12.0)
    xs=sorted(l[1] for l in lines)
    x_base=xs[max(0, len(xs) // 10)]
    paras=[]
    cur=lines[0][3]
    prev_y, _, prev_fs, _=lines[0]
    for y, x, fs, txt in lines[1:]:
        dy=prev_y - y
        para_break=(dy < 0) or (dy > max(med_dy * 1.42, prev_fs * 1.55)) or (bool(_SENT_END.search(cur)) and (x - x_base) > max(8.0, prev_fs * 0.7))
        if para_break:
            paras.append(cur)
            cur=txt
        elif _HYPHEN_END.search(cur) and _LOWER_START.match(txt):
            cur=cur[:-1] + txt
        else:
            cur=cur + ' ' + txt
        prev_y, prev_fs=y, fs
    paras.append(cur)
    return '\n\n'.join(paras)


def _norm_hf(s):
    return re.sub(r'\d+', '#', s.strip()).lower()


def extract_pdf_pages(reader):
    page_groups=[]
    for page in reader.pages:
        frags=[]
        def _visitor(text, cm, tm, font_dict, font_size):
            if not text or not text.strip():
                return
            x=float(cm[0]) * float(tm[4]) + float(cm[2]) * float(tm[5]) + float(cm[4])
            y=float(cm[1]) * float(tm[4]) + float(cm[3]) * float(tm[5]) + float(cm[5])
            fs=abs(float(font_size or 0.0)) or 10.0
            frags.append((x, y, fs, text))
        try:
            page.extract_text(visitor_text=_visitor)
        except Exception:
            frags=[]
        if frags:
            try:
                pw=float(page.mediabox.width)
            except Exception:
                pw=max(f[0] for f in frags) - min(f[0] for f in frags)
            cols=_split_two_columns(frags, pw)
            col_lines=[_cluster_lines(c) for c in cols]
            col_lines=[cl for cl in col_lines if cl]
            page_groups.append(col_lines)
        else:
            raw=(page.extract_text() or '').strip()
            if raw:
                fallback_lines=[(float(1000 - i * 14), 0.0, 12.0, ln.strip()) for i, ln in enumerate(raw.splitlines()) if ln.strip()]
                page_groups.append([fallback_lines] if fallback_lines else [])
            else:
                page_groups.append([])
    if len(page_groups) >= 3:
        top_counts, bot_counts={}, {}
        for cols in page_groups:
            if not cols:
                continue
            first=cols[0][0][3]
            last=cols[-1][-1][3]
            if len(first) <= 100:
                k=_norm_hf(first)
                top_counts[k]=top_counts.get(k, 0) + 1
            if len(last) <= 100:
                k=_norm_hf(last)
                bot_counts[k]=bot_counts.get(k, 0) + 1
        thresh=max(3, int(len(page_groups) * 0.6))
        drop_top={k for k, c in top_counts.items() if c >= thresh}
        drop_bot={k for k, c in bot_counts.items() if c >= thresh}
        for cols in page_groups:
            if not cols:
                continue
            if cols[0] and len(cols[0][0][3]) <= 100 and _norm_hf(cols[0][0][3]) in drop_top:
                cols[0]=cols[0][1:]
            if cols[-1] and len(cols[-1][-1][3]) <= 100 and _norm_hf(cols[-1][-1][3]) in drop_bot:
                cols[-1]=cols[-1][:-1]
    out=[]
    for cols in page_groups:
        parts=[_lines_to_paragraphs(cl) for cl in cols if cl]
        if parts:
            out.append('\n\n'.join(parts))
    return out
