# Microsoft sign-in (Entra ID) — status and set-up

## Status: **working — verified 8 Nov 2026, 16:40 UTC**

| What | State | Evidence |
|---|---|---|
| App registration | Single-tenant web app "Campus Lost & Found SE-2623" in the Astana IT University Entra directory, created by a team member; redirect URI `http://localhost:5055/auth/microsoft/callback` | tenant and client IDs in `START_MICROSOFT.bat` (IDs are not secrets) |
| Real sign-in | A real `@astanait.edu.kz` account signed in; a student row was created; audit `microsoft_login_success` | `runtime/audit.jsonl` on the demo laptop (not in Git) |
| Code | `microsoft_auth.py`; Microsoft display name shown in the header (session only, not stored); local self-registration closed while Microsoft sign-in is on | `main` branch |
| Tests | 13 tests with simulated Microsoft (signature, issuer, tenant, audience, expiry, nonce, domain, PKCE, single-use state, escaping, registration closed); full suite 96/96 | `Final/Evidence/test_suite_final.log` |
| Requirement F1 / N2 | **Done** | report pp. 4–5 |

**Secret hygiene.** One client secret was accidentally pasted into a chat. It must be deleted in Entra (Certificates & secrets) and replaced. Secrets are typed into `START_MICROSOFT.bat` at start-up only.

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

**How it was verified (repeat before the defense):** a real `@astanait.edu.kz` account signs in; `DB.bat query "SELECT email, role FROM users ORDER BY id DESC LIMIT 1;"` shows the account; `runtime/audit.jsonl` has `microsoft_login_success`; a non-university Microsoft account is refused. Add a screenshot to `Final/Evidence/` and change F1 in `report_template.html`/`Requirements_Status.md` only then.

## Known limits

* Accounts are matched by email (`preferred_username`). Microsoft recommends the immutable `oid` claim for long-term identity; adding an `entra_oid` column is the next step.
* HTTP on localhost only. A hosted version must use HTTPS, set `SESSION_COOKIE_SECURE=True` and register the HTTPS redirect URI.
* Sign-out ends the local session only; it does not sign the user out of Microsoft.
* A personal or developer tenant can prove the code works technically, but not that a user belongs to the university.

References: Microsoft Learn, *Register an application with the Microsoft identity platform* — <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app>; *OpenID Connect on the Microsoft identity platform* — <https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc> (both checked 8 Nov 2026).
