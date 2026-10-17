"""HTTP app for the hosted demo, isolated from the desktop application."""
import asyncio,hashlib,hmac,json,re,secrets,time,io,os
from pathlib import Path
from fastapi import FastAPI,Request,File,UploadFile
from fastapi.responses import HTMLResponse,JSONResponse
from demo_quota import MAX_USES

MAX_CHARS=6000
MIN_WORDS=20
MAX_UPLOAD_BYTES=2_000_000
MAX_REQUEST_BYTES=32_000
COOKIE='linda_demo_visitor'
SUPPORTED_FORMATS=['txt','md','docx']
RECOMMENDED_WORDS=300

def docx_parts(container):
    """Yield body paragraphs and table cells in order without merged-cell duplicates."""
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.table import Table

    element=container._tc if hasattr(container,'_tc') else container.element.body
    for child in element:
        if child.tag==qn('w:p'):
            yield Paragraph(child,container).text
        elif child.tag==qn('w:tbl'):
            table=Table(child,container)
            seen=set()
            for row in table.rows:
                for cell in row.cells:
                    if cell._tc not in seen:
                        seen.add(cell._tc)
                        yield from docx_parts(cell)

def create_api(page,quota_call,run_call,secret):
    if len(secret)<32:raise RuntimeError('Demo session signing secret is missing')
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    def identity(request):
        token=request.cookies.get(COOKIE,'')
        visitor,sep,signature=token.partition('.')
        valid=bool(re.fullmatch('[0-9a-f]{32}',visitor) and sep and re.fullmatch('[0-9a-f]{64}',signature) and hmac.compare_digest(signature,hmac.new(secret.encode(),('visitor:'+visitor).encode(),hashlib.sha256).hexdigest()))
        if not valid:visitor=secrets.token_hex(16)
        signed=visitor+'.'+hmac.new(secret.encode(),('visitor:'+visitor).encode(),hashlib.sha256).hexdigest()
        # Modal supplies the client IP in the ASGI scope; arbitrary headers are not identity.
        ip=request.client.host if request.client else 'unknown'
        network=hmac.new(secret.encode(),('network:'+ip).encode(),hashlib.sha256).hexdigest()
        return visitor,network,signed
    def response(payload,status,token):
        out=JSONResponse(payload,status_code=status)
        out.set_cookie(COOKIE,token,max_age=365*86400,httponly=True,secure=True,samesite='lax',path='/')
        out.headers['Cache-Control']='no-store'
        out.headers['X-Content-Type-Options']='nosniff'
        return out
    def normalize(text):return text.replace('\r\n','\n').replace('\r','\n')
    def validate(text):
        if not isinstance(text,str):return 'Text must be a string.'
        if len(normalize(text))>MAX_CHARS:return 'This free demo allows at most 6,000 characters per check. The desktop app has no demo character cap.'
        if len(text.split())<MIN_WORDS:return 'Add at least 20 words. Very short texts are unreliable.'
        return None
    def origin_allowed(request):
        origin=request.headers.get('origin')
        return not origin or origin in ('https://ninjagovlad--linda-pro-demo-web.modal.run',str(request.base_url).rstrip('/'))

    @api.middleware('http')
    async def upload_size_guard(request,call_next):
        if request.url.path=='/api/upload':
            length=request.headers.get('content-length','')
            if not length.isdigit():return JSONResponse({'detail':'Upload requires a known file size.'},status_code=411)
            if int(length)>MAX_UPLOAD_BYTES+16_384:return JSONResponse({'detail':'Free demo uploads are limited to 2 MB.'},status_code=413)
        return await call_next(request)

    @api.get('/',response_class=HTMLResponse)
    def index():
        return HTMLResponse(page,headers={'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"})

    @api.get('/health')
    def health():
        return {'status':'ok','app_version':'2.0.6.2','model_version':'1.3.4','model_pack_version':'1.3.4','markup_version':'2.0.6.2','demo_revision':'public-release-2062-20261017','detectors':['loupe','assay'],'max_chars':MAX_CHARS,'max_uses':MAX_USES,'recommended_words':RECOMMENDED_WORDS,'supported_formats':SUPPORTED_FORMATS,'access_code_required':False}

    @api.get('/api/session')
    async def session(request:Request):
        visitor,network,token=identity(request)
        try:state=await quota_call('status',visitor,network,None)
        except Exception:return response({'detail':'Demo counter unavailable; try again shortly.'},503,token)
        return response({**state,'max_chars':MAX_CHARS,'min_words':MIN_WORDS,'max_uses':MAX_USES,'recommended_words':RECOMMENDED_WORDS,'supported_formats':SUPPORTED_FORMATS,'app_version':'2.0.6.2','model_pack_version':'1.3.4','markup_version':'2.0.6.2','quota_identity':'signed browser cookie with shared-network daily protection'},200,token)

    @api.post('/api/detect')
    async def detect(request:Request):
        visitor,network,token=identity(request)
        if not origin_allowed(request):return response({'detail':'Use the demo from its own page.'},403,token)
        if request.headers.get('content-type','').split(';')[0]!='application/json':return response({'detail':'Expected JSON.'},415,token)
        length=request.headers.get('content-length')
        if length and (not length.isdigit() or int(length)>MAX_REQUEST_BYTES):return response({'detail':'This demo request is too large.'},413,token)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>MAX_REQUEST_BYTES:return response({'detail':'This demo request is too large.'},413,token)
            chunks.append(chunk)
        try:
            body=json.loads(b''.join(chunks))
            if not isinstance(body,dict):raise ValueError
            text=body.get('text');mode=body.get('mode','sensitive');detector=body.get('detector','loupe')
            if mode not in ('sensitive','precise') or detector not in ('assay','loupe'):raise ValueError
        except (ValueError,TypeError,UnicodeError):return response({'detail':'Invalid demo request.'},400,token)
        error=validate(text)
        if error:return response({'detail':error},400,token)
        text=normalize(text).strip()
        rid=secrets.token_hex(16)
        try:reservation=await quota_call('reserve',visitor,network,rid)
        except Exception:return response({'detail':'Demo counter unavailable; try again shortly.'},503,token)
        if not reservation['ok']:
            msg=f'The {MAX_USES} free demo checks for this browser or shared network have been used. Download the desktop app for further checks.' if reservation['reason']=='visitor_limit' else 'The free demo has reached its shared daily capacity. Please try tomorrow or use the desktop app.'
            return response({'detail':msg,'remaining':reservation['remaining']},429,token)
        try:
            result=await run_call(text,mode,detector)
            if not isinstance(result,dict) or result.get('detector_id')!=detector:raise RuntimeError('Detector identity mismatch')
        except asyncio.CancelledError:
            # A cancelled web request must release its pending reservation too.
            try:await asyncio.shield(quota_call('refund',visitor,network,rid))
            except Exception:pass
            raise
        except Exception:
            try:state=await quota_call('refund',visitor,network,rid)
            except Exception:state={}
            return response({'detail':'Detector unavailable; try again shortly.','remaining':state.get('remaining',reservation['remaining'])},503,token)
        try:state=await quota_call('finish',visitor,network,rid)
        except asyncio.CancelledError:
            # The request may disappear while the durable finish call is in flight.
            # A shielded refund is safe: quota.refund deletes pending rows only,
            # so a finish that committed before cancellation remains charged.
            try:await asyncio.shield(quota_call('refund',visitor,network,rid))
            except (Exception, asyncio.CancelledError):pass
            raise
        except Exception:
            # Refund removes only a pending row; a committed finish stays charged.
            # Withhold the result while the final counter state is uncertain.
            try:state=await quota_call('refund',visitor,network,rid)
            except Exception:state={}
            return response({'detail':'Could not finalize the demo counter. Try again shortly.','remaining':state.get('remaining',reservation['remaining'])},503,token)
        if not state.get('ok'):return response({'detail':'Demo reservation expired; try again shortly.','remaining':state['remaining']},503,token)
        return response({'status':'ok','result':result,'remaining':state['remaining'],'check_id':rid},200,token)

    @api.post('/api/upload')
    async def upload(request:Request,file:UploadFile=File(...)):
        visitor,network,token=identity(request)
        if not origin_allowed(request):return response({'detail':'Use the demo from its own page.'},403,token)
        content=await file.read(MAX_UPLOAD_BYTES+1)
        if len(content)>MAX_UPLOAD_BYTES:return response({'detail':'Free demo uploads are limited to 2 MB.'},413,token)
        ext=Path(file.filename or '').suffix.lower()
        try:
            if ext in ('.txt','.md'):
                text=content.decode('utf-8-sig')
                if any((ord(char)<32 and char not in '\t\n\r\f') or 0x7f<=ord(char)<=0x9f for char in text):
                    return response({'error_code':'invalid_file','detail':'This file does not look like a text document.'},400,token)
            elif ext=='.docx':
                import zipfile,docx
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    entries=archive.infolist()
                    if len(entries)>2000 or sum(x.file_size for x in entries)>8_000_000:raise ValueError('Expanded document exceeds the free demo limit.')
                document=docx.Document(io.BytesIO(content))
                text='\n\n'.join(value for value in docx_parts(document) if value.strip())
            else:return response({'error_code':'unsupported_format','detail':'This demo supports TXT, MD and DOCX files. PPT, PPTX and PDF files are not supported.'},400,token)
            text=normalize(text)
            if len(text)>MAX_CHARS:return response({'error_code':'text_too_long','detail':'Extracted text exceeds the free demo limit of 6,000 characters. Choose a shorter excerpt; it is not truncated automatically.'},400,token)
            text=text.strip()
            if not text:return response({'error_code':'empty_document','detail':'No text found in this file.'},400,token)
        except UnicodeDecodeError:
            return response({'error_code':'invalid_encoding','detail':'This text file is not valid UTF-8.'},400,token)
        except Exception:
            return response({'error_code':'invalid_file','detail':'The file could not be read. Check that it is a valid TXT, MD or DOCX file.'},400,token)
        return response({'status':'ok','filename':Path(file.filename or 'text.txt').name,'text':text,'words':len(text.split()),'chars':len(text)},200,token)
    return api
