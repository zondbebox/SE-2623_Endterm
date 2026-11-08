# System map — everyone must know this page (Part D)

Version: commit `a7e5c74` (only commit). Line numbers refer to that commit.

## 1. How one request flows (say this in 20 seconds)

> "The browser sends HTTP to Waitress on 127.0.0.1:5055. Flask's `before_request` hook in `app.py` loads the signed-in user from the session cookie and checks the CSRF token on every POST. The route function checks ownership or the admin role, runs a parameterised SQL query on `data/campus.sqlite3`, and renders a Jinja template. `after_request` adds security headers (CSP, nosniff, no-store)."

```
Browser ──HTTP 127.0.0.1:5055──▶ Waitress (4 threads) ──▶ Flask app (create_app in app.py)
   before_request: g.user from session · CSRF check on POST           │
   route: login_required / admin_required / require_owner             ▼
   SQL with ? parameters ──▶ campus.sqlite3 · research.sqlite3 · telemetry.sqlite3 · data/uploads/
   Jinja template (auto-escaped) ◀── after_request: CSP, nosniff, Referrer-Policy, no-store
```

## 2. Files and what they do

| File | Purpose | Key functions |
|---|---|---|
| `Campus_Lost_Found/app.py` | App factory, security hooks, accounts, notices, photos | `create_app` (27), `security` (71), `headers` (83), `register` (112), `login` (147), `browse` (183), `detail` (220), `photo` (225), `save_photo` (239), `validate_form` (279), `create` (299), `edit` (319), `returned` (343), `remove` (352) |
| `admin_panel.py` | Admin overview, notice list, user list (read-only) | `admin_dashboard`, `admin_notices`, `admin_users`, `_pagination` |
| `analytics_routes.py` | Admin analytics page and CSV | `analytics`, `analytics_csv`, `_csv_cell` |
| `backend/analytics.py` | The three SQL questions | `build_analytics` |
| `stage2_features.py` | User-test timer and smart-locker simulation | `admin_required` (58), `research_summary` (69), `record_simulated_event` (88), `research` (135), `smart_locker` (218) |
| `backend/db.py` | Connection settings, schema check, seed data | `get_connection`, `init_database`, `seed_database`, `TABLE_COLUMNS` (22) |
| `backend/schema.sql` | Tables, CHECK constraints, foreign keys, indexes | — |
| `backend/manage.py` | CLI: `init`, `seed`, `summary`, `backup`, `restore-check`, `query` | `main` |
| `backup_full.py`, `backup_tools.py` | Full ZIP backup + non-destructive restore check | — |
| `simulate_locker.py` | CLI heartbeats for the locker simulation | `main` |
| `static/locker.js` | Locker buttons without page reload (fetch) | `requestUpdate`, `updatePage` |
| `static/photo-upload.js` | Photo picker preview and checks in the browser | — |
| `templates/*.html` | Jinja pages (`base.html` = layout, top bar, navigation) | — |
| `microsoft_auth.py` | Optional Microsoft Entra sign-in (OIDC + PKCE), off unless `CAMPUS_ENTRA_*` env vars are set | `settings`, `login`, `callback`, `validate_id_token`, `rsa_sha256_verify` |
| `test_*.py`, `backend/test_backend.py` | 94 automated tests (11 in `test_microsoft_auth.py`) | — |

## 3. Routes

| Route | Method | Who | What |
|---|---|---|---|
| `/register` | GET, POST | anyone | create a local student account (`@astanait.edu.kz`, 12–128-char password) |
| `/login` | GET, POST | anyone | sign in; 5 failed attempts / 60 s per address → 429 |
| `/logout` | POST | signed in | clear session |
| `/` | GET | signed in | noticeboard; `q`, `category`, `status`, `mine`, `page` (8 per page) |
| `/how-it-works` | GET | signed in | help page |
| `/post` | GET, POST | signed in | create a notice (+ optional photo) |
| `/notice/<id>` | GET | signed in | details + Contact author (mailto) |
| `/notice/<id>/photo` | GET | signed in | serves the private photo |
| `/notice/<id>/edit` | GET, POST | owner | edit notice / replace photo |
| `/notice/<id>/returned` | POST | owner | mark returned |
| `/notice/<id>/remove` | GET, POST | admin | confirmation page (GET), delete row + photo (POST) |
| `/admin`, `/admin/notices`, `/admin/users` | GET | admin | overview and lists (read-only connection) |
| `/admin/analytics`, `/admin/analytics.csv` | GET | admin | three SQL series; CSV export |
| `/admin/research`, `/admin/research.csv` | GET, POST | admin | timer for real external testers |
| `/admin/smart-locker` | GET, POST | admin | SIMULATED door readings for LF-01 |
| `/auth/microsoft/login`, `/auth/microsoft/callback` | GET | anyone | Microsoft sign-in; **404 unless configured** |

## 4. Database tables

**`campus.sqlite3`** (`backend/schema.sql`, foreign keys ON, `ON DELETE RESTRICT`)

| Table | Columns | Rules |
|---|---|---|
| `users` | `id`, `email` UNIQUE, `password_hash`, `role` | email lower-case, ends `@astanait.edu.kz`, 17–254 chars; hash starts `scrypt:`; role `student`/`admin` |
| `categories` | `id`, `name` UNIQUE NOCASE | 10 rows |
| `notices` | `id`, `owner_id`→users, `category_id`→categories, `title`, `description`, `location`, `event_date`, `type`, `status`, `created_at`, `updated_at`, `photo_filename` | title 3–120, description 10–1200, location 2–100; type lost/found; status open/returned; `event_date ≤ created date`; indexes on category, status, owner |

**`research.sqlite3`** → `research_sessions(participant T01–T99, task publish/find, device, external_consent=1, started_at, finished_at, duration_seconds, outcome, helped, observation1–3, UNIQUE(participant, task))`.
**`telemetry.sqlite3`** → `locker_events(locker_id='LF-01', notice_id, door_state open/closed, event_type change/heartbeat, observed_at, open_since_at, source='SIMULATED')`.

Remember: `backend/db.py` checks the exact column list (`TABLE_COLUMNS`). **Adding a column means changing `schema.sql`, `db.py` and migrating the existing file** (see `Live_Change_Drills.md`).

## 5. Security in one breath

scrypt password hashes · signed HttpOnly SameSite=Lax session cookie, 30 min · CSRF token on every POST (`hmac.compare_digest`) · rate limit on login/register · parameterised SQL with escaped LIKE · Jinja auto-escaping + CSP `default-src 'self'` · owner check (`require_owner`) and role check (`admin_required`) on the server · uploads: type/size/pixel checks, re-encode, random 48-hex names, served only to signed-in users · CSV formula neutralising · server only on 127.0.0.1 with trusted hosts localhost. **Not present:** HTTPS, encryption at rest, LAN/Internet access, a *connected* university sign-in (code ready, off).

## 6. Who presented / owns what (team-confirmed contribution table, Stage 2 report p. 9)

| Area | Lead | Must still be able to explain |
|---|---|---|
| Accounts, notices, photos, permissions, backup (F1–F3, F6–F8, N2) | Zhanzhol | everyone |
| Browse/search, performance, SQL analytics, user study (F4–F5, N1, SC1–SC2) | Daniil | everyone |
| Locker simulation, multimedia, 360 px/keyboard/availability evidence (N3–N4) | Daulet | everyone |

Git cannot prove this split yet: the repository has one upload commit from Zhanzhol's account (see `Final/Repository_History_Guide.md`).

## 7. Numbers to know (all from 8 Nov 2026 re-run)

94/94 tests · SC1 3/3, SC2 3/3 (T01–T03) · p95 search 44.9 ms (target 2,000 ms, 10 sessions, 100 requests) · SC3 5/5 · N4 20/20 over 30 min · 12/12 pages without sideways scroll at 360 px · 122 notices (96 open/26 returned; 60 lost/62 found), 20 users, 10 categories · seed creates 120 notices · locker warning after 10 s · photo ≤ 5 MiB, ≤ 12 MP, scaled to ≤ 1600 px · session 30 min · login limit 5 per 60 s.
