# Campus Lost & Found database

This backend is for an offline educational demonstration. Its seeded users and
notices are fictional. Local password authentication is **not university SSO**.

Place this directory at `PROJECT_ROOT/backend`. All default paths are calculated
from the script location, so the project can be moved to another folder or laptop.
The normal database is `PROJECT_ROOT/data/campus.sqlite3`; backups go into
`PROJECT_ROOT/backups`. Audit records are handled by the application as JSONL and
are not a fourth database table.

## Requirements and commands

Python with Werkzeug is required for password hashing and seeding. The containing
application supplies Flask and Werkzeug. The delivered Windows package includes
Python at `python/python.exe`; from the project root:

```text
.\python\python.exe -m backend.manage summary
.\python\python.exe -m backend.manage query "SELECT c.name, COUNT(n.id) AS notices FROM categories c LEFT JOIN notices n ON n.category_id=c.id GROUP BY c.id,c.name ORDER BY c.name"
.\python\python.exe -m backend.manage backup
.\python\python.exe -m unittest discover -s backend -p test_backend.py -v
```

To verify the latest backup from PowerShell:

```powershell
$latestBackup = Get-ChildItem -LiteralPath backups -Filter '*.sqlite3' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\python\python.exe -m backend.manage restore-check $latestBackup.FullName
```

Initialization and seeding are for a new empty database. An alternate database
goes **before** the subcommand:

```text
.\python\python.exe -m backend.manage --db data/other.sqlite3 init --seed
```

For a standard Python installation with the project's dependencies installed,
`python -m backend.manage` is equivalent. Do not reseed an already populated
delivered database.

`init` creates an empty schema or validates the existing schema without deleting
data. `init --seed` and `seed` refuse to seed a database containing any records.
No reset, destructive restore, or deletion command is provided. `restore-check`
copies a backup into a **new scratch database**, validates integrity, foreign keys
and row counts, and never overwrites the live database. `query` permits read-only
SELECT statements and denies modifications and attached databases.

## Seeded data and login accounts

There are exactly three entity tables: **20 users**, **10 categories**, and
**120 notices**. Each category has 12 notices. There are 60 lost and 60 found
notices; 96 are open and 24 are returned. Nineteen users are students and one is an
administrator. The fictional event dates range from 30 August to 10 October 2026.
All sample descriptions explicitly identify themselves as fictional demo notices.

All 20 local demo accounts use the public demonstration password
`CampusDemo!2026`. It is a documented test credential, not a private secret.

| Email | Role |
| --- | --- |
| zhanzhol.demo@astanait.edu.kz | student |
| daniil.demo@astanait.edu.kz | student |
| daulet.demo@astanait.edu.kz | student |
| admin.demo@astanait.edu.kz | admin |
| student01.demo@astanait.edu.kz through student16.demo@astanait.edu.kz | student |

Each password is stored as an independently salted Werkzeug scrypt hash. There is
no plaintext password column. An email domain check constrains database values;
it does not verify ownership of a real university identity. The app must continue
to label these as local demo accounts.

## Schema

`schema.sql` is the complete authoritative DDL. `PRAGMA user_version` is 1.
Foreign-key enforcement is enabled on every helper-created connection.

| Table | Fields |
| --- | --- |
| users | id PK, email UNIQUE, password_hash, role |
| categories | id PK, name UNIQUE (case-insensitive) |
| notices | id PK, owner_id FK, category_id FK, title, description, location, event_date, type, status, created_at, updated_at, photo_filename NULL allowed |

`notices.owner_id` references `users.id`; `notices.category_id` references
`categories.id`. Both relationships use `ON DELETE RESTRICT ON UPDATE RESTRICT`.
No automatic cascading deletion is used. Separate indexes cover owner, category,
and status. Photo uploads are disabled in this submission. The nullable
`photo_filename` field is reserved for a possible later implementation and is
NULL in all 120 seeded notices; it does not claim an implemented file store.

Validation rules include:

- Lowercase email ending in exactly `@astanait.edu.kz`, one `@`, and allowed ASCII
  email characters. Values are unique. This is a local data rule, not SSO.
- Roles limited to `student` or `admin`; password hash has the scrypt format prefix.
- Category names 2–60 characters; titles 3–120; descriptions 10–1200; locations
  2–100. These fields may not have leading/trailing spaces.
- Notice type is `lost` or `found`; status is `open` or `returned`.
- `event_date` is a real ISO calendar date between 2020 and 2100 and cannot be
  after the notice creation date. Impossible dates such as 30 February fail.
- Creation/update timestamps use UTC `YYYY-MM-DDTHH:MM:SSZ`. Update time cannot
  precede creation time. The app should set `updated_at` on an edit.
- A non-null photo filename contains only ASCII letters, digits, periods,
  underscores or hyphens and no `..`; it has no directory separators.

## Python API

```text
get_connection(path=DEFAULT_DB_PATH, *, read_only=False) -> sqlite3.Connection
init_database(path=DEFAULT_DB_PATH) -> dict
seed_database(path=DEFAULT_DB_PATH) -> dict
summary_database(path=DEFAULT_DB_PATH) -> dict
backup_database(path=DEFAULT_DB_PATH, backup_dir=None) -> dict
restore_check(backup_path, restore_path=None) -> dict
query_database(path, sql) -> dict
```

Connections use `sqlite3.Row`, `PRAGMA foreign_keys=ON` and a 5000 ms busy timeout.
The caller must close a returned connection. Use parameters for values in
application SQL. `summary_database` returns counts, role/type/status/category
distributions, an integrity result and foreign-key violations. Backups use
`sqlite3.Connection.backup`; an adjacent JSON file records verified counts and
integrity, without plaintext credentials. This is a database backup; it does not
include the separate application audit JSONL file. `DatabaseStateError` identifies a
refused initialization, seed, or restore; normal constraint failures use
`sqlite3.IntegrityError`.

## Tests

The standard-library unittest suite uses temporary databases. It checks dataset
counts, independent password hashes, FK enforcement and deletion restrictions,
invalid inputs, transaction rollback, read-only inspection, non-destructive
initialization/seeding, and a backup/restore that recovers 120 rows while leaving
an intentionally modified live database at 119 rows. These backend checks do not
claim that the complete application has passed its UI, load, or user tests.
