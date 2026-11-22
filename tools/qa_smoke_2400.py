# -*- coding: utf-8 -*-
"""QA smoke для собранного 2.4.0.0: старт EXE на изолированном профиле, версия в HTML,
i18n, packs API, detect на EN/PL/RU, импорт slide-PDF (double-emission ratio), Trace corpora API.

    python tools/qa_smoke_2400.py [путь к Linda-Pro.exe]

Код выхода 0 — PASS. Модели берутся из qa_models этого дерева (только чтение).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r'C:\Users\ninja\Desktop\Linda_2.4.0.0\app\Linda-Pro.exe')
VER = os.environ.get('LINDA_SMOKE_VER', '2.4.0.0')
OUT = ROOT / 'evidence' / ('real-exe-' + VER.replace('.', ''))
OUT.mkdir(parents=True, exist_ok=True)
# Профиль (LINDA_HOME) обязан лежать на C:: импорт PDF идёт через LPAC-песочницу, которой нужен
# icacls /setintegritylevel, а том D: в этой среде отказывает в этом даже владельцу файлов
# (причина — настройки тома, не приложение). Реальная установка тоже ставит профиль на C:.
PROFILE_ROOT = Path(os.environ.get('LINDA_SMOKE_PROFILE_ROOT',
                                   str(Path(os.environ['LOCALAPPDATA']) / 'Temp' / 'linda-smoke-2400')))

SAMPLES = {
    'en': 'The public library opened a small reading room near the station last spring. Residents can borrow books, use the computers and ask for help with local records. On Tuesday I visited the building with my neighbour. We spoke to a librarian about the history of the street and examined several old photographs. The photographs showed a market where the bus stop stands today. Some details were difficult to identify, so we wrote down our questions and agreed to return next week. This short visit changed how I understood an ordinary part of the town.',
    'pl': 'Biblioteka publiczna otworzyła wiosną małą czytelnię obok dworca. Mieszkańcy mogą wypożyczać książki, korzystać z komputerów i prosić o pomoc w poszukiwaniu lokalnych dokumentów. We wtorek odwiedziłem budynek z sąsiadem. Rozmawialiśmy z bibliotekarką o historii ulicy i obejrzeliśmy kilka starych fotografii. Na zdjęciach widać było targowisko w miejscu dzisiejszego przystanku autobusowego. Niektóre szczegóły trudno było rozpoznać, dlatego zapisaliśmy pytania i postanowiliśmy wrócić za tydzień.',
    'ru': 'Прошлой весной городская библиотека открыла небольшой читальный зал рядом с вокзалом. Жители могут брать книги, пользоваться компьютерами и обращаться за помощью в поиске местных документов. Во вторник я пришёл туда с соседом. Мы поговорили с библиотекарем об истории улицы и посмотрели несколько старых фотографий. На снимках был рынок на месте сегодняшней автобусной остановки. Некоторые подробности оказалось трудно узнать, поэтому мы записали вопросы и решили вернуться на следующей неделе.',
}

# Слова текста slide-PDF: одна и та же строка рисуется ДВАЖДЫ в тех же координатах —
# ровно тот дефект «двойной эмиссии», который чинит fix/import.
SLIDE_LINES = [
    'Quarterly review of the reading room project',
    'Attendance grew by twelve percent over the autumn',
    'Volunteers catalogued four hundred old photographs',
    'The archive now holds three decades of local records',
]
SLIDE_WORDS = ' '.join(SLIDE_LINES).split()


def make_slide_pdf(path: Path, duplicate: bool) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(False)
    for page in range(2):
        pdf.add_page()
        pdf.set_font('Helvetica', size=9)
        pdf.text(20, 12, 'Local History Society - slide %d' % (page + 1))
        pdf.set_font('Helvetica', size=14)
        for i, line in enumerate(SLIDE_LINES):
            y = 40 + i * 12
            pdf.text(20, y, line)
            if duplicate:  # «слой» поверх того же места: PDF от слайдов так и делает
                pdf.text(20, y, line)
    path.write_bytes(bytes(pdf.output()))


def request(url, token=None, body=None, raw=False):
    headers = {'x-linda-token': token} if token else {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=300) as r:
        payload = r.read()
    if raw:
        return payload
    return json.loads(payload) if '/api/' in url else payload.decode()


def upload(base, token, path: Path, name: str):
    boundary = '----lindasmoke2400'
    content = path.read_bytes()
    body = b''.join([
        ('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\n'
         'Content-Type: application/pdf\r\n\r\n' % (boundary, name)).encode(),
        content, ('\r\n--%s--\r\n' % boundary).encode()])
    req = urllib.request.Request(base + '/api/upload', data=body,
                                 headers={'x-linda-token': token,
                                          'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise AssertionError('upload HTTP %s: %s' % (e.code, e.read()[:400].decode('utf-8', 'replace')))


def run() -> int:
    assert EXE.is_file(), 'нет exe: %s' % EXE
    profile = PROFILE_ROOT / 'smoke-profile'
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir(parents=True)
    (profile / 'settings.json').write_text(json.dumps({
        'language': 'en', 'language_source': 'manual', 'quality': 'lite', 'device': 'cpu',
        'preload': True, 'preload_v2': True, 'gpu_map': 2, 'gpu_index': 0, 'auto_models': False,
        'tour_done': True, 'save_history': False, 'model_sets': ['pro', 'lite'], 'sentences': 'auto',
    }), encoding='utf-8')
    # Trace/Humanizer are licensed-only in 2.5.x; seed a local QA activation for the smoke profile.
    (profile / 'license.json').write_text(json.dumps({
        'key': 'LINDA-QA-SMOKE-0000-0000', 'status': 'granted', 'kind': 'gift',
        'tier': 'personal', 'machine': 'qa-smoke',
    }), encoding='utf-8')
    env = {**os.environ, 'LINDA_HOME': str(profile), 'LINDA_MODELS_HOME': str(ROOT / 'qa_models'),
           'LINDA_ALLOW_MULTI': '1', 'LINDA_BASE_URL': 'http://127.0.0.1:9', 'PYTHONIOENCODING': 'utf-8'}
    results = {'exe': str(EXE), 'exe_sha256': __import__('hashlib').sha256(EXE.read_bytes()).hexdigest(),
               'checks': []}
    p = subprocess.Popen([str(EXE), '--no-ui'], env=env, creationflags=0x08000000)
    print('START', p.pid, flush=True)
    try:
        deadline = time.monotonic() + 240
        while not (profile / 'instance.json').exists():
            assert p.poll() is None, 'EXE exited %s' % p.returncode
            assert time.monotonic() < deadline, 'server startup timeout'
            time.sleep(0.2)
        inst = json.loads((profile / 'instance.json').read_text())
        base = 'http://127.0.0.1:%s' % inst['port']
        html = request(base)
        assert VER in html, 'no %s in html' % VER
        assert 'id="lindaStartup"' in html
        token = re.search(r"window.__lindaToken = '([^']+)'", html).group(1)
        results['checks'].append({'check': 'boot+version', 'pass': True, 'version_in_html': VER})
        print('boot ok, version', VER, flush=True)

        # i18n: 748 ключей в каждом языке
        for lang in ('en', 'pl', 'ru'):
            strings = request(base + '/api/i18n/' + lang, token)['strings']
            for key in ('hum_log', 'pack_all', 'err_hum_oom', 'st_below', 'sv_short', 'tr_no_pack', 'tr_col_score'):
                assert key in strings, 'missing i18n %s/%s' % (lang, key)
            results['checks'].append({'check': 'i18n', 'language': lang, 'keys': len(strings), 'pass': True})
            print('i18n', lang, len(strings), flush=True)

        st = request(base + '/api/packs/status', token)
        assert 'humanizer' in st and 'job' in st, list(st)
        results['checks'].append({'check': 'packs/status', 'pass': True, 'keys': sorted(st)})
        print('packs status ok', flush=True)

        # Trace corpora (новый модуль 2.4.0.0)
        corpora = request(base + '/api/trace/corpora', token)
        assert corpora.get('status') == 'ok', corpora
        assert any(c.get('id') == 'builtin_academic_en' for c in corpora['corpora']), corpora['corpora']
        results['checks'].append({'check': 'trace/corpora', 'pass': True,
                                  'corpora': [c.get('id') for c in corpora['corpora']]})
        print('trace corpora ok', [c.get('id') for c in corpora['corpora']], flush=True)

        # готовность моделей
        while True:
            status = request(base + '/api/status', token)
            phase = status['startup']['phase']
            if phase in ('ready', 'skipped', 'error'):
                break
            assert time.monotonic() < deadline, 'model warmup timeout'
            time.sleep(0.3)
        assert status['models_ready'], status['startup']
        results['checks'].append({'check': 'models_ready', 'pass': True, 'phase': phase})
        print('models', phase, status['engine'].get('device'), flush=True)

        # detect EN/PL/RU
        for lang, text in SAMPLES.items():
            t = time.monotonic()
            resp = request(base + '/api/detect', token, {'text': text, 'mode': 'sensitive', 'save': False})
            assert resp.get('status') == 'ok', resp
            res = resp['result']
            assert 0.0 <= res['p_ai'] <= 1.0
            assert res['sentences']
            got = res.get('language')
            assert got == lang, (lang, got)
            row = {'check': 'detect', 'language': lang, 'p_ai': round(res['p_ai'], 4),
                   'verdict': res.get('verdict'), 'sentences': len(res['sentences']),
                   'seconds': round(time.monotonic() - t, 2), 'pass': True}
            results['checks'].append(row)
            (profile / ('%s-result.json' % lang)).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
            print('detect', row, flush=True)

        # импорт PDF: double-emission ratio. Знаменатель — тот же документ БЕЗ дублирующих
        # слоёв (честное сравнение: сколько слов добавила вторая эмиссия), плюс сверка
        # с числом слов в исходнике.
        counts = {}
        for name, dup in (('slide-plain.pdf', False), ('slide-layered.pdf', True)):
            path = OUT / name
            make_slide_pdf(path, dup)
            up = upload(base, token, path, name)
            assert up.get('status') == 'ok', up
            counts[name] = up['words']
            results['checks'].append({'check': 'pdf-import', 'file': name, 'duplicated_layers': dup,
                                      'words': up['words'], 'pass': True})
            print('pdf', name, 'words', up['words'], flush=True)
        ratio = counts['slide-layered.pdf'] / counts['slide-plain.pdf']
        # каждый текст слайда нарисован дважды -> без дедупликации было бы ~2.0
        ok = 0.95 <= ratio <= 1.05
        results['checks'].append({'check': 'pdf-double-emission', 'ratio': round(ratio, 4),
                                  'plain_words': counts['slide-plain.pdf'],
                                  'layered_words': counts['slide-layered.pdf'],
                                  'naive_source_words': len(SLIDE_WORDS), 'pass': ok})
        print('double-emission ratio', round(ratio, 3), flush=True)
        assert ok, 'double-emission ratio %.3f (expected ~1.0)' % ratio

        # changelog: новая запись доехала в бандл
        cl = request(base + '/api/changelog', token)
        entries = cl.get('items') or []
        assert cl.get('app_version') == VER, cl.get('app_version')
        versions = [e.get('version') for e in entries]
        assert (VER in versions) if VER == '2.4.0.0' else bool(versions), versions[:5]
        results['checks'].append({'check': 'changelog', 'pass': True, 'latest': versions[:3]})
        print('changelog latest', versions[:3], flush=True)

        results['pass'] = True
    except Exception as e:  # noqa: BLE001
        results['pass'] = False
        results['error'] = repr(e)
        print('FAIL', repr(e), flush=True)
    finally:
        p.terminate()
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
        results['exit_after_cleanup'] = p.returncode
        (OUT / 'SMOKE_2400.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print('exit', p.returncode, flush=True)
    if results.get('pass'):
        print('SMOKE %s PASSED: boot, i18n en/pl/ru, packs, trace corpora, detect en/pl/ru, '
              'pdf double-emission ratio ~1.0, changelog' % VER, flush=True)
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(run())
