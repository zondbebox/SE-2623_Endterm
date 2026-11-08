# Защита — Mengdigerey Zhanzhol (3–5 минут)

Твоя подтверждённая зона (таблица вкладов Stage 2, подтверждена командой): **аккаунты и вход, публикация/редактирование объявлений, фото, права владельца/админа, backup** (F1–F3, F6–F8, N2). Единственный коммит `a7e5c74` загружен с твоего аккаунта `zondbebox`. Общая карта: `00_System_Map.md`.

## 1. Твоё объяснение за 60 секунд (English, говорить вслух)

"I built the account and notice workflow. Registration in `app.py` accepts only a well-formed `@astanait.edu.kz` address and a 12-to-128-character password, and stores a scrypt hash — never the password. Login uses a constant-time check with a dummy hash for unknown emails and is rate-limited to five failures per minute. Every POST must carry the CSRF token from the session. When a student publishes, `validate_form` checks lengths, the date and the category, `save_photo` validates and re-encodes one JPG or PNG, and a parameterised INSERT saves the row. Only the owner can edit or mark returned — `require_owner` returns 403 for anyone else — and only an admin can remove a notice, after a confirmation page. I also built the full backup with a SHA-256 manifest and a restore check that never overwrites live data."

## 2. Ключевые места в коде (открыть заранее в VS Code)

| Что | Где |
|---|---|
| Флаги cookie, 30 мин, trusted hosts | `app.py` 29–33 |
| CSRF-проверка на каждый POST | `app.py` 71–80 (`security`) |
| Заголовки CSP, nosniff | `app.py` 83–88 |
| Регистрация | `app.py` 112–144 |
| Вход + rate limit + dummy hash | `app.py` 147–173 |
| Проверка владельца | `app.py` 106–109 (`require_owner`) |
| Фото: тип, 5 MiB, 12 MP, перекодирование, случайное имя | `app.py` 239–277 (`save_photo`) |
| Валидация формы | `app.py` 279–295 |
| Создание / редактирование / returned / remove | `app.py` 297–362 |
| Таблицы и CHECK | `backend/schema.sql` |
| Backup / restore check | `backup_full.py`, `backup_tools.py`, `BACKUP.bat`, `RESTORE_CHECK.bat` |

## 3. Команды для демонстрации своей части

```bat
cd Campus_Lost_Found
START.bat
DB.bat query "SELECT id, title, status, photo_filename FROM notices ORDER BY id DESC LIMIT 3;"
DB.bat query "SELECT email, substr(password_hash,1,7) AS algo, role FROM users LIMIT 3;"
BACKUP.bat
RESTORE_CHECK.bat
python\python.exe -B -m unittest test_app test_stage2_core -v
```

Сценарий (≈ 2 мин): войти студентом → Post a notice с фото → показать строку в БД (`DB.bat query …`) → Mark as returned → во втором окне войти `daniil.demo` и открыть `/notice/<id>/edit` → 403 → показать `require_owner`.

## 4. Решённая проблема (для заявления — подтверди сам!)

Черновик заявления говорит: backup writer и restore reader имели разные лимиты manifest; ты сделал общий лимит 1 MiB и 3 регрессионных теста (`test_backup_full.py`: `test_backup_rejects_oversized_manifest_before_publishing_archive`, `test_restore_rejects_manifest_above_shared_limit_without_destination`, `test_manifest_at_shared_limit_can_be_written_and_restored`). **Если это исправлял не ты — замени пример в `Final/_build/report_config.json` на свой реальный и пересобери отчёт.**

## 5. Вопросы по твоей части и сильные ответы

| Вопрос | Ответ (English) |
|---|---|
| Why scrypt and not MD5/SHA-256? | "scrypt is deliberately slow and memory-hard, so stolen hashes are expensive to brute-force; a plain SHA-256 is fast to guess." |
| What is the dummy hash for? | "When the email does not exist we still run a hash check, so response time does not reveal which emails are registered." |
| What is CSRF and how do you stop it? | "A foreign site could make your browser POST to us with your cookie. Every form carries a random token from the session; we compare it with `hmac.compare_digest`; a missing or wrong token gives 400." |
| Why re-encode photos? | "To drop hidden metadata like GPS and to make sure we store real pixels, not a disguised file." |
| Does the domain check prove identity? | "No. It only checks the format. Real proof needs university Entra sign-in — that is why F1 is Partly." |
| What if two people edit at once? | "The last save wins; the UPDATE also checks `owner_id`, so only the owner's save is accepted." |

## 6. Вопросы о частях товарищей

* **Поиск (Daniil):** "`browse` builds a WHERE clause from the search text with escaped `%` and `_`, optional category and status, then `LIMIT 8 OFFSET`. Huge numbers are rejected with 400 before SQLite sees them."
* **Аналитика (Daniil):** "Three SQL queries in `backend/analytics.py`, run in one read-only transaction, so the four counts and three charts are consistent. Admin only; CSV cells starting with = + − @ are prefixed."
* **Locker (Daulet):** "Admin buttons post via `fetch` with the CSRF token; the server checks the notice is 'found' and writes a SIMULATED row in `telemetry.sqlite3`. Warning after 10 s, evaluated when the page is requested. No hardware."
* **Отказ:** если упал сервер → `START.bat` снова; если повреждён backup → restore check отказывает ещё до создания папки.

## 7. Незакрытое из Stage 1

Незакрытых Must нет: F1 закрыт в Final — вход через Microsoft (§10) проверен реальной учёткой 8.11.2026. Риск был записан ещё в Stage 1 («SSO approval is delayed → clearly label simulated sign-in»). Инструкция: `Final/SSO/`.

## 8. Что сделал бы иначе

Коммитил бы каждую функцию отдельно и попросил бы товарищей коммитить со своих аккаунтов с первой недели.

## 9. Тренировка живых изменений

`Live_Change_Drills.md` — Drill 1 (поле Colour) именно в твоих файлах (`app.py`, `form.html`, `schema.sql`). Отрепетируй дважды на копии; цель — < 5 минут.

## 10. Вход через Microsoft — объяснить за 60 секунд (English)

Код `Campus_Lost_Found/microsoft_auth.py` написан при подготовке Final с помощью ИИ-ассистента. Это зона аккаунтов — если коммитишь ты, ты должен уметь его объяснить. Честно скажи на защите, что использовался ИИ-ассистент; вход проверен твоей реальной учёткой 8 ноября.

"We added optional Microsoft sign-in with OpenID Connect. It is off unless three environment variables are set, so without them nothing changes. The login route creates a random state, nonce and PKCE verifier, keeps them in the signed session, and sends the user to Microsoft's authorize endpoint. On the callback we check the state, exchange the code for tokens on the server with the client secret and the PKCE verifier, and then validate the ID token: RS256 signature against Microsoft's published keys, issuer and tenant, audience, expiry, nonce, and that the email is an astanait.edu.kz address. A new user becomes a student; an existing admin keeps the admin role. We registered the app in the university Entra directory, tested it with 13 tests against a simulated Microsoft, and on 8 November signed in with a real university account. The header shows the Microsoft display name, which we keep only in the session."

| Вопрос | Ответ |
|---|---|
| What is PKCE for? | "The code alone is useless without the verifier that only our server knows, so a stolen code cannot be redeemed." |
| Why state and nonce? | "state stops a forged callback (CSRF on login); nonce ties the ID token to this sign-in, so an old token cannot be replayed." |
| Why check the signature if the token came over HTTPS? | "Defence in depth: we verify it with Microsoft's public keys, so a tampered or foreign token is refused — tested with a wrong key." |
| Where is the secret? | "Only in an environment variable on the demo laptop. Not in code, Git or the audit log; the test checks it is not in the redirect URL." |
| Why 127.0.0.1 → localhost redirect? | "Cookies are per host. Microsoft returns to localhost, so the session must already live there." |
| What if Microsoft or Wi-Fi is down? | "START.bat runs without Microsoft: the button is hidden and demo accounts still work." |
| Why can't people self-register now? | "In Microsoft mode every new account must come from the university directory, so nobody can claim someone else's address." |

Демо (если спросят): `python\python.exe -B test_microsoft_auth.py` → 13 OK; открыть `microsoft_auth.py` функции `login`, `callback`, `validate_id_token`.
