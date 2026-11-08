# B2 — Individual contribution statements (confirmed by the team on 8 Nov 2026 — sign the printed copy)

**How these drafts were made.** The areas come from the contribution table in the Stage 2 report (p. 9), which the team confirmed on 8 Nov 2026 as correct. File paths were checked in commit `a7e5c74`. Git cannot confirm authorship yet: the repository has one upload commit from Zhanzhol's account (`zondbebox`). The "problem I solved" examples are real fixes recorded in `Technical_Verification.txt` and the Stage 2 report, **assigned to a member by area — each member must confirm that they personally did it or replace it with their own example**. Nobody may sign for someone else.

**Rules from the brief:** 100–120 words, signed with the member's name; what they personally built (with links to commits or files), one problem they solved and how, one thing they would do differently.

**To change a statement:** edit `Final/_build/report_config.json` → run `Campus_Lost_Found\python\python.exe -B Final\_build\build_report.py` (it refuses texts outside 100–120 words) → when all three are confirmed set `"statements_confirmed": true` and rebuild → print page 18 of the report and sign.

---

## Mengdigerey Zhanzhol — 112 words

> I built the account and notice workflow: local registration and sign-in, publishing and editing notices, the single-photo upload, owner and administrator permissions, and the full backup with restore check. My files are Campus_Lost_Found/app.py, templates/form.html, backup_full.py and backup_tools.py. Commits a7e5c74, ca5d0e5 and 4d91abd were pushed from my GitHub account, zondbebox. One problem I solved: the backup writer and the restore reader used different size limits for the manifest file, so a backup could be created that restore would then refuse. I made both use one shared 1 MiB limit and added three regression tests. Next time I would commit every feature separately, so the history shows who built what.

Links: [app.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/app.py) · [backup_full.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/backup_full.py) · [commit a7e5c74](https://github.com/zondbebox/SE-2623_Endterm/commit/a7e5c749095e63e1cff1280b95279ca8bae6e447)
To confirm: ☐ the manifest-limit fix was mine ☐ wording is mine Signature: ______________ Date: ________

## Galitskiy Daniil — 110 words

> I was responsible for browsing and search, the search performance test, the SQL analytics and the user-testing method. My files are Campus_Lost_Found/analytics_routes.py, backend/analytics.py, Analysis/01-03 SQL queries, benchmark_search.py, the research timer in stage2_features.py and Testing/TASK_CARDS_EN.txt. They are in commit a7e5c74, and I am a co-author of the Final commits ca5d0e5 and 4d91abd. One problem I solved: very large numbers in the category and page filters crashed SQLite with an overflow error. I added range checks that return HTTP 400 or 404 before any query runs, plus four regression tests. Next time I would run the external user study weeks earlier, not at the end.

Links: [analytics_routes.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/analytics_routes.py) · [backend/analytics.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/backend/analytics.py) · [benchmark_search.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/benchmark_search.py)
To confirm: ☐ the overflow fix was mine ☐ add my own commit link ☐ wording is mine Signature: ______________ Date: ________

## Bisengaliev Daulet — 111 words

> I worked on the smart-locker extension, the multimedia and the 360 px, keyboard and availability evidence. My files are the locker part of Campus_Lost_Found/stage2_features.py, static/locker.js, static/locker.css, templates/smart_locker.html, simulate_locker.py, static/media/CREDITS.txt and the Assignment 4 video. They are in commit a7e5c74, and I am a co-author of the Final commits ca5d0e5 and 4d91abd. One problem I solved: when the found notice linked to an open locker was deleted, the simulation could not be closed. I added a reset action that records a new closed, unassigned state and keeps the history. Next time I would test on a real phone early and re-record the video after every interface change.

Links: [stage2_features.py](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/stage2_features.py) · [static/locker.js](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/static/locker.js) · [smart_locker.html](https://github.com/zondbebox/SE-2623_Endterm/blob/main/Campus_Lost_Found/templates/smart_locker.html)
To confirm: ☐ the reset fix was mine ☐ add my own commit link ☐ wording is mine Signature: ______________ Date: ________
