"""Local, offline teaching prototype. Synthetic accounts; no university SSO."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
if sys.platform == 'win32':
    sys.path.insert(0, str(ROOT / 'vendor'))
from collections import defaultdict, deque
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from functools import wraps
import hmac
from io import BytesIO
import json
import re
import secrets
import sqlite3
import time
import warnings
from threading import Lock
from flask import Flask, abort, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from backend.db import DEFAULT_DB_PATH, get_connection, init_database, seed_database

SQLITE_MAX_INTEGER = (1 << 63) - 1

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=DEFAULT_DB_PATH, MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        UPLOAD_FOLDER=ROOT / 'data' / 'uploads',
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False, PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        TRUSTED_HOSTS=['127.0.0.1', 'localhost'], AUDIT_PATH=ROOT / 'runtime' / 'audit.jsonl')
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY'):
        key_path = ROOT / 'runtime' / 'session.key'
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if not key_path.exists():
            try:
                with key_path.open('x', encoding='ascii') as f:
                    f.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        app.config['SECRET_KEY'] = key_path.read_text(encoding='ascii').strip()
    attempts, lock = defaultdict(deque), Lock()
    dummy_hash = generate_password_hash('not-a-valid-demo-password', method='scrypt')

    def db():
        if 'db' not in g:
            g.db = get_connection(app.config['DATABASE'])
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        conn = g.pop('db', None)
        if conn is not None:
            conn.close()

    def audit(action, notice_id=None):
        record = {'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                  'action': action, 'actor_id': session.get('user_id')}
        if notice_id is not None:
            record['notice_id'] = notice_id
        path = Path(app.config['AUDIT_PATH'])
        path.parent.mkdir(parents=True, exist_ok=True)
        with lock, path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')

    @app.before_request
    def security():
        g.user = None
        if session.get('user_id'):
            g.user = db().execute('SELECT id,email,role FROM users WHERE id=?', (session['user_id'],)).fetchone()
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST':
            supplied = request.form.get('csrf', '')
            if not hmac.compare_digest(supplied, session['csrf']):
                audit('csrf_rejected')
                abort(400, description='This form expired. Reload the page and try again.')

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapped

    def load_notice(notice_id):
        if not 1 <= notice_id <= SQLITE_MAX_INTEGER:
            abort(404)
        notice = db().execute('SELECT n.*,c.name AS category,u.email FROM notices n JOIN categories c ON c.id=n.category_id JOIN users u ON u.id=n.owner_id WHERE n.id=?', (notice_id,)).fetchone()
        if not notice:
            abort(404)
        return notice

    def require_owner(notice):
        if notice['owner_id'] != g.user['id']:
            audit('owner_access_denied', notice['id'])
            abort(403, description='Only the notice owner can change this notice.')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        error, email = None, ''
        if request.method == 'POST':
            now, key = time.monotonic(), ('register', request.remote_addr or 'local')
            with lock:
                queue = attempts[key]
                while queue and queue[0] < now - 60:
                    queue.popleft()
                limited = len(queue) >= 5
                if not limited:
                    queue.append(now)
            if limited:
                audit('registration_rate_limited')
                return render_template('register.html', email='', error='Too many attempts. Wait 60 seconds.'), 429
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            if not (17 <= len(email) <= 254 and re.fullmatch(r'[a-z0-9._-]+@astanait\.edu\.kz', email)):
                error = 'Use an @astanait.edu.kz address with letters, digits, dots, underscores or hyphens.'
            elif not 12 <= len(password) <= 128:
                error = 'Choose a local password with 12-128 characters.'
            else:
                try:
                    with db():
                        db().execute("INSERT INTO users(email,password_hash,role) VALUES(?,?,'student')",
                            (email, generate_password_hash(password, method='scrypt')))
                except sqlite3.IntegrityError:
                    error = 'An account with this address already exists. Sign in instead.'
                else:
                    audit('registration_success')
                    flash('Local student account created. Sign in with your new password.')
                    return redirect(url_for('login'))
            audit('registration_rejected')
        return render_template('register.html', email=email, error=error)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            now, key = time.monotonic(), request.remote_addr or 'local'
            with lock:
                queue = attempts[key]
                while queue and queue[0] < now - 60:
                    queue.popleft()
                limited = len(queue) >= 5
            if limited:
                audit('login_rate_limited')
                return render_template('login.html', error='Too many attempts. Wait 60 seconds.'), 429
            email = request.form.get('email', '').strip().lower()[:254]
            password = request.form.get('password', '')[:256]
            user = db().execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
            valid = check_password_hash(user['password_hash'] if user else dummy_hash, password)
            if valid and user:
                session.clear()
                session.update(user_id=user['id'], csrf=secrets.token_urlsafe(32))
                session.permanent = True
                audit('login_success')
                return redirect(url_for('browse'))
            with lock:
                attempts[key].append(now)
            audit('login_failed')
            error = 'Email or password is incorrect.'
        return render_template('login.html', error=error)

    @app.post('/logout')
    def logout():
        audit('logout')
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def browse():
        q = request.args.get('q', '').strip()[:120]
        category = request.args.get('category', '', type=str)
        status = request.args.get('status', '')
        page = max(1, request.args.get('page', 1, type=int))
        if page > SQLITE_MAX_INTEGER // 8 + 1:
            abort(400, description='Choose a valid page number.')
        clauses, params = [], []
        if q:
            clauses.append("n.title LIKE ? ESCAPE '\\'")
            params.append('%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
        if category.isdigit():
            try:
                category_id = int(category)
            except ValueError:
                abort(400, description='Choose a valid category.')
            if category_id > SQLITE_MAX_INTEGER:
                abort(400, description='Choose a valid category.')
            clauses.append('n.category_id=?'); params.append(category_id)
        if status in ('open', 'returned'):
            clauses.append('n.status=?'); params.append(status)
        if request.args.get('mine') == '1':
            clauses.append('n.owner_id=?'); params.append(g.user['id'])
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        count = db().execute('SELECT count(*) FROM notices n' + where, params).fetchone()[0]
        notices = db().execute('SELECT n.*, c.name AS category FROM notices n JOIN categories c ON c.id=n.category_id' + where + ' ORDER BY n.id DESC LIMIT 8 OFFSET ?', params + [(page-1)*8]).fetchall()
        args = request.args.to_dict(); args.pop('page', None)
        return render_template('browse.html', notices=notices, categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall(), count=count, page=page, q=q, selected_category=category, status=status, args=args,
            baseline=request.args.get('media') == 'baseline')

    @app.get('/how-it-works')
    @login_required
    def how_it_works():
        return render_template('how_it_works.html')

    @app.get('/notice/<int:notice_id>')
    @login_required
    def detail(notice_id):
        return render_template('detail.html', notice=load_notice(notice_id))

    @app.get('/notice/<int:notice_id>/photo')
    @login_required
    def photo(notice_id):
        notice = load_notice(notice_id)
        filename = notice['photo_filename']
        if not filename or not re.fullmatch(r'[0-9a-f]{48}\.(?:jpg|png)', filename):
            abort(404)
        path = Path(app.config['UPLOAD_FOLDER']) / filename
        if path.is_symlink():
            abort(404)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    def delete_photo(filename):
        if filename and re.fullmatch(r'[0-9a-f]{48}\.(?:jpg|png)', filename):
            (Path(app.config['UPLOAD_FOLDER']) / filename).unlink(missing_ok=True)

    def save_photo():
        """Validate one optional upload and save only freshly encoded pixel data."""
        uploads = [upload for upload in request.files.getlist('photo') if upload.filename]
        if not uploads:
            return None, None
        if len(uploads) != 1:
            return None, 'Choose only one photograph.'
        upload = uploads[0]
        extension = Path(upload.filename).suffix.lower()
        expected = {'.jpg': ('JPEG', 'image/jpeg'), '.jpeg': ('JPEG', 'image/jpeg'),
                    '.png': ('PNG', 'image/png')}.get(extension)
        if not expected or upload.mimetype != expected[1]:
            return None, 'Choose a JPG or PNG photograph with the matching file type.'
        content = upload.stream.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            return None, 'The photograph must be no larger than 5 MB.'
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as original:
                    if original.format != expected[0] or original.width * original.height > 12_000_000:
                        return None, 'Use a valid JPG or PNG image of at most 12 million pixels.'
                    original.verify()
                with Image.open(BytesIO(content)) as original:
                    oriented = ImageOps.exif_transpose(original)
                    mode = 'RGBA' if expected[0] == 'PNG' else 'RGB'
                    pixels = oriented.convert(mode)
                    pixels.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    clean = Image.frombytes(mode, pixels.size, pixels.tobytes())
                    encoded = BytesIO()
                    clean.save(encoded, format=expected[0], **({'quality': 85} if expected[0] == 'JPEG' else {}))
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            return None, 'The photograph could not be read. Choose a valid JPG or PNG image.'
        folder = Path(app.config['UPLOAD_FOLDER'])
        folder.mkdir(parents=True, exist_ok=True)
        filename = secrets.token_hex(24) + ('.jpg' if expected[0] == 'JPEG' else '.png')
        with (folder / filename).open('xb') as target:
            target.write(encoded.getvalue())
        return filename, None

    def validate_form():
        values = {key: request.form.get(key, '').strip() for key in ('title','description','location','event_date','type','category_id')}
        limits = {'title':(3,120), 'description':(10,1200), 'location':(2,100)}
        for key,(minimum,maximum) in limits.items():
            if not minimum <= len(values[key]) <= maximum:
                return values, f'{key.capitalize()} must have {minimum}-{maximum} characters.'
        try:
            event = date.fromisoformat(values['event_date'])
            if values['event_date'] != event.isoformat() or not date(2020,1,1) <= event <= datetime.now(timezone.utc).date():
                raise ValueError()
        except ValueError:
            return values, 'Choose a valid date between 2020 and today (UTC).'
        if values['type'] not in ('lost','found'):
            return values, 'Choose Lost or Found.'
        if not values['category_id'].isdigit() or not db().execute('SELECT id FROM categories WHERE id=?', (values['category_id'],)).fetchone():
            return values, 'Choose an existing category.'
        return values, None

    @app.route('/post', methods=['GET','POST'])
    @login_required
    def create():
        values, error = {}, None
        if request.method == 'POST':
            values, error = validate_form()
            if not error:
                filename, error = save_photo()
            if not error:
                try:
                    with db():
                        cursor = db().execute('INSERT INTO notices(owner_id,category_id,title,description,location,event_date,type,photo_filename) VALUES(?,?,?,?,?,?,?,?)', (g.user['id'], values['category_id'], values['title'],values['description'],values['location'],values['event_date'],values['type'],filename))
                except sqlite3.Error:
                    delete_photo(filename)
                    raise
                audit('notice_created', cursor.lastrowid)
                flash('Notice published and saved to the database.')
                return redirect(url_for('detail', notice_id=cursor.lastrowid))
        return render_template('form.html', values=values, error=error, editing=False, today=datetime.now(timezone.utc).date().isoformat(), categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall())

    @app.route('/notice/<int:notice_id>/edit', methods=['GET','POST'])
    @login_required
    def edit(notice_id):
        notice = load_notice(notice_id); require_owner(notice)
        values, error = dict(notice), None
        if request.method == 'POST':
            values, error = validate_form()
            if not error and values['event_date'] > notice['created_at'][:10]:
                error = 'The event date cannot be later than the date this notice was first published.'
            if not error:
                filename, error = save_photo()
            if not error:
                try:
                    with db():
                        db().execute("UPDATE notices SET category_id=?,title=?,description=?,location=?,event_date=?,type=?,photo_filename=?,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=? AND owner_id=?", (values['category_id'],values['title'],values['description'],values['location'],values['event_date'],values['type'],filename or notice['photo_filename'],notice_id,g.user['id']))
                except sqlite3.Error:
                    delete_photo(filename)
                    raise
                if filename:
                    delete_photo(notice['photo_filename'])
                audit('notice_updated', notice_id); flash('Your changes have been saved.')
                return redirect(url_for('detail', notice_id=notice_id))
        return render_template('form.html',values=values,error=error,editing=True,today=datetime.now(timezone.utc).date().isoformat(),categories=db().execute('SELECT * FROM categories ORDER BY name').fetchall())

    @app.post('/notice/<int:notice_id>/returned')
    @login_required
    def returned(notice_id):
        notice = load_notice(notice_id); require_owner(notice)
        with db():
            db().execute("UPDATE notices SET status='returned',updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=? AND owner_id=?", (notice_id,g.user['id']))
        audit('notice_returned', notice_id); flash('Marked as returned. Thank you!')
        return redirect(url_for('detail',notice_id=notice_id))

    @app.route('/notice/<int:notice_id>/remove', methods=['GET','POST'])
    @login_required
    def remove(notice_id):
        if g.user['role'] != 'admin':
            audit('admin_access_denied',notice_id); abort(403,description='Administrator access is required.')
        notice = load_notice(notice_id)
        if request.method == 'POST':
            with db():
                db().execute('DELETE FROM notices WHERE id=?',(notice_id,))
            delete_photo(notice['photo_filename'])
            audit('notice_removed',notice_id); flash('Notice removed by the administrator.')
            return redirect(url_for('browse'))
        return render_template('remove.html', notice=notice)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def error_page(error):
        return render_template('error.html', code=error.code, message=error.description), error.code

    from stage2_features import register_blueprints
    register_blueprints(app)
    from analytics_routes import register_analytics
    register_analytics(app)
    from admin_panel import register_admin_panel
    register_admin_panel(app)
    from microsoft_auth import register_microsoft_auth  # optional; off unless CAMPUS_ENTRA_* is set
    register_microsoft_auth(app)
    return app

if __name__ == '__main__':
    import argparse
    from waitress import serve
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=5055)
    args=parser.parse_args()
    if not DEFAULT_DB_PATH.exists():
        init_database(); seed_database()
    print(f'Campus Lost & Found: http://127.0.0.1:{args.port}', flush=True)
    print('Offline demonstration. Press Ctrl+C to stop.', flush=True)
    serve(create_app(),host='127.0.0.1',port=args.port,threads=4)
