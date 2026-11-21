"""DPAPI restart-draft storage using synthetic temporary profiles only."""
import json
import time

import pytest

from linda_desktop import config, protected_storage, restart_draft


@pytest.fixture
def path(tmp_path, monkeypatch):
    root = tmp_path / 'synthetic-draft-profile'
    root.mkdir()
    monkeypatch.setattr(config, 'data_dir', lambda: root)
    monkeypatch.setattr(config, 'enterprise', lambda: {})
    monkeypatch.setattr(restart_draft, 'load_settings', lambda: {'save_history': True})
    return root / 'restart-draft.json'


def test_draft_and_atomic_buffer_are_encrypted(path, monkeypatch):
    original = protected_storage.atomic_write
    buffers = []
    def capture(target, data):
        buffers.append(data)
        assert data.startswith(protected_storage.MAGIC)
        assert b'SYNTHETIC_PRIVATE_TEXT' not in data
        original(target, data)
    monkeypatch.setattr(protected_storage, 'atomic_write', capture)
    text = 'SYNTHETIC_PRIVATE_TEXT\n exact whitespace. '
    restart_draft.save(text)
    stored = path.read_bytes()
    assert stored.startswith(protected_storage.MAGIC)
    assert text.encode() not in stored
    assert restart_draft.read()['text'] == text
    assert len(buffers) == 1
    assert not list(path.parent.glob('*.protected-tmp'))


def test_native_legacy_migration_keeps_nonce_timestamp_and_matching_ack(path):
    record = {'id': 'legacy-nonce-existing-ui', 'ts': time.time(), 'text': 'synthetic legacy text'}
    path.write_text(json.dumps(record), encoding='utf-8')
    assert restart_draft.read() == record
    assert path.read_bytes().startswith(protected_storage.MAGIC)
    decoded = json.loads(protected_storage.unprotect(path.read_bytes(), 'restart-draft'))
    assert decoded == record
    assert not restart_draft.acknowledge('stale-other-nonce')
    assert restart_draft.acknowledge(record['id'])
    assert not path.exists()


def test_ack_can_migrate_and_ack_legacy_without_changing_nonce(path):
    record = {'id': 'legacy-ack', 'ts': time.time(), 'text': 'synthetic'}
    path.write_text(json.dumps(record), encoding='utf-8')
    assert restart_draft.acknowledge(record['id'])
    assert not path.exists()


@pytest.mark.parametrize('damage', ['ciphertext', 'wrong_purpose', 'invalid_json', 'invalid_metadata', 'overflow_timestamp'])
def test_corrupt_or_unreadable_draft_is_preserved(path, damage):
    restart_draft.save('synthetic document')
    if damage == 'ciphertext':
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
    elif damage == 'wrong_purpose':
        path.write_bytes(protected_storage.protect(b'{}', 'another-storage-domain'))
    elif damage == 'invalid_json':
        path.write_bytes(b'{broken legacy JSON')
    elif damage == 'invalid_metadata':
        path.write_bytes(protected_storage.protect(b'{"id":"valid","ts":0,"text":17}', 'restart-draft'))
    else:
        record = {'id': 'valid', 'ts': 10 ** 400, 'text': 'synthetic'}
        path.write_bytes(protected_storage.protect(json.dumps(record).encode(), 'restart-draft'))
    before = path.read_bytes()
    assert restart_draft.read() is None
    assert path.read_bytes() == before
    assert not restart_draft.acknowledge('valid')
    assert path.read_bytes() == before


def test_unavailable_windows_account_does_not_destroy_draft(path, monkeypatch):
    restart_draft.save('synthetic recovery copy')
    before = path.read_bytes()
    def unavailable(*args, **kwargs):
        raise ValueError('Unavailable to this Windows account')
    monkeypatch.setattr(protected_storage, 'unprotect', unavailable)
    assert restart_draft.read() is None
    assert not restart_draft.acknowledge('anything')
    assert path.read_bytes() == before


def test_expired_encrypted_draft_purged(path):
    record = {'id': 'expired', 'ts': time.time() - 86401, 'text': 'synthetic'}
    path.write_bytes(protected_storage.protect(json.dumps(record).encode(), 'restart-draft'))
    assert restart_draft.read() is None
    assert not path.exists()


def test_policy_disabled_purges_encrypted_draft(path, monkeypatch):
    restart_draft.save('synthetic policy test')
    monkeypatch.setattr(config, 'enterprise', lambda: {'disable_history': True})
    assert restart_draft.read() is None
    assert not path.exists()
    with pytest.raises(PermissionError):
        restart_draft.save('must not persist')


def test_failed_atomic_write_preserves_previous_ciphertext_and_nonce(path, monkeypatch):
    restart_draft.save('original synthetic recovery')
    previous = restart_draft.read()
    before = path.read_bytes()
    def failure(*args, **kwargs):
        raise OSError('simulated full disk')
    monkeypatch.setattr(protected_storage, 'atomic_write', failure)
    with pytest.raises(OSError):
        restart_draft.save('new draft cannot persist')
    assert path.read_bytes() == before
    assert restart_draft.read() == previous


def test_failed_legacy_migration_preserves_only_recovery_copy(path, monkeypatch):
    record = {'id': 'legacy-preserved', 'ts': time.time(), 'text': 'synthetic'}
    path.write_text(json.dumps(record), encoding='utf-8')
    before = path.read_bytes()
    def failure(*args, **kwargs):
        raise OSError('migration disk full')
    monkeypatch.setattr(protected_storage, 'atomic_write', failure)
    assert restart_draft.read() is None
    assert not restart_draft.acknowledge(record['id'])
    assert path.read_bytes() == before
