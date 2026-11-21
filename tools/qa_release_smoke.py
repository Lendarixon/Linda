"""Bounded real EXE/model smoke, isolated profiles and model/cache copy."""
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXE=Path.home()/'Desktop/Linda_2.1.0.0/app/Linda-Pro.exe'
OUT=ROOT/'evidence/real-exe'
OUT.mkdir(parents=True,exist_ok=True)
SAMPLES={
 'en': 'The public library opened a small reading room near the station last spring. Residents can borrow books, use the computers and ask for help with local records. On Tuesday I visited the building with my neighbour. We spoke to a librarian about the history of the street and examined several old photographs. The photographs showed a market where the bus stop stands today. Some details were difficult to identify, so we wrote down our questions and agreed to return next week. This short visit changed how I understood an ordinary part of the town. The collection is useful because it preserves small events that rarely appear in national histories.',
 'pl': 'Biblioteka publiczna otworzyła wiosną małą czytelnię obok dworca. Mieszkańcy mogą wypożyczać książki, korzystać z komputerów i prosić o pomoc w poszukiwaniu lokalnych dokumentów. We wtorek odwiedziłem budynek z sąsiadem. Rozmawialiśmy z bibliotekarką o historii ulicy i obejrzeliśmy kilka starych fotografii. Na zdjęciach widać było targowisko w miejscu dzisiejszego przystanku autobusowego. Niektóre szczegóły trudno było rozpoznać, dlatego zapisaliśmy pytania i postanowiliśmy wrócić za tydzień. Ta krótka wizyta zmieniła moje spojrzenie na zwyczajną część miasta. Zbiór jest przydatny, ponieważ zachowuje małe wydarzenia, które rzadko trafiają do ogólnokrajowych opracowań historycznych. Chciałbym kiedyś porozmawiać ze starszymi mieszkańcami i porównać ich wspomnienia z opisami zdjęć.',
 'ru': 'Прошлой весной городская библиотека открыла небольшой читальный зал рядом с вокзалом. Жители могут брать книги, пользоваться компьютерами и обращаться за помощью в поиске местных документов. Во вторник я пришёл туда с соседом. Мы поговорили с библиотекарем об истории улицы и посмотрели несколько старых фотографий. На снимках был рынок на месте сегодняшней автобусной остановки. Некоторые подробности оказалось трудно узнать, поэтому мы записали вопросы и решили вернуться на следующей неделе. Эта короткая встреча изменила мой взгляд на привычную часть города. Коллекция полезна тем, что сохраняет небольшие события, редко попадающие в общие исторические труды. В следующий раз мы хотим сравнить подписи к снимкам с воспоминаниями старых жителей.'
}


def request(url,token=None,body=None):
    headers={'x-linda-token':token} if token else {}
    data=None
    if body is not None:
        data=json.dumps(body).encode()
        headers['Content-Type']='application/json'
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers),timeout=180) as r:
        data=r.read()
        return json.loads(data) if '/api/' in url else data.decode()


def run_case(name,quality,device,preload=True,native=False):
    profile=OUT/name
    if profile.exists():
        profile=OUT/(name+'-'+str(int(time.time())))
    profile.mkdir()
    settings={'language':'en','language_source':'manual','quality':quality,'device':device,
        'preload':preload,'preload_v2':True,'gpu_map':2,'gpu_index':0,'auto_models':False,
        'tour_done':True,'save_history':False,'model_sets':['pro','lite'],'sentences':'auto'}
    (profile/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
    env={**os.environ,'LINDA_HOME':str(profile),'LINDA_MODELS_HOME':str(ROOT/'qa_models'),
        'LINDA_ALLOW_MULTI':'1','LINDA_BASE_URL':'http://127.0.0.1:9','PYTHONIOENCODING':'utf-8'}
    started=time.monotonic()
    p=subprocess.Popen([str(EXE)]+([] if native else ['--no-ui']),env=env,creationflags=0x08000000)
    result={'name':name,'pid':p.pid,'native_window':native,'settings':settings,'timeline':[],'checks':[]}
    print('START',name,p.pid,flush=True)
    try:
        deadline=time.monotonic()+180
        while not (profile/'instance.json').exists():
            assert p.poll() is None, f'EXE exited {p.returncode}'
            assert time.monotonic()<deadline,'server startup timeout'
            time.sleep(.2)
        inst=json.loads((profile/'instance.json').read_text())
        base=f'http://127.0.0.1:{inst["port"]}'
        html=request(base)
        token=re.search(r"window.__lindaToken = '([^']+)'",html).group(1)
        assert '2.1.0.0' in html and 'id="lindaStartup"' in html
        previous=None
        while True:
            status=request(base+'/api/status',token)
            phase=status['startup']['phase']
            if phase!=previous:
                result['timeline'].append({'phase':phase,'seconds':round(time.monotonic()-started,3),'engine':status['engine']})
                print(name,phase,round(time.monotonic()-started,2),flush=True)
                previous=phase
            if phase in ('ready','skipped','error'):
                break
            assert time.monotonic()<deadline,'model warmup timeout'
            time.sleep(.3)
        assert status['models_ready'],{'models_ready':False,'startup':status['startup']}
        assert phase==('ready' if preload else 'skipped'),status['startup']
        if preload:
            for lang,text in SAMPLES.items():
                t=time.monotonic()
                response=request(base+'/api/detect',token,{'text':text,'mode':'sensitive','save':False})
                assert response.get('status')=='ok',response
                data=response['result']
                assert 0<=data['p_ai']<=1
                assert data['sentences'],data
                assert data.get('language')==lang,(lang,data.get('language'))
                (profile/f'{lang}-result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                result['checks'].append({'language':lang,'seconds':round(time.monotonic()-t,3),'p_ai':data['p_ai'],'verdict':data['verdict'],'sentences':len(data['sentences'])})
                print(name,result['checks'][-1],flush=True)
        else:
            assert status['engine']['phase']=='idle'
        result['pass']=True
    except Exception as e:
        result['pass']=False;result['error']=repr(e)
        raise
    finally:
        p.terminate()
        p.wait(timeout=30)
        result['exit_after_cleanup']=p.returncode
        (OUT/f'{name}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    run_case('loupe-cpu','lite','cpu',native=True)
    run_case('assay-dml','pro','cuda',native=True)
    run_case('both-dml','both','cuda')
    run_case('preload-disabled','lite','cpu',preload=False)
    print('ALL REAL EXE SMOKES PASSED',flush=True)
