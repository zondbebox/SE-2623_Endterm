"""Endterm features. Separate observation/telemetry files; no hardware claims."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import csv
import io
import re
import sqlite3

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, Response, url_for

ROOT = Path(__file__).resolve().parent
RESEARCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_sessions (
 id INTEGER PRIMARY KEY, participant TEXT NOT NULL,
 task TEXT NOT NULL CHECK(task IN ('publish','find')), device TEXT NOT NULL,
 external_consent INTEGER NOT NULL CHECK(external_consent=1),
 started_at TEXT NOT NULL, finished_at TEXT, duration_seconds REAL,
 outcome TEXT CHECK(outcome IN ('success','failure')), helped INTEGER CHECK(helped IN (0,1)),
 observation1 TEXT NOT NULL DEFAULT '', observation2 TEXT NOT NULL DEFAULT '',
 observation3 TEXT NOT NULL DEFAULT '', UNIQUE(participant,task)
);
"""
TELEMETRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS locker_events (
 id INTEGER PRIMARY KEY, locker_id TEXT NOT NULL CHECK(locker_id='LF-01'),
 notice_id INTEGER, door_state TEXT NOT NULL CHECK(door_state IN ('open','closed')),
 event_type TEXT NOT NULL CHECK(event_type IN ('change','heartbeat')),
 observed_at TEXT NOT NULL, open_since_at TEXT,
 source TEXT NOT NULL CHECK(source='SIMULATED')
);
"""


def utc_now():
    """Injectable UTC clock; the browser cannot submit durations."""
    clock = current_app.config.get('STAGE2_CLOCK')
    value = clock() if clock else datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


@contextmanager
def storage(path, schema):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.executescript(schema)
        with conn:
            yield conn
    finally:
        conn.close()


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login'))
        if g.user['role'] != 'admin':
            abort(403, description='Administrator access is required.')
        return fn(*args, **kwargs)
    return wrapped


def research_summary(rows):
    people = {r['participant'] for r in rows}
    complete = len(people) == 5 and len(rows) == 10 and all(r['finished_at'] and r['outcome'] for r in rows)
    results = []
    for task, target in [('publish', 120), ('find', 60)]:
        finished = [r for r in rows if r['task'] == task and r['finished_at']]
        met = sum(r['outcome'] == 'success' and not r['helped'] and r['duration_seconds'] <= target for r in finished)
        results.append({'task': task, 'target': target, 'completed': len(finished),
                        'met_count': met, 'status': ('Met' if met >= 4 else 'Not met') if complete else 'Pending'})
    return {'participants': len(people), 'complete': complete, 'criteria': results}


def safe_csv(value):
    text = '' if value is None else str(value)
    if text[:1] in ('\t', '\r', '\n') or text.lstrip()[:1] in ('=', '+', '-', '@'):
        return "'" + text
    return text


def record_simulated_event(telemetry_path, main_path, action, notice_id=None, now=None):
    """Local operator helper also used by the CLI; never writes the main database."""
    if action not in ('open', 'closed', 'heartbeat', 'reset'):
        raise ValueError('Choose open, closed, heartbeat or reset.')
    now = now or datetime.now(timezone.utc)
    timestamp = now.astimezone(timezone.utc).isoformat(timespec='microseconds')
    with storage(telemetry_path, TELEMETRY_SCHEMA) as conn:
        conn.execute('BEGIN IMMEDIATE')
        prior = conn.execute('SELECT * FROM locker_events ORDER BY id DESC LIMIT 1').fetchone()
        if action == 'reset':
            if not prior or prior['notice_id'] is None:
                raise ValueError('There is no unavailable assignment to reset.')
            with closing(sqlite3.connect(Path(main_path).resolve().as_uri() + '?mode=ro', uri=True)) as main:
                valid_assignment = main.execute('SELECT id FROM notices WHERE id=? AND type=?',
                                                (prior['notice_id'], 'found')).fetchone()
            if valid_assignment:
                raise ValueError('The assigned notice is still available. Simulate close instead.')
            state, notice_id, opened = 'closed', None, None
        elif action == 'heartbeat':
            if not prior:
                raise ValueError('Simulate a state first; a heartbeat cannot invent a door state.')
            state, notice_id, opened = prior['door_state'], prior['notice_id'], prior['open_since_at']
        else:
            state = action
            if not str(notice_id or '').isdigit():
                raise ValueError('Select an existing found notice.')
            notice_id = int(notice_id)
            if prior and prior['door_state'] == 'open' and prior['notice_id'] != notice_id:
                raise ValueError('Close the current locker before assigning a different notice.')
            opened = (prior['open_since_at'] if prior and prior['door_state'] == 'open' else timestamp) if state == 'open' else None
        if notice_id is not None:
            with closing(sqlite3.connect(Path(main_path).resolve().as_uri() + '?mode=ro', uri=True)) as main:
                notice = main.execute('SELECT id FROM notices WHERE id=? AND type=?', (notice_id, 'found')).fetchone()
            if not notice:
                raise ValueError('The found notice no longer exists. Reset the unavailable assignment, then select another notice.')
        conn.execute('INSERT INTO locker_events(locker_id,notice_id,door_state,event_type,observed_at,open_since_at,source) VALUES(?,?,?,?,?,?,?)',
                     ('LF-01', notice_id, state, 'heartbeat' if action == 'heartbeat' else 'change', timestamp, opened, 'SIMULATED'))


def register_blueprints(app):
    """Attach routes to the existing factory; its global CSRF guard covers POST."""
    app.config.setdefault('RESEARCH_DATABASE', ROOT / 'data' / 'research.sqlite3')
    app.config.setdefault('TELEMETRY_DATABASE', ROOT / 'data' / 'telemetry.sqlite3')
    bp = Blueprint('stage2', __name__)

    @bp.route('/admin/research', methods=['GET', 'POST'])
    @admin_required
    def research():
        with storage(current_app.config['RESEARCH_DATABASE'], RESEARCH_SCHEMA) as conn:
            if request.method == 'POST':
                action = request.form.get('action')
                if action == 'start':
                    participant = request.form.get('participant', '').strip().upper()
                    task = request.form.get('task', '')
                    device = request.form.get('device', '').strip()
                    if not re.fullmatch(r'T(?:0[1-9]|[1-9][0-9])', participant):
                        abort(400, description='Use a participant code from T01 to T99, without a name.')
                    if task not in ('publish', 'find') or not 1 <= len(device) <= 120:
                        abort(400, description='Choose a task and enter a device/browser description (1–120 characters).')
                    if request.form.get('external_consent') != 'yes':
                        abort(400, description='Confirm voluntary participation by a real person outside the team.')
                    conn.execute('BEGIN IMMEDIATE')
                    participants = {r[0] for r in conn.execute('SELECT DISTINCT participant FROM research_sessions')}
                    if participant not in participants and len(participants) >= 5:
                        abort(409, description='This five-person cohort is full. Complete the existing participants; do not replace failed attempts.')
                    try:
                        conn.execute('INSERT INTO research_sessions(participant,task,device,external_consent,started_at) VALUES(?,?,?,?,?)',
                                     (participant, task, device, 1, utc_now().isoformat(timespec='microseconds')))
                    except sqlite3.IntegrityError:
                        abort(409, description='A first attempt already exists for this participant and task. Finish it; do not repeat it.')
                    flash('Timer started. Let the participant work without coaching.')
                elif action == 'stop':
                    raw_id = request.form.get('session_id', '')
                    if not raw_id.isdigit():
                        abort(400, description='Choose a valid attempt.')
                    conn.execute('BEGIN IMMEDIATE')
                    row = conn.execute('SELECT * FROM research_sessions WHERE id=?', (int(raw_id),)).fetchone()
                    if not row:
                        abort(404, description='Attempt not found.')
                    if row['finished_at']:
                        abort(409, description='This timer is already stopped; its original duration is retained.')
                    now = utc_now()
                    seconds = (now - datetime.fromisoformat(row['started_at'])).total_seconds()
                    if seconds < 0:
                        abort(400, description='The system clock moved backwards. Correct it before stopping.')
                    conn.execute('UPDATE research_sessions SET finished_at=?,duration_seconds=? WHERE id=? AND finished_at IS NULL',
                                 (now.isoformat(timespec='microseconds'), seconds, int(raw_id)))
                    flash('Timer stopped. Add observations below; note entry will not change the measured time.')
                elif action == 'finish':
                    raw_id = request.form.get('session_id', '')
                    outcome, helped = request.form.get('outcome'), request.form.get('helped')
                    notes = [request.form.get('observation' + str(i), '').strip() for i in range(1, 4)]
                    if not raw_id.isdigit() or outcome not in ('success', 'failure') or helped not in ('yes', 'no') or any(len(n) > 1000 for n in notes):
                        abort(400, description='Provide a valid attempt, outcome, help answer and notes of at most 1,000 characters each.')
                    conn.execute('BEGIN IMMEDIATE')
                    row = conn.execute('SELECT * FROM research_sessions WHERE id=?', (int(raw_id),)).fetchone()
                    if not row:
                        abort(404, description='Attempt not found.')
                    if row['outcome']:
                        abort(409, description='This attempt is already finished. Its original measurement is retained.')
                    now = utc_now()
                    seconds = row['duration_seconds'] if row['finished_at'] else (now - datetime.fromisoformat(row['started_at'])).total_seconds()
                    if seconds < 0:
                        abort(400, description='The system clock moved backwards. Correct it before finishing this attempt.')
                    finished_at = row['finished_at'] or now.isoformat(timespec='microseconds')
                    conn.execute('UPDATE research_sessions SET finished_at=?,duration_seconds=?,outcome=?,helped=?,observation1=?,observation2=?,observation3=? WHERE id=? AND outcome IS NULL',
                                 (finished_at, seconds, outcome, int(helped == 'yes'), *notes, int(raw_id)))
                    flash('Attempt finished. The measured duration and original observations are saved.')
                else:
                    abort(400, description='Unknown recorder action.')
                return redirect(url_for('stage2.research'))
            rows = conn.execute('SELECT * FROM research_sessions ORDER BY id').fetchall()
        return render_template('research.html', rows=rows, summary=research_summary(rows), now=utc_now())

    @bp.get('/admin/research.csv')
    @admin_required
    def research_csv():
        with storage(current_app.config['RESEARCH_DATABASE'], RESEARCH_SCHEMA) as conn:
            rows = conn.execute('SELECT * FROM research_sessions ORDER BY id').fetchall()
        fields = ['id','participant','task','device','external_consent','started_at','finished_at','duration_seconds','outcome','helped','observation1','observation2','observation3']
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow(fields)
        for row in rows:
            writer.writerow([safe_csv(row[field]) for field in fields])
        return Response('\ufeff' + output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=external-user-observations.csv'})

    @bp.route('/admin/smart-locker', methods=['GET', 'POST'])
    @admin_required
    def smart_locker():
        if request.method == 'POST':
            try:
                record_simulated_event(current_app.config['TELEMETRY_DATABASE'], current_app.config['DATABASE'],
                                       request.form.get('action'), request.form.get('notice_id'), utc_now())
            except ValueError as error:
                abort(400, description=str(error))
            flash('SIMULATED reading saved. No physical hardware was contacted.')
            return redirect(url_for('stage2.smart_locker'))
        with storage(current_app.config['TELEMETRY_DATABASE'], TELEMETRY_SCHEMA) as conn:
            events = conn.execute('SELECT * FROM locker_events ORDER BY id DESC LIMIT 30').fetchall()
        latest = events[0] if events else None
        elapsed = max(0, (utc_now() - datetime.fromisoformat(latest['open_since_at'])).total_seconds()) if latest and latest['open_since_at'] else 0
        with closing(sqlite3.connect(Path(current_app.config['DATABASE']).resolve().as_uri() + '?mode=ro', uri=True)) as main:
            main.row_factory = sqlite3.Row
            notices = main.execute("SELECT id,title,status FROM notices WHERE type=? ORDER BY id DESC", ('found',)).fetchall()
        stale_assignment = bool(latest and latest['notice_id'] is not None
                                and not any(notice['id'] == latest['notice_id'] for notice in notices))
        return render_template('smart_locker.html', events=events, latest=latest, elapsed=elapsed,
                               alert=bool(latest and latest['door_state'] == 'open' and elapsed >= 10),
                               notices=notices, stale_assignment=stale_assignment)

    app.register_blueprint(bp)
