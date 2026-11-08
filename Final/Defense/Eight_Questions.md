# The eight sample defense questions (ICT_Final.pdf, section 5) — model answers

Answers are in English to say aloud; short Russian notes (RU) explain what to show. Every fact here is checked against commit `a7e5c74` and the 8 Nov 2026 evidence.

---

### 1. "Show me the commit where you implemented your main feature and walk me through the code."

**Answer (honest version, valid today):** "Our repository has a single upload commit, `a7e5c74`, made from Zhanzhol's account on 6 November. We did not commit feature by feature, which we now see was a mistake. My main feature is in `<your file>` — let me open it." Then walk through the function (see your personal guide).
**If members have pushed their own Final commits:** open GitHub → Commits → your commit → explain the diff.
RU: не придумывайте коммиты. Откройте файл и функцию из своего гайда; скажите честно про один коммит.

### 2. "Add a new field to this form right now, and make sure it is saved in the database."

Follow `Live_Change_Drills.md`, Drill 1 (colour field). Order to say: **schema.sql → db.py TABLE_COLUMNS → migrate existing file → validate_form → INSERT/UPDATE → form.html → detail.html → prove with `DB.bat query` and the tests.** Practise it twice on a copy; target under 5 minutes.

### 3. "Explain how your teammate's part works. What happens if it fails?"

Use the table in `Live_Change_Drills.md` (Drill 5). Example: "Daulet's locker page posts the button with `fetch` and a CSRF token; the server validates that the notice exists and is 'found', then writes a SIMULATED row to `telemetry.sqlite3`. If the network drops, the page says the result could not be confirmed and never re-sends the POST automatically, so we cannot record a door event twice. If the notice was deleted, the page offers 'Reset unavailable assignment'. It never changes the main notices table."

### 4. "Which instructor comment from Stage 1 did you not address, and why?"

"We did not receive written instructor comments on Stage 1, as recorded in our Stage 2 report. The one Stage 1 commitment we could not fully deliver is university sign-in, F1: our Stage 1 risk table already said SSO approval might be delayed and that we would clearly label a simulated sign-in — that is what we did. For the Final we closed it: we registered the app in the university's Microsoft Entra directory and added OpenID Connect sign-in with PKCE; on 8 November a real university account signed in."
RU: если преподаватель напомнит конкретное замечание — признайте и назовите, что сделано/не сделано; не спорьте.

### 5. "Where is your users' personal data physically stored, and why does that matter under Kazakhstan law?"

"On the demo laptop's disk: emails, password hashes and notices in `Campus_Lost_Found/data/campus.sqlite3`, photos in `data/uploads/`, test timings in `research.sqlite3`, backups in `backups/`. The laptop is in Kazakhstan, nothing is sent to a server, and today all data is synthetic. It matters because the Law 'On Personal Data and Their Protection' No. 94-V, Article 12 paragraph 2, requires personal data to be stored in a database located in Kazakhstan, and storage should end when the purpose is achieved. So if we hosted it, we would need a Kazakhstan data centre — not a foreign cloud region — and we must never commit a database with real users to GitHub. The law also requires consent and protection measures, and breach notification to the authorised body within one working day."
RU: источник — adilet.zan.kz, проверено 8.11.2026 (`Final/Legal/Personal_Data_Kazakhstan.md`). Не говорите «мы полностью соответствуем закону».

### 6. "Show me the as-built architecture. Where is the security boundary, and what lies outside it?"

Show report page 6 or slide 8. "Everything runs on one laptop. The boundary is the laptop's Windows account: inside are the browser, Waitress + Flask, and the SQLite files. Inside the app, sessions, CSRF tokens and role checks protect every action, and passwords are scrypt hashes. What is **not** protected: traffic is plain HTTP — acceptable only because it never leaves 127.0.0.1 — and files on disk are not encrypted, so anyone with the laptop login can copy them. Outside the boundary: other devices, which cannot connect; the user's email app; Microsoft Entra, the university directory that signs students in; and GitHub, which holds only synthetic data."

### 7. "Which requirement was hardest to finish, and what did you have to cut to finish it?"

"The hardest was N4/N3 evidence and, overall, identity. Identity was the last piece: university sign-in only worked in the final week, after we registered the app in the university Entra directory. To keep the core flow stable we also cut what Stage 1 already listed as out of scope — chat, payments, delivery, automatic matching — and we did not build LAN access or HTTPS, because exposing the app on Wi-Fi without TLS would send passwords in clear text."
RU: каждый может назвать своё «самое трудное» (см. личный гайд), но ответ должен совпадать с отчётом.

### 8. "If 10,000 users joined tomorrow, which part of your system would fail first, and what would you do?"

"First, access: the server only listens on 127.0.0.1, so nobody else could even reach it. After hosting it, writes would be the bottleneck: SQLite allows one writer at a time and Waitress runs four threads, so bursts of posts and up-to-6-MB photo uploads would queue; photos sit on one disk and our rate limit lives in memory. Our 45 ms result was for 10 users on a laptop, so it does not predict 10,000. Plan: host in a Kazakhstan data centre with HTTPS, move to PostgreSQL, put photos in object storage, run several app instances behind a load balancer with a shared rate limiter such as Redis, add Entra sign-in, and load-test before launch."

---

## Extra questions to expect

| Question | Short answer |
|---|---|
| Is the locker real IoT? | No. Software simulation; every row says SIMULATED; no sensor, no network device. |
| Why SQLite? | One file, no server, constraints and foreign keys; right for a local prototype; wrong for many concurrent writers. |
| How do you prevent SQL injection? | `?` parameters everywhere; LIKE wildcards escaped; `test_sql_injection_cannot_bypass_login` and `test_search_treats_sql_and_like_metacharacters_as_literal_text` prove it. |
| Why is HTTP acceptable? | Only on loopback; the moment it leaves the laptop we need HTTPS. |
| Where are the human test results? | `Final/Testing/final_test_results.csv` — only real participants outside the team; say exactly what is recorded. |
| Did AI help? | Yes, AI tools were used to review code and prepare documents; all checks were re-run and every claim has evidence; AI reviews are never counted as testers. |
| What is synthetic data? | Generated demo notices and accounts — not real campus events; the analytics page says so. |
