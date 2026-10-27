import concurrent.futures
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from auth_core import (
    Store,
    QUESTIONS,
    answer_error,
    password_errors,
    issue_token,
    decode_token,
    valid_email,
)

SECRET = "test-signing-key-" * 4
PASSWORD = "StrongPwd1!"
NEW_PASSWORD = "NewStrongPwd2!"


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "auth.db"
        self.store = Store(self.path)
        self.assertTrue(
            self.store.signup(
                "alex", "alex@example.com", PASSWORD, QUESTIONS[0], "My School"
            )[0]
        )

    def tearDown(self):
        self.tmp.cleanup()

    def admin_token(self):
        return issue_token("admin", SECRET, role="admin", kind="configured_admin")

    def wrong_code(self, code):
        return "000001" if code != "000001" else "000002"

    def lock(self):
        code, _ = self.store.begin_otp("alex@example.com", SECRET)
        for _ in range(5):
            self.store.verify_otp("alex@example.com", self.wrong_code(code), SECRET)

    def test_resend_schedule_and_budget(self):
        now = 1000000
        with patch("auth_core.time.time", side_effect=lambda: now):
            for number in range(1, 6):
                code, err = self.store.begin_otp("alex@example.com", SECRET)
                self.assertIsNone(err)
                self.assertRegex(code, r"^[0-9]{6}$")
                delay = 60 if number <= 3 else 300
                self.assertEqual(self.store.code_status("alex")["resend_in"], delay)
                self.assertIsNone(self.store.begin_otp("alex@example.com", SECRET)[0])
                now += delay - 1
                self.assertIsNone(self.store.begin_otp("alex@example.com", SECRET)[0])
                self.assertEqual(self.store.code_status("alex")["requests"], number)
                now += 1
            self.assertTrue(self.store.is_locked("alex"))
            self.assertIsNone(self.store.begin_otp("alex@example.com", SECRET)[0])

    def test_fifth_code_usable(self):
        now = 1000000
        with patch("auth_core.time.time", side_effect=lambda: now):
            for number in range(1, 6):
                code, _ = self.store.begin_otp("alex@example.com", SECRET)
                if number < 5:
                    now += 60 if number <= 3 else 300
            self.assertFalse(self.store.is_locked("alex"))
            grant = self.store.verify_otp("alex@example.com", code, SECRET)
            self.assertIsInstance(grant, str)
            self.assertTrue(
                self.store.reset_password("alex@example.com", NEW_PASSWORD, grant)[0]
            )
            self.assertEqual(self.store.code_status("alex")["requests"], 0)

    def test_failures_survive_resend_and_restart(self):
        now = 1000000
        with patch("auth_core.time.time", side_effect=lambda: now):
            code, _ = self.store.begin_otp("alex@example.com", SECRET)
            for _ in range(3):
                self.store.verify_otp("alex@example.com", self.wrong_code(code), SECRET)
            now += 60
            code, _ = self.store.begin_otp("alex@example.com", SECRET)
            other = Store(self.path)
            for _ in range(2):
                other.verify_otp("alex@example.com", self.wrong_code(code), SECRET)
            self.assertTrue(other.is_locked("alex"))
            self.assertFalse(other.verify_otp("alex@example.com", code, SECRET))
            self.assertIsNone(other.authenticate("alex", PASSWORD)[0])
            self.assertFalse(other.verify_answer("alex", "My School"))

    def test_admin_unlock(self):
        self.lock()
        self.assertFalse(
            self.store.unlock_account("alex", issue_token("alex", SECRET), SECRET)[0]
        )
        self.assertFalse(
            self.store.unlock_account("alex", self.admin_token(), "wrong-key")[0]
        )
        expired = issue_token("admin", SECRET, role="admin", lifetime=-1)
        self.assertFalse(self.store.unlock_account("alex", expired, SECRET)[0])
        self.assertTrue(
            self.store.unlock_account("alex", self.admin_token(), SECRET)[0]
        )
        self.assertFalse(self.store.is_locked("alex"))
        self.assertEqual(self.store.code_status("alex")["failures"], 0)
        self.assertIsNotNone(self.store.authenticate("alex", PASSWORD)[0])
        self.assertIsNotNone(self.store.begin_otp("alex@example.com", SECRET)[0])
        self.assertTrue(
            any(
                e["event"] == "account_unlocked:alex"
                for e in self.store.recent_events()
            )
        )

    def test_blank_invisible_and_long_answers(self):
        for answer in ["    ", "\t\n", "\u200b\u200b", "\u00a0" * 4, "!!!", "é" * 40]:
            self.assertIsNotNone(answer_error(answer))
            self.assertFalse(
                self.store.signup(
                    "other", "other@example.com", PASSWORD, QUESTIONS[0], answer
                )[0]
            )
            self.assertFalse(self.store.verify_answer("alex", answer))
        self.assertTrue(self.store.verify_answer("alex", "  MY SCHOOL  "))

    def test_password_rules(self):
        for password in [
            "StrongPwd1 ",
            "StrongPwd1",
            "strongpwd1!",
            "STRONGPWD1!",
            "StrongPwd!",
            "Aa1!" + "é" * 40,
        ]:
            self.assertTrue(password_errors(password), password)
        self.assertFalse(password_errors(PASSWORD))

    def test_reset_grant_required_expiring_and_single_use(self):
        self.assertFalse(self.store.reset_password("alex@example.com", NEW_PASSWORD)[0])
        code, _ = self.store.begin_otp("alex@example.com", SECRET)
        grant = self.store.verify_otp("alex@example.com", code, SECRET)
        self.assertFalse(self.store.verify_otp("alex@example.com", code, SECRET))
        self.assertFalse(
            self.store.reset_password("alex@example.com", NEW_PASSWORD, "bad")[0]
        )
        self.assertTrue(
            self.store.reset_password("alex@example.com", NEW_PASSWORD, grant)[0]
        )
        self.assertFalse(
            self.store.reset_password("alex@example.com", "AnotherPwd3!", grant)[0]
        )
        self.assertIsNone(self.store.authenticate("alex", PASSWORD)[0])
        self.assertIsNotNone(self.store.authenticate("alex", NEW_PASSWORD)[0])
        grant = self.store.verify_answer("alex", "My School")
        with self.store.db() as c:
            c.execute("UPDATE reset_grants SET expires_at=?", (int(time.time()) - 1,))
        self.assertFalse(
            self.store.reset_password("alex@example.com", PASSWORD, grant)[0]
        )

    def test_lock_revokes_sessions_and_grants(self):
        before = self.store.user("alex")["session_version"]
        grant = self.store.verify_answer("alex", "My School")
        self.lock()
        self.assertGreater(self.store.user("alex")["session_version"], before)
        self.assertFalse(
            self.store.reset_password("alex@example.com", NEW_PASSWORD, grant)[0]
        )
        self.assertFalse(self.store.change_password("alex", PASSWORD, NEW_PASSWORD)[0])

    def test_replaced_and_expired_code(self):
        now = 1000000
        with patch("auth_core.time.time", side_effect=lambda: now):
            first, _ = self.store.begin_otp("alex@example.com", SECRET)
            now += 60
            with patch(
                "auth_core.secrets.randbelow", return_value=(int(first) + 1) % 1000000
            ):
                second, _ = self.store.begin_otp("alex@example.com", SECRET)
            self.assertFalse(self.store.verify_otp("alex@example.com", first, SECRET))
            now += 300
            self.assertFalse(self.store.verify_otp("alex@example.com", second, SECRET))

    def test_smtp_failure_retains_limits(self):
        self.store.begin_otp("alex@example.com", SECRET)
        self.store.cancel_otp("alex@example.com")
        self.assertEqual(self.store.code_status("alex")["requests"], 1)
        self.assertIsNone(self.store.begin_otp("alex@example.com", SECRET)[0])

    def test_nonempty_malformed_codes_count(self):
        self.store.begin_otp("alex@example.com", SECRET)
        self.assertFalse(self.store.verify_otp("alex@example.com", "", SECRET))
        self.assertEqual(self.store.code_status("alex")["failures"], 0)
        for _ in range(5):
            self.store.verify_otp("alex@example.com", "abcdef", SECRET)
        self.assertTrue(self.store.is_locked("alex"))

    def test_email_activation(self):
        self.store.signup(
            "newuser",
            "new@example.com",
            PASSWORD,
            QUESTIONS[0],
            "School",
            require_verification=True,
        )
        self.assertIsNone(self.store.authenticate("newuser", PASSWORD)[0])
        code, _ = self.store.begin_email_verification("new@example.com", SECRET)
        self.assertEqual(self.store.code_status("newuser", "verify")["resend_in"], 60)
        self.assertTrue(self.store.verify_email("new@example.com", code, SECRET))
        self.assertFalse(self.store.verify_email("new@example.com", code, SECRET))
        self.assertIsNotNone(self.store.authenticate("newuser", PASSWORD)[0])

    def test_duplicate_accounts_and_generic_login_errors(self):
        self.assertFalse(
            self.store.signup(
                "ALEX", "other@example.com", PASSWORD, QUESTIONS[0], "Answer"
            )[0]
        )
        self.assertFalse(
            self.store.signup(
                "other", "alex@example.com", PASSWORD, QUESTIONS[0], "Answer"
            )[0]
        )
        self.assertEqual(
            self.store.authenticate("alex", "bad")[1],
            self.store.authenticate("missing", "bad")[1],
        )
        self.assertNotIn("password_hash", self.store.list_users()[0])

    def test_login_rate_limit_shared_by_aliases(self):
        for _ in range(5):
            self.store.authenticate("alex", "bad")
        self.assertIsNone(self.store.authenticate("alex@example.com", PASSWORD)[0])

    def test_tokens_and_email(self):
        token = issue_token("alex", SECRET)
        self.assertEqual(decode_token(token, SECRET)["sub"], "alex")
        self.assertIsNone(decode_token(token, SECRET + "bad"))
        self.assertIsNone(
            decode_token(issue_token("alex", SECRET, lifetime=-1), SECRET)
        )
        self.assertTrue(valid_email("ab@cd.ef"))
        self.assertFalse(valid_email("a@b.c"))

    def test_concurrent_sends_and_single_use(self):
        def send(_):
            return Store(self.path).begin_otp("alex@example.com", SECRET)[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:
            codes = list(e.map(send, range(3)))
        self.assertEqual(sum(c is not None for c in codes), 1)
        code = next(c for c in codes if c)

        def verify(_):
            return Store(self.path).verify_otp("alex@example.com", code, SECRET)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:
            grants = list(e.map(verify, range(3)))
        self.assertEqual(sum(bool(g) for g in grants), 1)

    def test_migration_preserves_accounts(self):
        old = Path(self.tmp.name) / "old.db"
        with sqlite3.connect(old) as c:
            c.execute(
                """CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,security_question TEXT NOT NULL,answer_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,login_count INTEGER DEFAULT 0,
                last_login TEXT,previous_login TEXT,session_version INTEGER DEFAULT 0,email_verified INTEGER DEFAULT 1)"""
            )
            c.execute(
                "INSERT INTO users VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(self.store.user("alex"))[:13],
            )
        migrated = Store(old)
        self.assertIsNotNone(migrated.authenticate("alex", PASSWORD)[0])
        self.assertIsNotNone(migrated.begin_otp("alex@example.com", SECRET)[0])


if __name__ == "__main__":
    unittest.main()
