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
_RU_DEC_BAD=re.compile(r'\b\d+[.,]\d+\s+(?:процентов|рублей|годов|лет)\b',re.I)
_RU_INT_UNIT=re.compile(r'\b(\d+)\s+(процент(?:а|ов)?|рубл(?:ь|я|ей))\b',re.I)
_RU_GLUED=re.compile(r'\b[а-яё]{2,}[А-ЯЁ][а-яё]{2,}\b')
_LATIN_GLUED=re.compile(r'\b[a-z]{3,}[A-Z][a-z]{3,}\b')
_META_PREFIX_RE=re.compile(
    r'^(?:here\s+is\s+(?:the\s+)?(?:rewritten|edited|revised)\s+text\s*[:\-–]\s*|'
    r'rewritten\s+text\s*[:\-–]\s*|'
    r'вот\s+(?:переписанный|отредактированный|измен[ёе]нный)\s+текст\s*[:\-–]\s*|'
    r'oto\s+(?:przeredagowany|poprawiony)\s+tekst\s*[:\-–]\s*)',
    re.I,
)
_MD_INJECT_RE=re.compile(r'(?:\*\*[^*]+\*\*|^#{1,4}\s+)',re.M)


def strip_meta_wrapper(cand: str) -> str:
    """Strip stray <text>...</text> wrappers and common LLM preamble lines."""
    c = (cand or '').strip()
    if c.startswith('<text>') and c.endswith('</text>'):
        c = c[6:-7].strip()
    c = _META_PREFIX_RE.sub('', c).strip()
    return c


def _ru_numeral_issues(src,cand):
    """Detect Russian decimal/integer numeral agreement errors and glued CamelCase words not present in src."""
    issues=[]
    src_low=src.lower()
    for m in _RU_DEC_BAD.finditer(cand):
        if m.group(0).lower() not in src_low:
            issues.append('numeral_agreement')
            break
    if 'numeral_agreement' not in issues:
        for m in _RU_INT_UNIT.finditer(cand):
            # skip if part of a decimal like 1,8 процента
            if m.start()>0 and cand[m.start()-1] in '.,':
                continue
            n=int(m.group(1))
            unit=m.group(2).lower()
            n100,n10=n%100,n%10
            if 11<=n100<=14 or n10==0 or n10>=5:
                want='процентов' if unit.startswith('процент') else 'рублей'
            elif n10==1:
                want='процент' if unit.startswith('процент') else 'рубль'
            else:
                want='процента' if unit.startswith('процент') else 'рубля'
            if unit!=want and m.group(0).lower() not in src_low:
                issues.append('numeral_agreement')
                break
    for m in _RU_GLUED.finditer(cand):
        if m.group(0) not in src:
            issues.append('glued_word')
            break
    return issues


def _last_sentence_cut(src,cand):
    """Catch candidates that end with a period but silently truncated the final sentence(s) of a multi-sentence Russian chunk."""
    s_sents=[x.strip() for x in re.split(r'[.!?…]+',src) if x.strip()]
    c_sents=[x.strip() for x in re.split(r'[.!?…]+',cand) if x.strip()]
    if len(s_sents)<3 or len(c_sents)>=len(s_sents)*0.65:
        return False
    s_last,c_last=s_sents[-1],c_sents[-1]
    s_nums=set(_NUM.findall(s_last))
    c_nums=set(_NUM.findall(c_last))
    if s_nums and (s_nums & c_nums):
        return False
    s_stems={w[:4].lower() for w in re.findall(r'[а-яёa-z]{5,}',s_last,re.I)}
    c_stems={w[:4].lower() for w in re.findall(r'[а-яёa-z]{5,}',c_last,re.I)}
    return not (s_stems & c_stems)

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
    s=src.strip()
    c=strip_meta_wrapper(cand)
    if not c:return ['empty']
    bad=[]
    if re.sub(r'\W+','',s.lower())==re.sub(r'\W+','',c.lower()):bad.append('identical')
    if not 0.6<=len(c)/max(1,len(s))<=1.6:bad.append('length_ratio')
    if sorted(_NUM.findall(s))!=sorted(_NUM.findall(c)):bad.append('numbers_changed')
    if sorted(_URL.findall(s))!=sorted(_URL.findall(c)):bad.append('urls_changed')
    if _TERM.search(s) and not _TERM.search(c):bad.append('truncation_suspect')
    elif lang_guess(s)=='ru' and _last_sentence_cut(s,c):bad.append('truncation_suspect')
    if '\n' in c and '\n' not in s:bad.append('layout_changed')
    if _MD_INJECT_RE.search(c) and not _MD_INJECT_RE.search(s):bad.append('markdown_injected')
    lg=lang_guess(s)
    if lang_guess(c)!=lg:bad.append('language_changed')
    if lg=='ru':bad.extend(_ru_numeral_issues(s,c))
    else:
        for m in _LATIN_GLUED.finditer(c):
            if m.group(0) not in s:
                bad.append('glued_word')
                break
    if not bad and difflib.SequenceMatcher(None,s,c).ratio()>similarity:bad.append('too_similar')
    return bad

def pick_best_candidate(src,candidates):
    """Лучший из годных: сперва валидация без обёрток, затем естественная степень переработки (~0.68 similarity) и баланс длины."""
    s=src.strip()
    good=[];why=set()
    for raw in candidates:
        c=strip_meta_wrapper(raw)
        p=candidate_problems(s,c)
        if p:why.update(p)
        else:good.append(c)
    if not good:return None,sorted(why)
    return min(good,key=lambda c:abs(difflib.SequenceMatcher(None,s,c).ratio()-0.68)+0.15*abs(len(c)-len(s))/max(1,len(s))),[]

def pick(src,candidates):
    """Совместимая обёртка над pick_best_candidate."""
    return pick_best_candidate(src,candidates)

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
