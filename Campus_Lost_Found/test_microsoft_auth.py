"""Microsoft Entra ID sign-in against SIMULATED Microsoft endpoints (no network, no real tenant).
A throw-away RSA key signs test ID tokens; the app must accept only correctly signed, correctly addressed tokens."""
from contextlib import closing
import base64
import hashlib
import json
import random
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app import create_app
from backend.db import seed_database
import microsoft_auth

TENANT = '11111111-2222-3333-4444-555555555555'
CLIENT = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def _probable_prime(bits, rng):
    while True:
        n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if all(n % p for p in (3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)) and all(pow(a, n - 1, n) == 1 for a in (2, 3, 5, 7, 11, 13)):
            d, s = n - 1, 0
            while d % 2 == 0:
                d //= 2; s += 1
            ok = True
            for a in (2, 3, 5, 7, 11, 13, 17, 19, 23):
                x = pow(a, d, n)
                if x in (1, n - 1):
                    continue
                for _ in range(s - 1):
                    x = pow(x, 2, n)
                    if x == n - 1:
                        break
                else:
                    ok = False; break
            if ok:
                return n


def make_key(seed):
    rng = random.Random(seed)
    e = 65537
    while True:
        p, q = _probable_prime(512, rng), _probable_prime(512, rng)
        phi = (p - 1) * (q - 1)
        if p != q and phi % e:
            return p * q, e, pow(e, -1, phi)


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def sign(n, d, message):
    k = (n.bit_length() + 7) // 8
    t = microsoft_auth.SHA256_DIGEST_INFO + hashlib.sha256(message).digest()
    em = b'\x00\x01' + b'\xff' * (k - len(t) - 3) + b'\x00' + t
    return pow(int.from_bytes(em, 'big'), d, n).to_bytes(k, 'big')


class MicrosoftSignInTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n, cls.e, cls.d = make_key(2623)
        cls.other = make_key(9999)
        cls.fixture = tempfile.TemporaryDirectory(prefix='entra-', dir=ROOT)
        cls.seed = Path(cls.fixture.name) / 'seed.sqlite3'
        seed_database(cls.seed)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='case-', dir=self.fixture.name)
        self.db = Path(self.temp.name) / 'campus.sqlite3'
        shutil.copy2(self.seed, self.db)
        self.clock = 1_800_000_000
        self.token_requests = []
        self.next_claims = {}
        self.next_tokens = None
        self.app = self.make_app(enabled=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def make_app(self, enabled):
        config = {'TESTING': True, 'SECRET_KEY': 'entra-test', 'DATABASE': self.db,
                  'AUDIT_PATH': Path(self.temp.name) / 'audit.jsonl', 'UPLOAD_FOLDER': Path(self.temp.name) / 'up',
                  'ENTRA_HTTP_GET': self.fake_get, 'ENTRA_HTTP_POST': self.fake_post, 'ENTRA_CLOCK': lambda: self.clock}
        if enabled:
            config.update(ENTRA_TENANT_ID=TENANT, ENTRA_CLIENT_ID=CLIENT, ENTRA_CLIENT_SECRET='test-secret-not-real',
                          ENTRA_REDIRECT_URI='http://localhost/auth/microsoft/callback')
        return create_app(config)

    # ---- simulated Microsoft -------------------------------------------------
    def fake_get(self, url):
        assert url == f'https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys', url
        return {'keys': [{'kty': 'RSA', 'kid': 'k1', 'n': b64(self.n.to_bytes((self.n.bit_length() + 7) // 8, 'big')), 'e': b64(self.e.to_bytes(3, 'big'))}]}

    def fake_post(self, url, data):
        assert url == f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token', url
        self.token_requests.append(data)
        if self.next_tokens is not None:
            return self.next_tokens
        return {'id_token': self.id_token(**self.next_claims), 'token_type': 'Bearer'}

    def id_token(self, key=None, alg='RS256', **override):
        claims = {'iss': f'https://login.microsoftonline.com/{TENANT}/v2.0', 'aud': CLIENT, 'tid': TENANT,
                  'exp': self.clock + 3600, 'nbf': self.clock - 10, 'iat': self.clock - 10, 'nonce': self.nonce,
                  'preferred_username': 'new.student@astanait.edu.kz', 'name': 'New Student'}
        claims.update(override)
        head = b64(json.dumps({'alg': alg, 'kid': 'k1', 'typ': 'JWT'}).encode())
        body = b64(json.dumps(claims).encode())
        n, _, d = key or (self.n, self.e, self.d)
        return f'{head}.{body}.' + b64(sign(n, d, f'{head}.{body}'.encode()))

    # ---- helpers ---------------------------------------------------------------
    def start(self):
        r = self.client.get('/auth/microsoft/login')
        self.assertEqual(r.status_code, 302)
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(r.headers['Location']).query))
        with self.client.session_transaction() as s:
            self.verifier = s['entra']['verifier']
        self.state, self.nonce = q['state'], q['nonce']
        return r, q

    def finish(self, **claims):
        self.next_claims = claims
        return self.client.get('/auth/microsoft/callback?' + urllib.parse.urlencode({'code': 'simulated-code', 'state': self.state}))

    def user(self, email):
        with closing(sqlite3.connect(self.db)) as c:
            return c.execute('SELECT id, role, password_hash FROM users WHERE email=?', (email,)).fetchone()

    def signed_in(self):
        with self.client.session_transaction() as s:
            return s.get('user_id')

    # ---- tests -------------------------------------------------------------------
    def test_disabled_without_configuration_and_page_unchanged(self):
        client = self.make_app(enabled=False).test_client()
        self.assertEqual(client.get('/auth/microsoft/login').status_code, 404)
        self.assertEqual(client.get('/auth/microsoft/callback?code=x&state=y').status_code, 404)
        page = client.get('/login').get_data(as_text=True)
        self.assertNotIn('Sign in with Microsoft', page)
        self.assertIn('No university SSO', page)

    def test_enabled_shows_button_and_redirects_with_pkce_state_and_nonce(self):
        page = self.client.get('/login').get_data(as_text=True)
        self.assertIn('Sign in with Microsoft', page)
        r, q = self.start()
        self.assertTrue(r.headers['Location'].startswith(f'https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize?'))
        self.assertEqual(q['client_id'], CLIENT)
        self.assertEqual(q['response_type'], 'code')
        self.assertEqual(q['redirect_uri'], 'http://localhost/auth/microsoft/callback')
        self.assertEqual(q['code_challenge_method'], 'S256')
        self.assertEqual(q['code_challenge'], b64(hashlib.sha256(self.verifier.encode()).digest()))
        self.assertIn('openid', q['scope'])
        self.assertGreaterEqual(len(q['state']), 40)
        self.assertNotIn('test-secret-not-real', r.headers['Location'])

    def test_login_moves_to_the_redirect_host_first(self):
        r = self.client.get('/auth/microsoft/login', base_url='http://127.0.0.1')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers['Location'], 'http://localhost/auth/microsoft/login')

    def test_valid_token_creates_student_and_signs_in(self):
        self.start()
        r = self.finish()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers['Location'].endswith('/'))
        row = self.user('new.student@astanait.edu.kz')
        self.assertIsNotNone(row)
        self.assertEqual(row[1], 'student')
        self.assertTrue(row[2].startswith('scrypt:'))
        self.assertEqual(self.signed_in(), row[0])
        sent = self.token_requests[-1]
        self.assertEqual(sent['code_verifier'], self.verifier)
        self.assertEqual(sent['grant_type'], 'authorization_code')
        self.assertIn('microsoft_login_success', (Path(self.temp.name) / 'audit.jsonl').read_text())
        self.assertNotIn('test-secret-not-real', (Path(self.temp.name) / 'audit.jsonl').read_text())

    def test_existing_account_keeps_its_role(self):
        self.start()
        self.finish(preferred_username='Admin.Demo@astanait.edu.kz')
        row = self.user('admin.demo@astanait.edu.kz')
        self.assertEqual(row[1], 'admin')
        self.assertEqual(self.signed_in(), row[0])
        with closing(sqlite3.connect(self.db)) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 20)

    def test_state_is_checked_and_single_use(self):
        self.start()
        bad = self.client.get('/auth/microsoft/callback?code=c&state=wrong')
        self.assertEqual(bad.status_code, 400)
        self.assertIsNone(self.signed_in())
        self.start()
        self.assertEqual(self.finish().status_code, 302)
        self.client.get('/login')
        with self.client.session_transaction() as s:
            s.clear()
        replay = self.client.get('/auth/microsoft/callback?' + urllib.parse.urlencode({'code': 'simulated-code', 'state': self.state}))
        self.assertEqual(replay.status_code, 400)
        self.assertIsNone(self.signed_in())

    def test_expired_state_is_refused(self):
        self.start()
        self.clock += 601
        self.assertEqual(self.finish().status_code, 400)
        self.assertIsNone(self.signed_in())

    def test_bad_tokens_are_refused_and_create_no_user(self):
        cases = {
            'wrong audience': dict(aud='someone-else'),
            'wrong issuer': dict(iss='https://login.microsoftonline.com/other/v2.0'),
            'other tenant': dict(tid='99999999-2222-3333-4444-555555555555'),
            'expired': dict(exp=1_800_000_000 - 3600),
            'not yet valid': dict(nbf=1_800_000_000 + 3600),
            'wrong nonce': dict(nonce='not-the-nonce'),
            'not university email': dict(preferred_username='someone@gmail.com'),
        }
        for label, claims in cases.items():
            with self.subTest(label):
                self.start()
                r = self.finish(**claims)
                self.assertEqual(r.status_code, 400, label)
                self.assertIsNone(self.signed_in(), label)
                self.assertIsNone(self.user('new.student@astanait.edu.kz'), label)

    def test_forged_signature_and_alg_none_are_refused(self):
        for label, token in (('foreign key', lambda: self.id_token(key=self.other)),
                             ('alg none', lambda: self.id_token(alg='none')),
                             ('tampered', lambda: self.id_token().replace('.', '.x', 1))):
            with self.subTest(label):
                self.start()
                self.next_tokens = {'id_token': token()}
                r = self.client.get('/auth/microsoft/callback?' + urllib.parse.urlencode({'code': 'c', 'state': self.state}))
                self.next_tokens = None
                self.assertEqual(r.status_code, 400, label)
                self.assertIsNone(self.signed_in(), label)

    def test_microsoft_error_and_token_failure_are_shown_safely(self):
        self.start()
        r = self.client.get('/auth/microsoft/callback?error=access_denied&state=' + self.state)
        self.assertEqual(r.status_code, 400)
        self.assertIn('cancelled or refused', r.get_data(as_text=True))
        self.start()
        self.next_tokens = {'error': 'invalid_grant', 'error_description': 'AADSTS70008 expired'}
        r = self.client.get('/auth/microsoft/callback?' + urllib.parse.urlencode({'code': 'c', 'state': self.state}))
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('AADSTS', r.get_data(as_text=True))
        self.assertIsNone(self.signed_in())

    def test_rsa_verifier_matches_known_answer(self):
        msg = b'campus lost and found'
        sig = sign(self.n, self.d, msg)
        self.assertTrue(microsoft_auth.rsa_sha256_verify(self.n, self.e, msg, sig))
        self.assertFalse(microsoft_auth.rsa_sha256_verify(self.n, self.e, msg + b'!', sig))
        self.assertFalse(microsoft_auth.rsa_sha256_verify(self.n, self.e, msg, sig[:-1]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
