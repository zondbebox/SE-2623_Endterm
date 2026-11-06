"""Portable SQLite helpers for an explicitly fictional, offline campus demo.

Put this directory at PROJECT_ROOT/backend.  No helper overwrites an existing
database's records.  Callers must close connections returned by get_connection.
"""
from __future__ import annotations

from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / 'data' / 'campus.sqlite3'
DEFAULT_BACKUP_DIR = PROJECT_ROOT / 'backups'
SCHEMA_PATH = Path(__file__).with_name('schema.sql')
SCHEMA_VERSION = 1
DEMO_PASSWORD = 'CampusDemo!2026'  # Public demo credential, intentionally documented.
EXPECTED_COUNTS = {'users': 20, 'categories': 10, 'notices': 120}
TABLE_COLUMNS = {
    'users': ('id', 'email', 'password_hash', 'role'),
    'categories': ('id', 'name'),
    'notices': ('id', 'owner_id', 'category_id', 'title', 'description', 'location',
                'event_date', 'type', 'status', 'created_at', 'updated_at', 'photo_filename'),
}

CATEGORIES = (
    (1, 'Electronics'), (2, 'Keys and Access Cards'), (3, 'Bags'),
    (4, 'Books and Stationery'), (5, 'Clothing'), (6, 'Drinkware'),
    (7, 'Sports Equipment'), (8, 'Documents'), (9, 'Accessories'), (10, 'Other'),
)
ITEMS = {
    1: (('wireless earbud case', 'The case has a small star sticker.'),
        ('USB flash drive', 'A short fabric loop is attached.'),
        ('phone charging cable', 'The cable has a reusable strap.'),
        ('wireless mouse', 'The underside has a worn label.'),
        ('power bank', 'A plain protective sleeve is fitted.'),
        ('calculator', 'The cover has a small corner scratch.')),
    2: (('key ring', 'Two unlabelled keys are attached.'),
        ('card holder', 'The holder has a blank paper insert.'),
        ('lanyard', 'The lanyard has a simple metal clip.'),
        ('locker key', 'A round plastic tag is attached.'),
        ('access-card sleeve', 'The sleeve has no visible name.'),
        ('key pouch', 'A small zipper closes the pouch.')),
    3: (('backpack', 'A reflective strip is on the front pocket.'),
        ('laptop sleeve', 'The sleeve closes with a zipper.'),
        ('tote bag', 'The bag has a simple leaf illustration.'),
        ('drawstring bag', 'One cord has a small knot.'),
        ('pencil pouch', 'The pouch has a fabric pull tab.'),
        ('sports bag', 'A plain luggage tag is attached.')),
    4: (('notebook', 'The first page has no personal details.'),
        ('folder', 'The folder contains blank worksheets.'),
        ('pencil case', 'A ruler is visible through the mesh pocket.'),
        ('textbook cover', 'There is a small label on the spine.'),
        ('ring binder', 'Three blank dividers are inside.'),
        ('sketchbook', 'An elastic band holds it closed.')),
    5: (('hoodie', 'The hoodie has a plain front pocket.'),
        ('scarf', 'A narrow stripe runs along the edge.'),
        ('cap', 'The adjustable strap has a metal buckle.'),
        ('gloves', 'The pair has knitted cuffs.'),
        ('light jacket', 'The jacket has two zipped pockets.'),
        ('sports shirt', 'There is a small geometric mark on the sleeve.')),
    6: (('water bottle', 'The lid has a short carrying loop.'),
        ('travel mug', 'The lid has a sliding cover.'),
        ('thermos', 'The lid also works as a small cup.'),
        ('reusable cup', 'A silicone band is around the middle.'),
        ('bottle sleeve', 'A small clip is attached to the top.'),
        ('lunch flask', 'A foldable handle is fitted to the lid.')),
    7: (('resistance band', 'The band is folded in a cloth pouch.'),
        ('table-tennis case', 'The case has a round zipper pull.'),
        ('swimming goggles case', 'A small vent is on the side.'),
        ('wrist support', 'The fastening strip has no name label.'),
        ('skipping-rope handle', 'The grip has a dotted pattern.'),
        ('sports towel', 'One corner has a hanging loop.')),
    8: (('document wallet', 'Only blank example pages are inside.'),
        ('paper envelope', 'The envelope contains unlabelled sheets.'),
        ('certificate folder', 'No real certificate is included in this demo.'),
        ('plastic document sleeve', 'The sleeve has a snap closure.'),
        ('project folder', 'The cover has a plain rectangular sticker.'),
        ('receipt pouch', 'The pouch contains no readable personal information.')),
    9: (('umbrella', 'The handle has a short wrist strap.'),
        ('glasses case', 'The case has a soft lining.'),
        ('watch strap', 'The buckle has a small scratch.'),
        ('hair clip', 'The clip has a simple curved shape.'),
        ('badge holder', 'A blank demo badge is inside.'),
        ('coin pouch', 'The pouch has a small side loop.')),
    10: (('lunch box', 'The lid has two side clips.'),
         ('reusable shopping bag', 'The bag folds into a small pocket.'),
         ('desk organiser', 'The organiser has three compartments.'),
         ('cable pouch', 'Two elastic loops are inside.'),
         ('small storage case', 'The case has a sliding latch.'),
         ('reusable food container', 'The lid has a plain circular mark.')),
}
LOCATIONS = ('Library study area', 'Block C lobby', 'Main entrance',
             'Computer lab corridor', 'Cafeteria seating area', 'Sports hall entrance',
             'Lecture room corridor', 'Student lounge', 'Coworking area',
             'Ground floor lockers', 'Bus stop near campus', 'Reading room desk')
COLOURS = ('Blue', 'Black', 'Green', 'Grey', 'Red', 'Navy')


class DatabaseStateError(RuntimeError):
    """A requested operation would replace data or use an unexpected schema."""


def _path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def get_connection(path: str | Path = DEFAULT_DB_PATH, *, read_only: bool = False) -> sqlite3.Connection:
    """Return a configured connection. The caller owns it and must close it."""
    db_path = _path(path)
    if read_only:
        connection = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True, timeout=5)
    else:
        connection = sqlite3.connect(str(db_path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 5000')
    if read_only:
        connection.execute('PRAGMA query_only = ON')
    return connection


def _validate_schema(connection: sqlite3.Connection) -> None:
    tables = {row['name'] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    if tables != set(TABLE_COLUMNS):
        raise DatabaseStateError(f'Unexpected database tables: {sorted(tables)}')
    if connection.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise DatabaseStateError('Unsupported database schema version.')
    for table, expected in TABLE_COLUMNS.items():
        actual = tuple(row['name'] for row in connection.execute(f'PRAGMA table_info({table})'))
        if actual != expected:
            raise DatabaseStateError(f'Unexpected columns in {table}: {actual}')


def init_database(path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Create the schema in an empty database, or validate an existing one.

    Existing tables and records are never dropped, cleared, or migrated.
    """
    db_path = _path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_connection(db_path)) as connection:
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
        if existing:
            _validate_schema(connection)
            return {'database': str(db_path), 'created': False, 'schema_version': SCHEMA_VERSION}
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        _validate_schema(connection)
    return {'database': str(db_path), 'created': True, 'schema_version': SCHEMA_VERSION}


def _seed_notices() -> list[tuple[Any, ...]]:
    result = []
    anchor = date(2026, 10, 10)
    for index in range(120):
        category_id = index % 10 + 1
        round_number = index // 10
        item, detail = ITEMS[category_id][round_number % 6]
        colour = COLOURS[(category_id + round_number // 6) % len(COLOURS)]
        title = f'{colour} {item}'
        location = LOCATIONS[(index * 5 + round_number) % len(LOCATIONS)]
        notice_type = 'lost' if (category_id + round_number) % 2 else 'found'
        status = 'returned' if index % 5 == 0 else 'open'
        event_date = anchor - timedelta(days=index % 42)
        created_at = f'{event_date + timedelta(days=1)}T09:00:00Z'
        updated_at = (f'{event_date + timedelta(days=2)}T15:30:00Z'
                      if status == 'returned' else created_at)
        action = (f'I last saw this {item} near {location}.' if notice_type == 'lost'
                  else f'This {item} was found near {location}.')
        description = (f'Fictional demo notice. {action} {detail} '
                       'Contact the author and describe a distinguishing feature before arranging a handover.')
        if status == 'returned':
            description += ' This fictional example is marked as returned.'
        # IDs 1–3 and 5–20 are students; ID 4 is the demonstration administrator.
        student_ids = (1, 2, 3, *range(5, 21))
        result.append((index + 1, student_ids[index % len(student_ids)], category_id,
                       title, description, location, event_date.isoformat(), notice_type,
                       status, created_at, updated_at, None))
    return result


def seed_database(path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Populate an initialized, empty schema with fictional examples exactly once."""
    from werkzeug.security import generate_password_hash

    db_path = _path(path)
    init_database(db_path)
    emails = ['zhanzhol.demo@astanait.edu.kz', 'daniil.demo@astanait.edu.kz',
              'daulet.demo@astanait.edu.kz', 'admin.demo@astanait.edu.kz']
    emails.extend(f'student{number:02d}.demo@astanait.edu.kz' for number in range(1, 17))
    with closing(get_connection(db_path)) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            if any(connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                   for table in TABLE_COLUMNS):
                raise DatabaseStateError('Seed refused: the database already contains data.')
            users = [(index, email, generate_password_hash(DEMO_PASSWORD, method='scrypt'),
                      'admin' if index == 4 else 'student')
                     for index, email in enumerate(emails, start=1)]
            connection.executemany(
                'INSERT INTO users(id,email,password_hash,role) VALUES (?,?,?,?)', users)
            connection.executemany('INSERT INTO categories(id,name) VALUES (?,?)', CATEGORIES)
            connection.executemany(
                'INSERT INTO notices(id,owner_id,category_id,title,description,location,'
                'event_date,type,status,created_at,updated_at,photo_filename) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', _seed_notices())
    return summary_database(db_path)


def _summary(connection: sqlite3.Connection) -> dict[str, Any]:
    _validate_schema(connection)
    return {
        'schema_version': connection.execute('PRAGMA user_version').fetchone()[0],
        'counts': {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                   for table in TABLE_COLUMNS},
        'roles': {row[0]: row[1] for row in connection.execute(
            'SELECT role,COUNT(*) FROM users GROUP BY role ORDER BY role')},
        'notice_types': {row[0]: row[1] for row in connection.execute(
            'SELECT type,COUNT(*) FROM notices GROUP BY type ORDER BY type')},
        'notice_statuses': {row[0]: row[1] for row in connection.execute(
            'SELECT status,COUNT(*) FROM notices GROUP BY status ORDER BY status')},
        'notices_by_category': [dict(row) for row in connection.execute(
            'SELECT c.id,c.name,COUNT(n.id) AS notice_count FROM categories c '
            'LEFT JOIN notices n ON n.category_id=c.id GROUP BY c.id,c.name ORDER BY c.id')],
        'integrity_check': connection.execute('PRAGMA integrity_check').fetchone()[0],
        'foreign_key_violations': [list(row) for row in connection.execute('PRAGMA foreign_key_check')],
        'foreign_keys_enabled': bool(connection.execute('PRAGMA foreign_keys').fetchone()[0]),
    }


def summary_database(path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    db_path = _path(path)
    with closing(get_connection(db_path, read_only=True)) as connection:
        return {'database': str(db_path), **_summary(connection)}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def backup_database(path: str | Path = DEFAULT_DB_PATH,
                    backup_dir: str | Path | None = None) -> dict[str, Any]:
    """Use SQLite's online backup API and write counts/integrity metadata."""
    db_path = _path(path)
    destination_dir = _path(backup_dir or DEFAULT_BACKUP_DIR)
    # Validate the source before creating output artifacts.
    with closing(get_connection(db_path, read_only=True)) as source:
        _validate_schema(source)
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / f'campus_{_stamp()}.sqlite3'
        if target.exists() or target == db_path:
            raise DatabaseStateError('Backup destination already exists or is the live database.')
        with closing(get_connection(target)) as destination:
            source.backup(destination)
            checked = _summary(destination)
        if checked['integrity_check'] != 'ok' or checked['foreign_key_violations']:
            raise DatabaseStateError('Backup verification failed.')
    metadata_path = target.with_suffix('.json')
    metadata = {
        'operation': 'sqlite_online_backup',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source_database': str(db_path), 'backup_path': str(target),
        'metadata_path': str(metadata_path), **checked,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return metadata


def restore_check(backup_path: str | Path,
                  restore_path: str | Path | None = None) -> dict[str, Any]:
    """Restore into a new scratch file, never replace the live database."""
    source_path = _path(backup_path)
    target = _path(restore_path or (PROJECT_ROOT / 'data' / 'restore_checks' /
                                    f'restored_{_stamp()}.sqlite3'))
    if target.exists() or target in (source_path, DEFAULT_DB_PATH.resolve()):
        raise DatabaseStateError('Restore-check requires a new scratch path, not an existing/live database.')
    with closing(get_connection(source_path, read_only=True)) as source:
        original = _summary(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(get_connection(target)) as destination:
            source.backup(destination)
            restored = _summary(destination)
    success = (original['counts'] == restored['counts']
               and restored['integrity_check'] == 'ok'
               and not restored['foreign_key_violations'])
    if not success:
        raise DatabaseStateError('Restored database failed integrity, relationship, or row-count checks.')
    return {'operation': 'restore_check', 'backup_path': str(source_path),
            'restored_path': str(target), 'success': True, **restored}


def query_database(path: str | Path, sql: str) -> dict[str, Any]:
    """Execute one read-only SELECT (including CTEs) for local inspection."""
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
               sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

    def authorize(action: int, arg1: str | None, arg2: str | None,
                  database: str | None, trigger: str | None) -> int:
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    with closing(get_connection(path, read_only=True)) as connection:
        connection.set_authorizer(authorize)
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise DatabaseStateError('The query must return rows without changing data.')
        return {'columns': [item[0] for item in cursor.description],
                'rows': [list(row) for row in cursor.fetchall()]}
