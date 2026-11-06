"""Stage 2 registration and private-image behavior against real SQLite and Pillow."""
from contextlib import closing
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app import create_app
from backend.db import seed_database, DEMO_PASSWORD
from PIL import Image
from werkzeug.security import check_password_hash


class Stage2CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='stage2-core-', dir=ROOT)
        cls.seed = Path(cls.fixture.name) / 'seed.sqlite3'
        seed_database(cls.seed)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=self.fixture.name)
        self.directory = Path(self.temp.name)
        self.database = self.directory / 'campus.sqlite3'
        shutil.copy2(self.seed, self.database)
        self.uploads = self.directory / 'private-photos'
        self.audit = self.directory / 'audit.jsonl'
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'stage2-test',
            'DATABASE': self.database, 'AUDIT_PATH': self.audit,
            'UPLOAD_FOLDER': self.uploads})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def rows(self, sql, params=()):
        with closing(sqlite3.connect(self.database)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute(sql, params)]

    def token(self, client=None):
        client = client or self.client
        client.get('/login')
        with client.session_transaction() as session:
            return session['csrf']

    def post(self, path, data=None, client=None):
        client = client or self.client
        response = client.post(path, data={**(data or {}), 'csrf': self.token(client)})
        response.request.input_stream.close()
        return response

    def login(self, email='zhanzhol.demo@astanait.edu.kz', password=DEMO_PASSWORD, client=None):
        response = self.post('/login', {'email': email, 'password': password}, client)
        self.assertEqual(response.status_code, 302)

    def notice(self, **values):
        return dict(title='Photo test notebook', description='Fictional notebook with a useful identifying mark.',
            location='Library', event_date=datetime.now(timezone.utc).date().isoformat(),
            type='found', category_id='4', **values)

    def photo(self, format='JPEG', size=(24, 18), exif=False):
        stream = BytesIO()
        picture = Image.new('RGB', size, '#187782')
        metadata = Image.Exif()
        if exif:
            metadata[270] = 'Private test metadata that must disappear'
        picture.save(stream, format=format, exif=metadata)
        stream.seek(0)
        return (stream, 'camera.jpg' if format == 'JPEG' else 'camera.png',
                'image/jpeg' if format == 'JPEG' else 'image/png')

    def create_photo(self, **values):
        response = self.post('/post', self.notice(photo=self.photo(exif=True), **values))
        self.assertEqual(response.status_code, 302)
        notice_id = int(response.headers['Location'].split('/')[-1])
        row = self.rows('SELECT * FROM notices WHERE id=?', (notice_id,))[0]
        self.assertIsNotNone(row['photo_filename'], 'Uploaded photograph must be persisted.')
        return row

    def test_registration_creates_student_scrypt_account_that_can_sign_in(self):
        response = self.post('/register', {'email': ' New.Student@astanait.edu.kz ',
            'password': 'A-local-password-2026', 'role': 'admin'})
        self.assertEqual(response.status_code, 302)
        row = self.rows('SELECT * FROM users WHERE email=?', ('new.student@astanait.edu.kz',))[0]
        self.assertEqual(row['role'], 'student')
        self.assertTrue(row['password_hash'].startswith('scrypt:'))
        self.assertTrue(check_password_hash(row['password_hash'], 'A-local-password-2026'))
        self.login('new.student@astanait.edu.kz', 'A-local-password-2026')
        self.assertNotIn('A-local-password-2026', self.audit.read_text())

    def test_registration_rejects_invalid_domain_syntax_and_password_lengths(self):
        cases = [('outside@example.com', 'a' * 12), ('a@b@astanait.edu.kz', 'a' * 12),
            ('a+tag@astanait.edu.kz', 'a' * 12), ('a@astanait.edu.kz.evil', 'a' * 12),
            ('new.demo@astanait.edu.kz', 'a' * 11), ('new.demo@astanait.edu.kz', 'a' * 129)]
        for email, password in cases:
            with self.subTest(email=email, length=len(password)):
                client = self.app.test_client()
                response = client.post('/register', data={'csrf': self.token(client),
                    'email': email, 'password': password}, environ_base={'REMOTE_ADDR': str(len(password)) + email})
                self.assertEqual(response.status_code, 200)
                self.assertIn('form-error', response.text)
        self.assertEqual(len(self.rows('SELECT id FROM users')), 20)

    def test_registration_duplicate_is_handled_and_missing_csrf_cannot_create(self):
        duplicate = self.post('/register', {'email': 'zhanzhol.demo@astanait.edu.kz', 'password': 'x' * 12})
        self.assertEqual(duplicate.status_code, 200)
        self.assertIn('form-error', duplicate.text)
        self.assertEqual(self.client.post('/register', data={'email': 'new@astanait.edu.kz', 'password': 'x' * 12}).status_code, 400)
        self.assertEqual(len(self.rows('SELECT id FROM users')), 20)

    def test_registration_rate_limit_stops_repeated_submissions(self):
        for _ in range(5):
            self.assertEqual(self.post('/register', {'email': 'bad@example.com', 'password': 'x' * 12}).status_code, 200)
        self.assertEqual(self.post('/register', {'email': 'good@astanait.edu.kz', 'password': 'x' * 12}).status_code, 429)
        self.assertEqual(len(self.rows('SELECT id FROM users')), 20)

    def test_photo_is_reencoded_without_metadata_and_only_served_after_login(self):
        self.login()
        row = self.create_photo()
        self.assertIsNotNone(row['photo_filename'])
        self.assertRegex(row['photo_filename'], r'^[0-9a-f]{48}\.jpg$')
        saved = self.uploads / row['photo_filename']
        self.assertTrue(saved.is_file())
        with Image.open(saved) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertEqual(len(image.getexif()), 0)
        response = self.client.get(f'/notice/{row["id"]}/photo')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/jpeg')
        response.close()
        self.assertEqual(self.app.test_client().get(f'/notice/{row["id"]}/photo').status_code, 302)
        self.assertEqual(self.client.get('/static/uploads/' + row['photo_filename']).status_code, 404)

    def test_png_photo_is_supported(self):
        self.login()
        response = self.post('/post', self.notice(photo=self.photo('PNG')))
        self.assertEqual(response.status_code, 302)
        row = self.rows('SELECT * FROM notices ORDER BY id DESC LIMIT 1')[0]
        self.assertTrue((row['photo_filename'] or '').endswith('.png'))

    def test_invalid_photo_extension_type_bytes_and_multiple_files_do_not_insert(self):
        self.login()
        for image in [(BytesIO(b'<svg></svg>'), 'bad.svg', 'image/svg+xml'),
                      (BytesIO(b'not an image'), 'bad.jpg', 'image/jpeg'),
                      (self.photo('PNG')[0], 'bad.jpg', 'image/jpeg'),
                      (self.photo()[0], 'bad.jpg', 'text/plain'),
                      [self.photo(), self.photo()]]:
            with self.subTest(photo=str(image)[-70:]):
                response = self.post('/post', self.notice(photo=image))
                self.assertEqual(response.status_code, 200)
                self.assertIn('form-error', response.text)
        self.assertEqual(len(self.rows('SELECT id FROM notices')), 120)
        self.assertFalse(self.uploads.exists() and any(self.uploads.iterdir()))

    def test_photo_file_limit_pixel_limit_and_request_limit(self):
        self.login()
        for upload in [(BytesIO(b'x' * (5 * 1024 * 1024 + 1)), 'big.jpg', 'image/jpeg'),
                       self.photo('PNG', size=(4000, 3001))]:
            response = self.post('/post', self.notice(photo=upload))
            self.assertEqual(response.status_code, 200)
            self.assertIn('form-error', response.text)
        response = self.post('/post', self.notice(photo=(BytesIO(b'x' * (6 * 1024 * 1024)), 'big.jpg', 'image/jpeg')))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(len(self.rows('SELECT id FROM notices')), 120)

    def test_edit_preserves_photo_without_replacement_and_replaces_it_once(self):
        self.login()
        row = self.create_photo()
        path = f'/notice/{row["id"]}/edit'
        self.assertEqual(self.post(path, self.notice()).status_code, 302)
        self.assertEqual(self.rows('SELECT photo_filename FROM notices WHERE id=?', (row['id'],))[0]['photo_filename'], row['photo_filename'])
        self.assertEqual(self.post(path, self.notice(photo=self.photo('PNG'))).status_code, 302)
        replacement = self.rows('SELECT photo_filename FROM notices WHERE id=?', (row['id'],))[0]['photo_filename']
        self.assertNotEqual(replacement, row['photo_filename'])
        self.assertTrue((self.uploads / replacement).exists())
        self.assertFalse((self.uploads / row['photo_filename']).exists())

    def test_other_student_cannot_replace_photo_and_admin_removal_removes_file(self):
        self.login()
        row = self.create_photo()
        other = self.app.test_client()
        self.login('daniil.demo@astanait.edu.kz', client=other)
        self.assertEqual(self.post(f'/notice/{row["id"]}/edit', self.notice(photo=self.photo()), other).status_code, 403)
        self.assertEqual(self.rows('SELECT photo_filename FROM notices WHERE id=?', (row['id'],))[0]['photo_filename'], row['photo_filename'])
        admin = self.app.test_client()
        self.login('admin.demo@astanait.edu.kz', client=admin)
        self.assertEqual(self.post(f'/notice/{row["id"]}/remove', client=admin).status_code, 302)
        self.assertFalse((self.uploads / row['photo_filename']).exists())

    def test_contact_is_mailto_and_admin_navigation_is_not_shown_to_student(self):
        self.login()
        page = self.client.get('/notice/1').text
        self.assertIn('href="mailto:zhanzhol.demo@astanait.edu.kz', page)
        self.assertNotIn('href="/admin/analytics"', page)
        admin = self.app.test_client()
        self.login('admin.demo@astanait.edu.kz', client=admin)
        page = admin.get('/').text
        for path in ('/admin/analytics', '/admin/research', '/admin/smart-locker'):
            self.assertIn(f'href="{path}"', page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
