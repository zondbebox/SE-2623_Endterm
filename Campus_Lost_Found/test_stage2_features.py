"""Behavioural endterm tests. All observations and telemetry use temporary files."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
if sys.platform == 'win32':
    sys.path.insert(0, str(ROOT / 'vendor'))
from app import create_app
from backend.db import init_database, seed_database
from stage2_features import register_blueprints


class Stage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='stage2-tests-', dir=ROOT)
        cls.directory = Path(cls.temp.name)
        cls.seed = cls.directory / 'seed.sqlite3'
        init_database(cls.seed)
        seed_database(cls.seed)

    @classmethod
    def tearDownClass(cls):
        if cls.directory.resolve().is_relative_to(ROOT.resolve()):
            cls.temp.cleanup()

    def setUp(self):
        self.folder = self.directory / self._testMethodName
        self.folder.mkdir()
        self.main = self.folder / 'campus.sqlite3'
        with closing(sqlite3.connect(self.seed)) as source, closing(sqlite3.connect(self.main)) as dest:
            source.backup(dest)
        self.now = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'stage2-test',
            'DATABASE': self.main, 'AUDIT_PATH': self.folder / 'audit.jsonl',
            'RESEARCH_DATABASE': self.folder / 'research.sqlite3',
            'TELEMETRY_DATABASE': self.folder / 'telemetry.sqlite3',
            'STAGE2_CLOCK': lambda: self.now})
        if 'stage2' not in self.app.blueprints:
            register_blueprints(self.app)
        self.client = self.app.test_client()
        with closing(sqlite3.connect(self.main)) as conn:
            self.admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()[0]
            self.student = conn.execute("SELECT id FROM users WHERE role='student' LIMIT 1").fetchone()[0]
            self.notice = conn.execute("SELECT id FROM notices WHERE type='found' LIMIT 1").fetchone()[0]

    def auth(self, user=None):
        with self.client.session_transaction() as state:
            state['user_id'] = self.admin if user is None else user
            state['csrf'] = 'test-csrf'

    def post(self, url='/admin/research', **data):
        return self.client.post(url, data={'csrf': 'test-csrf', **data})

    def rows(self, name='research', table='research_sessions'):
        with closing(sqlite3.connect(self.folder / (name + '.sqlite3'))) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute('SELECT * FROM ' + table + ' ORDER BY id')]

    def start(self, participant='T01', task='publish', **extra):
        return self.post(action='start', participant=participant, task=task,
                         device='Laptop / Chrome', external_consent='yes', **extra)

    def finish(self, session_id, **extra):
        return self.post(action='finish', session_id=session_id, outcome='success',
                         helped='no', observation1='', observation2='', observation3='', **extra)

    def test_get_and_post_permissions(self):
        for url in ['/admin/research', '/admin/smart-locker', '/admin/research.csv']:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.auth(self.student)
        for url in ['/admin/research', '/admin/smart-locker', '/admin/research.csv']:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.post(action='start').status_code, 403)
        self.assertEqual(self.post('/admin/smart-locker', action='open').status_code, 403)

    def test_admin_forms_reject_missing_csrf(self):
        self.auth()
        for url in ['/admin/research', '/admin/smart-locker']:
            self.assertEqual(self.client.post(url, data={'action': 'start'}).status_code, 400)

    def test_empty_research_has_no_invented_observations(self):
        self.auth()
        response = self.client.get('/admin/research')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pending', response.data)
        self.assertEqual(self.rows(), [])

    def test_timer_uses_server_duration_and_finishes_once(self):
        self.auth()
        self.assertEqual(self.start().status_code, 302)
        row = self.rows()[0]
        self.assertIsNone(row['finished_at'])
        self.now += timedelta(seconds=42.25)
        self.assertEqual(self.finish(row['id']).status_code, 302)
        self.assertAlmostEqual(self.rows()[0]['duration_seconds'], 42.25)
        self.now += timedelta(seconds=100)
        self.assertEqual(self.finish(row['id']).status_code, 409)
        self.assertAlmostEqual(self.rows()[0]['duration_seconds'], 42.25)

    def test_consent_code_device_and_task_are_required(self):
        self.auth()
        base = dict(action='start', participant='T01', task='publish', device='Laptop', external_consent='yes')
        for field, value in [('external_consent',''), ('participant','Name'), ('participant','T00'), ('device',''), ('task','fake')]:
            self.assertEqual(self.post(**{**base, field: value}).status_code, 400)
        self.assertEqual(self.rows(), [])

    def test_duplicate_participant_task_cannot_inflate_results(self):
        self.auth()
        self.assertEqual(self.start().status_code, 302)
        self.assertEqual(self.start().status_code, 409)
        self.assertEqual(len(self.rows()), 1)

    def test_five_people_both_tasks_required_and_exact_boundaries(self):
        self.auth()
        for index in range(1, 6):
            for task, seconds in [('publish',120), ('find',60)]:
                self.assertEqual(self.start('T%02d' % index, task).status_code, 302)
                self.now += timedelta(seconds=seconds + (1 if index == 5 else 0))
                if index == 5 and task == 'find':
                    self.assertIn(b'Pending', self.client.get('/admin/research').data)
                self.assertEqual(self.finish(self.rows()[-1]['id']).status_code, 302)
        response = self.client.get('/admin/research')
        self.assertIn(b'4 / 5', response.data)
        self.assertIn(b'Met', response.data)
        self.assertEqual(self.start('T06').status_code, 409)

    def test_csv_export_neutralises_spreadsheet_formulas(self):
        self.auth()
        self.assertEqual(self.post(action='start', participant='T01', task='find', device='=1+1', external_consent='yes').status_code, 302)
        self.now += timedelta(seconds=5)
        self.post(action='finish', session_id=self.rows()[0]['id'], outcome='failure', helped='yes',
                  observation1='@SUM(1,2)', observation2='-danger', observation3='+danger')
        response = self.client.get('/admin/research.csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"'=1+1", response.data)
        self.assertIn(b"'@SUM", response.data)
        self.assertIn(b"'-danger", response.data)

    def test_observation_entry_does_not_extend_stopped_task_time(self):
        self.auth()
        self.assertEqual(self.start().status_code, 302)
        self.now += timedelta(seconds=25)
        self.assertEqual(self.post(action='stop', session_id=self.rows()[0]['id']).status_code, 302)
        self.now += timedelta(seconds=90)
        self.assertEqual(self.finish(self.rows()[0]['id']).status_code, 302)
        self.assertAlmostEqual(self.rows()[0]['duration_seconds'], 25)

    def test_invalid_notice_is_rejected_without_event(self):
        self.auth()
        self.assertEqual(self.post('/admin/smart-locker', action='open', notice_id='999999').status_code, 400)
        self.assertEqual(self.rows('telemetry', 'locker_events'), [])

    def test_locker_open_alert_close_and_heartbeat_preserve_state(self):
        self.auth()
        self.assertEqual(self.post('/admin/smart-locker', action='open', notice_id=self.notice).status_code, 302)
        self.assertNotIn(b'OPEN TOO LONG', self.client.get('/admin/smart-locker').data)
        self.now += timedelta(seconds=10)
        self.assertIn(b'OPEN TOO LONG', self.client.get('/admin/smart-locker').data)
        self.assertEqual(self.post('/admin/smart-locker', action='heartbeat', notice_id=self.notice).status_code, 302)
        self.assertIn(b'OPEN TOO LONG', self.client.get('/admin/smart-locker').data)
        self.assertEqual(self.post('/admin/smart-locker', action='closed', notice_id=self.notice).status_code, 302)
        page = self.client.get('/admin/smart-locker').data
        self.assertNotIn(b'OPEN TOO LONG', page)
        self.assertIn(b'SIMULATED', page)
        self.assertEqual([row['door_state'] for row in self.rows('telemetry','locker_events')], ['open','open','closed'])

    def test_new_features_do_not_mutate_main_database(self):
        self.auth()
        before = hashlib.sha256(self.main.read_bytes()).hexdigest()
        self.client.get('/admin/research')
        self.start()
        self.post('/admin/smart-locker', action='open', notice_id=self.notice)
        self.assertEqual(before, hashlib.sha256(self.main.read_bytes()).hexdigest())

    def test_unavailable_open_locker_assignment_can_be_reset_without_erasing_history(self):
        self.auth()
        for change in ('deleted', 'changed_to_lost'):
            with self.subTest(change=change):
                with closing(sqlite3.connect(self.main)) as conn:
                    selected = conn.execute("SELECT id FROM notices WHERE type='found' ORDER BY id LIMIT 1").fetchone()[0]
                self.assertEqual(self.post('/admin/smart-locker', action='open', notice_id=selected).status_code, 302)
                self.assertEqual(self.post('/admin/smart-locker', action='reset').status_code, 400)
                if change == 'deleted':
                    self.assertEqual(self.post(f'/notice/{selected}/remove').status_code, 302)
                else:
                    with closing(sqlite3.connect(self.main)) as conn:
                        with conn:
                            conn.execute("UPDATE notices SET type='lost' WHERE id=?", (selected,))
                original_events = self.rows('telemetry', 'locker_events')
                main_hash = hashlib.sha256(self.main.read_bytes()).hexdigest()
                self.assertEqual(self.post('/admin/smart-locker', action='closed', notice_id=selected).status_code, 400)
                self.assertIn(b'name="action" value="reset"', self.client.get('/admin/smart-locker').data)
                self.assertEqual(self.post('/admin/smart-locker', action='reset').status_code, 302)
                events = self.rows('telemetry', 'locker_events')
                self.assertEqual(events[:-1], original_events)
                self.assertEqual((events[-1]['door_state'], events[-1]['notice_id'], events[-1]['source']),
                                 ('closed', None, 'SIMULATED'))
                self.assertEqual(self.post('/admin/smart-locker', action='heartbeat').status_code, 302)
                self.assertNotIn(b'name="action" value="reset"', self.client.get('/admin/smart-locker').data)
                self.assertEqual(main_hash, hashlib.sha256(self.main.read_bytes()).hexdigest())

    def test_cli_heartbeat_preserves_current_simulated_state(self):
        self.auth()
        self.assertEqual(self.post('/admin/smart-locker', action='open', notice_id=self.notice).status_code, 302)
        script = ROOT / 'simulate_locker.py'
        self.assertTrue(script.is_file(), 'The local heartbeat simulator is missing')
        result = subprocess.run([sys.executable, '-B', str(script), '--database', str(self.main),
            '--telemetry', str(self.folder / 'telemetry.sqlite3'), '--samples', '1', '--interval', '0'],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        event = self.rows('telemetry','locker_events')[-1]
        self.assertEqual((event['door_state'], event['event_type'], event['source']), ('open','heartbeat','SIMULATED'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
