import io
import json
from pathlib import Path
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from deepstudy.app import create_app
from deepstudy.backup import export_profile, restore_profile, digest
from deepstudy.database import SCHEMA_VERSION, connect, migrate, read_settings, save_settings, MIGRATIONS, DEFAULT_SETTINGS

ORIGIN = 'http://127.0.0.1:43123'
TOKEN = 'test-only-bootstrap-never-a-production-secret'


def client_for(profile):
    client = TestClient(create_app(profile, ORIGIN, TOKEN), base_url=ORIGIN)
    result = client.post('/api/session', headers={'Origin': ORIGIN, 'Authorization': f'Bearer {TOKEN}'})
    assert result.status_code == 200
    assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=strict' in result.headers['set-cookie']
    client.headers['Origin'] = ORIGIN
    return client


def seed(profile):
    migrate(profile / 'deepstudy.db')
    with connect(profile / 'deepstudy.db') as db:
        db.execute("INSERT INTO sources VALUES('s','local','fixture',1,'read')")
        db.execute("INSERT INTO materials VALUES('m','s','chapter')")
        db.execute("INSERT INTO material_versions VALUES('v','m','1',?,'text','ready')", ('a'*64,))
        db.execute("INSERT INTO chunks VALUES('c','v','paragraph:1','Example','reviewed','1')")
        db.execute("INSERT INTO objectives VALUES('o','1','Foundations')")
        db.execute("INSERT INTO question_versions VALUES('q','o','Question','[]','answer','rationale','[]','reviewed')")
        db.execute("INSERT INTO attempts VALUES('a','device','q','answer',1,'2026-11-26T12:00:00Z')")
        db.execute("INSERT INTO note_versions VALUES('n','note',NULL,'personal note','device')")
    (profile / 'derived').mkdir()
    (profile / 'derived' / 'fixture.txt').write_text('Local derived text', encoding='utf-8')


def test_auth_origin_host_and_bootstrap_replay(tmp_path):
    app = create_app(tmp_path, ORIGIN, TOKEN)
    client = TestClient(app, base_url=ORIGIN)
    assert client.get('/api/settings').status_code == 401
    assert client.post('/api/session', headers={'Origin': ORIGIN, 'Authorization': 'Bearer wrong'}).status_code == 401
    good = {'Origin': ORIGIN, 'Authorization': f'Bearer {TOKEN}'}
    assert client.post('/api/session', headers=good).status_code == 200
    assert client.post('/api/session', headers=good).status_code == 401
    for headers in ({'Host': 'evil.test'}, {'Origin': 'https://evil.test'}, {'Origin': 'null'}, {'Sec-Fetch-Site': 'cross-site'}):
        assert client.get('/api/settings', headers=headers).status_code == 403
    assert client.put('/api/settings', json=DEFAULT_SETTINGS).status_code == 403
    assert client.get('/api/settings').status_code == 200
    assert TOKEN not in client.get('/api/status').text


def test_settings_validation_persistence_and_conflict(tmp_path):
    client = client_for(tmp_path)
    settings = client.get('/api/settings').json()
    for patch in ({'theme':'invalid'}, {'timezone':'bad/zone'}, {'ai_mode':'cloud'}, {'api_key':'private'}, {'revision':-1}, {'display_name':'a'*81}):
        assert client.put('/api/settings', json={**settings, **patch}).status_code == 422
    updated = {**settings, 'display_name':'Ada', 'theme':'dark'}
    assert client.put('/api/settings', json=updated).json()['revision'] == 1
    assert client.put('/api/settings', json=updated).status_code == 409
    restarted = client_for(tmp_path)
    assert restarted.get('/api/settings').json()['display_name'] == 'Ada'
    # A session cookie from an earlier server is no longer authoritative.
    assert client.cookies != restarted.cookies


def test_migrations_keep_data_backup_and_rollback(tmp_path, monkeypatch):
    path = tmp_path / 'deepstudy.db'
    migrate(path, target=1)
    with connect(path) as db:
        db.execute('UPDATE settings SET value=?', (json.dumps({**DEFAULT_SETTINGS,'display_name':'Before'}),))
    migrate(path)
    assert read_settings(path)['display_name'] == 'Before'
    backup = next((tmp_path / 'backups').glob('*.db'))
    with connect(backup) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 1
        assert 'Before' in db.execute('SELECT value FROM settings').fetchone()[0]
    monkeypatch.setitem(MIGRATIONS, SCHEMA_VERSION + 1, ['ALTER TABLE settings ADD COLUMN temporary TEXT', 'INVALID SQL'])
    with pytest.raises(sqlite3.Error):
        migrate(path, target=SCHEMA_VERSION + 1)
    with connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION
        assert 'temporary' not in [row[1] for row in db.execute('PRAGMA table_info(settings)')]
    assert read_settings(path)['display_name'] == 'Before'
    # Recovery of the pre-migration snapshot into a clean location, followed by upgrade.
    recovered = tmp_path / 'recovered' / 'deepstudy.db'
    recovered.parent.mkdir()
    recovered.write_bytes(backup.read_bytes())
    migrate(recovered)
    assert read_settings(recovered)['display_name'] == 'Before'


def test_foreign_keys_immutability_and_prerequisite_cycles(tmp_path):
    seed(tmp_path)
    with connect(tmp_path / 'deepstudy.db') as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO attempts VALUES('orphan','device','missing','answer',1,'now')")
        for table in ('attempts','material_versions','question_versions','note_versions'):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f'DELETE FROM {table}')
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f'UPDATE {table} SET id=id')
        db.execute("INSERT INTO objectives VALUES('b','1','B'),('c','1','C')")
        db.execute("INSERT INTO prerequisites VALUES('o','b'),('b','c')")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO prerequisites VALUES('c','o')")


def test_export_restore_preserves_records_files_and_rejects_overwrite(tmp_path):
    source, destination = tmp_path/'source', tmp_path/'destination'
    seed(source)
    save_settings(source/'deepstudy.db',{**DEFAULT_SETTINGS,'display_name':'Ada'},0)
    payload = export_profile(source)
    migrate(destination/'deepstudy.db')
    restore_profile(destination, payload)
    with connect(source/'deepstudy.db') as a, connect(destination/'deepstudy.db') as b:
        assert list(a.iterdump()) == list(b.iterdump())
    assert (destination/'derived/fixture.txt').read_text() == 'Local derived text'
    with pytest.raises(ValueError, match='profilo vuoto'):
        restore_profile(destination, payload)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {'deepstudy.db','derived/fixture.txt','manifest.json'}


def change_archive(payload, mutate):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    mutate(files)
    result = io.BytesIO()
    with zipfile.ZipFile(result,'w') as archive:
        for name, content in files.items(): archive.writestr(name, content)
    return result.getvalue()


def test_bad_archive_and_traversal_never_change_live_db(tmp_path):
    source, destination = tmp_path/'source', tmp_path/'destination'
    seed(source); migrate(destination/'deepstudy.db')
    payload = export_profile(source)
    before = (destination/'deepstudy.db').read_bytes()
    corrupted = change_archive(payload, lambda files:files.__setitem__('derived/fixture.txt',b'corrupt'))
    def traversal(files):
        manifest=json.loads(files['manifest.json'])
        manifest['files']['derived/../../outside.txt']={'bytes':4,'sha256':digest(b'evil')}
        files['derived/../../outside.txt']=b'evil'
        files['manifest.json']=json.dumps(manifest).encode()
    for invalid in (b'not a zip',corrupted,change_archive(payload,traversal)):
        with pytest.raises(ValueError): restore_profile(destination,invalid)
        assert (destination/'deepstudy.db').read_bytes() == before
        assert not (tmp_path/'outside.txt').exists()


def test_api_restore_and_export(tmp_path):
    source = client_for(tmp_path/'source')
    original = source.get('/api/settings').json()
    source.put('/api/settings',json={**original,'display_name':'Restored'})
    result = source.post('/api/exports')
    assert result.status_code == 200 and result.headers['content-type']=='application/zip'
    target = client_for(tmp_path/'target')
    assert target.post('/api/restore',content=b'broken').status_code == 400
    assert target.post('/api/restore',content=result.content).status_code == 200
    assert target.get('/api/settings').json()['display_name']=='Restored'
    assert target.post('/api/restore',content=result.content).status_code==400


def test_concurrent_settings_do_not_silently_overwrite(tmp_path):
    migrate(tmp_path/'deepstudy.db')
    def update(name):
        try:
            save_settings(tmp_path/'deepstudy.db',{**DEFAULT_SETTINGS,'display_name':name},0)
            return 'saved'
        except ValueError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update,['A','B'])) == ['conflict','saved']
