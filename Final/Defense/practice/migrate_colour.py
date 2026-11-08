"""Practice drill only: add the optional 'colour' column to the PRACTICE copy's database.
Run from the practice Campus_Lost_Found folder:  python\\python.exe migrate_colour.py
Undo: delete the practice folder (SQLite cannot drop a column that has a CHECK constraint)."""
import sqlite3

with sqlite3.connect('data/campus.sqlite3') as c:
    c.execute("ALTER TABLE notices ADD COLUMN colour TEXT NOT NULL DEFAULT '' CHECK (length(colour) <= 40)")
    columns = [row[1] for row in c.execute('PRAGMA table_info(notices)')]
print('ok, notices columns:', ', '.join(columns))
