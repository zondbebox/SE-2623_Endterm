# Live demo plan and fallback (Part C)

Total talk: **about 8:50**, 12 slides + 4 backup slides. Every member speaks. Exact script: speaker notes in `Final/Presentation/Group_Team_ICT_FinalPresentation.pptx`; timing table: `Final/Presentation/Speaker_Timing.md`.

## Before the session (15 minutes earlier)

1. Charge the laptop; disable sleep; close chat apps and notifications; hide the browser bookmark bar (the old A4 video shows personal tabs — avoid that live).
2. Use a **copy** of the project for the demo, not the only copy: e.g. copy `SE-2623_Endterm` to `Desktop\Demo_SE-2623`. Run `RESTORE_CHECK.bat` once in the real folder to confirm a backup exists.
3. In the demo copy start `Campus_Lost_Found\START.bat`. Check `http://127.0.0.1:5055/login` opens.
4. Window A (normal): sign in as `zhanzhol.demo@astanait.edu.kz`. Window B (InPrivate/Incognito): sign in as `admin.demo@astanait.edu.kz`. Password for both: `CampusDemo!2026`. Sessions last 30 minutes — sign in no earlier than 20 minutes before your slot, or sign in again just before.
5. Have `Sources\stationery_source.jpg` ready for the photo upload.
6. Zoom the browser to 125 % so the room can read it.
7. Open the PDF of the slides as a second fallback (no PowerPoint needed).

## Demo moments

| Slide | Who | Window | Steps (≈ time) | Say |
|---|---|---|---|---|
| 4 | Zhanzhol | A (student) | Post a notice → Found, Books and Stationery, "Blue notebook (live demo)", Library second floor, today, photo → Publish (30 s) · Browse → "red notebook" + category → open (20 s) · point at Contact author (5 s) · My notices → own notice → Mark as returned (15 s) | Saved in SQLite; photo re-encoded; only the owner can close it |
| 5 | Daniil | B (admin) | Admin panel counts (10 s) · Notices → search "live demo" → open → Remove notice → Confirm removal (30 s) · Analytics (20 s) | Counts are live; nothing is deleted until the POST; synthetic data label |
| 10 | Daulet | B (admin) | Smart locker simulation → choose a Found notice → Simulate open → talk 10 s → Refresh status → OPEN TOO LONG → Simulate close (50 s) | Software simulation only; no hardware; never closes a notice automatically |

## If something fails

| Problem | Do this (do not debug in front of the class) |
|---|---|
| Page does not load | Check the server window. Close it, start `START.bat` again (≈ 20 s), sign in again. |
| "Port already in use" | Another copy is running: Ctrl+C in its window, or `python\python.exe app.py --port 5056` and use `:5056`. |
| "Too many attempts. Wait 60 seconds." | Rate limit after 5 failed logins — use the other window/account or wait 60 s. |
| "This form expired" (CSRF) | Session timed out — reload the page and sign in again. |
| Laptop or projector problem | Stay on slides 4, 5, 10: each frame is a real screenshot of the final build; narrate the same steps. |
| Need moving pictures | Play `Video/SE-2623_Campus_Lost_Found_A4.mp4` (local, 2:14) or <https://youtu.be/76M3hSqR-7w> (needs Internet). **Say first:** "This video is from Assignment 4; the interface has changed since then." |
| Wi-Fi down | Nothing changes: the app, slides and video all run offline. Only the YouTube link needs Internet. |

## Assignment 4 video — checked on 8 Nov 2026

* **Availability:** YouTube oEmbed returned HTTP 200, title "ICT Assignment 4" (unlisted link works without sign-in). Local MP4: 24,172,240 bytes, 2:14, 1920×1080, 30 fps.
* **Does it match the final version? No.** Frames extracted from the MP4 show the earlier white-and-teal interface, the old hero "Find what matters.", the top-bar label "Multimedia project / Part 2", the old plain photo field, notices "#121 Blue notebook - live database demo" and "#123 A4 video demo bottle", DevTools network throttling and an image-format comparison page. It shows **no** administrator panel, analytics, user-testing page, smart-locker simulation, registration page or the new photo picker. The browser bookmark bar with personal tabs is visible. Captions still need re-timing (`Video/subtitles_EN_PLANNED.srt`).
* **Scenes to re-record** (the brief says "update it if the system has changed"):
  1. Opening: new green noticeboard hero and "LOCAL DEMO · No university SSO" bar.
  2. Student: Post a notice with the new **Choose photo** picker (preview, size, pixels) → saved notice.
  3. Student: search + category filter → detail → Contact author → Mark as returned.
  4. Administrator (new): Admin panel counts → Notices list → Remove with confirmation.
  5. Administrator (new): Analytics with the synthetic-data label and CSV export.
  6. Smart locker simulation (new): open → 10 s → refresh → OPEN TOO LONG → close, saying "simulation".
  7. Optional: 360 px view and Motion off switch.
  8. Keep the image-format comparison only if the multimedia part is asked about; hide the bookmark bar.
* Not done by Claude: the video was **not** re-recorded or re-uploaded.
