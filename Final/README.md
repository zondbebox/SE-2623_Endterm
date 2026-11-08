# Final — Campus Lost & Found (SE-2623)

Final-project package for the ICT course (brief: `ICT_Final.pdf`, Week 10). Team: Mengdigerey Zhanzhol, Galitskiy Daniil, Bisengaliev Daulet.

**System assessed:** <https://github.com/zondbebox/SE-2623_Endterm>, branch `main`, commit `a7e5c749095e63e1cff1280b95279ca8bae6e447` (only commit, 6 Nov 2026). The Endterm ZIP (`SE-2623_Endterm.zip`, 8 Nov 2026) is file-for-file identical to it. For the Final, one optional module was added to the application — **Microsoft sign-in** (`microsoft_auth.py`, `test_microsoft_auth.py`, one line in `app.py`, two template lines, test scripts). It is off unless configured and is **not yet committed**. Endterm documents, evidence and data were left untouched. All evidence was re-run on **8 Nov 2026**.

How to run the app and the verified test accounts: see the root [`README.md`](../README.md).

## Contents

| Deliverable (brief §3) | File | Status |
|---|---|---|
| Final report, single PDF | `Report/Group_Team_ICT_FinalProject.pdf` (19 pages, A4) — source `Report/source/report.html` | ready; rebuild after adding test data and signatures |
| Final presentation (PDF) | `Presentation/Group_Team_ICT_FinalPresentation.pdf` (12 slides + 4 backup, 16:9) | ready |
| Editable presentation | `Presentation/Group_Team_ICT_FinalPresentation.pptx` (speaker notes on every slide), source `Presentation/source/build_deck.js` | ready |
| Speaking order and timing | `Presentation/Speaker_Timing.md` | ready |
| README with run instructions and test accounts | `../README.md` | ready, verified |
| Requirement status table (A1) | `Requirements/Requirements_Status.md` | ready |
| As-built architecture + changes (A2) | `Architecture/as_built_architecture*.svg`, `Architecture/Changes_from_Stage1.md` | ready |
| Commit history (A3) | `Repository_History_Guide.md` | **team action needed** — one commit only |
| Final test (A4) | `Testing/Final_Test_Protocol.md`, `Testing/final_test_results.csv`, `Testing/Final_Test_Results.md`, `Testing/stage2_team_reported.csv` | done: T01–T03, SC1 3/3, SC2 3/3 (data supplied by the team) |
| Contribution statements (B2) | `Contributions/Individual_Contribution_Statements.md` (also report p. 18) | **drafts — confirm and sign** |
| Defense preparation (D) | `Defense/00_System_Map.md`, `Defense/Defense_<name>.md`, `Defense/Live_Change_Drills.md`, `Defense/Eight_Questions.md`, `Defense/practice/` | ready |
| Demo plan and video fallback | `Demo/Demo_Plan_and_Backup.md` | ready; video **not** re-recorded |
| Personal data & Kazakhstan law | `Legal/Personal_Data_Kazakhstan.md` | ready (sources checked 8 Nov 2026) |
| Microsoft sign-in | `../Campus_Lost_Found/microsoft_auth.py`, `SSO/Microsoft_Entra_SignIn_Status_and_Setup.md` | code + 11 tests (simulated Microsoft); **not connected** — needs a university app registration |
| Evidence | `Evidence/` — test log, measurements, browser checks, account checks, 26 screenshots | re-run 8 Nov 2026 |
| Team checklist (RU) | `CHECKLIST_RU.md`, guide `START_HERE_RU.md` | ready |

## Evidence files (8 Nov 2026, isolated copy of commit a7e5c74, Windows 11, bundled Python 3.14.8, Edge 157)

| File | What it proves |
|---|---|
| `test_suite_final.log` | `Ran 94 tests in 29.590s — OK` (final code incl. Microsoft sign-in); `test_suite_a7e5c74_83.log`: 83/83 on the unchanged commit |
| `entra_smoke_placeholder_config.json` | real server with placeholder Entra IDs: button shown, redirect to Microsoft authorize endpoint with PKCE, secret not in URL |
| `search_performance_final.json` | N1: p95 44.866 ms, max 54.597 ms (10 sessions × 10 searches) |
| `sc3_final.json` | SC3: 5/5 invalid-access attempts blocked, with database-state checks |
| `stability_30min_final.json` | N4: 20/20 authenticated checks over 1,800 s |
| `browser_checks.json` | N3: 12/12 pages without horizontal scroll at 360 px, labels, Tab order; N4 offline → retry; F5 search; F6 mailto; F7 returned; F8 removal; locker alert without page reload |
| `account_checks.json` | all four demo accounts sign in; 403/200 matrix for `/admin/*` |
| `screenshots/` | S01–S18 desktop (1440 × 900), M01–M04 at 360 px, K01 keyboard focus |

## Rebuilding after changes

```bat
rem report (standard library only; prints word counts and refuses out-of-range texts)
Campus_Lost_Found\python\python.exe -B Final\_build\build_report.py
rem slides (needs Node.js; run "npm install" once in Final\Presentation\source)
cd Final\Presentation\source && node build_deck.js && cd ..\..\..
powershell -ExecutionPolicy Bypass -File Final\_build\export_pptx.ps1
```

`export_pptx.ps1` uses Microsoft PowerPoint to write the PDF. Screenshot crops for the slides: `Final/_build/crop_assets.py` (needs Pillow).

## What is not claimed

No public URL, no LAN access, no HTTPS, no working university sign-in (code only), no physical locker, no human results beyond the three participants supplied by the team, no upload to the LMS, no push to GitHub.
