"""Authorization is enforced by the store, not just by visible navigation."""

import tempfile
import unittest
from pathlib import Path
from auth_core import Store, QUESTIONS, ROLES, can, issue_token, admin_credential_tag

SECRET = "test-roles-signing-key-" * 3
PASSWORD = "TestPassword123!"
ADMIN_PASSWORD = "TestAdministrator123!"


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "accounts.db")
        self.store.signup(
            "member", "member@example.com", PASSWORD, QUESTIONS[0], "School"
        )
        self.root = issue_token(
            "admin",
            SECRET,
            role="admin",
            kind="configured_admin",
            credential_tag=admin_credential_tag(ADMIN_PASSWORD, SECRET),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def token(self, username="member"):
        row = self.store.user(username)
        return issue_token(
            row["email"], SECRET, role=row["role"], version=row["session_version"]
        )

    def assign(self, role, username="member", token=None):
        return self.store.assign_role(
            username, role, token or self.root, SECRET, "admin", ADMIN_PASSWORD
        )

    def test_one_login_and_customer_default(self):
        member, error = self.store.sign_in("member@example.com", PASSWORD)
        self.assertIsNone(error)
        self.assertEqual(member["role"], "customer")
        admin, error = self.store.sign_in(
            " ADMIN ", ADMIN_PASSWORD, "admin", ADMIN_PASSWORD
        )
        self.assertIsNone(error)
        self.assertEqual(admin["role"], "admin")
        self.assertEqual(admin["principal_type"], "configured_admin")
        self.assertEqual(
            self.store.sign_in("admin", "wrong", "admin", ADMIN_PASSWORD)[1],
            self.store.sign_in("missing", "wrong")[1],
        )
        self.assertIsNone(self.store.sign_in("admin", ADMIN_PASSWORD)[0])

    def test_reserved_names(self):
        self.assertFalse(
            self.store.signup(
                "ADMIN", "other@example.com", PASSWORD, QUESTIONS[0], "School"
            )[0]
        )
        self.assertFalse(
            self.store.signup(
                "other",
                "owner@example.com",
                PASSWORD,
                QUESTIONS[0],
                "School",
                reserved_identity="owner@example.com",
            )[0]
        )

    def test_all_roles_and_session_invalidation(self):
        previous = self.token()
        for role in ROLES:
            if role == "customer":
                continue
            self.assertTrue(self.assign(role)[0])
            self.assertIsNone(self.store.session(previous, SECRET))
            row, err = self.store.sign_in("member", PASSWORD)
            self.assertIsNone(err)
            self.assertEqual(row["role"], role)
            previous = self.token()
            self.assertEqual(self.store.session(previous, SECRET)["role"], role)
        self.assertTrue(self.assign("customer")[0])
        self.assertIsNone(self.store.session(previous, SECRET))

    def test_forged_role_and_invalid_kind_rejected(self):
        forged = issue_token("member@example.com", SECRET, role="admin")
        self.assertIsNone(self.store.session(forged, SECRET))
        self.assertFalse(self.assign("admin", token=self.token())[0])
        self.assertFalse(self.assign("superadmin")[0])
        self.assertIsNone(
            self.store.session(issue_token("admin", SECRET, role="admin"), SECRET)
        )
        self.assertIsNone(
            self.store.session(self.root, SECRET, "someone-else", ADMIN_PASSWORD)
        )
        self.assertIsNone(
            self.store.session(self.root, SECRET, "admin", "ChangedPassword123!")
        )

    def test_read_permissions(self):
        for role in ("customer", "operations_manager", "freight_broker", "auditor"):
            if role != "customer":
                self.assertTrue(self.assign(role)[0])
            token = self.token()
            with self.assertRaises(PermissionError):
                self.store.visible_users(token, SECRET)
            if role == "auditor":
                self.assertTrue(self.store.audit_events(token, SECRET))
            else:
                with self.assertRaises(PermissionError):
                    self.store.audit_events(token, SECRET)
            self.assertFalse(self.store.unlock_account("member", token, SECRET)[0])
        self.assertTrue(
            self.store.visible_users(self.root, SECRET, "admin", ADMIN_PASSWORD)
        )
        self.assertFalse(can({"role": "unknown"}, "workspace"))

    def test_registered_admin_and_demotion(self):
        self.assertTrue(self.assign("admin")[0])
        admin_token = self.token()
        self.store.signup(
            "another", "another@example.com", PASSWORD, QUESTIONS[0], "School"
        )
        self.assertTrue(self.assign("auditor", "another", admin_token)[0])
        self.assertFalse(self.assign("customer", "member", admin_token)[0])
        with self.store.db() as c:
            c.execute("UPDATE users SET account_locked=1 WHERE username='another'")
        self.assertTrue(self.store.unlock_account("another", admin_token, SECRET)[0])
        self.assertTrue(self.assign("customer")[0])
        self.assertFalse(self.assign("admin", "another", admin_token)[0])
        self.assertFalse(self.store.unlock_account("another", admin_token, SECRET)[0])

    def test_unverified_or_locked_cannot_be_promoted(self):
        self.store.signup(
            "pending",
            "pending@example.com",
            PASSWORD,
            QUESTIONS[0],
            "School",
            require_verification=True,
        )
        self.assertFalse(self.assign("admin", "pending")[0])
        with self.store.db() as c:
            c.execute("UPDATE users SET account_locked=1 WHERE username='member'")
        self.assertFalse(self.assign("admin")[0])
        self.assertIsNone(self.store.session(self.token(), SECRET))

    def test_transaction_rechecks_authorization(self):
        self.assertTrue(self.assign("admin")[0])
        stale_account = self.store.session(self.token(), SECRET)
        self.assertTrue(self.assign("customer")[0])
        with self.store.db() as c:
            self.assertFalse(
                self.store._still_authorized(c, stale_account, "manage_access")
            )


if __name__ == "__main__":
    unittest.main()
