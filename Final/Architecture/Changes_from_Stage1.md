# A2 — Differences between the Stage 1 design and the as-built system

Diagram: `as_built_architecture.svg` (landscape, for slides) and `as_built_architecture_portrait.svg` (report page 6). Both describe commit `a7e5c74` plus the Final changes (Microsoft sign-in, LOCAL DEMO bar removed).

| Area | Stage 1 design (Stage 1 report p. 5) | Final, as built | Reason |
|---|---|---|---|
| Identity | University SSO via the university identity provider | Microsoft Entra sign-in in the university directory (OpenID Connect + PKCE), verified 8 Nov 2026; local demo accounts kept for offline demos | As planned; local accounts remain because the demo must also run without Internet |
| Network | Wi-Fi / HTTPS, DNS-resolved host | Loopback HTTP only (`127.0.0.1:5055`, trusted hosts `127.0.0.1`, `localhost`) | No certificate or host; loopback keeps unencrypted traffic off the network |
| Hosting | Prototype server, deployment "needs setup" | Waitress 3.0.2 on the demo laptop; portable Windows Python 3.14.8 bundled | Static hosts cannot run Flask + SQLite; Kazakhstan data-location rule needs a deliberate hosting choice |
| Stored data | Planned disk encryption, restricted file access | Plain SQLite files and photos under `data/` | Disk encryption is an OS setting outside the app; demo data is synthetic |
| Databases | One SQLite database + private photo files | `campus.sqlite3` + `research.sqlite3` + `telemetry.sqlite3` + `data/uploads/` | Test timings and simulated sensor events must not mix with notices |
| Administrator UI | One moderation screen with confirmation | Admin panel, notice and user lists, analytics with CSV, removal confirmation | Stage 2 required data analysis inside the product |
| Smart component | none | Smart-locker LF-01 software simulation (no hardware) | Stage 2 smart-extension task |
| Recovery | Offline copy of files | Full ZIP backup with SHA-256 manifest + non-destructive restore check | A single SQLite file is easy to lose during a demo |
| Contact | Contact via university email | `mailto:` draft to the stored owner; the site sends no email | No mail server; avoids storing messages |
| Team tools | VS Code, Git, Google Drive | Same; GitHub repository holds one upload commit | History was not committed per feature |

**Not built although discussed:** LAN access (the task description mentions an Endterm "LAN launch", but the code binds only to 127.0.0.1 and no LAN build exists in the repository or ZIP), public hosting, HTTPS, physical locker hardware.
