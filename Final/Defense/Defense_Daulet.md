# Защита — Bisengaliev Daulet (3–5 минут)

Твоя подтверждённая зона (таблица вкладов Stage 2, подтверждена командой): **симуляция smart locker, мультимедиа, доказательства 360 px / клавиатура / доступность (N3–N4), видео A4**. В Git твоих коммитов пока нет — всё в одном коммите `a7e5c74` с аккаунта Zhanzhol. Добавь настоящий коммит до защиты (`Final/Repository_History_Guide.md`). Общая карта: `00_System_Map.md`.

## 1. Твоё объяснение за 60 секунд (English)

"I built the smart-locker extension as a software simulation and the multimedia and device evidence. On `/admin/smart-locker` an administrator picks a 'found' notice and simulates the door. The buttons use `fetch` with the CSRF token, so the page updates without reloading. On the server, `record_simulated_event` checks the notice still exists and is 'found', then writes a row labelled SIMULATED to a separate `telemetry.sqlite3`, so sensor data never mixes with notices. If the door stays open ten seconds, the next refresh shows OPEN TOO LONG. It never marks an item returned — a person must check. If the network drops, the page says the result could not be confirmed and never re-sends the action. For multimedia, photos are re-encoded, category images are small WebP files with alt text, and animations respect 'reduce motion'."

## 2. Ключевые места в коде

| Что | Где |
|---|---|
| Таблица `locker_events`, только `SIMULATED` | `stage2_features.py` 25–33 |
| Логика open/close/heartbeat/reset | `stage2_features.py` 88–124 (`record_simulated_event`) |
| Маршрут и правило 10 с | `stage2_features.py` 216–238 |
| Кнопки без перезагрузки, таймаут 15 с, без повторной отправки | `static/locker.js` |
| Страница и дверца | `templates/smart_locker.html`, `static/locker.css` |
| CLI heartbeat | `simulate_locker.py` |
| Медиа и лицензии | `static/media/`, `static/media/CREDITS.txt`, `Sources/provenance.json` |
| Motion on/off, reduce motion | `static/motion.js`, `static/motion.css` |

## 3. Команды для демонстрации

```bat
cd Campus_Lost_Found
START.bat
python\python.exe -B simulate_locker.py --samples 2 --interval 1
python\python.exe -c "import sqlite3; c=sqlite3.connect('data/telemetry.sqlite3'); [print(r) for r in c.execute('SELECT id, door_state, event_type, notice_id, source FROM locker_events ORDER BY id DESC LIMIT 5')]"
python\python.exe -B -m unittest test_stage2_features test_media -v
```

(`simulate_locker.py` пишет только heartbeat и требует, чтобы уже было хотя бы одно состояние — сначала нажми Simulate open/close на странице.)

Сценарий (≈ 2 мин): админ → Smart locker simulation → выбрать Found-notice → Simulate open → 10 секунд объяснять 4 физических слоя (датчик → Wi-Fi/HTTPS → обработка → приложение) → Refresh status → OPEN TOO LONG → Simulate close. Затем DevTools (F12) → Network → Offline → Refresh status → сообщение «could not be confirmed» → Online → Refresh status.

## 4. Решённая проблема (подтверди сам!)

Черновик заявления: если найденное объявление, назначенное открытому шкафчику, удаляли, симуляцию нельзя было закрыть; добавлено действие «Reset unavailable assignment», которое пишет новое закрытое неназначенное состояние и сохраняет историю (`test_stage2_features.py::test_unavailable_open_locker_assignment_can_be_reset_without_erasing_history`). **Если это делал не ты — замени пример в `report_config.json`.**

## 5. Вопросы по твоей части

| Вопрос | Ответ |
|---|---|
| Is this IoT? | "It is the software half of an IoT design. There is no sensor or device; every record says SIMULATED." |
| Why a separate database? | "Telemetry has a different lifetime and purpose; keeping it apart means a sensor bug cannot corrupt notices. The notice link is checked in code because SQLite cannot enforce a foreign key across two files." |
| Why evaluate on refresh, not in the background? | "Simpler and honest for a demo; a real pilot needs a periodic rule and offline detection after 120 s." |
| What could go wrong physically? | "A missing 'close' reading creates a false alarm; a door event does not prove who took the item — so staff always verify." |
| How do you know it works on phones? | "We checked 12 pages at 360 × 760 px in Edge — no sideways scrolling — and tabbed through the post form. It was automated, not a test with screen-reader users." |
| Is the A4 video up to date? | "No. It shows the older white/teal interface without admin, analytics or locker. It is only a backup; the scenes to re-record are listed in our demo plan." |

## 6. Вопросы о частях товарищей

* **Публикация (Zhanzhol):** форма → `validate_form` → `save_photo` → параметризованный INSERT; только владелец может edit/returned (403 иначе); админ удаляет после подтверждения.
* **Поиск и аналитика (Daniil):** LIKE с экранированием, фильтры, 8 на страницу; три SQL-запроса в одной read-only транзакции; p95 44.9 мс.
* **Если сервер упадёт во время демо:** закрыть окно, `START.bat`, войти снова; или говорить по скриншотам слайда 10.

## 7. Незакрытое

Linux-скрипты не запускались на Linux (WSL на ноутбуке не установлен). Если есть двойная загрузка — запусти `bash START.sh` и `bash TESTS.sh`, сохрани вывод в `Final/Evidence/linux_run.log` и закоммить со своего аккаунта. Видео A4 не переснято.

## 8. Что сделал бы иначе

Проверял бы на реальном телефоне с первой недели и перезаписывал бы видео после каждого изменения интерфейса.

## 9. Тренировка

`Live_Change_Drills.md` — Drill 5 (объяснить часть товарища и что будет при отказе) и Drill 1 на копии.
