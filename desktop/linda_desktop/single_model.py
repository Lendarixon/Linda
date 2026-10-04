"""Single legacy voter: same calibrated thresholds, no other model execution."""
import numpy as np
from linda_pro.core import split_windows, top25
from linda_pro.voters import clean_text, check_cancel
from .sentences import split_sentences_with_offsets


def run(engine, det, text, mode, name):
    from .engine import _sig, authorship
    key = {'linda_essay':'essay','linda_multi_v2':'multi','stylo7c':'stylo'}[name]
    rules = det.rules[key]
    center = rules['thr_5']
    scale = max(1.0,(rules['thr_05']-center)/2.0)
    windows = split_windows(text,det.window_words,det.max_windows)
    check_cancel()
    voter = det._factory(name)
    if name=='stylo7c':
        raw = float(voter.margins([clean_text(text)])[0])
        margins = []
    else:
        margins = [float(x) for x in voter.margins([clean_text(w[0]) for w in windows])]
        raw = top25(margins)
    check_cancel()
    verdict = 'ai' if raw>=rules['thr_05'] else 'uncertain' if raw>=center else 'human'
    probability = round(_sig(raw,center,scale),3)
    result = {'verdict':verdict,'p_ai':probability,'mode':mode,'voters':{name:raw},'ens_z':None,
              'analysis_scope':'single','models_used':[name],'models_executed':[name],'heatmap_available':name!='stylo7c',
              'custom_verdict':{'model':name,'score':round(raw,2),'verdict':verdict,'p_ai':probability},
              'windows':[],'n_windows':len(windows),'sentences':[],'sentence_stats':None,
              'ai_share':None,'authorship':{'label':'unavailable'}}
    if name=='stylo7c':
        result['n_windows'] = 0
        return result  # Stylometry has no calibrated sentence heatmap.
    spans = split_sentences_with_offsets(text)
    gran = engine.sentence_mode(len(text.split()))
    word_count = len(text.split())
    if gran in ('full','hybrid','context') and spans:
        if gran in ('full','hybrid'):
            direct = [float(x) for x in voter.margins([s.text for s in spans])]
        if gran in ('context','hybrid'):
            anchors,context = engine._sentence_contexts([s.text for s in spans],engine.CONTEXT_ANCHORS_CPU if engine.device=='cpu' else engine.CONTEXT_ANCHORS_GPU)
            scores = voter.margins([clean_text(t) for t in context])
            contextual = [float(x) for x in np.interp(list(range(len(spans))),anchors,scores)]
        values = direct if gran=='full' else contextual if gran=='context' else [max(a,b) for a,b in zip(direct,contextual)]
    else:
        covers = [(a,b,score) for (_,a,b),score in zip(windows,margins)]
        if gran=='smooth' and spans:
            positions = [(m.start(),m.end()) for m in __import__('re').finditer(r'\S+',text)]
            intervals = engine._smooth_windows(word_count)
            if len(intervals)>1:
                texts = [clean_text(text[positions[a][0]:positions[b-1][1]]) for a,b in intervals]
                covers = [(a,b,float(v)) for (a,b),v in zip(intervals,voter.margins(texts))]
        values = []
        for span in spans:
            point = len(text[:span.start].split())+max(1,len(span.text.split()))//2
            cover = [w for w in covers if w[0]<=point<w[1]] or [min(covers,key=lambda w:abs((w[0]+w[1])/2-point))]
            values.append(sum(w[2] for w in cover)/len(cover))
    check_cancel()
    ai,uncertain = engine.thresholds(gran)
    counts = {'ai':0,'uncertain':0,'human':0}
    prefix = 'essay' if name=='linda_essay' else 'multi'
    for span,value in zip(spans,values):
        p = _sig(value,center,scale)
        label = 'ai' if p>=ai else 'uncertain' if p>=uncertain else 'human'
        counts[label]+=1
        result['sentences'].append({'start':span.start,'end':span.end,'text':span.text,'p_ai':round(p,3),'label':label,
                                    prefix+'_margin':round(value,2),prefix+'_prob':round(p,3)})
    sentences = result['sentences']
    total_words = sum(max(1,len(s['text'].split())) for s in sentences) or 1
    result['ai_share'] = sum(max(1,len(s['text'].split())) for s in sentences if s['label']=='ai')/total_words
    result['authorship'] = authorship(verdict,sentences)
    result['sentence_stats'] = {'total':len(sentences),**counts,'ai_pct':round(counts['ai']/len(sentences)*100) if sentences else 0,
                               'granularity':{'full':'sentence','context':'context','hybrid':'hybrid','smooth':'smooth','windows':'window'}[gran],
                               'thresholds':{'ai':ai,'uncertain':uncertain},'models_used':[name]}
    result['windows'] = [{'first_word':a,'last_word':b,'margin':value,'model':name} for (_,a,b),value in zip(windows,margins)]
    return result
