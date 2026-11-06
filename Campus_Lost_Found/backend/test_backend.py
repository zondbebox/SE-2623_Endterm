"""Meaningful storage checks; all mutations use temporary databases."""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from werkzeug.security import check_password_hash

try:
    from . import db
except ImportError:
    import db


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_temp = tempfile.TemporaryDirectory(prefix='campus-db-fixture-')
        cls.base_path = Path(cls.base_temp.name) / 'fixture.sqlite3'
        db.seed_database(cls.base_path)

    @classmethod
    def tearDownClass(cls):
        cls.base_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='campus-db-case-')
        self.directory = Path(self.temp.name)
        self.path = self.directory / 'campus.sqlite3'
        shutil.copy2(self.base_path, self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_seed_counts_distribution_and_relationships(self):
        summary = db.summary_database(self.path)
        self.assertEqual(summary['counts'], {'users': 20, 'categories': 10, 'notices': 120})
        self.assertEqual(summary['roles'], {'admin': 1, 'student': 19})
        self.assertEqual(summary['notice_types'], {'found': 60, 'lost': 60})
        self.assertEqual(summary['notice_statuses'], {'open': 96, 'returned': 24})
        self.assertTrue(all(row['notice_count'] == 12 for row in summary['notices_by_category']))
        self.assertEqual(summary['integrity_check'], 'ok')
        self.assertEqual(summary['foreign_key_violations'], [])
        self.assertTrue(summary['foreign_keys_enabled'])

    def test_passwords_use_independent_scrypt_hashes(self):
        with closing(db.get_connection(self.path)) as connection:
            rows = connection.execute('SELECT email,password_hash FROM users ORDER BY id').fetchall()
        hashes = [row['password_hash'] for row in rows]
        self.assertEqual(len(set(hashes)), 20)
        self.assertTrue(all(value.startswith('scrypt:') for value in hashes))
        self.assertTrue(check_password_hash(hashes[0], db.DEMO_PASSWORD))
        self.assertFalse(check_password_hash(hashes[0], 'incorrect-demo-password'))
        self.assertNotIn(db.DEMO_PASSWORD.encode(), self.path.read_bytes())
        self.assertEqual(rows[0]['email'], 'zhanzhol.demo@astanait.edu.kz')

    def test_connection_configuration_and_row_factory(self):
        with closing(db.get_connection(self.path)) as connection:
            self.assertIs(connection.row_factory, sqlite3.Row)
            self.assertEqual(connection.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(connection.execute('PRAGMA busy_timeout').fetchone()[0], 5000)

    def test_init_is_non_destructive_and_seed_refuses_existing_data(self):
        initialized = db.init_database(self.path)
        self.assertFalse(initialized['created'])
        with self.assertRaises(db.DatabaseStateError):
            db.seed_database(self.path)
        self.assertEqual(db.summary_database(self.path)['counts'], db.EXPECTED_COUNTS)

    def test_unexpected_database_is_not_overwritten(self):
        other = self.directory / 'unrelated.sqlite3'
        with closing(sqlite3.connect(other)) as connection:
            with connection:
                connection.execute('CREATE TABLE personal_notes (message TEXT)')
                connection.execute("INSERT INTO personal_notes VALUES ('keep this')")
        with self.assertRaises(db.DatabaseStateError):
            db.init_database(other)
        with closing(sqlite3.connect(other)) as connection:
            self.assertEqual(connection.execute('SELECT message FROM personal_notes').fetchone()[0], 'keep this')

    def test_user_constraints_reject_duplicate_external_or_invalid_role(self):
        with closing(db.get_connection(self.path)) as connection:
            password_hash = connection.execute('SELECT password_hash FROM users WHERE id=1').fetchone()[0]
            invalid = [
                ('zhanzhol.demo@astanait.edu.kz', password_hash, 'student'),
                ('outsider@example.com', password_hash, 'student'),
                ('a@b@astanait.edu.kz', password_hash, 'student'),
                ('UPPER@astanait.edu.kz', password_hash, 'student'),
                ('new.demo@astanait.edu.kz', password_hash, 'superuser'),
                ('new.demo@astanait.edu.kz', db.DEMO_PASSWORD, 'student'),
            ]
            for row in invalid:
                with self.subTest(email=row[0], role=row[2]):
                    with self.assertRaises(sqlite3.IntegrityError):
                        with connection:
                            connection.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)', row)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0], 20)

    def test_category_name_is_unique_case_insensitively(self):
        with closing(db.get_connection(self.path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute("INSERT INTO categories(name) VALUES ('electronics')")

    def test_notices_reject_bad_foreign_keys_and_invalid_values(self):
        with closing(db.get_connection(self.path)) as connection:
            invalid = [
                ('owner_id', 99999), ('category_id', 99999),
                ('type', 'sale'), ('status', 'deleted'), ('title', '  '),
                ('title', 'x' * 121), ('description', 'short'), ('location', 'x'),
                ('event_date', '2026-02-30'), ('event_date', '2026-13-01'),
                ('event_date', '2026-1-2'), ('event_date', '2099-01-01'),
                ('created_at', '2026-02-30T09:00:00Z'),
                ('updated_at', '2000-01-01T00:00:00Z'),
                ('photo_filename', '../private.txt'), ('photo_filename', 'folder/photo.png'),
                ('photo_filename', 'folder\\photo.png'),
            ]
            for column, value in invalid:
                with self.subTest(column=column, value=value):
                    with self.assertRaises(sqlite3.IntegrityError):
                        with connection:
                            connection.execute(f'UPDATE notices SET {column}=? WHERE id=1', (value,))

    def test_referenced_users_and_categories_cannot_be_deleted(self):
        with closing(db.get_connection(self.path)) as connection:
            for table in ('users', 'categories'):
                with self.subTest(table=table):
                    with self.assertRaises(sqlite3.IntegrityError):
                        with connection:
                            connection.execute(f'DELETE FROM {table} WHERE id=1')

    def test_transaction_rolls_back_earlier_write_on_constraint_error(self):
        with closing(db.get_connection(self.path)) as connection:
            original = connection.execute('SELECT title FROM notices WHERE id=1').fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                with connection:
                    connection.execute("UPDATE notices SET title='Temporary valid title' WHERE id=1")
                    connection.execute("UPDATE notices SET status='invalid' WHERE id=2")
            self.assertEqual(connection.execute('SELECT title FROM notices WHERE id=1').fetchone()[0], original)

    def test_query_allows_join_and_denies_mutation_or_attach(self):
        result = db.query_database(self.path,
            'SELECT n.id,c.name AS category FROM notices n '
            'JOIN categories c ON c.id=n.category_id ORDER BY n.id LIMIT 3')
        self.assertEqual(result['columns'], ['id', 'category'])
        self.assertEqual(len(result['rows']), 3)
        for sql in ('DELETE FROM notices', 'DROP TABLE notices',
                    "ATTACH DATABASE ':memory:' AS extra", 'PRAGMA user_version=2'):
            with self.subTest(sql=sql):
                with self.assertRaises(sqlite3.DatabaseError):
                    db.query_database(self.path, sql)
        self.assertEqual(db.summary_database(self.path)['counts']['notices'], 120)

    def test_backup_and_scratch_restore_preserve_the_live_database(self):
        backup = db.backup_database(self.path, self.directory / 'backups')
        self.assertEqual(backup['counts'], db.EXPECTED_COUNTS)
        self.assertEqual(backup['integrity_check'], 'ok')
        saved_metadata = json.loads(Path(backup['metadata_path']).read_text())
        self.assertEqual(saved_metadata['counts'], db.EXPECTED_COUNTS)
        self.assertNotIn(db.DEMO_PASSWORD, Path(backup['metadata_path']).read_text())
        with closing(db.get_connection(self.path)) as connection:
            with connection:
                connection.execute('DELETE FROM notices WHERE id=1')
        restored_path = self.directory / 'restored.sqlite3'
        restored = db.restore_check(backup['backup_path'], restored_path)
        self.assertTrue(restored['success'])
        self.assertEqual(restored['counts']['notices'], 120)
        self.assertEqual(db.summary_database(self.path)['counts']['notices'], 119)
        self.assertEqual(restored['foreign_key_violations'], [])

    def test_restore_refuses_existing_target_and_live_database(self):
        backup = db.backup_database(self.path, self.directory / 'backups')
        with self.assertRaises(db.DatabaseStateError):
            db.restore_check(backup['backup_path'], self.path)
        with self.assertRaises(db.DatabaseStateError):
            db.restore_check(backup['backup_path'], db.DEFAULT_DB_PATH)
        self.assertEqual(db.summary_database(self.path)['counts'], db.EXPECTED_COUNTS)

    def test_cli_summary_works_from_another_working_directory(self):
        result = subprocess.run(
            [sys.executable, str(Path(db.__file__).with_name('manage.py')),
             '--db', str(self.path), 'summary'],
            cwd=self.directory, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['counts'], db.EXPECTED_COUNTS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
