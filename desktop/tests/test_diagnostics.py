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
