# -*- coding: utf-8 -*-
"""Сборка диагностического ZIP: состав архива, маскировка пути, пропуск логов, лимит размера."""
import base64
import io
import json
import os
import random
import zipfile

from linda_desktop import diagnostics


def _open(info):
    """Собрать архив и вернуть (байты, открытый ZIP)."""
    data = diagnostics.build_zip(info)
    assert isinstance(data, bytes)
    return data, zipfile.ZipFile(io.BytesIO(data))


def test_zip_contents_and_settings_without_text(tmp_path):
    """Внутри system.json (настройки без текста), хвост лога на 300 строк и README."""
    log = tmp_path / 'app.log'
    log.write_text('\n'.join('line %d' % i for i in range(1, 351)) + '\n', encoding='utf-8')
    info = {
        'app_version': '2.0.2.21', 'weights_version': '1.4',
        'device': 'cuda', 'gpus': ['NVIDIA GeForce RTX 4070', 'AMD Radeon RX 9070 XT'],
        'settings': {'theme': 'dark', 'language': 'ru', 'draft': 'короткий текст',
                     'hint': 'x' * 200, 'ui': {'note': 'пользовательская заметка', 'density': 'cozy'}},
        'log_files': [str(log)],
    }
    data, z = _open(info)
    assert set(z.namelist()) == {'system.json', 'logs/app.log.txt', 'README.txt'}
    assert len(data) <= diagnostics.MAX_ZIP_BYTES

    system = json.loads(z.read('system.json').decode('utf-8'))
    assert system['app_version'] == '2.0.2.21' and system['weights_version'] == '1.4'
    assert system['device'] == 'cuda' and len(system['gpus']) == 2
    # Поля с текстом (по имени и по длине значения) вырезаны, обычные настройки остались.
    assert system['settings'] == {'theme': 'dark', 'language': 'ru', 'ui': {'density': 'cozy'}}
    assert info['settings']['draft'] == 'короткий текст'  # исходный словарь не изменён

    lines = z.read('logs/app.log.txt').decode('utf-8').splitlines()
    assert len(lines) == diagnostics.MAX_LOG_LINES == 300
    assert lines[0] == 'line 51' and lines[-1] == 'line 350'  # последние 300 строк

    readme = z.read('README.txt').decode('utf-8')
    assert 'system.json' in readme and 'logs' in readme
    assert 'текст' in readme.lower() and 'истори' in readme.lower()  # тексты и история не включены


def test_home_path_is_replaced_with_userprofile(tmp_path):
    """Путь домашней папки в логе заменяется на %USERPROFILE%."""
    home = os.path.expanduser('~')
    log = tmp_path / 'user.log'
    log.write_text('открыл %s\\Documents\\текст.txt\nсм. %s/Downloads\n' % (home, home), encoding='utf-8')
    _, z = _open({'log_files': [str(log)], 'settings': {}})
    body = z.read('logs/user.log.txt').decode('utf-8')
    assert home and home not in body
    assert 'открыл %USERPROFILE%\\Documents\\текст.txt' in body
    assert 'см. %USERPROFILE%/Downloads' in body


def test_metadata_recursively_redacts_profile_and_custom_model_paths(tmp_path, monkeypatch):
    profile = tmp_path / 'PrivateAccount'
    profile_text = str(profile)
    monkeypatch.setattr(diagnostics.os.path, 'expanduser', lambda _path: profile_text)
    custom_models = profile / 'LindaModels'
    log = profile / 'Linda-Pro' / 'app.log'
    log.parent.mkdir(parents=True)
    log.write_text('started from %s\\AppData\\Local\n' % profile_text, encoding='utf-8')
    info = {
        'models_location': {
            'path': str(custom_models), 'default': str(profile / 'Linda-Pro'),
            'chosen': str(custom_models), 'custom': True,
        },
        'log_files': [str(log)],
        'nested': [
            {'detail': 'cache under %s' % custom_models},
            {'detail': 'alternate path %s' % str(custom_models).replace('\\', '/').lower()},
        ],
        'settings': {'theme': 'dark'},
    }

    _, archive = _open(info)
    members = {name: archive.read(name) for name in archive.namelist()}
    assert members
    assert all(b'PrivateAccount' not in body for body in members.values())
    system = json.loads(members['system.json'].decode('utf-8'))
    assert system['models_location']['path'] == '%MODELS_LOCATION%'
    assert system['models_location']['default'] == '%MODELS_LOCATION%'
    assert system['log_files'] == ['%LOG_FILE%']
    assert system['nested'][0]['detail'] == 'cache under %MODELS_LOCATION%'
    assert system['nested'][1]['detail'] == 'alternate path %MODELS_LOCATION%'
    assert b'%USERPROFILE%\\AppData\\Local' in members['logs/app.log.txt']
    # The privacy transformation is applied to a copy; the real paths remain
    # available to the log reader and in the caller's original metadata.
    assert info['log_files'] == [str(log)]
    assert info['models_location']['path'] == str(custom_models)


def test_missing_and_unreadable_logs_do_not_break(tmp_path):
    """Отсутствующий файл и ошибка чтения не роняют сборку, рабочий лог попадает в архив."""
    log = tmp_path / 'ok.log'
    log.write_text('запись\n', encoding='utf-8')
    info = {'log_files': [str(tmp_path / 'missing.log'), str(tmp_path), str(log)], 'settings': {}}
    _, z = _open(info)
    names = z.namelist()
    assert 'logs/ok.log.txt' in names
    assert not any('missing' in n for n in names)
    assert len(names) == 3  # system.json, один рабочий лог и README
    assert z.read('logs/ok.log.txt').decode('utf-8') == 'запись\n'


def test_zip_never_exceeds_two_megabytes(tmp_path):
    """Крупный несжимаемый лог обрезается: архив в пределах лимита, свежий хвост сохранён."""
    rng = random.Random(7)
    lines = ['%.3d %s' % (i, base64.b64encode(rng.randbytes(30000)).decode()) for i in range(300)]
    log = tmp_path / 'big.log'
    log.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    data, z = _open({'log_files': [str(log)], 'settings': {}})
    assert len(data) <= diagnostics.MAX_ZIP_BYTES
    kept = z.read('logs/big.log.txt').decode('utf-8').splitlines()
    assert 0 < len(kept) < diagnostics.MAX_LOG_LINES  # старые строки обрезаны
    assert kept[-1] == lines[-1]  # самый свежий хвост лога остался
