"""Behavioral tests against the delivered Flask application and real SQLite.

Run from the delivered project root with its portable interpreter:
  python/python.exe -B test_app.py

Only temporary databases/audit files are written beneath the project directory.
The delivered database, runtime secret, application and dependencies are not edited.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
if sys.platform == "win32":
    sys.path.insert(0, str(PROJECT / "vendor"))

from app import create_app
from backend.db import DEMO_PASSWORD, init_database, seed_database


class CampusApplicationIntegrationTests(unittest.TestCase):
    """A real seed per class and an independent database/application per test."""

    @classmethod
    def setUpClass(cls):
        cls.temp_root = Path(__file__).resolve().parent
        cls.temp = tempfile.TemporaryDirectory(prefix="flask-integration-", dir=cls.temp_root)
        cls.test_dir = Path(cls.temp.name).resolve()
        if not cls.test_dir.is_relative_to(cls.temp_root):
            raise RuntimeError("Temporary test directory escaped the intended work directory.")
        cls.seed_path = cls.test_dir / "seed.sqlite3"
        init_database(cls.seed_path)
        seed_database(cls.seed_path)

    @classmethod
    def tearDownClass(cls):
        # Verify the cleanup target is this class's own temporary workspace.
        if cls.test_dir.is_relative_to(cls.temp_root):
            cls.temp.cleanup()

    def setUp(self):
        self.db_path = self.test_dir / (self._testMethodName + ".sqlite3")
        self.audit_path = self.test_dir / (self._testMethodName + ".jsonl")
        with closing(sqlite3.connect(self.seed_path)) as source:
            with closing(sqlite3.connect(self.db_path)) as destination:
                source.backup(destination)
        self.app = self.new_app()
        self.client = self.app.test_client()

    def new_app(self):
        return create_app({
            "TESTING": True,
            "DATABASE": self.db_path,
            "SECRET_KEY": "test-only",
            "AUDIT_PATH": self.audit_path,
        })

    def query(self, sql, params=()):
        with closing(sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def count_notices(self):
        return self.query("SELECT COUNT(*) AS total FROM notices")[0]["total"]

    def token(self, client=None):
        client = client or self.client
        with client.session_transaction() as state:
            token = state.get("csrf")
        if token is None:
            self.assertEqual(client.get("/login").status_code, 200)
            with client.session_transaction() as state:
                token = state["csrf"]
        return token

    def login(self, email="zhanzhol.demo@astanait.edu.kz", password=DEMO_PASSWORD,
              client=None, expect_success=True):
        client = client or self.client
        response = client.post("/login", data={
            "email": email, "password": password, "csrf": self.token(client),
        })
        if expect_success:
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/")
        return response

    def post(self, path, data=None, client=None, with_csrf=True):
        client = client or self.client
        values = dict(data or {})
        if with_csrf:
            values.setdefault("csrf", self.token(client))
        return client.post(path, data=values)

    def valid_notice(self, **overrides):
        values = {
            "title": "Integration-test notebook",
            "description": "Fictional test notice with a useful identifying detail.",
            "location": "Library study area",
            "event_date": datetime.now(timezone.utc).date().isoformat(),
            "type": "found",
            "category_id": "4",
        }
        values.update(overrides)
        return values

    def create_notice(self, **overrides):
        response = self.post("/post", self.valid_notice(**overrides))
        self.assertEqual(response.status_code, 302)
        match = re.fullmatch(r"/notice/(\d+)", response.headers["Location"])
        self.assertIsNotNone(match)
        return int(match.group(1))

    def result_count(self, response):
        self.assertEqual(response.status_code, 200)
        match = re.search(r'class="count">(\d+) notices', response.get_data(as_text=True))
        self.assertIsNotNone(match, "Rendered response must include the result count.")
        return int(match.group(1))

    def test_valid_login_establishes_session_and_logout_clears_it(self):
        original_token = self.token()
        self.login()
        with self.client.session_transaction() as state:
            self.assertEqual(state["user_id"], 1)
            self.assertTrue(state.permanent)
            self.assertNotEqual(state["csrf"], original_token)
            self.assertNotIn("password", state)
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.post("/logout")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as state:
            self.assertNotIn("user_id", state)
        self.assertEqual(self.client.get("/").headers["Location"], "/login")

    def test_invalid_password_rejected_without_leaking_credentials_to_audit(self):
        private_password = "test-password-that-must-not-enter-audit"
        response = self.login(password=private_password, expect_success=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Email or password is incorrect", response.get_data(as_text=True))
        with self.client.session_transaction() as state:
            self.assertNotIn("user_id", state)
        audit = self.audit_path.read_text(encoding="utf-8")
        self.assertNotIn(private_password, audit)
        self.assertNotIn("zhanzhol.demo@astanait.edu.kz", audit)
        records = [json.loads(line) for line in audit.splitlines()]
        self.assertEqual(records[-1]["action"], "login_failed")
        self.assertNotIn("ip", records[-1])

    def test_five_failed_logins_trigger_rate_limit_on_next_attempt(self):
        for attempt in range(5):
            with self.subTest(attempt=attempt + 1):
                response = self.login(password="wrong-demo-password", expect_success=False)
                self.assertEqual(response.status_code, 200)
        response = self.login(expect_success=False)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Wait 60 seconds", response.get_data(as_text=True))
        with self.client.session_transaction() as state:
            self.assertNotIn("user_id", state)
        # The documented limiter is process-local; a new application has fresh state.
        fresh_client = self.new_app().test_client()
        self.login(client=fresh_client)

    def test_sql_injection_cannot_bypass_login(self):
        baseline = self.count_notices()
        for email, password in [
            ("' OR 1=1 --", DEMO_PASSWORD),
            ("admin.demo@astanait.edu.kz' --", DEMO_PASSWORD),
            ("zhanzhol.demo@astanait.edu.kz", "' OR '1'='1"),
        ]:
            with self.subTest(email=email):
                response = self.login(email=email, password=password, expect_success=False)
                self.assertEqual(response.status_code, 200)
                with self.client.session_transaction() as state:
                    self.assertNotIn("user_id", state)
        self.assertEqual(self.count_notices(), baseline)
        self.assertEqual(self.query("SELECT COUNT(*) AS total FROM users")[0]["total"], 20)

    def test_missing_or_wrong_csrf_rejects_write(self):
        self.login()
        baseline = self.count_notices()
        for extra in ({}, {"csrf": "forged-token"}):
            with self.subTest(token=extra):
                data = self.valid_notice(**extra)
                response = self.post("/post", data, with_csrf=False)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.count_notices(), baseline)

    def test_student_cannot_edit_or_close_another_owners_notice(self):
        self.login()
        notice = self.query("SELECT * FROM notices WHERE owner_id=2 ORDER BY id LIMIT 1")[0]
        path = f'/notice/{notice["id"]}/edit'
        self.assertEqual(self.client.get(path).status_code, 403)
        response = self.post(path, self.valid_notice(owner_id="1", title="Forged ownership edit"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.post(f'/notice/{notice["id"]}/returned', {"owner_id": "1"}).status_code, 403)
        self.assertEqual(self.query("SELECT * FROM notices WHERE id=?", (notice["id"],))[0], notice)

    def test_student_cannot_remove_notice_even_with_forged_admin_role(self):
        self.login()
        notice_id = self.query("SELECT id FROM notices ORDER BY id LIMIT 1")[0]["id"]
        path = f"/notice/{notice_id}/remove"
        baseline = self.count_notices()
        self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.post(path, {"role": "admin", "user_id": "4"}).status_code, 403)
        self.assertEqual(self.count_notices(), baseline)

    def test_owner_create_edit_and_return_persist_after_application_restart(self):
        self.login()
        baseline = self.count_notices()
        notice_id = self.create_notice(owner_id="4", status="returned")
        self.assertEqual(self.count_notices(), baseline + 1)
        row = self.query("SELECT * FROM notices WHERE id=?", (notice_id,))[0]
        self.assertEqual(row["owner_id"], 1, "Owner must come from the authenticated session.")
        self.assertEqual(row["status"], "open", "Create must not accept an arbitrary status.")
        self.assertIsNone(row["photo_filename"])
        response = self.post(f"/notice/{notice_id}/edit", self.valid_notice(
            title="Updated durable notebook", owner_id="2", category_id="1", type="lost"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.post(f"/notice/{notice_id}/returned").status_code, 302)
        fresh_client = self.new_app().test_client()
        self.login(client=fresh_client)
        detail = fresh_client.get(f"/notice/{notice_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Updated durable notebook", detail.get_data(as_text=True))
        self.assertIn("Returned", detail.get_data(as_text=True))
        row = self.query("SELECT * FROM notices WHERE id=?", (notice_id,))[0]
        self.assertEqual((row["owner_id"], row["category_id"], row["type"], row["status"]),
                         (1, 1, "lost", "returned"))

    def test_admin_confirmation_is_read_only_until_posted(self):
        self.login(email="admin.demo@astanait.edu.kz")
        notice_id = self.query("SELECT id FROM notices ORDER BY id LIMIT 1")[0]["id"]
        baseline = self.count_notices()
        confirmation = self.client.get(f"/notice/{notice_id}/remove")
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn("Confirm removal", confirmation.get_data(as_text=True))
        self.assertEqual(self.count_notices(), baseline)
        # Following the Cancel link returns to details without changing the database.
        self.assertEqual(self.client.get(f"/notice/{notice_id}").status_code, 200)
        self.assertEqual(self.count_notices(), baseline)
        response = self.post(f"/notice/{notice_id}/remove")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.count_notices(), baseline - 1)
        self.assertEqual(self.query("SELECT id FROM notices WHERE id=?", (notice_id,)), [])
        self.assertEqual(self.client.get(f"/notice/{notice_id}").status_code, 404)

    def test_search_treats_sql_and_like_metacharacters_as_literal_text(self):
        self.login()
        payload = "' OR 1=1 --"
        notice_id = self.create_notice(title=f"Notebook %_ marker {payload}")
        baseline = self.count_notices()
        for term in (payload, "%_ marker"):
            with self.subTest(search=term):
                response = self.client.get("/", query_string={"q": term})
                self.assertEqual(self.result_count(response), 1)
                self.assertIn(f'href="/notice/{notice_id}"', response.get_data(as_text=True))
        response = self.client.get("/", query_string={"q": "'; DROP TABLE notices; --"})
        self.assertEqual(self.result_count(response), 0)
        self.assertEqual(self.count_notices(), baseline)

    def test_stored_markup_is_escaped_in_browse_and_detail(self):
        self.login()
        title = '<script>alert("xss")</script>'
        description = '<img src=x onerror=alert("xss")> Fictional test description.'
        notice_id = self.create_notice(title=title, description=description)
        # Storing plain text is acceptable; rendering it must not create executable tags.
        row = self.query("SELECT title,description FROM notices WHERE id=?", (notice_id,))[0]
        self.assertEqual(row["title"], title)
        for path in ("/", f"/notice/{notice_id}"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                text = response.get_data(as_text=True)
                self.assertNotIn(title, text)
                self.assertNotIn(description, text)
                self.assertIn("&lt;script&gt;", text)
                self.assertIn("&lt;img", text)

    def test_invalid_forms_do_not_insert_records(self):
        self.login()
        baseline = self.count_notices()
        future = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        invalid_cases = [
            {"title": "  "}, {"title": "x" * 121}, {"description": "short"},
            {"location": ""}, {"category_id": "99999"}, {"category_id": "1 OR 1=1"},
            {"type": "sale"}, {"event_date": "2026-02-30"},
            {"event_date": "2019-12-31"}, {"event_date": future},
        ]
        for override in invalid_cases:
            with self.subTest(invalid=override):
                response = self.post("/post", self.valid_notice(**override))
                self.assertEqual(response.status_code, 200)
                self.assertIn('class="form-error"', response.get_data(as_text=True))
                self.assertEqual(self.count_notices(), baseline)

    def test_anonymous_requests_cannot_read_or_write_notices(self):
        baseline = self.count_notices()
        for path in ("/", "/post", "/notice/1", "/notice/1/edit", "/notice/1/remove"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/login")
        response = self.post("/post", self.valid_notice())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        self.assertEqual(self.count_notices(), baseline)

    def test_browse_rejects_numbers_that_cannot_be_bound_to_sqlite(self):
        self.login()
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        for query in (
            {"category": "9223372036854775808"},
            {"category": "9" * 100},
            {"category": "9" * 5000},
            {"category": "\u00b2"},
            {"page": "1152921504606846977"},
            {"page": "9" * 100},
        ):
            with self.subTest(field=next(iter(query)), digits=len(next(iter(query.values())))):
                response = self.client.get("/", query_string=query)
                self.assertEqual(response.status_code, 400)

    def test_browse_retains_valid_filters_pagination_and_safe_fallbacks(self):
        self.login()
        notice_ids = [self.create_notice(title=f"Boundary pagination item {index}",
                                        category_id="1", type="lost") for index in range(10)]
        query = {"q": "Boundary pagination item", "category": "1", "status": "open", "mine": "1"}
        for page, expected_ids in (("1", list(reversed(notice_ids[2:]))),
                                   ("2", list(reversed(notice_ids[:2])))):
            response = self.client.get("/", query_string={**query, "page": page})
            self.assertEqual(self.result_count(response), 10)
            self.assertEqual([int(value) for value in re.findall(
                r'href="/notice/(\d+)"', response.get_data(as_text=True))], expected_ids)
        for page in ("0", "-9223372036854775809", "9" * 5000,
                     "-" + "9" * 5000, "not-a-number"):
            with self.subTest(page_length=len(page)):
                response = self.client.get("/", query_string={**query, "page": page})
                self.assertEqual(self.result_count(response), 10)
                self.assertEqual([int(value) for value in re.findall(
                    r'href="/notice/(\d+)"', response.get_data(as_text=True))],
                    list(reversed(notice_ids[2:])))
        for category in ("2", "9223372036854775807"):
            self.assertEqual(self.result_count(self.client.get(
                "/", query_string={**query, "category": category})), 0)
        response = self.client.get("/", query_string={**query, "page": "1152921504606846976"})
        self.assertEqual(self.result_count(response), 10)
        self.assertNotRegex(response.get_data(as_text=True), r'href="/notice/\d+"')
        for category in ("-9223372036854775809", "-" + "9" * 5000):
            response = self.client.get("/", query_string={**query, "category": category})
            self.assertEqual(self.result_count(response), 10)

    def test_notice_routes_reject_out_of_range_ids_without_changing_rows(self):
        self.login(email="admin.demo@astanait.edu.kz")
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        baseline = self.query("SELECT * FROM notices ORDER BY id")
        for notice_id in ("9223372036854775807", "9223372036854775808", "9" * 100,
                          "9" * 5000, "-9223372036854775809"):
            for suffix, method in (("", "get"), ("/photo", "get"), ("/edit", "get"),
                                   ("/edit", "post"), ("/returned", "post"),
                                   ("/remove", "get"), ("/remove", "post")):
                with self.subTest(id_length=len(notice_id), suffix=suffix, method=method):
                    path = f"/notice/{notice_id}{suffix}"
                    response = (self.client.get(path) if method == "get"
                                else self.post(path, self.valid_notice()))
                    self.assertEqual(response.status_code, 404)
        self.assertEqual(self.query("SELECT * FROM notices ORDER BY id"), baseline)

    def test_out_of_range_form_categories_cannot_create_or_change_notices(self):
        self.login()
        original = self.query("SELECT * FROM notices WHERE owner_id=1 ORDER BY id LIMIT 1")[0]
        baseline = self.count_notices()
        for category in ("9223372036854775808", "9" * 100, "9" * 5000,
                         "-9223372036854775809", "-" + "9" * 5000, "\u00b2"):
            for path in ("/post", f'/notice/{original["id"]}/edit'):
                with self.subTest(path=path, category_length=len(category)):
                    response = self.post(path, self.valid_notice(category_id=category,
                                                                 event_date=original["event_date"]))
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('class="form-error"', response.get_data(as_text=True))
                    self.assertEqual(self.count_notices(), baseline)
                    self.assertEqual(self.query("SELECT * FROM notices WHERE id=?",
                                                (original["id"],))[0], original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
