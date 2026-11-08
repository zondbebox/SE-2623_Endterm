# Personal data in Campus Lost & Found and Kazakhstan law

Checked on **8 November 2026** on the official legal database Adilet (Ministry of Justice of RK). The site banner calls it a "test version" of the database; the **Russian text is authoritative**, the English page is an unofficial translation. This note separates what the sources say from our interpretation. It is not legal advice.

## Sources

| Source | URL | Note |
|---|---|---|
| Law RK No. 94-V of 21 May 2013 "On Personal Data and Their Protection" (Russian) | <https://adilet.zan.kz/rus/docs/Z1300000094> | Status: in force. Last change shown: 14.09.2026 (41 versions). |
| Same law, English (unofficial) | <https://adilet.zan.kz/eng/docs/Z1300000094> | Formatting drops some phrases (e.g. "one working day" in Art. 25). |
| Law RK No. 326-VIII of 24 June 2026 (digitalisation, personal data protection) | <https://adilet.zan.kz/rus/docs/Z2600000326> | Amended Arts. 12, 22, 25; added Art. 23-2. Exact entry-into-force dates not confirmed by us. |
| Ministry of Artificial Intelligence and Digital Development | <https://www.gov.kz/org/maidd> | Publishes personal-data guidance. The law itself defines the "authorised body" without naming a ministry; the formal designation act was not found. |

## What the law says (paraphrased)

* **Art. 1(2)** — personal data: information about a data subject, linked to one or more identifiers.
* **Arts. 7–8** — collection and processing need the subject's consent (with exceptions in Art. 7(5) and Art. 9); consent must be confirmable; after withdrawal processing stops within 15 working days (Art. 8(7)).
* **Art. 12(2)** — storage is carried out "in a database and/or digital object located on the territory of the Republic of Kazakhstan"; storage ends when the purposes of collection and processing are achieved, unless law says otherwise.
* **Art. 22** — owners, operators and third parties must take measures to prevent unauthorised access, detect it in time and minimise consequences, from collection until destruction or anonymisation.
* **Art. 25(2)(8)** (Russian text) — notify the authorised body of a personal-data security breach **within one working day** of detecting it.

## Where the data physically is in the final configuration (fact)

| Data | Personal? | Location |
|---|---|---|
| Email addresses, roles | yes | `Campus_Lost_Found/data/campus.sqlite3` → `users`, on the demo laptop's disk |
| Password hashes (scrypt) | secret | same table |
| Notices (text, campus location, date, owner link) | can be, via the owner link | same file → `notices` |
| Photos | can be (faces, ID cards) | `data/uploads/` |
| Test timings | pseudonymous (T01…) | `data/research.sqlite3` |
| Audit log | account ids + times | `runtime/audit.jsonl` |
| Backups | all of the above | `backups/*.zip` |

The laptop is used in Kazakhstan. Nothing is sent to a server. The **GitHub repository is public** and contains `campus.sqlite3` with **synthetic** accounts and demo password hashes only.

## Our interpretation (clearly ours)

* Today: only synthetic data is processed; with real students the email address + notice link would be personal data, stored on a laptop in Kazakhstan.
* Risks to avoid: (1) committing a database with real users to GitHub (servers outside Kazakhstan) — add `data/`, `runtime/`, `backups/` to `.gitignore` before any real use; (2) hosting on a foreign cloud region; (3) keeping returned notices forever.
* For a public launch: hosting in a data centre located in Kazakhstan, HTTPS, university sign-in, a consent text at registration, a retention period (e.g. delete or anonymise returned notices after a set time), and an incident procedure with a named person who can notify the authorised body within one working day. The university's lawyers should confirm.
