"""Admin-panel access, read-only browsing and boundary regression checks."""
from contextlib import closing
from html import unescape
from pathlib import Path
import re
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
from backend.db import get_connection, init_database
from werkzeug.security import generate_password_hash


class AdminPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='admin-panel-test-', dir=PROJECT)
        cls.test_dir = Path(cls.temp.name).resolve()
        cls.seed = cls.test_dir / 'seed.sqlite3'
        cls.password_hash = generate_password_hash('test-only-password', method='scrypt')
        init_database(cls.seed)
        with closing(get_connection(cls.seed)) as conn, conn:
            conn.executemany('INSERT INTO users(id,email,password_hash,role) VALUES(?,?,?,?)',
                             [(i, f'person{i:02d}@astanait.edu.kz', cls.password_hash,
                               'admin' if i == 4 else 'student') for i in range(1, 25)])
            conn.executemany('INSERT INTO categories(id,name) VALUES(?,?)',
                             [(1, 'Electronics'), (2, 'Books')])
            conn.executemany('INSERT INTO notices(id,owner_id,category_id,title,description,location,'
                             'event_date,type,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                             [(i, 24 if i == 25 else 1 + i % 2, 1 + i % 2,
                               f'Notice {i:02d}', 'A fictional test item.', 'Library',
                               '2026-10-01', 'lost' if i % 2 else 'found',
                               'returned' if i % 5 == 0 else 'open',
                               f'2026-10-{i:02d}T09:00:00Z', f'2026-10-{i:02d}T09:00:00Z')
                              for i in range(1, 26)])

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.is_relative_to(PROJECT):
            cls.temp.cleanup()

    def setUp(self):
        self.path = self.test_dir / (self._testMethodName + '.sqlite3')
        with closing(sqlite3.connect(self.seed)) as source:
            with closing(sqlite3.connect(self.path)) as target:
                source.backup(target)
        self.app = create_app({'TESTING': True, 'DATABASE': self.path,
                               'SECRET_KEY': 'admin-panel-test-only',
                               'AUDIT_PATH': self.test_dir / 'audit.jsonl'})
        self.client = self.app.test_client()

    def user(self, user_id=4):
        with self.client.session_transaction() as state:
            state['user_id'] = user_id

    def page(self, url, **query):
        response = self.client.get(url, query_string=query)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def ids(self, html, kind='notice'):
        return [int(value) for value in re.findall(r'data-' + kind + r'-id="(\d+)"', html)]

    def test_all_routes_require_login_and_admin_role(self):
        routes = ('/admin', '/admin/notices', '/admin/users')
        for route in routes:
            with self.subTest(route=route, role='anonymous'):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers['Location'], '/login')
        self.user(1)
        for route in routes:
            with self.subTest(route=route, role='student'):
                self.assertEqual(self.client.get(route).status_code, 403)

    def test_overview_counts_latest_notices_and_quicklinks(self):
        self.user()
        html = self.page('/admin')
        visible = {key: int(count) for key, count in re.findall(
            r'<dd data-summary="([a-z]+)">(\d+)</dd>', html)}
        self.assertEqual(visible, {'notices': 25, 'open': 20, 'returned': 5, 'users': 24})
        with closing(get_connection(self.path, read_only=True)) as conn:
            self.assertEqual(visible['notices'], conn.execute('SELECT COUNT(*) FROM notices').fetchone()[0])
            self.assertEqual(visible['users'], conn.execute('SELECT COUNT(*) FROM users').fetchone()[0])
        self.assertEqual(self.ids(html), [25, 24, 23, 22, 21, 20])
        for url in ('/admin/notices', '/admin/users', '/admin/analytics',
                    '/admin/research', '/admin/smart-locker'):
            self.assertIn(f'href="{url}"', html)

    def test_notice_pagination_is_complete_and_out_of_range_is_404(self):
        self.user()
        first = self.page('/admin/notices')
        second = self.page('/admin/notices', page='2')
        self.assertEqual(self.ids(first), list(range(25, 5, -1)))
        self.assertEqual(self.ids(second), [5, 4, 3, 2, 1])
        self.assertIn('Page 1 of 2', first)
        self.assertIn('Page 2 of 2', second)
        self.assertEqual(self.client.get('/admin/notices?page=3').status_code, 404)

    def test_notice_search_combines_literal_keyword_and_status(self):
        self.user()
        html = self.page('/admin/notices', q='nOtIcE 1', status='returned')
        self.assertEqual(self.ids(html), [15, 10])
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute('UPDATE notices SET title=? WHERE id=1', ('Кітап 100%_found',))
        for keyword in ('Кітап', '%_', '100%'):
            with self.subTest(keyword=keyword):
                self.assertEqual(self.ids(self.page('/admin/notices', q=keyword)), [1])
        self.assertEqual(self.ids(self.page('/admin/notices', q="' OR 1=1 --")), [])
        filtered = unescape(self.page('/admin/notices', q='Notice', status='open'))
        self.assertIn('name="q" value="Notice"', filtered)
        self.assertIn('value="open" selected', filtered)

    def test_pagination_links_retain_the_search(self):
        self.user()
        html = unescape(self.page('/admin/notices', q='Notice', status=''))
        self.assertRegex(html, r'href="/admin/notices\?[^\"]*q=Notice[^\"]*page=2"')

    def test_invalid_filters_and_enormous_page_numbers_are_controlled(self):
        self.user()
        for route in ('/admin/notices', '/admin/users'):
            for value in ('', '0', '-1', 'abc', '1.2', '²', ' 1'):
                with self.subTest(route=route, page=value):
                    self.assertEqual(self.client.get(route, query_string={'page': value}).status_code, 400)
            for value in ('9223372036854775807', '9' * 5000):
                with self.subTest(route=route, huge_page=len(value)):
                    self.assertEqual(self.client.get(route, query_string={'page': value}).status_code, 404)
            self.assertEqual(self.client.get(route, query_string={'q': 'a' * 121}).status_code, 400)
            self.assertEqual(self.client.get(route, query_string={'q': 'a' * 120}).status_code, 200)
        self.assertEqual(self.client.get('/admin/notices?status=deleted').status_code, 400)

    def test_users_are_paginated_searchable_and_include_zero_notice_counts(self):
        self.user()
        first = self.page('/admin/users')
        second = self.page('/admin/users', page=2)
        self.assertEqual(self.ids(first, 'user'), list(range(1, 21)))
        self.assertEqual(self.ids(second, 'user'), [21, 22, 23, 24])
        self.assertIn('Read-only', first)
        self.assertEqual(self.client.get('/admin/users?page=3').status_code, 404)
        found = self.page('/admin/users', q='PERSON24')
        self.assertEqual(self.ids(found, 'user'), [24])
        self.assertRegex(found, r'data-user-id="24"[\s\S]*?data-notice-count>1</td>')
        zero = self.page('/admin/users', q='person04')
        self.assertRegex(zero, r'data-user-id="4"[\s\S]*?data-notice-count>0</td>')
        self.assertEqual(self.ids(self.page('/admin/users', q='%'), 'user'), [])
        self.assertEqual(self.ids(self.page('/admin/users', q='Қазақша'), 'user'), [])

    def test_pages_never_render_password_hashes(self):
        self.user()
        for route in ('/admin', '/admin/notices', '/admin/users'):
            html = self.page(route)
            self.assertNotIn(self.password_hash, html)
            self.assertNotIn('scrypt:', html)
            self.assertNotIn('password_hash', html)

    def test_untrusted_titles_categories_and_search_are_escaped(self):
        self.user()
        value = '<script>alert(7)</script>'
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute('UPDATE notices SET title=? WHERE id=25', (value,))
            conn.execute('UPDATE categories SET name=? WHERE id=2', (value,))
        for route in ('/admin', '/admin/notices'):
            html = self.page(route)
            self.assertIn('&lt;script&gt;alert(7)&lt;/script&gt;', html)
            self.assertNotIn(value, html)
        for route in ('/admin/notices', '/admin/users'):
            html = self.page(route, q='"><script>alert(1)</script>')
            self.assertNotIn('<script>alert(1)</script>', html)
            self.assertNotIn('style=', html)

    def test_gets_preserve_database_and_remove_uses_existing_confirmation(self):
        self.user()
        before = self.path.read_bytes()
        for route in ('/admin', '/admin/notices', '/admin/users'):
            self.page(route)
        html = self.page('/admin/notices')
        self.assertIn('href="/notice/25"', html)
        self.assertIn('href="/notice/25/remove"', html)
        confirm = self.page('/notice/25/remove')
        self.assertIn('Confirm removal', confirm)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.client.post('/notice/25/remove').status_code, 400)
        self.assertEqual(self.path.read_bytes(), before)
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        for route in ('/admin', '/admin/notices', '/admin/users'):
            self.assertEqual(self.client.post(route, data={'csrf': csrf}).status_code, 405)
        self.assertEqual(self.path.read_bytes(), before)

    def test_no_notices_and_no_matching_users_have_usable_empty_states(self):
        self.user()
        with closing(get_connection(self.path)) as conn, conn:
            conn.execute('DELETE FROM notices')
        self.assertIn('<dd data-summary="notices">0</dd>', self.page('/admin'))
        self.assertIn('No notices yet', self.page('/admin'))
        self.assertIn('No notices found', self.page('/admin/notices'))
        self.assertIn('No users found', self.page('/admin/users', q='missing'))
        self.assertEqual(self.client.get('/admin/notices?page=2').status_code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
