import pytest
from linda_desktop.engine import Engine
from linda_desktop import history, report


class Detector:
    window_words,max_windows = 300,12
    rules = {key:{'thr_5':5,'thr_05':9,'thr_1':7} for key in ('essay','multi','stylo','ensemble')}
    mean = {name:0 for name in ('linda_essay','linda_multi_v2','stylo7c')}
    std = dict(mean,linda_essay=1,linda_multi_v2=1,stylo7c=1)
    def __init__(self,name,value=12):
        self.name,self.value,self.factories = name,value,[]
    def _factory(self,name):
        assert name==self.name,'An unselected model was executed'
        self.factories.append(name)
        return self
    def margins(self,texts):
        return [self.value]*len(texts)
    def detect(self,*args):
        raise AssertionError('Single mode must not run the ensemble')


def engine_for(det,gran='windows'):
    engine = Engine()
    engine.dets = {'sensitive':det,'precise':det}
    engine.device = 'cpu'
    engine.sentence_mode = lambda n:gran
    return engine


@pytest.mark.parametrize('name',['linda_essay','linda_multi_v2','stylo7c'])
def test_single_never_runs_other_voters(name):
    det = Detector(name)
    result = engine_for(det).run('First test sentence. Second test sentence.',models=[name])
    assert result['verdict']=='ai' and result['p_ai']==result['custom_verdict']['p_ai']
    assert set(result['voters'])=={name} and result['ens_z'] is None
    assert det.factories==[name] and result['models_used']==[name]
    assert result['heatmap_available']==(name!='stylo7c')
    if name=='stylo7c':
        assert result['ai_share'] is None and not result['sentences']
    else:
        assert all(s['label']=='ai' for s in result['sentences'])


@pytest.mark.parametrize('gran',['full','hybrid','context','smooth'])
def test_single_heatmap_modes_use_only_selected_model(gran):
    det = Detector('linda_multi_v2',-2)
    result = engine_for(det,gran).run('A human sentence. Another human sentence.',models=['linda_multi_v2'])
    assert result['verdict']=='human' and result['sentences']
    assert all(s['label']=='human' and 'essay_prob' not in s for s in result['sentences'])
    assert set(det.factories)=={'linda_multi_v2'}


@pytest.mark.parametrize('name',['linda_multi_v2','stylo7c'])
def test_history_and_report_keep_single_verdict(repo,name):
    result = engine_for(Detector(name)).run('An AI example. Another sentence.',models=[name])
    identity = history.add('An AI example. Another sentence.',result,'sensitive')
    check = history.get(identity)
    assert check['verdict']=='ai' and check['pct']==round(result['p_ai']*100)
    rep = report.report_for_check(check)
    assert rep['verdict']=='ai' and rep['models_used']==[name] and rep['ens_z'] is None
    assert rep['pct']==round(result['p_ai']*100)
    assert rep['p_ai']==result['p_ai']
    csv = report.to_csv(rep)
    assert 'models_used,'+name in csv and 'analysis_scope,single' in csv
    if name=='stylo7c':
        assert rep['ai_share'] is None and check['ai_share'] is None
        html = report.to_html(rep,'en')
        assert 'Sentence heatmap is unavailable' in html
        assert 'class="stack"' not in html


def test_routed_does_not_silently_run_a_different_selection():
    det = Detector('linda_essay')
    det.routed = True
    with pytest.raises(ValueError,match='requires all models'):
        engine_for(det).run('A test sentence.',models=['linda_essay'])
    assert not det.factories


@pytest.mark.parametrize('models', [['linda_essay'], ['linda_essay','linda_multi_v2'], ['stylo7c','stylo7c']])
def test_precise_subset_is_rejected_before_loading(models):
    engine = Engine()
    engine.ensure_loaded = lambda: pytest.fail('Unsupported request must not load models')
    with pytest.raises(ValueError, match='Precise mode requires all models'):
        engine._run_locked('A test sentence.', 'precise', models)


def test_subset_canonical_verdict_matches_display():
    det = Detector(None)
    det.detect = lambda texts:[{'verdict':'ai','p_ai':.99,'ens_z':20,'essay':12,'ai_share':1,
                               'voters':{'linda_essay':-10,'linda_multi_v2':-10,'stylo7c':20},
                               'windows':[{'first_word':0,'last_word':20,'essay':-10,'multi':-10}]}]
    result = engine_for(det).run('A test sentence.',models=['linda_essay','linda_multi_v2'])
    assert result['verdict']==result['custom_verdict']['verdict']=='human'
    assert result['p_ai']==result['custom_verdict']['p_ai']
    assert result['ensemble_reference']['verdict']=='ai' and result['analysis_scope']=='subset'
    assert result['ai_share']==result['authorship']['ai_share']


def test_cpu_initialization_does_not_eagerly_load_any_voter(repo,monkeypatch):
    from linda_pro import core,server
    from linda_desktop import engine as module
    monkeypatch.setattr(core,'DEFAULT_MODELS',core.DEFAULT_MODELS)
    monkeypatch.setattr(core,'DEFAULT_CALIBRATION',core.DEFAULT_CALIBRATION)
    engine = Engine()
    det = Detector('linda_essay')
    monkeypatch.setattr(engine,'routing_file',lambda:None)
    monkeypatch.setattr(engine,'calibration_file',lambda:repo.root/'fake-calibration.json')
    monkeypatch.setattr(module,'pick_device',lambda pref:'cpu')
    monkeypatch.setattr(server,'make_detectors',lambda device:{'sensitive':det,'precise':det})
    monkeypatch.setattr(engine,'_load_voters',lambda *args:pytest.fail('CPU eagerly loaded all voters'))
    assert engine.ensure_loaded()['sensitive'] is det and not det.factories
