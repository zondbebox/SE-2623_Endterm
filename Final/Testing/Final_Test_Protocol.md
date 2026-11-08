# A4 Final test — protocol (fixed before testing)

**Purpose.** Re-test the three Stage 1 success criteria on the final build (commit `a7e5c74`; the later Microsoft sign-in module is off and does not change the tested pages) with **at least three people who are not members of the team**. SC1 and SC2 were *Pending* in the submitted Stage 2 report, so both must be re-tested; SC3 is an access-control check and was re-run automatically (`Final/Evidence/sc3_final.json`, 5/5 blocked, 8 Nov 2026).

| ID | Criterion (Stage 1) | Measure | Target | Pass rule with N participants |
|---|---|---|---|---|
| SC1 | Testers post a notice within 2 minutes | seconds from handing over Task card 1 to the participant saying "done", first attempt | ≤ 120 s, completed correctly, no help | met if ≥ 80 % of participants pass (Stage 1: 4 of 5). With 3 people that means 3/3; with 4 people 4/4; with 5 people 4/5 |
| SC2 | Testers find an item within 1 minute | seconds from handing over Task card 2 to the participant naming "Computer lab corridor" with the Red notebook open | ≤ 60 s, correct notice, no help | same rule |
| SC3 | Invalid-access checks are blocked | 5 scripted attempts (domain, password, anonymous, foreign edit, student removal) | 5/5 blocked | automated, not a human test |

## Who may take part
* Real people outside SE-2623's three-person team, who agree to take part (verbal consent is enough; write "yes" in the sheet).
* Record a code (T01, T02, …), never a name, email or phone number.
* AI tools, scripts, team members or invented people are **never** entered as participants.

## Set-up (observer)
1. Start the app from a **copy** of `Campus_Lost_Found` (`START.bat`), so test notices do not end up in the delivered database.
2. Participant: a normal browser window signed in as `zhanzhol.demo@astanait.edu.kz` (or `daniil.demo`/`daulet.demo`) on the noticeboard, filters cleared.
3. Observer: separate private window as `admin.demo@astanait.edu.kz`, open **User testing** (`/admin/research`) — or use a phone stopwatch.
4. Print `Campus_Lost_Found/../Testing/TASK_CARDS_EN.txt` (Task 1 and Task 2). Replace "T01" in Task 1 with the participant's code.

## Procedure (same for every participant)
1. Read: "We are testing the website, not you. Please work as you normally would. Say 'done' when you think you have finished."
2. Hand over Task card 1 → start the timer → do not help or comment → stop when they say "done" (or give up, or 3 minutes pass).
3. Write seconds, whether the result is correct, whether you helped (yes/no), device/browser, and one observation.
4. Clear the search box and filters. Hand over Task card 2 and repeat.
5. Only the first attempt counts. Failures stay in the results. Do not replace a participant to improve the score.

> Note: the built-in recorder (`/admin/research`) shows "Pending" until exactly five people and ten attempts are complete, because it enforces the Stage 1 cohort of five. With three or four people, take the durations from its table or CSV export and compute the result with the rule above.

## Recording the results
Copy every attempt into `Final/Testing/final_test_results.csv` — one row per attempt:

| column | example | meaning |
|---|---|---|
| participant_code | T01 | pseudonymous code |
| outside_team | yes | must be yes |
| consent | yes | must be yes |
| date | 2026-11-09 | date of the session |
| device | laptop | laptop / phone / tablet |
| os_browser | Windows 11 / Chrome | what was actually used |
| task | publish | `publish` or `find` |
| seconds | 84 | measured time |
| completed_correctly | yes | yes / no |
| assisted | no | yes / no |
| observation | hesitated at the date field | short, factual |

Then rebuild:

```
Campus_Lost_Found\python\python.exe -B Final\_build\build_report.py
cd Final\Presentation\source && node build_deck.js && cd ..\..\..
powershell -ExecutionPolicy Bypass -File Final\_build\export_pptx.ps1
```

The report (Section 7, pages 5 and 14), the executive summary and slide 7 update automatically from the CSV.

## Historical Stage 2 numbers
`stage2_team_reported.csv` keeps the five publish times (78, 70, 82, 88, 92 s) and five find times (45, 48, 49, 53, 47 s) the team reported for Endterm. The submitted Stage 2 report says *Pending* and no raw record exists, so these are shown only as team-reported history — never as Final results.
