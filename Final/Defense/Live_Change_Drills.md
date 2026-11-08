# Live-change drills (Part D) — practise on a COPY, never on the only copy

The instructor may ask you to: add a field and save it, change a validation rule, change a query, find a commit, or explain a teammate's part. Each drill below was **actually applied to a practice copy on 8 Nov 2026 and verified**: the new field was saved (`('Drill blue pen', 'Blue')`), a 4-character title was rejected, a 41-character colour was rejected, searching "Computer lab corridor" returned 12 notices, and the full suite still passed **83/83** (practice copy of commit `a7e5c74`, before the Microsoft sign-in module and its 11 tests were added; line numbers below are unchanged by that module).

## 0. Make a practice copy (1 minute)

```bat
xcopy /E /I /Q "%USERPROFILE%\Downloads\SE-2623_Endterm\Campus_Lost_Found" "%USERPROFILE%\Desktop\Practice\Campus_Lost_Found"
cd /d "%USERPROFILE%\Desktop\Practice\Campus_Lost_Found"
```

If the project is a Git clone you can instead work on a branch: `git switch -c practice` (rollback: `git switch main` and `git branch -D practice`). To undo everything in a copy: delete the `Practice` folder.

Stop any running server first (Ctrl+C). Open the files in VS Code: `code .`

---

## Drill 1 — add a field "Colour" and save it in the database (≈ 4 min)

**1. Database schema for new databases** — `backend/schema.sql`, inside `CREATE TABLE notices`, add a line just before `FOREIGN KEY (owner_id)…`:

```sql
    colour TEXT NOT NULL DEFAULT '' CHECK (length(colour) <= 40),
```

**2. The schema check** — `backend/db.py` line 25–26, add `'colour'` at the end of the `notices` tuple:

```python
'event_date', 'type', 'status', 'created_at', 'updated_at', 'photo_filename', 'colour'),
```

*(Forgetting this makes every test fail with `DatabaseStateError: Unexpected columns in notices` — good to mention: the app refuses a database it does not expect.)*

**3. Migrate the existing database file** — copy `Final/Defense/practice/migrate_colour.py` into the practice `Campus_Lost_Found` folder and run:

```bat
python\python.exe migrate_colour.py
```

It runs `ALTER TABLE notices ADD COLUMN colour TEXT NOT NULL DEFAULT '' CHECK (length(colour) <= 40)` and prints the column list (last one: `colour`). Do not type this SQL as a one-line `python -c` in cmd: the `<` is treated as a redirection and the command silently fails (we tested it).

**4. Read and validate the value** — `app.py`, function `validate_form` (line 279):

```python
values = {key: request.form.get(key, '').strip() for key in ('title','description','location','event_date','type','category_id','colour')}
```

and right after the `for key,(minimum,maximum) in limits.items():` loop add:

```python
        if len(values['colour']) > 40:
            return values, 'Colour must have at most 40 characters.'
```

**5. Save it** — `app.py`, in `create` (line 308) add `colour` to the INSERT:

```python
'INSERT INTO notices(owner_id,category_id,title,description,location,event_date,type,photo_filename,colour) VALUES(?,?,?,?,?,?,?,?,?)', (g.user['id'], values['category_id'], values['title'],values['description'],values['location'],values['event_date'],values['type'],filename,values['colour'])
```

and in `edit` (line 331) change `photo_filename=?,updated_at=…` to `photo_filename=?,colour=?,updated_at=…` and add `values['colour'],` before `notice_id,g.user['id']`.

**6. Form field** — `templates/form.html`, before `<div class="field"><label for="location">`:

```html
<div class="field"><label for="colour">Colour <span class="muted">(optional)</span></label><input id="colour" name="colour" maxlength="40" value="{{values.get('colour','')}}" placeholder="Blue"></div>
```

**7. Show it** — `templates/detail.html`, before `<div><dt>Notice number</dt>`:

```html
{% if notice.colour %}<div><dt>Colour</dt><dd>{{notice.colour}}</dd></div>{% endif %}
```

**8. Prove it** — start `START.bat`, post a notice with colour "Blue", then:

```bat
DB.bat query "SELECT id, title, colour FROM notices ORDER BY id DESC LIMIT 1;"
python\python.exe -B -m unittest discover
```

**Say:** "The value goes form → `validate_form` → parameterised INSERT → SQLite column with a CHECK constraint → shown on the detail page. The database also enforces the 40-character limit, so even a bypassed form cannot store more."

## Drill 2 — change a validation rule (≈ 1 min)

`app.py` line 281: `limits = {'title':(3,120), …}` → `'title':(5,120)`. Restart, try the title "Pen" → message "Title must have 5-120 characters." Mention: the SQL `CHECK (length(title) BETWEEN 3 AND 120)` still allows 3, so the browser rule is now stricter than the database — to make them match, also change `schema.sql` (affects new databases only). Also change `minlength="3"` in `form.html` so the browser hint matches.

## Drill 3 — modify a database query (≈ 2 min)

Make search also match the location. `app.py` lines 191–193 (inside `browse`):

```python
        if q:
            pattern = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            clauses.append("(n.title LIKE ? ESCAPE '\\' OR n.location LIKE ? ESCAPE '\\')")
            params.extend([pattern, pattern])
```

Restart and search "Computer lab corridor" → 12 notices (before the change: 0, because no title contains it). **Say:** "Still parameterised — the user's text is a parameter, never part of the SQL string; `%` and `_` are escaped so they are literal."

Read-only alternative without touching code: `DB.bat query "SELECT type, COUNT(*) FROM notices GROUP BY type;"` → 60 lost / 62 found (vs `GROUP BY status` → 96 / 26).

## Drill 4 — find a commit and explain it (≈ 1 min)

```bat
git log --oneline
git show --stat a7e5c74
git log --oneline -- Campus_Lost_Found/app.py
```

GitHub: <https://github.com/zondbebox/SE-2623_Endterm/commits/main> → click the commit → Browse files. **Be honest:** "Our history has one upload commit from Zhanzhol's account; our individual parts are in these files: … We learned to commit per feature." (If members add real commits before the defense, show yours.)

## Drill 5 — explain a teammate's part and what happens if it fails

| Part | How it works (code) | If it fails |
|---|---|---|
| Photo upload (Zhanzhol) | `save_photo` checks extension + MIME, ≤ 5 MiB, ≤ 12 MP, re-encodes with Pillow, random name, `open('xb')` | Invalid image → friendly error, nothing inserted; if the DB insert fails the new file is deleted (`delete_photo`) |
| Search (Daniil) | `browse`: LIKE with escaped wildcards + optional category/status, `LIMIT 8 OFFSET` | Huge page/category numbers → 400 instead of a crash (regression tests) |
| Analytics (Daniil) | `backend/analytics.py` three SQL queries in one read-only transaction | Empty DB → empty states (tested); student → 403; it opens the DB read-only, so a bug there cannot change notices |
| Locker (Daulet) | `record_simulated_event` validates the found notice, writes `telemetry.sqlite3`; `locker.js` posts with fetch | Network cut → "result could not be confirmed", never re-posts; removed notice → "Reset unavailable assignment" |
| Backup (Zhanzhol) | `backup_full.py` online SQLite snapshot + photos + SHA-256 manifest | Corrupt or tampered ZIP → restore check refuses before creating any folder |

## Rollback checklist

1. Stop the server (Ctrl+C).
2. Delete the practice folder **or** `git restore .` / `git switch main` in a Git clone.
3. Never run the drills in the folder you will present from.
