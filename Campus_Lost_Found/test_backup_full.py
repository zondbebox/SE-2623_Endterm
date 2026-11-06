"""Full archive recovery checks; all writes use isolated temporary projects."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from backend.db import seed_database
import backup_full


class FullBackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='full-backup-tests-', dir=ROOT)
        cls.seed = Path(cls.fixture.name) / 'seed.sqlite3'
        seed_database(cls.seed)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.fixture.name)
        self.root = Path(self.temp.name) / 'project'
        (self.root / 'data').mkdir(parents=True)
        self.main = self.root / 'data' / 'campus.sqlite3'
        shutil.copy2(self.seed, self.main)

    def tearDown(self):
        self.temp.cleanup()

    def api(self):
        return backup_full

    def archive(self):
        return Path(self.api().create_full_backup(self.root)['backup_path'])

    def add_photo_and_sidecars(self):
        filename = 'a' * 48 + '.png'
        photos = self.root / 'data' / 'uploads'
        photos.mkdir()
        (photos / filename).write_bytes(b'private-photo-example')
        with closing(sqlite3.connect(self.main)) as conn:
            with conn:
                conn.execute('UPDATE notices SET photo_filename=? WHERE id=1', (filename,))
        for name, table in [('research', 'research_sessions'), ('telemetry', 'locker_events')]:
            with closing(sqlite3.connect(self.root / 'data' / (name + '.sqlite3'))) as conn:
                with conn:
                    conn.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY, value TEXT)')
                    conn.execute(f'INSERT INTO {table}(value) VALUES (?)', ('test observation',))
        (self.root / 'runtime').mkdir()
        (self.root / 'runtime' / 'session.key').write_text('must-not-be-exported')
        return filename

    def test_archive_includes_online_databases_photos_hashes_and_excludes_session_key(self):
        filename = self.add_photo_and_sidecars()
        before = {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.root.rglob('*') if p.is_file()}
        archive = self.archive()
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read('manifest.json'))
            self.assertEqual(set(manifest['files']), {'data/campus.sqlite3', 'data/research.sqlite3',
                'data/telemetry.sqlite3', 'data/uploads/' + filename})
            self.assertNotIn('runtime/session.key', bundle.namelist())
            for name, entry in manifest['files'].items():
                self.assertEqual(hashlib.sha256(bundle.read(name)).hexdigest(), entry['sha256'])
        self.assertEqual(before, {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in before})
        checked = self.api().restore_full_check(archive, Path(self.temp.name) / 'restored')
        self.assertTrue(checked['success'])
        self.assertEqual(checked['databases']['data/campus.sqlite3']['counts']['notices'], 120)
        self.assertEqual(checked['databases']['data/research.sqlite3']['counts']['research_sessions'], 1)
        self.assertEqual((Path(checked['restored_path']) / 'data' / 'uploads' / filename).read_bytes(), b'private-photo-example')

    def test_recovery_keeps_changed_live_database_and_rejects_existing_destination(self):
        archive = self.archive()
        with closing(sqlite3.connect(self.main)) as conn:
            with conn:
                conn.execute('DELETE FROM notices WHERE id=1')
        checked = self.api().restore_full_check(archive, Path(self.temp.name) / 'fresh')
        self.assertEqual(checked['databases']['data/campus.sqlite3']['counts']['notices'], 120)
        with closing(sqlite3.connect(self.main)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM notices').fetchone()[0], 119)
        with self.assertRaises(self.api().BackupError):
            self.api().restore_full_check(archive, self.root)
        self.assertTrue(self.main.exists())

    def test_traversal_zip_is_rejected_without_writing_destination(self):
        archive = self.archive()
        with zipfile.ZipFile(archive, 'a') as bundle:
            bundle.writestr('../escaped.txt', 'must not escape')
        target = Path(self.temp.name) / 'checked'
        with self.assertRaises(self.api().BackupError):
            self.api().restore_full_check(archive, target)
        self.assertFalse(target.exists())
        self.assertFalse((Path(self.temp.name) / 'escaped.txt').exists())

    def test_corrupt_payload_hash_is_rejected_without_creating_restored_folder(self):
        filename = self.add_photo_and_sidecars()
        original = self.archive()
        tampered = Path(self.temp.name) / 'corrupt.zip'
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, 'w') as target:
            for name in source.namelist():
                target.writestr(name, b'changed-photo' if name == 'data/uploads/' + filename else source.read(name))
        destination = Path(self.temp.name) / 'checked'
        with self.assertRaises(self.api().BackupError):
            self.api().restore_full_check(tampered, destination)
        self.assertFalse(destination.exists())

    def test_backup_rejects_oversized_manifest_before_publishing_archive(self):
        before = hashlib.sha256(self.main.read_bytes()).hexdigest()
        with patch.object(self.api(), 'MAX_MANIFEST_BYTES', 128, create=True):
            with self.assertRaises(self.api().BackupError):
                self.archive()
        self.assertEqual(list((self.root / 'backups').iterdir()), [])
        self.assertEqual(hashlib.sha256(self.main.read_bytes()).hexdigest(), before)

    def test_restore_rejects_manifest_above_shared_limit_without_destination(self):
        archive = self.archive()
        destination = Path(self.temp.name) / 'checked'
        with patch.object(self.api(), 'MAX_MANIFEST_BYTES', 128, create=True):
            with self.assertRaises(self.api().BackupError):
                self.api().restore_full_check(archive, destination)
        self.assertFalse(destination.exists())

    def test_manifest_at_shared_limit_can_be_written_and_restored(self):
        # Hold the timestamp stable so both real manifests have identical sizes.
        with patch.object(self.api(), 'datetime') as clock:
            clock.now.return_value = datetime(2026, 11, 1, tzinfo=timezone.utc)
            with zipfile.ZipFile(self.archive()) as bundle:
                manifest_size = bundle.getinfo('manifest.json').file_size
            with patch.object(self.api(), 'MAX_MANIFEST_BYTES', manifest_size, create=True):
                archive = self.archive()
                checked = self.api().restore_full_check(archive, Path(self.temp.name) / 'checked')
        self.assertTrue(checked['success'])
        self.assertEqual(checked['databases']['data/campus.sqlite3']['counts']['notices'], 120)


if __name__ == '__main__':
    unittest.main(verbosity=2)
