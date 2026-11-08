"""Optional sign-in with a Microsoft Entra ID (work/school) account — OpenID Connect, authorization code + PKCE.

Disabled unless configured through environment variables (never in code or Git):
    CAMPUS_ENTRA_TENANT_ID      directory (tenant) ID of the app registration
    CAMPUS_ENTRA_CLIENT_ID      application (client) ID
    CAMPUS_ENTRA_CLIENT_SECRET  client secret value
    CAMPUS_ENTRA_REDIRECT_URI   optional; default http://localhost:5055/auth/microsoft/callback
When disabled the routes return 404 and the sign-in page is unchanged.

Status (Final, 8 Nov 2026): verified only with simulated Microsoft responses in test_microsoft_auth.py.
It is not "university SSO" until a real university account has signed in through a real registration.
"""
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from pathlib import Path
from threading import Lock

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from backend.db import get_connection

AUTHORITY = 'https://login.microsoftonline.com'
DEFAULT_REDIRECT = 'http://localhost:5055/auth/microsoft/callback'
EMAIL_RULE = re.compile(r'[a-z0-9._-]+@astanait\.edu\.kz')
TENANT_RULE = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[a-z0-9-]+(\.[a-z0-9-]+)+')
SHA256_DIGEST_INFO = bytes.fromhex('3031300d060960864801650304020105000420')
STATE_MAX_AGE = 600        # seconds the user may spend on the Microsoft page
CLOCK_SKEW = 300           # seconds of tolerance for exp / nbf
JWKS_MAX_AGE = 3600
_audit_lock = Lock()


class AuthError(Exception):
    """A sign-in that must be refused; the message is safe to show to the user."""


def settings(app):
    get = lambda key: str(app.config.get('ENTRA_' + key) or os.environ.get('CAMPUS_ENTRA_' + key, '')).strip()
    cfg = {'tenant': get('TENANT_ID'), 'client_id': get('CLIENT_ID'), 'secret': get('CLIENT_SECRET'),
           'redirect_uri': get('REDIRECT_URI') or DEFAULT_REDIRECT}
    cfg['enabled'] = bool(cfg['tenant'] and cfg['client_id'] and cfg['secret'] and TENANT_RULE.fullmatch(cfg['tenant']))
    return cfg


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def b64url_decode(text):
    if not isinstance(text, str) or not re.fullmatch(r'[A-Za-z0-9_-]*', text):
        raise AuthError('The sign-in response was malformed.')
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def _http_json(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={'Accept': 'application/json', 'User-Agent': 'CampusLostFound/Final'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:       # Microsoft returns JSON error bodies
        try:
            return json.loads(error.read().decode('utf-8'))
        except ValueError:
            raise AuthError('Microsoft sign-in is not reachable right now. Try again or use a local account.')
    except (urllib.error.URLError, OSError, ValueError):
        raise AuthError('Microsoft sign-in is not reachable right now. Try again or use a local account.')


def http_post(url, data):
    return (current_app.config.get('ENTRA_HTTP_POST') or _http_json)(url, data)


def http_get(url):
    fn = current_app.config.get('ENTRA_HTTP_GET')
    return fn(url) if fn else _http_json(url)


def now():
    clock = current_app.config.get('ENTRA_CLOCK')
    return clock() if clock else time.time()


def rsa_sha256_verify(n, e, message, signature):
    """RSASSA-PKCS1-v1_5 with SHA-256 (JWT 'RS256'), standard library only."""
    k = (n.bit_length() + 7) // 8
    if len(signature) != k or int.from_bytes(signature, 'big') >= n:
        return False
    encoded = pow(int.from_bytes(signature, 'big'), e, n).to_bytes(k, 'big')
    t = SHA256_DIGEST_INFO + hashlib.sha256(message).digest()
    if k < len(t) + 11:
        return False
    expected = b'\x00\x01' + b'\xff' * (k - len(t) - 3) + b'\x00' + t
    return hmac.compare_digest(encoded, expected)


def signing_keys(cfg, refresh=False):
    cache = current_app.extensions.setdefault('entra_jwks', {})
    if refresh or not cache or now() - cache.get('fetched', 0) > JWKS_MAX_AGE:
        document = http_get(f"{AUTHORITY}/{cfg['tenant']}/discovery/v2.0/keys")
        keys = {}
        for key in document.get('keys', []) if isinstance(document, dict) else []:
            if key.get('kty') == 'RSA' and key.get('kid') and key.get('n') and key.get('e'):
                keys[key['kid']] = (int.from_bytes(b64url_decode(key['n']), 'big'), int.from_bytes(b64url_decode(key['e']), 'big'))
        cache.clear()
        cache.update(keys=keys, fetched=now())
    return cache['keys']


def validate_id_token(token, cfg, expected_nonce):
    parts = token.split('.') if isinstance(token, str) else []
    if len(parts) != 3:
        raise AuthError('The sign-in response was malformed.')
    try:
        header = json.loads(b64url_decode(parts[0]))
        claims = json.loads(b64url_decode(parts[1]))
    except ValueError:
        raise AuthError('The sign-in response was malformed.')
    if not isinstance(header, dict) or not isinstance(claims, dict) or header.get('alg') != 'RS256':
        raise AuthError('The sign-in response used an unexpected signature type.')
    signed, signature = (parts[0] + '.' + parts[1]).encode('ascii'), b64url_decode(parts[2])
    key = signing_keys(cfg).get(header.get('kid')) or signing_keys(cfg, refresh=True).get(header.get('kid'))
    if not key or not rsa_sha256_verify(key[0], key[1], signed, signature):
        raise AuthError('The sign-in response could not be verified.')
    t = now()
    if claims.get('iss') != f"{AUTHORITY}/{cfg['tenant']}/v2.0" or claims.get('tid', cfg['tenant']) != cfg['tenant']:
        raise AuthError('This account belongs to a different organisation.')
    if claims.get('aud') != cfg['client_id']:
        raise AuthError('The sign-in response was issued for a different application.')
    if not isinstance(claims.get('exp'), (int, float)) or claims['exp'] < t - CLOCK_SKEW:
        raise AuthError('The sign-in response has expired. Please sign in again.')
    if isinstance(claims.get('nbf'), (int, float)) and claims['nbf'] > t + CLOCK_SKEW:
        raise AuthError('The sign-in response is not valid yet. Check the computer clock.')
    if not isinstance(claims.get('nonce'), str) or not hmac.compare_digest(claims['nonce'], expected_nonce):
        raise AuthError('The sign-in response did not match this browser session.')
    email = str(claims.get('preferred_username') or claims.get('email') or '').strip().lower()
    if not (17 <= len(email) <= 254 and EMAIL_RULE.fullmatch(email)):
        raise AuthError('Use your Astana IT University Microsoft account (@astanait.edu.kz).')
    return email, claims


def audit(action, user_id=None):
    record = {'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'action': action, 'actor_id': user_id}
    path = Path(current_app.config['AUDIT_PATH'])
    path.parent.mkdir(parents=True, exist_ok=True)
    with _audit_lock, path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')


def refuse(message, status=400):
    audit('microsoft_login_refused', session.get('user_id'))
    return render_template('login.html', error=message), status


def register_microsoft_auth(app):
    bp = Blueprint('microsoft_auth', __name__)
    app.jinja_env.globals['microsoft_login_enabled'] = lambda: settings(app)['enabled']

    @bp.get('/auth/microsoft/login')
    def login():
        cfg = settings(current_app)
        if not cfg['enabled']:
            abort(404)
        target = urllib.parse.urlsplit(cfg['redirect_uri'])
        if target.netloc != request.host:
            # The session cookie must live on the same host Microsoft returns to (e.g. localhost, not 127.0.0.1).
            return redirect(f'{target.scheme}://{target.netloc}' + url_for('microsoft_auth.login'))
        state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        session['entra'] = {'state': state, 'nonce': nonce, 'verifier': verifier, 'at': now()}
        query = urllib.parse.urlencode({
            'client_id': cfg['client_id'], 'response_type': 'code', 'redirect_uri': cfg['redirect_uri'],
            'response_mode': 'query', 'scope': 'openid profile email', 'state': state, 'nonce': nonce,
            'code_challenge': b64url(hashlib.sha256(verifier.encode('ascii')).digest()),
            'code_challenge_method': 'S256', 'prompt': 'select_account'})
        return redirect(f"{AUTHORITY}/{cfg['tenant']}/oauth2/v2.0/authorize?{query}")

    @bp.get('/auth/microsoft/callback')
    def callback():
        cfg = settings(current_app)
        if not cfg['enabled']:
            abort(404)
        pending = session.pop('entra', None)          # single use: a replayed callback finds nothing
        if request.args.get('error'):
            return refuse('Microsoft sign-in was cancelled or refused. You can try again or use a local account.')
        supplied = request.args.get('state', '')
        if not pending or not hmac.compare_digest(supplied, pending.get('state', '')) or now() - pending.get('at', 0) > STATE_MAX_AGE:
            return refuse('This sign-in link has expired or does not belong to this browser. Start again.')
        code = request.args.get('code', '')
        if not 1 <= len(code) <= 4096:
            return refuse('Microsoft did not return a sign-in code. Start again.')
        try:
            tokens = http_post(f"{AUTHORITY}/{cfg['tenant']}/oauth2/v2.0/token", {
                'client_id': cfg['client_id'], 'client_secret': cfg['secret'], 'grant_type': 'authorization_code',
                'code': code, 'redirect_uri': cfg['redirect_uri'], 'code_verifier': pending['verifier'],
                'scope': 'openid profile email'})
            if not isinstance(tokens, dict) or 'id_token' not in tokens:
                raise AuthError('Microsoft could not complete the sign-in. Start again or use a local account.')
            email, claims = validate_id_token(tokens['id_token'], cfg, pending['nonce'])
        except AuthError as error:
            return refuse(str(error), 400)
        with closing(get_connection(current_app.config['DATABASE'])) as db:
            user = db.execute('SELECT id, role FROM users WHERE email=?', (email,)).fetchone()
            if not user:
                try:
                    with db:   # new university account: student role, random unusable local password
                        db.execute("INSERT INTO users(email,password_hash,role) VALUES(?,?,'student')",
                                   (email, generate_password_hash(secrets.token_urlsafe(48), method='scrypt')))
                except sqlite3.IntegrityError:
                    pass
                user = db.execute('SELECT id, role FROM users WHERE email=?', (email,)).fetchone()
        session.clear()
        session.update(user_id=user['id'], csrf=secrets.token_urlsafe(32), auth='microsoft')
        session.permanent = True
        audit('microsoft_login_success', user['id'])
        return redirect(url_for('browse'))

    app.register_blueprint(bp)
