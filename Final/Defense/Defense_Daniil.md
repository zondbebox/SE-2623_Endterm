# Защита — Galitskiy Daniil (3–5 минут)

Твоя подтверждённая зона (таблица вкладов Stage 2, подтверждена командой): **просмотр и поиск, производительность (N1), SQL-аналитика, метод пользовательского теста (SC1–SC2)**. В Git ты указан соавтором (`Co-authored-by`) Final-коммитов с аккаунта Zhanzhol (`ca5d0e5` и следующий). Лучше всё же сделать и свой коммит до защиты (`Final/Repository_History_Guide.md`). Общая карта: `00_System_Map.md`.

## 1. Твоё объяснение за 60 секунд (English)

"I worked on finding things and on measuring the system. The noticeboard route `browse` in `app.py` turns the search box into a parameterised `LIKE` with `%` and `_` escaped, adds the category and status filters, and shows eight notices per page. Very large page or category numbers are rejected with HTTP 400 before SQLite sees them. For N1, `benchmark_search.py` signs in ten users and fires a hundred searches at the same time — the 95th percentile on the final code was 44.9 milliseconds against a two-second target. For analytics, three SQL questions in `backend/analytics.py` — category backlog, locations and weekly events — run in one read-only transaction and feed the admin dashboard and the CSV. And I set up the user-test method: same task cards, real people outside the team, first attempt counts."

## 2. Ключевые места в коде

| Что | Где |
|---|---|
| Поиск, фильтры, пагинация, защита от огромных чисел | `app.py` 183–211 (`browse`) |
| Три SQL-вопроса | `backend/analytics.py`; копии: `Analysis/01_category_backlog.sql`, `02_location_types.sql`, `03_weekly_events.sql` |
| Страница аналитики и CSV-защита | `analytics_routes.py` (`_csv_cell`, `analytics`, `analytics_csv`) |
| Админ-списки, поиск через `instr`, пагинация по 20 | `admin_panel.py` |
| Таймер теста, правила (T01–T99, согласие, один первый подход) | `stage2_features.py` 69–79, 133–214 |
| Бенчмарк N1 | `benchmark_search.py` |
| Карточки заданий | `Testing/TASK_CARDS_EN.txt`; протокол Final: `Final/Testing/Final_Test_Protocol.md` |

## 3. Команды для демонстрации

```bat
cd Campus_Lost_Found
DB.bat query "SELECT status, COUNT(*) AS n FROM notices GROUP BY status;"
DB.bat query "SELECT type, COUNT(*) AS n FROM notices GROUP BY type;"
DB.bat query "SELECT c.name, COUNT(n.id) AS total FROM categories c LEFT JOIN notices n ON n.category_id=c.id GROUP BY c.id ORDER BY total DESC;"
DATABASE.bat
python\python.exe -B benchmark_search.py
python\python.exe -B -m unittest test_analytics test_admin_panel -v
```

Ожидаемо: status → open 96 / returned 26; type → lost 60 / found 62 (итог 122 в обоих). `benchmark_search.py` нужен запущенный сервер; он перезаписывает `Evidence/search_performance.json` — запускай в копии.

Сценарий (≈ 2 мин): админ → Analytics → объяснить вопрос 1 и LEFT JOIN → `DB.bat query` с GROUP BY status → поменять на GROUP BY type → «итог тот же, график связан с базой».

## 4. Решённая проблема (подтверди сам!)

Черновик заявления: огромные числа в фильтрах category/page приводили к ошибке переполнения SQLite; добавлены проверки диапазона (400/404) и 4 регрессионных теста (`test_app.py`: `test_browse_rejects_numbers_that_cannot_be_bound_to_sqlite`, `test_browse_retains_valid_filters_pagination_and_safe_fallbacks`, `test_notice_routes_reject_out_of_range_ids_without_changing_rows`, `test_out_of_range_form_categories_cannot_create_or_change_notices`). **Если это делал не ты — замени пример в `report_config.json`.**

## 5. Вопросы по твоей части

| Вопрос | Ответ |
|---|---|
| Why LEFT JOIN in question 1? | "So categories with zero notices still appear; `COUNT(n.id)` counts only real notices, not the empty joined row." |
| Is p95 45 ms realistic for users? | "It is server response over loopback, without images or rendering, with 10 users. It proves N1 as written; it does not predict a phone on mobile data or 10,000 users." |
| Why is analytics data 'synthetic'? | "The notices were generated for teaching; the pattern (Electronics all returned) comes from the generator, not from campus behaviour." |
| What did the analysis change? | "It showed free-text locations split one place into two labels; the fix is a fixed list of locations." |
| How is the user test fair? | "Same cards, people outside the team, timer from card to 'done', no coaching, first attempt only, failures kept. AI and team members are never participants." |
| Why does the recorder say Pending with 3 people? | "It enforces the Stage 1 cohort of five; with three to five people we apply the 80 % rule from the protocol." |

## 6. Вопросы о частях товарищей

* **Вход и фото (Zhanzhol):** scrypt, CSRF на каждом POST, rate limit 5/мин, фото перекодируется и хранится под случайным именем, отдаётся только после входа.
* **Locker (Daulet):** fetch без перезагрузки, отдельная `telemetry.sqlite3`, предупреждение после 10 с при запросе страницы, без оборудования; при обрыве сети POST не повторяется автоматически.
* **Если аналитика упадёт:** она открывает базу только для чтения — сломать объявления не может; студент получает 403.

## 7. Незакрытое

SC1/SC2 выполнены: T01–T03 (вне команды, с согласия), публикация 89/84/78 с, поиск 40/45/42 с, без помощи → 3/3 и 3/3. Держи под рукой исходные записи наблюдателя. Выборка — минимум брифа (3), цель Stage 1 писалась на 5 человек — скажи это сам. Числа Endterm (78–92 с, 45–53 с) — только «team-reported», сырых записей нет.

## 8. Что сделал бы иначе

Запустил бы тест с реальными пользователями на 7-й неделе и сразу сохранял бы сырые записи (CSV рекордера).

## 9. Тренировка

`Live_Change_Drills.md` — Drill 3 (запрос: поиск ещё и по location) и Drill 2 (правило валидации). Отрепетируй на копии.
