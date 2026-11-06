"""Full data archives. SQLite snapshots plus private photos; never session keys.

Pause changes in the app while making an archive so the separate databases and
photo directory describe the same moment. SQLite files use the online backup API.
Recovery checks always create a new folder and never replace the live project.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import sqlite3
import stat
import tempfile
import zipfile

from backend.db import get_connection, summary_database

ROOT = Path(__file__).resolve().parent
DATABASE_NAMES = ('data/campus.sqlite3', 'data/research.sqlite3', 'data/telemetry.sqlite3')
FORMAT = 'campus-full-backup-v1'
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024


class BackupError(RuntimeError):
    """The archive or destination cannot be safely backed up or restored."""


def _stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + secrets.token_hex(4)


def _digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _database_info(path, main=False):
    if main:
        summary_database(path)  # Preserve the core three-table/version contract.
    with closing(get_connection(path, read_only=True)) as conn:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {name: conn.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
                  for name in tables}
        integrity = [row[0] for row in conn.execute('PRAGMA integrity_check')]
        violations = [list(row) for row in conn.execute('PRAGMA foreign_key_check')]
        if integrity != ['ok'] or violations:
            raise BackupError('A database failed its integrity or foreign-key check.')
        return {'counts': counts, 'schema_version': conn.execute('PRAGMA user_version').fetchone()[0],
                'integrity_check': 'ok', 'foreign_key_violations': []}


def _allowed_path(name):
    if not isinstance(name, str) or '\\' in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('.', '..') or ':' in part for part in path.parts):
        return False
    return name in DATABASE_NAMES or bool(re.fullmatch(r'data/uploads/[0-9a-f]{48}\.(?:jpg|png)', name))


def _check_photo_references(directory, files):
    with closing(get_connection(Path(directory) / 'data/campus.sqlite3', read_only=True)) as conn:
        for row in conn.execute('SELECT DISTINCT photo_filename FROM notices WHERE photo_filename IS NOT NULL'):
            name = 'data/uploads/' + row[0]
            if not _allowed_path(name) or name not in files:
                raise BackupError('A notice photograph is missing from the archive. Pause changes and retry.')


def create_full_backup(project_root=ROOT, backup_dir=None):
    root = Path(project_root).resolve()
    destination = Path(backup_dir or root / 'backups').resolve()
    if not (root / DATABASE_NAMES[0]).is_file():
        raise BackupError('The main database is missing.')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='full-backup-', dir=destination) as staging_name:
        staging = Path(staging_name)
        files, databases = {}, {}
        for name in DATABASE_NAMES:
            source = root / name
            if not source.exists():
                continue
            if source.is_symlink() or not source.is_file():
                raise BackupError('Database paths must be regular files.')
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with closing(get_connection(source, read_only=True)) as original:
                with closing(sqlite3.connect(target)) as snapshot:
                    original.backup(snapshot)
            databases[name] = _database_info(target, main=name == DATABASE_NAMES[0])
            files[name] = {'sha256': _digest(target), 'size': target.stat().st_size}
        uploads = root / 'data/uploads'
        if uploads.is_symlink():
            raise BackupError('The photo directory must not be a symbolic link.')
        if uploads.exists():
            for photo in sorted(uploads.iterdir()):
                name = 'data/uploads/' + photo.name
                if not _allowed_path(name) or photo.is_symlink() or not photo.is_file():
                    raise BackupError('The private photo directory contains an unexpected path.')
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(photo, target)
                files[name] = {'sha256': _digest(target), 'size': target.stat().st_size}
        _check_photo_references(staging, files)
        if sum(entry['size'] for entry in files.values()) > MAX_ARCHIVE_BYTES or len(files) > 9999:
            raise BackupError('This teaching archive exceeds the supported 512 MB / 9,999-file limit.')
        manifest = {'format': FORMAT, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                    'files': files, 'databases': databases}
        manifest_bytes = (json.dumps(manifest, indent=2) + '\n').encode('utf-8')
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise BackupError('Manifest is too large.')
        archive = destination / ('campus_full_' + _stamp() + '.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in sorted(files):
                bundle.write(staging / name, name)
            bundle.writestr('manifest.json', manifest_bytes)
        return {'operation': 'full_data_backup', 'backup_path': str(archive),
                'archive_sha256': _digest(archive), 'file_count': len(files), 'databases': databases,
                'excluded': ['runtime/session.key'],
                'consistency_note': 'Separate SQLite snapshots and photos; pause app changes during backup.'}


def restore_full_check(backup_path, scratch_path=None):
    archive = Path(backup_path).resolve()
    destination = Path(scratch_path or ROOT / 'data/restore_checks' / ('full_' + _stamp())).resolve()
    if destination.exists():
        raise BackupError('Restore-check requires a new scratch folder; existing paths are never replaced.')
    try:
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > 10000 or len(names) != len(set(names)) or names.count('manifest.json') != 1:
                raise BackupError('Archive has duplicate, missing or excessive entries.')
            if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES + MAX_MANIFEST_BYTES:
                raise BackupError('Archive expands beyond the supported size limit.')
            for entry in entries:
                if (entry.filename != 'manifest.json' and not _allowed_path(entry.filename)) or entry.is_dir():
                    raise BackupError('Archive contains an unsafe or unexpected path.')
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    raise BackupError('Symbolic links and encrypted entries are unsupported.')
            if bundle.getinfo('manifest.json').file_size > MAX_MANIFEST_BYTES:
                raise BackupError('Manifest is too large.')
            manifest_bytes = bundle.read('manifest.json')
            manifest = json.loads(manifest_bytes)
            if not isinstance(manifest, dict) or manifest.get('format') != FORMAT:
                raise BackupError('Unsupported backup manifest.')
            files, databases = manifest.get('files'), manifest.get('databases')
            if not isinstance(files, dict) or set(files) != set(names) - {'manifest.json'}:
                raise BackupError('Manifest file list does not match the archive.')
            if (not isinstance(databases, dict) or DATABASE_NAMES[0] not in databases
                    or set(databases) != {name for name in files if name in DATABASE_NAMES}):
                raise BackupError('Manifest database list does not match the archive.')
            for name, entry in files.items():
                if (not isinstance(entry, dict) or type(entry.get('size')) is not int
                        or entry['size'] != bundle.getinfo(name).file_size
                        or not re.fullmatch(r'[a-f0-9]{64}', str(entry.get('sha256', '')))):
                    raise BackupError('Invalid manifest file metadata.')
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='restore-check-', dir=destination.parent) as stage_name:
                staging = Path(stage_name).resolve()
                for name, entry in files.items():
                    target = (staging / name).resolve()
                    if not target.is_relative_to(staging):
                        raise BackupError('Archive path escapes the scratch folder.')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(name) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    if _digest(target) != entry['sha256']:
                        raise BackupError('Archive SHA-256 verification failed.')
                checked = {name: _database_info(staging / name, main=name == DATABASE_NAMES[0]) for name in databases}
                if checked != databases:
                    raise BackupError('Database counts or integrity metadata do not match the manifest.')
                _check_photo_references(staging, files)
                (staging / 'manifest.json').write_bytes(manifest_bytes)
                # The exclusive directory creation protects existing destinations,
                # including one created after the initial check.
                destination.mkdir(exist_ok=False)
                for child in staging.iterdir():
                    shutil.move(str(child), str(destination / child.name))
        return {'operation': 'full_restore_check', 'backup_path': str(archive),
                'restored_path': str(destination), 'success': True, 'databases': checked,
                'verified_files': len(files), 'archive_sha256': _digest(archive)}
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeError, sqlite3.Error, KeyError, TypeError, OSError) as error:
        raise BackupError('Full restore-check failed: ' + str(error)) from error
