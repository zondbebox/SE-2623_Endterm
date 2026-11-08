# Microsoft sign-in (Entra ID) — status and set-up

## Status on 8 Nov 2026: **code ready and tested against simulated Microsoft; not connected to a real tenant**

| What | State | Evidence |
|---|---|---|
| Code | `Campus_Lost_Found/microsoft_auth.py`, wired in `app.py` (`register_microsoft_auth`), button in `templates/login.html`, top-bar text in `templates/base.html` | local change, **not yet committed** |
| Tests | 11 tests in `test_microsoft_auth.py` with a throw-away RSA key and simulated Microsoft endpoints — all pass; full suite 94/94 | `Final/Evidence/test_suite_final.log` |
| Real server smoke test | Placeholder IDs (no real tenant): button shown, top bar says "Microsoft sign-in configured", `/auth/microsoft/login` → 302 to `https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize` with PKCE S256; the secret is not in the URL | `Final/Evidence/entra_smoke_placeholder_config.json` |
| Real sign-in with a university account | **not done** — the team has no app registration | — |
| Requirement F1 / N2 | stays **Partly** until a real account signs in | report p. 4 |

Without configuration the module is off: both routes return 404, the login page and the "No university SSO" bar are exactly as before. The code was written with an AI assistant during Final preparation; whoever commits it must be able to explain it (`Final/Defense/Defense_Zhanzhol.md` §10).

## How it works (OpenID Connect, authorization code flow + PKCE)

1. **`GET /auth/microsoft/login`** — if the browser is on `127.0.0.1`, first redirect to the redirect-URI host (`localhost`) so the session cookie is on the same host Microsoft returns to. Generate random `state`, `nonce` and a PKCE `code_verifier`; store them in the signed session; redirect to the tenant's `authorize` endpoint with `code_challenge = BASE64URL(SHA256(verifier))`, `scope=openid profile email`.
2. User signs in at Microsoft; Microsoft redirects to **`GET /auth/microsoft/callback?code=…&state=…`**.
3. The callback takes the stored values out of the session (single use), compares `state` in constant time and rejects anything older than 10 minutes.
4. Server-to-server POST to the tenant's `token` endpoint with `code`, `client_secret`, `code_verifier`.
5. **ID token checks:** `alg` must be RS256; signature verified with the tenant's published keys (JWKS, cached 1 h, refreshed once for an unknown `kid`) using a standard-library RSA PKCS#1 v1.5 check; `iss` = `https://login.microsoftonline.com/<tenant>/v2.0`; `tid` = tenant; `aud` = client ID; `exp`/`nbf` within 5 min skew; `nonce` matches; `preferred_username` (or `email`) must be a well-formed `@astanait.edu.kz` address.
6. Existing user → keeps their role (an admin stays admin). New user → `student` with a random, unusable scrypt password. Session is cleared and re-created (no session fixation); `microsoft_login_success` is written to the audit log (no tokens or secrets).
7. Any failure shows a short message on the sign-in page (HTTP 400) and signs nobody in; Microsoft error details are not shown.

## To switch it on (needs university IT)

| Needed | Who |
|---|---|
| App registration in the Astana IT University Entra tenant, "Accounts in this organizational directory only", platform **Web**, redirect URI `http://localhost:5055/auth/microsoft/callback` | University IT (tenant administrator) |
| Directory (tenant) ID and Application (client) ID | Overview page of the registration |
| A client secret | Created by IT; given to the person running the demo laptop — never in chat, email threads or Git |
| Consent for `openid profile email` | usually allowed for sign-in; otherwise the tenant admin grants it |

On the demo laptop (Windows, current terminal only):

```bat
cd Campus_Lost_Found
set CAMPUS_ENTRA_TENANT_ID=<tenant id>
set CAMPUS_ENTRA_CLIENT_ID=<client id>
set CAMPUS_ENTRA_CLIENT_SECRET=<secret value>
python\python.exe app.py
```

Open `http://localhost:5055/login` → **Sign in with Microsoft (university account)**. Optional `CAMPUS_ENTRA_REDIRECT_URI` if you use a different port (it must exactly match the registration).

**Verification to record before calling it done:** a real `@astanait.edu.kz` account signs in; `DB.bat query "SELECT email, role FROM users ORDER BY id DESC LIMIT 1;"` shows the account; `runtime/audit.jsonl` has `microsoft_login_success`; a non-university Microsoft account is refused. Add a screenshot to `Final/Evidence/` and change F1 in `report_template.html`/`Requirements_Status.md` only then.

## Known limits

* Accounts are matched by email (`preferred_username`). Microsoft recommends the immutable `oid` claim for long-term identity; adding an `entra_oid` column is the next step.
* HTTP on localhost only. A hosted version must use HTTPS, set `SESSION_COOKIE_SECURE=True` and register the HTTPS redirect URI.
* Sign-out ends the local session only; it does not sign the user out of Microsoft.
* A personal or developer tenant can prove the code works technically, but not that a user belongs to the university.

References: Microsoft Learn, *Register an application with the Microsoft identity platform* — <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app>; *OpenID Connect on the Microsoft identity platform* — <https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc> (both checked 8 Nov 2026).
