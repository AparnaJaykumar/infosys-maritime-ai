import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from auth_core import Store, QUESTIONS

SECRET = "ui-test-key-" * 5
PASSWORD = "StrongPwd1!"
ADMIN_PASSWORD = "AdminForTests123!"
ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "JWT_SECRET": SECRET,
                "ADMIN_PASSWORD": ADMIN_PASSWORD,
                "ADMIN_USERNAME": "admin",
                "DATABASE_PATH": str(Path(self.tmp.name) / "auth.db"),
                "REQUIRE_EMAIL_VERIFICATION": "0",
                "EMAIL_ADDRESS": "sender@example.com",
                "EMAIL_PASSWORD": "test-only",
            },
        )
        self.env.start()
        self.smtp = patch("smtplib.SMTP_SSL")
        self.smtp_mock = self.smtp.start()
        self.smtp_mock.return_value.__enter__.return_value.send_message.return_value = (
            {}
        )
        self.at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=25).run()
        self.store = Store(os.environ["DATABASE_PATH"])
        self.assert_clean()

    def tearDown(self):
        self.smtp.stop()
        self.env.stop()
        self.tmp.cleanup()

    def assert_clean(self):
        self.assertEqual(len(self.at.exception), 0, str(self.at.exception))

    def click(self, label):
        next(x for x in self.at.button if x.label == label).click().run()
        self.assert_clean()

    def field(self, label, value):
        next(x for x in self.at.text_input if x.label == label).set_value(value)

    def seed(self):
        self.assertTrue(
            self.store.signup(
                "alex", "alex@example.com", PASSWORD, QUESTIONS[0], "My School"
            )[0]
        )

    def test_lock_closes_recovery_with_one_notice(self):
        self.seed()
        self.click("Forgot password?")
        self.field("Registered email", "alex@example.com")
        self.click("Send code")
        email = (
            self.smtp_mock.return_value.__enter__.return_value.send_message.call_args[
                0
            ][0]
        )
        code = re.search(r"\b[0-9]{6}\b", email.get_content()).group()
        wrong = "000001" if code != "000001" else "000002"
        for _ in range(4):
            self.store.verify_otp("alex@example.com", wrong, SECRET)
        self.field("Six-digit OTP", wrong)
        self.click("Verify code")
        self.assertTrue(self.store.is_locked("alex"))
        self.assertEqual(sum("Account locked" in e.value for e in self.at.error), 1)
        self.assertFalse(
            any(
                x.label in ("Verify code", "Send code", "Resend code")
                for x in self.at.button
            )
        )
        self.assertFalse(any(x.label == "Six-digit OTP" for x in self.at.text_input))
        self.click("Back to sign in")

    def test_motion_controls_and_theme(self):
        self.assertTrue(self.at.session_state["motion_enabled"])
        self.click("Pause motion")
        self.assertFalse(self.at.session_state["motion_enabled"])
        self.click("☾ Dark")
        self.assertEqual(self.at.session_state["theme"], "Dark")
        self.assertFalse(self.at.session_state["motion_enabled"])
        self.click("Resume motion")
        self.assertTrue(self.at.session_state["motion_enabled"])
        self.click("☀ Light")
        self.assertEqual(self.at.session_state["theme"], "Light")

    def test_signup_blank_answer_and_user_login(self):
        self.click("Create account")
        for label, value in [
            ("Username", "alex"),
            ("Email address", "alex@example.com"),
            ("Password", PASSWORD),
            ("Confirm password", PASSWORD),
            ("Security answer", "    "),
        ]:
            self.field(label, value)
        self.at.selectbox[0].select(QUESTIONS[0])
        self.click("Create account →")
        self.assertIsNone(self.store.user("alex"))
        self.assertTrue(len(self.at.error))
        self.field("Security answer", "My School")
        self.click("Create account →")
        self.field("Username or email", "alex")
        self.field("Password", PASSWORD)
        self.click("Sign in →")
        self.assertTrue(any(x.label == "Log out" for x in self.at.button))
        self.click("Log out")
        self.assertTrue(any(x.label == "Sign in →" for x in self.at.button))

    def test_otp_reset_and_admin_unlock(self):
        self.seed()
        self.click("Forgot password?")
        self.field("Registered email", "alex@example.com")
        self.click("Send code")
        email = (
            self.smtp_mock.return_value.__enter__.return_value.send_message.call_args[
                0
            ][0]
        )
        code = re.search(r"\b[0-9]{6}\b", email.get_content()).group()
        self.assertTrue(
            next(x for x in self.at.button if x.label == "Resend code").disabled
        )
        self.field("Six-digit OTP", code)
        self.click("Verify code")
        self.field("New password", "NewStrongPwd2!")
        self.field("Confirm new password", "NewStrongPwd2!")
        self.click("Reset password")
        self.assertIsNotNone(self.store.authenticate("alex", "NewStrongPwd2!")[0])
        # Lock the same account, then unlock it using the actual admin interface.
        code, _ = self.store.begin_otp("alex@example.com", SECRET)
        wrong = "000001" if code != "000001" else "000002"
        for _ in range(5):
            self.store.verify_otp("alex@example.com", wrong, SECRET)
        self.field("Username or email", "admin")
        self.field("Password", ADMIN_PASSWORD)
        self.click("Sign in →")
        self.at.radio[0].set_value("User management").run()
        self.assert_clean()
        self.assertTrue(self.store.is_locked("alex"))
        self.assertTrue(len(self.at.dataframe))
        self.click("Unlock account")
        self.assertFalse(self.store.is_locked("alex"))

    def test_single_login_role_navigation_and_revocation(self):
        from auth_core import issue_token

        self.seed()
        self.assertFalse(any("Admin sign" in x.label for x in self.at.button))
        root = issue_token("admin", SECRET, role="admin", kind="configured_admin")
        for role in ("operations_manager", "freight_broker", "auditor", "admin"):
            self.assertTrue(self.store.assign_role("alex", role, root, SECRET)[0])
            self.field("Username or email", "alex@example.com")
            self.field("Password", PASSWORD)
            self.click("Sign in →")
            choices = self.at.radio[0].options
            self.assertEqual("User management" in choices, role == "admin")
            self.assertEqual("Audit trail" in choices, role in ("admin", "auditor"))
            self.at.radio[0].set_value("My profile").run()
            self.assert_clean()
            self.at.radio[0].set_value("Security").run()
            self.assert_clean()
            self.assertTrue(
                any(x.label == "Current password" for x in self.at.text_input)
            )
            self.click("Log out")
        self.field("Username or email", "alex")
        self.field("Password", PASSWORD)
        self.click("Sign in →")
        self.assertTrue(self.store.assign_role("alex", "customer", root, SECRET)[0])
        self.at.run()
        self.assert_clean()
        self.assertTrue(any(x.label == "Sign in →" for x in self.at.button))
        self.assertFalse(any(x.label == "Log out" for x in self.at.button))

    def test_security_question_rejects_blank_then_resets(self):
        self.seed()
        self.click("Forgot password?")
        self.at.radio[0].set_value("Security question").run()
        self.assert_clean()
        self.field("Registered username", "alex")
        self.click("Find security question")
        self.field("Your answer", "    ")
        self.click("Verify answer")
        self.assertTrue(
            any("Enter a security answer" in e.value for e in self.at.error)
        )
        self.field("Your answer", "  MY SCHOOL  ")
        self.click("Verify answer")
        self.field("New password", "NewStrongPwd2!")
        self.field("Confirm new password", "NewStrongPwd2!")
        self.click("Reset password")
        self.assertIsNotNone(self.store.authenticate("alex", "NewStrongPwd2!")[0])

    def test_signup_activation_email_flow(self):
        os.environ["REQUIRE_EMAIL_VERIFICATION"] = "1"
        self.click("Create account")
        for label, value in [
            ("Username", "newuser"),
            ("Email address", "new@example.com"),
            ("Password", PASSWORD),
            ("Confirm password", PASSWORD),
            ("Security answer", "School"),
        ]:
            self.field(label, value)
        self.at.selectbox[0].select(QUESTIONS[0])
        self.click("Create account →")
        self.assertEqual(self.store.user("newuser")["email_verified"], 0)
        mail = (
            self.smtp_mock.return_value.__enter__.return_value.send_message.call_args[
                0
            ][0]
        )
        code = re.search(r"\b[0-9]{6}\b", mail.get_content()).group()
        self.field("Six-digit code", code)
        self.click("Verify email")
        self.assertEqual(self.store.user("newuser")["email_verified"], 1)
        self.assertTrue(any(x.label == "Sign in →" for x in self.at.button))


if __name__ == "__main__":
    unittest.main()
