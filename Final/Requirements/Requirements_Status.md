# A1 — Final requirement status

**System version assessed:** GitHub `zondbebox/SE-2623_Endterm`, branch `main`, commit `a7e5c749095e63e1cff1280b95279ca8bae6e447` (6 Nov 2026, only commit). The ZIP `SE-2623_Endterm.zip` (8 Nov 2026) was compared file-by-file with this commit: 1,164 files, 0 differences. The Final package does not change application code.

**Source of IDs, wording and priority:** Stage 1 Midterm report (9 Oct 2026), pages 3–4 (`Sources/Briefs/Stage1_Midterm_Portrait.pdf`). Stage 2 status: Stage 2 report, pages 5–6 (`SE-2623_CampusLostFound_ICT_ProjectStage2.pdf`).

**Instructor comments on Stage 1:** none were reported by the team (Stage 2 report p. 9; `Evidence/stage1_requirements.json`). If the team received written comments, add them to section C below.

**Evidence folder:** `Final/Evidence/` (re-run on 8 Nov 2026 against an isolated copy of the commit above).

## A. Functional requirements

| ID | Requirement (Stage 1 wording) | Priority | Stage 2 status | Final status | Evidence |
|---|---|---|---|---|---|
| F1 | University account sign-in. Check: reject identities outside astanait.edu.kz | Must | Partly | **Done** — sign-in with Astana IT University Microsoft accounts (Entra ID, OpenID Connect + PKCE), verified with a real account on 8 Nov 2026; other domains rejected | `test_stage2_core.py::test_registration_rejects_invalid_domain_syntax_and_password_lengths`; `Evidence/sc3_final.json` SC3-1; screenshot `S01_login.png`; Microsoft sign-in code: `test_microsoft_auth.py` (11 tests, simulated) |
| F2 | Publish a lost or found notice. Check: a valid notice appears in the list | Must | Done | **Done** | `test_app.py::test_owner_create_edit_and_return_persist_after_application_restart`; screenshots `S04_post_form.png`, `S05_notice_created.png` |
| F3 | Attach one photo. Check: accept JPG/PNG up to 5 MB | Should | Done | **Done** | `test_stage2_core.py::test_photo_file_limit_pixel_limit_and_request_limit`, `::test_png_photo_is_supported`; screenshot `S04_post_form.png` (photo picker), `S05_notice_created.png` |
| F4 | Browse notices and open details. Check: list and details show saved content | Must | Done | **Done** | `test_app.py::test_stored_markup_is_escaped_in_browse_and_detail`; screenshots `S02_browse.png`, `S06_search_result.png` |
| F5 | Search title; filter by category. Check: seeded matching notices appear | Must | Done | **Done** | `test_app.py::test_search_treats_sql_and_like_metacharacters_as_literal_text`, `::test_browse_retains_valid_filters_pagination_and_safe_fallbacks`; screenshot `S06_search_result.png` |
| F6 | Contact via university email. Check: contact opens the author's email | Must | Done | **Done** (the link opens a `mailto:` draft to the stored owner; the site sends no email) | `test_stage2_core.py::test_contact_is_mailto_and_admin_navigation_is_not_shown_to_student`; `Evidence/browser_checks.json` (mailto href); screenshot `S07_detail_contact.png` |
| F7 | Edit own notice; mark returned. Check: owner changes persist after refresh | Must | Done | **Done** | `test_app.py::test_owner_create_edit_and_return_persist_after_application_restart`, `::test_student_cannot_edit_or_close_another_owners_notice`; screenshot `S08_returned.png` |
| F8 | Administrator removes misuse. Check: admin succeeds; student is denied | Must | Done | **Done** | `test_app.py::test_admin_confirmation_is_read_only_until_posted`, `::test_student_cannot_remove_notice_even_with_forged_admin_role`; `Evidence/sc3_final.json` SC3-5; screenshots `S11_admin_notices.png`, `S12_remove_confirm.png` |

## B. Non-functional requirements (all Must in Stage 1)

| ID | Requirement | Priority | Stage 2 status | Final status | Evidence |
|---|---|---|---|---|---|
| N1 | Search p95 ≤ 2 s with 10 concurrent users (repeated searches on the demo laptop) | Must | Done (p95 81.47 ms, 30 Oct) | **Done** — p95 44.87 ms, max 54.60 ms, 100 requests from 10 authenticated sessions (8 Nov 2026) | `Evidence/search_performance_final.json` (`benchmark_search.py`). Loopback HTTP; assets and painting excluded |
| N2 | Enforce university identity and owner/admin rights | Must | Partly | **Done** — identity via university Microsoft sign-in (new accounts only that way in Microsoft mode); owner/admin rights enforced (5/5 blocked; 96/96 tests). Synthetic demo accounts kept for the offline demo | `Evidence/sc3_final.json`; `Evidence/account_checks.json`; `Evidence/test_suite_final.log` |
| N3 | Support 360 px screens and keyboard input (core screens, labels, focus order) | Must | Partly | see `Evidence/browser_checks.json` — filled after the browser check run (automated browser evidence, not a human accessibility audit) | `Evidence/browser_checks.json`; screenshots `M01–M03` (360 px) |
| N4 | Pass 20/20 checks during a 30-minute demo (core pages plus retry when offline) | Must | Partly (20/20 HTTP; offline retry not covered) | see `Evidence/stability_30min_final.json` and the offline/retry part of `Evidence/browser_checks.json` | as listed |

## C. Requirements not fully done — one-sentence reasons

* **F1 / N2:** closed in the Final by Microsoft Entra sign-in (verified 8 Nov 2026). No Must requirement remains open.
* Instructor comment from Stage 1 not addressed: none reported (team to confirm).

## D. Success criteria (Stage 1) — see `Final/Testing/Final_Test_Results.md`

| ID | Criterion | Target | Stage 2 result | Final result |
|---|---|---|---|---|
| SC1 | Testers post a notice within 2 minutes | ≥ 4/5 (≥ 80 %), ≤ 120 s | Official Stage 2 report: **Pending**. Team-reported (no raw record in the package): 5/5 | **3/3 ✓ Met** (89, 84, 78 s; T01–T03, 6–7 Nov 2026) |
| SC2 | Testers find an item within 1 minute | ≥ 4/5 (≥ 80 %), ≤ 60 s | Official Stage 2 report: **Pending**. Team-reported (no raw record in the package): 5/5 | **3/3 ✓ Met** (40, 45, 42 s; T01–T03) |
| SC3 | Invalid-access checks are blocked | 5/5 | 5/5 | **5/5** (8 Nov 2026, `Evidence/sc3_final.json`) |
