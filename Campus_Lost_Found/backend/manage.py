"""Command-line database management; run from any working directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

if __package__:
    from .db import (DEFAULT_DB_PATH, DatabaseStateError, backup_database,
                     init_database, query_database, restore_check,
                     seed_database, summary_database)
else:
    # Windows' embeddable Python can omit the script folder from sys.path.
    # Explicitly add this trusted module folder for direct-script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import (DEFAULT_DB_PATH, DatabaseStateError, backup_database,
                    init_database, query_database, restore_check,
                    seed_database, summary_database)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Manage the local Campus Lost & Found demo database.')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH,
                        help='Database file; default is PROJECT_ROOT/data/campus.sqlite3.')
    commands = parser.add_subparsers(dest='command', required=True)
    initialize = commands.add_parser('init', help='Initialize without replacing existing data.')
    initialize.add_argument('--seed', action='store_true', help='Seed 20 users, 10 categories and 120 notices; requires empty tables.')
    commands.add_parser('seed', help='Insert the fictional dataset into empty tables only.')
    commands.add_parser('summary', help='Show row counts, foreign keys and integrity checks.')
    backup = commands.add_parser('backup', help='Create and verify an SQLite online backup.')
    backup.add_argument('--output-dir', type=Path, default=None)
    restore = commands.add_parser('restore-check', help='Restore a backup to a new scratch file and verify it.')
    restore.add_argument('backup_file', type=Path)
    restore.add_argument('--restore-path', type=Path, default=None)
    query = commands.add_parser('query', help='Execute one read-only SELECT and print JSON.')
    query.add_argument('sql', help='Quote the complete SELECT statement.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = init_database(args.db)
            if args.seed:
                result = {'initialization': result, 'seed': seed_database(args.db)}
        elif args.command == 'seed':
            result = seed_database(args.db)
        elif args.command == 'summary':
            result = summary_database(args.db)
        elif args.command == 'backup':
            result = backup_database(args.db, args.output_dir)
        elif args.command == 'restore-check':
            result = restore_check(args.backup_file, args.restore_path)
        else:
            result = query_database(args.db, args.sql)
    except (DatabaseStateError, sqlite3.Error, OSError, ImportError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
