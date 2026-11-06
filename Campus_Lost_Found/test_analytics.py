"""Behavioral checks for aggregate accuracy, disclosure and administrator access."""
from contextlib import closing
import csv
import importlib.util
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
if sys.platform == 'win32':
    sys.path.insert(0, str(PROJECT / 'vendor'))

from app import create_app
from backend.db import get_connection, init_database, seed_database


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='analytics-test-', dir=PROJECT)
        cls.test_dir = Path(cls.temp.name).resolve()
        cls.seed_path = cls.test_dir / 'seed.sqlite3'
        init_database(cls.seed_path)
        seed_database(cls.seed_path)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.is_relative_to(PROJECT):
            cls.temp.cleanup()

    def setUp(self):
        self.path = self.test_dir / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.seed_path)) as source:
            with closing(sqlite3.connect(self.path)) as target:
                source.backup(target)
        self.app = create_app({'TESTING': True, 'DATABASE': self.path,
                               'SECRET_KEY': 'analytics-test-only',
                               'AUDIT_PATH': self.test_dir / 'audit.jsonl'})
        # Exercise this module before the concurrently edited app factory registers it.
        if importlib.util.find_spec('analytics_routes') is not None:
            if 'analytics' not in self.app.view_functions:
                from analytics_routes import register_analytics
                register_analytics(self.app)
        self.client = self.app.test_client()

    def data(self):
        self.assertIsNotNone(importlib.util.find_spec('backend.analytics'),
                             'The aggregate implementation is missing.')
        from backend.analytics import build_analytics
        with closing(get_connection(self.path, read_only=True)) as conn:
            return build_analytics(conn)

    def user(self, user_id):
        with self.client.session_transaction() as state:
            state['user_id'] = user_id

    def test_aggregates_match_independent_queries_without_modifying_database(self):
        original = self.path.read_bytes()
        result = self.data()
        self.assertEqual(result['source_label'], 'synthetic')
        self.assertEqual(result['counts'], {'notices': 120, 'open': 96, 'returned': 24,
                                          'lost': 60, 'found': 60, 'categories': 10})
        with closing(get_connection(self.path, read_only=True)) as conn:
            for row in result['category_series']:
                total = conn.execute('SELECT count(*) FROM notices WHERE category_id=?',
                                     (row['category_id'],)).fetchone()[0]
                opened = conn.execute("SELECT count(*) FROM notices WHERE category_id=? AND status='open'",
                                      (row['category_id'],)).fetchone()[0]
                self.assertEqual((row['total'], row['open'], row['returned']),
                                 (total, opened, total - opened))
            for row in result['location_series']:
                actual = dict(conn.execute('SELECT type,count(*) FROM notices WHERE location=? GROUP BY type',
                                           (row['location'],)).fetchall())
                self.assertEqual((row['lost'], row['found']),
                                 (actual.get('lost', 0), actual.get('found', 0)))
            for row in result['weekly_series']:
                actual = dict(conn.execute('SELECT type,count(*) FROM notices WHERE event_date BETWEEN ? AND ? GROUP BY type',
                                           (row['week_start'], row['week_end'])).fetchall())
                self.assertEqual((row['lost'], row['found']),
                                 (actual.get('lost', 0), actual.get('found', 0)))
        self.assertEqual(self.path.read_bytes(), original)

    def test_zero_categories_and_empty_dataset_are_retained(self):
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute("INSERT INTO categories(id,name) VALUES (11,'Empty category')")
        result = self.data()
        empty = next(row for row in result['category_series'] if row['category_id'] == 11)
        self.assertEqual((empty['total'], empty['open'], empty['returned']), (0, 0, 0))
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute('DELETE FROM notices')
        result = self.data()
        self.assertEqual(result['counts']['notices'], 0)
        self.assertEqual(len(result['category_series']), 11)
        self.assertEqual(result['location_series'], [])
        self.assertEqual(result['weekly_series'], [])

    def test_full_monday_sunday_weeks_include_gaps_and_sort_by_date(self):
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute('DELETE FROM notices WHERE id>2')
            conn.execute("UPDATE notices SET event_date='2026-01-04',type='lost' WHERE id=1")
            conn.execute("UPDATE notices SET event_date='2026-01-12',type='found' WHERE id=2")
        rows = self.data()['weekly_series']
        self.assertEqual([(r['week_start'], r['week_end'], r['lost'], r['found']) for r in rows],
                         [('2025-12-29', '2026-01-04', 1, 0),
                          ('2026-01-05', '2026-01-11', 0, 0),
                          ('2026-01-12', '2026-01-18', 0, 1)])

    def test_location_counts_sort_largest_first_with_stable_name_tiebreak(self):
        rows = self.data()['location_series']
        self.assertEqual([r['total'] for r in rows], sorted((r['total'] for r in rows), reverse=True))
        self.assertEqual(sum(r['total'] for r in rows), 120)

    def test_anonymous_and_student_cannot_access_dashboard_or_export(self):
        for url in ['/admin/analytics', '/admin/analytics.csv']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers['Location'], '/login')
        self.user(1)
        for url in ['/admin/analytics', '/admin/analytics.csv']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_dashboard_discloses_simulation_and_escapes_untrusted_labels(self):
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute("UPDATE categories SET name=? WHERE id=1", ('<script>alert(7)</script>',))
        self.user(4)
        response = self.client.get('/admin/analytics')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Synthetic teaching data', html)
        self.assertIn('&lt;script&gt;alert(7)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(7)</script>', html)
        self.assertGreaterEqual(html.count('<caption>'), 3)
        self.assertNotIn('style=', html)
        self.assertIn("style-src 'self'", response.headers['Content-Security-Policy'])

    def test_csv_neutralizes_formulas_and_omits_personal_fields(self):
        dangerous = ['=1+1', '+SUM(1,2)', '-1+2', '@SUM(1,2)', '\t=1+1', '\r=1+1', '\n=1+1']
        with closing(get_connection(self.path)) as conn, conn:
            for i, name in enumerate(dangerous, 1):
                conn.execute('UPDATE categories SET name=? WHERE id=?', (name, i))
                conn.execute('UPDATE notices SET location=? WHERE id=?', (name, i))
            conn.execute("UPDATE notices SET title='Private item title',description='Private description sentinel' WHERE id=1")
        self.user(4)
        response = self.client.get('/admin/analytics.csv')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.mimetype.startswith('text/csv'))
        body = response.get_data(as_text=True)
        rows = list(csv.DictReader(io.StringIO(body)))
        labels = {r['group'] for r in rows}
        for value in dangerous:
            self.assertIn("'" + value, labels)
            self.assertNotIn(value, labels)
        for forbidden in ['@astanait.edu.kz', 'scrypt:', 'Private item title',
                          'Private description sentinel', 'owner_id', 'password_hash', 'photo_filename']:
            self.assertNotIn(forbidden, body)
        self.assertTrue(all(r['source'] == 'synthetic' for r in rows))


if __name__ == '__main__':
    unittest.main(verbosity=2)
