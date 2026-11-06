-- Campus Lost & Found: three related tables, SQLite schema version 1.
-- All authentication here is local demonstration authentication, not university SSO.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE
        CHECK (
            length(email) BETWEEN 17 AND 254
            AND email = lower(email)
            AND email = trim(email)
            AND substr(email, -16) = '@astanait.edu.kz'
            AND instr(email, '@') = length(email) - 15
            AND email NOT GLOB '*[^a-z0-9._@-]*'
        ),
    password_hash TEXT NOT NULL
        CHECK (substr(password_hash, 1, 7) = 'scrypt:'
               AND length(password_hash) BETWEEN 100 AND 512),
    role TEXT NOT NULL DEFAULT 'student'
        CHECK (role IN ('student', 'admin'))
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
        CHECK (length(name) BETWEEN 2 AND 60 AND name = trim(name))
);

CREATE TABLE notices (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL
        CHECK (length(title) BETWEEN 3 AND 120 AND title = trim(title)),
    description TEXT NOT NULL
        CHECK (length(description) BETWEEN 10 AND 1200
               AND description = trim(description)),
    location TEXT NOT NULL
        CHECK (length(location) BETWEEN 2 AND 100 AND location = trim(location)),
    event_date TEXT NOT NULL
        CHECK (
            length(event_date) = 10
            AND event_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(event_date, '+0 days') IS NOT NULL
            AND date(event_date, '+0 days') = event_date
            AND event_date BETWEEN '2020-01-01' AND '2100-12-31'
        ),
    type TEXT NOT NULL CHECK (type IN ('lost', 'found')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'returned')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        CHECK (
            length(created_at) = 20
            AND created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
            AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at, '+0 seconds') IS NOT NULL
            AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at, '+0 seconds') = created_at
        ),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        CHECK (
            length(updated_at) = 20
            AND updated_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
            AND strftime('%Y-%m-%dT%H:%M:%SZ', updated_at, '+0 seconds') IS NOT NULL
            AND strftime('%Y-%m-%dT%H:%M:%SZ', updated_at, '+0 seconds') = updated_at
        ),
    photo_filename TEXT
        CHECK (
            photo_filename IS NULL OR (
                length(photo_filename) BETWEEN 1 AND 200
                AND photo_filename NOT GLOB '*[^a-zA-Z0-9._-]*'
                AND instr(photo_filename, '..') = 0
            )
        ),
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CHECK (event_date <= substr(created_at, 1, 10)),
    CHECK (updated_at >= created_at)
);

CREATE INDEX idx_notices_category ON notices(category_id);
CREATE INDEX idx_notices_status ON notices(status);
CREATE INDEX idx_notices_owner ON notices(owner_id);

PRAGMA user_version = 1;
COMMIT;
