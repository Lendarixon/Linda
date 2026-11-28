"""Чистая логика стилизации для демо: нарезка на фрагменты, проверки вариантов, сборка текста.
Без ML-зависимостей (тестируется без GPU). Детектор в отборе вариантов не участвует.
Индексы фрагментов - позиции Unicode-символов, как в разметке предложений детектора."""
import difflib,re

MAX_SPANS=40
MIN_SPAN_WORDS=4
CHUNK_WORDS=110
MAX_SIMILARITY=0.92
_NUM=re.compile(r'\d+(?:[.,]\d+)?')
_URL=re.compile(r'https?://\S+')
_TERM=re.compile(r'[.!?…»"\')\]]\s*$')
_PL=set('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')

def lang_guess(text):
    letters=[c for c in text if c.isalpha()]
    if not letters:return 'en'
    if sum('\u0400'<=c<='\u04ff' for c in letters)/len(letters)>0.3:return 'ru'
    if len(letters)>=80 and sum(c in _PL for c in letters)/len(letters)>=0.008:return 'pl'
    return 'en'

def validate_spans(text,spans):
    """None = весь текст. Иначе непустой список непересекающихся [start,end] внутри текста."""
    if spans is None:return None
    if not isinstance(spans,list) or not spans or len(spans)>MAX_SPANS:raise ValueError('bad spans')
    out=[]
    for s in spans:
        if not(isinstance(s,(list,tuple)) and len(s)==2 and all(isinstance(v,int) and not isinstance(v,bool) for v in s)):raise ValueError('bad span')
        a,b=s
        if a<0 or b>len(text) or a>=b:raise ValueError('span out of range')
        out.append((a,b))
    out.sort()
    for (a,b),(c,d) in zip(out,out[1:]):
        if c<b:raise ValueError('spans overlap')
    return out

def _trim(text,a,b):
    while b>a and text[b-1].isspace():b-=1
    while a<b and text[a].isspace():a+=1
    return a,b

def split_all(text,chunk_words=CHUNK_WORDS):
    """Весь текст -> абзацы; длинные абзацы режутся по границам предложений ~chunk_words слов."""
    spans=[]
    for m in re.finditer(r'[^\n]+',text):
        a=m.start();para=text[a:m.end()]
        if not para.strip():continue
        sents=[(x.start(),x.end()) for x in re.finditer(r'[^.!?…]+[.!?…]*\s*',para)] or [(0,len(para))]
        cs=None;ce=0;words=0
        for s,e in sents:
            w=len(para[s:e].split())
            if cs is not None and words+w>chunk_words:
                spans.append((a+cs,a+ce));cs=None;words=0
            if cs is None:cs=s
            ce=e;words+=w
        if cs is not None:spans.append((a+cs,a+ce))
    out=[]
    for a,b in spans:
        a,b=_trim(text,a,b)
        if b>a:out.append((a,b))
    return out[:MAX_SPANS]

def candidate_problems(src,cand,similarity=MAX_SIMILARITY):
    s,c=src.strip(),cand.strip()
    if not c:return ['empty']
    bad=[]
    if re.sub(r'\W+','',s.lower())==re.sub(r'\W+','',c.lower()):bad.append('identical')
    if not 0.6<=len(c)/max(1,len(s))<=1.6:bad.append('length_ratio')
    if sorted(_NUM.findall(s))!=sorted(_NUM.findall(c)):bad.append('numbers_changed')
    if sorted(_URL.findall(s))!=sorted(_URL.findall(c)):bad.append('urls_changed')
    if _TERM.search(s) and not _TERM.search(c):bad.append('truncation_suspect')
    if '\n' in c and '\n' not in s:bad.append('layout_changed')
    if lang_guess(c)!=lang_guess(s):bad.append('language_changed')
    if not bad and difflib.SequenceMatcher(None,s,c).ratio()>similarity:bad.append('too_similar')
    return bad

def pick(src,candidates):
    """Лучший из годных (ближайший по длине к исходнику) или None и причины отказа."""
    good=[];why=set()
    for c in candidates:
        p=candidate_problems(src,c)
        if p:why.update(p)
        else:good.append(c.strip())
    if not good:return None,sorted(why)
    return min(good,key=lambda c:abs(len(c)-len(src.strip()))),[]

def stylize_text(text,spans,generate,n=4):
    """generate(list[str],n)->list[list[str]]. Фрагмент без годного варианта остаётся исходным."""
    ranges=validate_spans(text,spans) if spans is not None else split_all(text)
    todo=[r for r in ranges if len(text[r[0]:r[1]].split())>=MIN_SPAN_WORDS]
    short=[r for r in ranges if r not in todo]
    outs=generate([text[a:b] for a,b in todo],n) if todo else []
    changes=[{'start':a,'end':b,'status':'too_short'} for a,b in short];repl={}
    for (a,b),cands in zip(todo,outs):
        best,why=pick(text[a:b],cands)
        if best is None:changes.append({'start':a,'end':b,'status':'kept','reasons':why})
        else:repl[(a,b)]=best;changes.append({'start':a,'end':b,'status':'changed','new':best})
    changes.sort(key=lambda x:x['start'])
    out=[];pos=0
    for (a,b),new in sorted(repl.items()):
        out.append(text[pos:a]);out.append(new);pos=b
    out.append(text[pos:])
    return {'text':''.join(out),'changes':changes,'changed':len(repl)}
