"""Native counterparts of modern HTML report sections; no browser process."""
import io,re
from . import report_pdf

def append_sections(pdf,rep,lang,fam,S,h1,need):
    t=report_pdf.T.get(lang,report_pdf.T['en'])
    if rep.get('heatmap_available') is not False:
        violin=report_pdf._violin(rep,t)
        if violin:
            # SVG paths stay vector; labels use the embedded Unicode font.
            violin=re.sub(r'<text\b[^>]*>.*?</text>','',violin,flags=re.S)
            violin=violin.replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ',1)
            need(86);h1(t['violin'])
            pdf.image(io.BytesIO(violin.encode('utf-8')),x=15,y=pdf.get_y(),w=180,h=69)
            pdf.ln(70);pdf.set_font(fam,'',9)
            pdf.multi_cell(0,5,S('   |   '.join(t[k] for k in ('vi_h','vi_a','vi_t'))),new_x='LMARGIN',new_y='NEXT')
    h1(t['structure']);pdf.set_font(fam,'',9)
    pdf.multi_cell(0,5,S(t['st_note']),new_x='LMARGIN',new_y='NEXT')
    layout=(rep.get('structure_layout') or [])[:40]
    largest=max([r.get('words',1) for r in layout] or [1]) or 1
    for index,row in enumerate(layout,1):
        need(9);y=pdf.get_y();pdf.set_text_color(93,101,117);pdf.set_font(fam,'',8)
        pdf.cell(10,7,str(index));width=max(8,145*row.get('words',1)/largest)
        chunks=row.get('sentences') or [];total=sum(max(1,c.get('words',1)) for c in chunks) or 1;x=25
        if chunks and rep.get('heatmap_available') is not False:
            for chunk in chunks:
                portion=width*max(1,chunk.get('words',1))/total
                color=report_pdf._col(float(chunk.get('p_ai',0)))
                pdf.set_fill_color(*(int(color[i:i+2],16) for i in (1,3,5)))
                pdf.rect(x,y+1,portion,5,style='F');x+=portion
        else:pdf.set_fill_color(201,206,218);pdf.rect(x,y+1,width,5,style='F')
        pdf.set_xy(175,y);pdf.cell(20,7,str(row.get('words',0)));pdf.set_xy(15,y+8)
    pdf.set_text_color(0,0,0)
    features=[f for f in rep.get('structure_notable') or [] if f.get('human_range')]
    if features:
        h1(t['features']);pdf.set_font(fam,'',9);pdf.multi_cell(0,5,S(t['ft_note']),new_x='LMARGIN',new_y='NEXT')
        for feature in features:
            need(16)
            label=report_pdf.FEAT.get(lang,{}).get(feature.get('key'),feature.get('name',''))
            pdf.multi_cell(0,5,S('%s: %s' % (label,feature.get('value','—'))),new_x='LMARGIN',new_y='NEXT')
            graph=report_pdf._range_row(feature)
            if graph:
                graph=graph.replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ',1)
                pdf.image(io.BytesIO(graph.encode('utf-8')),x=15,y=pdf.get_y(),w=100,h=9)
                pdf.ln(10)
    h1(t['marked']);pdf.set_font(fam,'',10)
    if rep.get('heatmap_available') is False:
        unavailable={'ru':'Подсветка предложений недоступна для выбранной модели.','pl':'Podświetlanie zdań jest niedostępne dla wybranego modelu.','en':'Sentence heatmap is unavailable for the selected model.'}[lang]
        pdf.multi_cell(0,6,S(unavailable),new_x='LMARGIN',new_y='NEXT')
    sentences=rep.get('sentences') or []
    if sentences:
        for sentence in sentences:
            label=sentence.get('label');fill=rep.get('heatmap_available') is not False and label in ('ai','uncertain')
            if fill:pdf.set_fill_color(*((253,226,228) if label=='ai' else (255,243,205)))
            pdf.multi_cell(0,6,S(sentence.get('text','')),fill=fill,new_x='LMARGIN',new_y='NEXT');pdf.ln(1)
    else:pdf.multi_cell(0,6,S(rep.get('text') or ''),new_x='LMARGIN',new_y='NEXT')
