# Campus Lost & Found — SE-2623

A local web application for publishing, searching and closing lost-and-found notices on a university campus. ICT course project (Stage 1 → Stage 2 → Final) by team SE-2623: **Mengdigerey Zhanzhol, Galitskiy Daniil, Bisengaliev Daulet**.

* **Final materials** (report, presentation, requirement table, tests, defense guides): [`Final/`](Final/) — start with [`Final/README.md`](Final/README.md).
* **Application:** [`Campus_Lost_Found/`](Campus_Lost_Found/) — Flask + SQLite, runs locally on `http://127.0.0.1:5055`.
* **Verified version:** branch `main`, commit `a7e5c749095e63e1cff1280b95279ca8bae6e447` (6 Nov 2026). Every command and account below was re-checked on **8 November 2026** on Windows 11 against an isolated copy of that commit.

> **Local demonstration only.** There is no public hosting, no HTTPS, no LAN access and no university single sign-on. All accounts and notices are synthetic. Never enter a real university password.

## 1. Requirements

| Platform | What you need | Verified |
|---|---|---|
| Windows 10/11 (64-bit) | Nothing extra — Python 3.14.8 and all dependencies are bundled in `Campus_Lost_Found/python` and `vendor` | ✓ 8 Nov 2026 |
| Linux | Bash, Python ≥ 3.10 with `venv`/`ensurepip`, Internet for the first dependency install (Flask 3.1.3, Werkzeug 3.1.9, waitress 3.0.2, sqlite-web 0.8.2, Pillow 12.3.0 — pinned in `requirements*.txt`) | ✗ not yet run on Linux by the team |

The project folder must be fully extracted (do not run from inside a ZIP). Keep the path free of exotic characters if possible.

## 2. Run on Windows

1. Open `Campus_Lost_Found` and double-click **`START.bat`** (or, in a terminal in that folder: `python\python.exe app.py`).
2. Wait for `Campus Lost & Found: http://127.0.0.1:5055`.
3. Open **http://127.0.0.1:5055** in Chrome, Edge or Firefox and sign in with an account from section 4.
4. Port busy? Stop the other copy (Ctrl+C in its window) or run `python\python.exe app.py --port 5056`.

## 3. Run on Linux

```bash
cd Campus_Lost_Found
bash START.sh          # first run creates a private venv in ~/.cache/campus-lost-found and installs pinned packages
bash TESTS.sh          # optional: full test suite
```

The Linux scripts never use the bundled Windows `python/` or `vendor/` folders. See `Campus_Lost_Found/START_LINUX_RU.txt`. **Status: written and reviewed, not yet executed on Linux** — please run them once before relying on them.

## 4. Test accounts (synthetic; verified 8 Nov 2026)

All demo accounts share the public teaching password **`CampusDemo!2026`**.

| Role | Email | What it can do |
|---|---|---|
| Administrator | `admin.demo@astanait.edu.kz` | Everything a student can, plus `/admin` (overview, notices, users), notice removal, `/admin/analytics`, `/admin/research` (test timer), `/admin/smart-locker` (simulation) |
| Student | `zhanzhol.demo@astanait.edu.kz` | Post, search, open, contact author, edit own notice, mark returned |
| Student | `daniil.demo@astanait.edu.kz` | same as above |
| Student | `daulet.demo@astanait.edu.kz` | same as above |
| Student | `student01.demo@astanait.edu.kz` … `student16.demo@astanait.edu.kz` | owners of the seeded notices |

Verification (`Final/Evidence/account_checks.json`): all four main accounts sign in; every `/admin/*` page returns **200** for the administrator and **403** for each student; anonymous visitors are redirected to the sign-in page. New student accounts can be registered at `/register` with any well-formed `@astanait.edu.kz` address (the address is *not* verified).

Use two separate browser sessions (normal + private window) to show student and administrator at the same time.

## 5. Database

| File | Contents |
|---|---|
| `Campus_Lost_Found/data/campus.sqlite3` | `users`, `categories`, `notices` (schema: `backend/schema.sql`) — shipped with 20 users, 10 categories, 122 synthetic notices |
| `data/uploads/` | photos attached to notices (random names, served only after sign-in) |
| `data/research.sqlite3` | user-test timings (participant codes only) |
| `data/telemetry.sqlite3` | smart-locker events, all labelled `SIMULATED` |
| `runtime/session.key`, `runtime/audit.jsonl` | session signing key and audit log (created on first start; do not share) |

Useful commands (Windows; on Linux use `bash DB.sh …`, `bash DATABASE.sh`, `bash BACKUP.sh`, `bash RESTORE_CHECK.sh`):

```bat
DB.bat summary
DB.bat query "SELECT status, COUNT(*) AS n FROM notices GROUP BY status;"
DATABASE.bat           & rem read-only browser inspector at http://127.0.0.1:8088
BACKUP.bat             & rem full ZIP: all databases + photos + SHA-256 manifest (session key excluded)
RESTORE_CHECK.bat      & rem verifies the newest backup in a NEW scratch folder; never overwrites live data
```

In PowerShell, prefix the scripts with `.\` (for example `.\DB.bat summary`). `DB.bat query` accepts only one read-only `SELECT`. Expected output of the query above on the shipped data: `open 96`, `returned 26`.

**Start again from clean demo data:** stop the server, move `data/campus.sqlite3` (and, if wanted, `data/uploads/`, `data/research.sqlite3`, `data/telemetry.sqlite3`) somewhere safe, then start `START.bat` — when `campus.sqlite3` is missing the app creates the schema and seeds the synthetic dataset (20 accounts, 10 categories, **120** notices; the shipped file has 122 because two demonstration notices, #121 and #122, were added on 12 and 25 October 2026). To get back exactly the shipped 122-notice file, copy `Analysis/frozen_campus.sqlite3` to `Campus_Lost_Found/data/campus.sqlite3` instead (same SHA-256).

## 6. Tests

```bat
cd Campus_Lost_Found
python\python.exe -B -m unittest discover -v      & rem 96 tests, about 40 s
```

Result on 8 Nov 2026: `Ran 96 tests … OK` (83 from commit a7e5c74 + 13 for Microsoft sign-in) (`Final/Evidence/test_suite_final.log`). `TESTS.bat` runs the same files one by one.

## 6a. Microsoft sign-in with a university account (Entra ID)

**Status: working — verified 8 Nov 2026** with a real Astana IT University account (audit log entry `microsoft_login_success`). The app is registered in the university's Microsoft Entra directory as a single-tenant web app with redirect URI `http://localhost:5055/auth/microsoft/callback`.

Start with **`Campus_Lost_Found\START_MICROSOFT.bat`**. It sets the tenant and application IDs (not secrets) and asks for the **client secret** in a hidden prompt; the secret stays only in that window's memory — never in a file, Git or chat. Then open **http://localhost:5055/login** (localhost, not 127.0.0.1) and click **Sign in with Microsoft (university account)**. The header shows the user's Microsoft display name.

In this mode new users can only come from the university directory: local self-registration is closed. The synthetic demo accounts still sign in with the demo password, and `START.bat` runs the whole demo offline without Microsoft.

Code: `microsoft_auth.py` (OpenID Connect, authorization code + PKCE, state, nonce, RS256 signature, issuer/audience/tenant/expiry checks, only `@astanait.edu.kz`). Tests: `test_microsoft_auth.py` (13, simulated Microsoft). Client secrets expire — create a new one in Entra (Certificates & secrets) before it runs out. Details: `Final/SSO/Microsoft_Entra_SignIn_Status_and_Setup.md`.

## 7. Stop safely

1. Finish or cancel any form you are submitting.
2. In the server window press **Ctrl+C** (then close the window). Do the same for `DATABASE.bat` if it is open.
3. Before copying the folder to another computer or switching between Windows and Linux, stop both servers and run `BACKUP.bat`.

## 8. Repository history

The repository currently contains a **single commit** (`a7e5c74 "Initial commit"`, uploaded from the `zondbebox` account, which belongs to Mengdigerey Zhanzhol). Individual work by Daniil and Daulet is therefore not visible in Git yet. See `Final/Repository_History_Guide.md` for how each member can add genuine commits from their own account (no history rewriting). The Final additions (`Final/`, this README, `microsoft_auth.py`, `test_microsoft_auth.py`, small edits in `app.py`, `templates/login.html`, `templates/base.html`, `TESTS.bat`, `TESTS.sh`) exist locally and are **not yet committed**.

## 9. Project layout

```
Campus_Lost_Found/   application, runtime, tests, launch scripts
Analysis/            SQL questions, charts, frozen analysis database (synthetic)
Evidence/            Stage 2 verification records (historical)
Testing/             task cards and observer instructions
Video/               Assignment 4 demo video (older interface)
Sources/             briefs, image sources, IoT sources
Final/               Final report, presentation, requirement table, evidence, defense preparation
```

## 10. Known limitations

Microsoft sign-in works only on this laptop (localhost redirect); loopback HTTP only (no TLS, no LAN); SQLite and photos are not encrypted by the application; the smart locker is a software simulation with no hardware. Details and next steps: `Final/Report/Group_Team_ICT_FinalProject.pdf`, Section 9.
