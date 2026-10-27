"""FreightQuote AI account store, JWT sessions and email verification.

SQLite is used for the single-instance milestone build. Never store plaintext
passwords, OTPs, recovery answers or secret values in the database.
"""

import datetime as dt
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import bcrypt
import jwt

EMAIL_RE = re.compile(
    r"^[A-Za-z]{2,}[A-Za-z0-9._%+\-]*@[A-Za-z]{2,}[A-Za-z0-9\-]*(?:\.[A-Za-z]{2,}[A-Za-z0-9\-]*)+$"
)
QUESTIONS = [
    "What was the name of your first school?",
    "In which city were you born?",
    "What was the name of your first pet?",
    "What is the middle name of your oldest sibling?",
]
GENERIC_LOGIN_ERROR = "Invalid username/email or password."
UTC = dt.timezone.utc
LOCKED_MESSAGE = "Account locked. Contact the administrator to unlock it."
OTP_TTL = 300
MAX_OTP_REQUESTS = 5
MAX_OTP_FAILURES = 5

ROLES = {
    "customer": "Customer",
    "operations_manager": "Operations Manager",
    "freight_broker": "Freight Broker",
    "auditor": "Auditor",
    "admin": "Admin",
}
ROLE_PERMISSIONS = {
    role: frozenset(
        {"profile", "security", "workspace"}
        | ({"users", "manage_access", "audit"} if role == "admin" else set())
        | ({"audit"} if role == "auditor" else set())
    )
    for role in ROLES
}


def can(account, permission):
    return bool(account and permission in ROLE_PERMISSIONS.get(account.get("role"), ()))


def admin_credential_tag(password, secret):
    return hmac.new(
        secret.encode(), ("admin:" + password).encode(), hashlib.sha256
    ).hexdigest()


def clean_answer(value):
    """Ignore case and surrounding whitespace; reject invisible-only answers."""
    value = unicodedata.normalize("NFKC", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Cf")
    return value.strip().casefold()


def answer_error(value):
    cleaned = clean_answer(value)
    if not cleaned or not any(ch.isalnum() for ch in cleaned):
        return "Enter a security answer containing a letter or number."
    if len(cleaned.encode("utf-8")) > 72:
        return "Security answer is too long (maximum 72 UTF-8 bytes)."
    return None


def utcnow():
    return dt.datetime.now(UTC).isoformat()


def valid_email(value):
    return (
        isinstance(value, str)
        and len(value.strip()) <= 254
        and bool(EMAIL_RE.fullmatch(value.strip()))
    )


def password_errors(password):
    issues = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if len(password.encode("utf-8")) > 72:
        issues.append("no more than 72 UTF-8 bytes")
    if not re.search(r"[A-Z]", password):
        issues.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        issues.append("one lowercase letter")
    if not re.search(r"[0-9]", password):
        issues.append("one number")
    if not any(
        not ch.isalnum()
        and not ch.isspace()
        and not unicodedata.category(ch).startswith("C")
        for ch in password
    ):
        issues.append("one special symbol (spaces do not count)")
    if any(ch.isspace() or unicodedata.category(ch).startswith("C") for ch in password):
        issues.append("no whitespace or invisible characters")
    return issues


def hashed(text):
    return bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def matches(text, saved):
    try:
        if len(text.encode("utf-8")) > 72:
            return False
        return bcrypt.checkpw(text.encode("utf-8"), saved.encode("ascii"))
    except (ValueError, TypeError, AttributeError):
        return False


def otp_digest(code, salt, secret, purpose="reset"):
    return hmac.new(
        secret.encode(), f"{purpose}:{salt}:{code}".encode(), hashlib.sha256
    ).hexdigest()


class Store:
    def __init__(self, path="auth.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=20000")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self):
        with self.db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                security_question TEXT NOT NULL,
                answer_hash TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                login_count INTEGER DEFAULT 0, last_login TEXT,
                previous_login TEXT, session_version INTEGER DEFAULT 0,
                email_verified INTEGER DEFAULT 1
            )""")
            # Upgrade existing milestone databases without dropping accounts.
            cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
            for name, ddl in (
                ("previous_login", "TEXT"),
                ("session_version", "INTEGER NOT NULL DEFAULT 0"),
                ("email_verified", "INTEGER NOT NULL DEFAULT 1"),
                ("account_locked", "INTEGER NOT NULL DEFAULT 0"),
                ("otp_failures", "INTEGER NOT NULL DEFAULT 0"),
                ("role", "TEXT NOT NULL DEFAULT 'customer'"),
            ):
                if name not in cols:
                    c.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
            c.execute("""CREATE TABLE IF NOT EXISTS resets (
                email TEXT PRIMARY KEY COLLATE NOCASE, code_hash TEXT NOT NULL,
                salt TEXT NOT NULL, expires_at INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, sent_at INTEGER NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS email_verifications (
                email TEXT PRIMARY KEY COLLATE NOCASE, code_hash TEXT NOT NULL,
                salt TEXT NOT NULL, expires_at INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, sent_at INTEGER NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS code_dispatch (
                email TEXT NOT NULL COLLATE NOCASE, purpose TEXT NOT NULL,
                sent_at INTEGER NOT NULL, PRIMARY KEY(email,purpose)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS limits (
                subject TEXT PRIMARY KEY, attempts INTEGER NOT NULL,
                window_start INTEGER NOT NULL, locked_until INTEGER NOT NULL DEFAULT 0
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,
                event TEXT NOT NULL, occurred_at TEXT NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS otp_policy (
                email TEXT NOT NULL COLLATE NOCASE, purpose TEXT NOT NULL,
                requests INTEGER NOT NULL DEFAULT 0, next_request_at INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(email,purpose),
                FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS reset_grants (
                email TEXT PRIMARY KEY COLLATE NOCASE, token_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL, version INTEGER NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email) ON DELETE CASCADE
            )""")
            c.execute(
                "CREATE INDEX IF NOT EXISTS audit_actor_id ON audit(actor,id DESC)"
            )

    def audit(self, actor, event):
        with self.db() as c:
            c.execute(
                "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
                (str(actor)[:100], event, utcnow()),
            )

    def limited(self, subject):
        with self.db() as c:
            r = c.execute(
                "SELECT locked_until FROM limits WHERE subject=?", (subject,)
            ).fetchone()
            return bool(r and r["locked_until"] > int(time.time()))

    def failure(self, subject, maximum=5, period=900):
        now = int(time.time())
        with self.db() as c:
            row = c.execute(
                "SELECT * FROM limits WHERE subject=?", (subject,)
            ).fetchone()
            if not row or now - row["window_start"] >= period:
                c.execute(
                    "INSERT OR REPLACE INTO limits VALUES(?,?,?,?)",
                    (subject, 1, now, 0),
                )
            else:
                n = row["attempts"] + 1
                c.execute(
                    "UPDATE limits SET attempts=?, locked_until=? WHERE subject=?",
                    (n, now + period if n >= maximum else 0, subject),
                )

    def clear_limit(self, subject):
        with self.db() as c:
            c.execute("DELETE FROM limits WHERE subject=?", (subject,))

    def signup(
        self,
        username,
        email,
        password,
        question,
        answer,
        *,
        require_verification=False,
        reserved_identity="admin",
    ):
        username = username.strip()
        email = email.strip().lower()
        if reserved_identity and reserved_identity.strip().casefold() in (
            username.casefold(),
            email.casefold(),
        ):
            return (
                False,
                "That identity is reserved. Choose another username and email.",
            )
        if not re.fullmatch(r"[\w.\-]{3,50}", username, re.UNICODE):
            return (
                False,
                "Username must be 3–50 letters/digits/dots/dashes/underscores.",
            )
        if not valid_email(email):
            return False, "Enter a valid email address."
        if password_errors(password):
            return False, "Password does not meet the requirements."
        if question not in QUESTIONS:
            return False, "Choose a security question."
        if answer_error(answer):
            return False, answer_error(answer)
        now = utcnow()
        try:
            with self.db() as c:
                c.execute(
                    """INSERT INTO users(username,email,password_hash,security_question,
                    answer_hash,created_at,updated_at,email_verified)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        username,
                        email,
                        hashed(password),
                        question,
                        hashed(clean_answer(answer)),
                        now,
                        now,
                        0 if require_verification else 1,
                    ),
                )
        except sqlite3.IntegrityError:
            with self.db() as c:
                name_taken = c.execute(
                    "SELECT 1 FROM users WHERE username=?", (username,)
                ).fetchone()
            return False, (
                "Username already exists."
                if name_taken
                else "Email address already registered."
            )
        self.audit(username, "signup")
        return True, (
            "Account created. Verify your email to activate it."
            if require_verification
            else "Account created. Sign in to continue."
        )

    def user(self, identity):
        identity = str(identity).strip()
        with self.db() as c:
            return c.execute(
                "SELECT * FROM users WHERE username=? OR email=?", (identity, identity)
            ).fetchone()

    def authenticate(self, identity, password):
        row = self.user(identity)
        key = "login:" + (str(row["id"]) if row else identity.strip().casefold())
        if self.limited(key):
            return None, "Too many attempts. Try again in 15 minutes."
        if not row or not matches(password, row["password_hash"]):
            self.failure(key)
            self.audit(identity[:100], "login_failed")
            return None, GENERIC_LOGIN_ERROR
        if self.is_locked(row["email"]):
            return None, LOCKED_MESSAGE
        if not row["email_verified"]:
            return None, "Please verify your registered email before signing in."
        self.clear_limit(key)
        now = utcnow()
        with self.db() as c:
            c.execute(
                """UPDATE users SET previous_login=last_login,last_login=?,login_count=login_count+1
                         WHERE id=?""",
                (now, row["id"]),
            )
        self.audit(row["username"], "login_success")
        return self.user(identity), None

    def sign_in(self, identity, password, admin_username="admin", admin_password=""):
        """One entry point for configured administrators and registered accounts."""
        identity = identity.strip()
        if identity.casefold() == admin_username.strip().casefold():
            if self.limited("admin-login"):
                return None, "Too many attempts. Try again in 15 minutes."
            if not admin_password or not hmac.compare_digest(
                password.encode(), admin_password.encode()
            ):
                self.failure("admin-login")
                self.audit(admin_username, "login_failed")
                return None, GENERIC_LOGIN_ERROR
            self.clear_limit("admin-login")
            self.audit(admin_username, "login_success")
            return {
                "username": admin_username,
                "email": None,
                "role": "admin",
                "principal_type": "configured_admin",
                "session_version": 0,
            }, None
        account, error = self.authenticate(identity, password)
        if error:
            return None, error
        if account["role"] not in ROLES:
            return None, GENERIC_LOGIN_ERROR
        return dict(account) | {"principal_type": "account"}, None

    def session(self, token, secret, admin_username="admin", admin_password=None):
        payload = decode_token(token, secret) if token and len(secret) >= 32 else None
        if not payload:
            return None
        if payload.get("kind") == "configured_admin":
            if payload.get("sub") != admin_username or payload.get("role") != "admin":
                return None
            if admin_password is not None and (
                not admin_password
                or not hmac.compare_digest(
                    payload.get("credential_tag", ""),
                    admin_credential_tag(admin_password, secret),
                )
            ):
                return None
            return {
                "username": admin_username,
                "email": None,
                "role": "admin",
                "principal_type": "configured_admin",
                "session_version": 0,
            }
        if payload.get("kind") != "account":
            return None
        row = self.user(payload.get("sub", ""))
        if not row or self.is_locked(row["email"]):
            return None
        row = self.user(row["email"])
        if (
            not row["email_verified"]
            or row["role"] not in ROLES
            or row["role"] != payload.get("role")
            or row["session_version"] != payload.get("ver")
        ):
            return None
        return dict(row) | {"principal_type": "account"}

    def _still_authorized(self, conn, account, permission):
        """Recheck stored permissions inside the same transaction as a mutation."""
        if not can(account, permission):
            return False
        if account.get("principal_type") == "configured_admin":
            return True
        row = conn.execute(
            "SELECT * FROM users WHERE id=?", (account["id"],)
        ).fetchone()
        return bool(
            row
            and not row["account_locked"]
            and row["email_verified"]
            and row["role"] == account["role"]
            and row["session_version"] == account["session_version"]
        )

    def assign_role(
        self,
        identity,
        role,
        admin_token,
        secret,
        admin_username="admin",
        admin_password=None,
    ):
        account = self.session(admin_token, secret, admin_username, admin_password)
        if not can(account, "manage_access"):
            return False, "Administrator authentication required."
        if role not in ROLES:
            return False, "Choose a valid role."
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            if not self._still_authorized(c, account, "manage_access"):
                return False, "Your access changed. Sign in again."
            row = c.execute(
                "SELECT * FROM users WHERE username=? OR email=?", (identity, identity)
            ).fetchone()
            if not row:
                return False, "Account not found."
            if account.get("id") == row["id"]:
                return False, "Ask another administrator to change your role."
            if row["account_locked"] or not row["email_verified"]:
                return False, "Verify and unlock the account before changing its role."
            if row["role"] == role:
                return False, "This account already has that role."
            c.execute(
                "UPDATE users SET role=?,session_version=session_version+1,updated_at=? WHERE id=?",
                (role, utcnow(), row["id"]),
            )
            c.execute("DELETE FROM reset_grants WHERE email=?", (row["email"],))
            c.execute(
                "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
                (
                    account["username"],
                    "role_changed:" + row["username"] + ":" + role,
                    utcnow(),
                ),
            )
        return True, "Role updated. The user must sign in again."

    def visible_users(self, token, secret, admin_username="admin", admin_password=None):
        account = self.session(token, secret, admin_username, admin_password)
        if not can(account, "users"):
            raise PermissionError("Administrator authentication required.")
        return self.list_users()

    def audit_events(self, token, secret, admin_username="admin", admin_password=None):
        account = self.session(token, secret, admin_username, admin_password)
        if not can(account, "audit"):
            raise PermissionError("Audit access required.")
        return self.recent_events(100)

    def _lock(self, conn, row, reason):
        conn.execute(
            """UPDATE users SET account_locked=1,
                     session_version=session_version+1 WHERE id=? AND account_locked=0""",
            (row["id"],),
        )
        for table in ("resets", "email_verifications", "reset_grants"):
            conn.execute(f"DELETE FROM {table} WHERE email=?", (row["email"],))
        conn.execute(
            "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
            (row["username"], reason, utcnow()),
        )

    def is_locked(self, identity):
        row = self.user(identity)
        if not row:
            return False
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
            if row["account_locked"]:
                return True
            # The last allowed code remains usable for its entire validity period.
            for purpose, table in (
                ("reset", "resets"),
                ("verify", "email_verifications"),
            ):
                expired = c.execute(
                    f"""SELECT 1 FROM otp_policy p JOIN {table} r
                    ON p.email=r.email WHERE p.email=? AND p.purpose=?
                    AND p.requests>=? AND r.expires_at<=?""",
                    (row["email"], purpose, MAX_OTP_REQUESTS, int(time.time())),
                ).fetchone()
                if expired:
                    self._lock(c, row, "account_locked_otp_budget")
                    return True
        return False

    def unlock_account(
        self, identity, admin_token, secret, admin_username="admin", admin_password=None
    ):
        account = self.session(admin_token, secret, admin_username, admin_password)
        if not can(account, "manage_access"):
            return False, "Administrator authentication required."
        row = self.user(identity)
        if not row:
            return False, "Account not found."
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            if not self._still_authorized(c, account, "manage_access"):
                return False, "Your access changed. Sign in again."
            c.execute(
                """UPDATE users SET account_locked=0,otp_failures=0,
                         session_version=session_version+1 WHERE id=?""",
                (row["id"],),
            )
            for table in (
                "resets",
                "email_verifications",
                "reset_grants",
                "otp_policy",
                "code_dispatch",
            ):
                c.execute(f"DELETE FROM {table} WHERE email=?", (row["email"],))
            for subject in (
                "login:" + str(row["id"]),
                "login:" + row["username"].casefold(),
                "login:" + row["email"].casefold(),
                "question:" + row["username"].casefold(),
            ):
                c.execute("DELETE FROM limits WHERE subject=?", (subject,))
            c.execute(
                "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
                (account["username"], "account_unlocked:" + row["username"], utcnow()),
            )
        return True, "Account unlocked. The user can request a new code."

    def _new_grant(self, conn, row):
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT OR REPLACE INTO reset_grants VALUES(?,?,?,?)",
            (
                row["email"],
                hashlib.sha256(token.encode()).hexdigest(),
                int(time.time()) + 300,
                row["session_version"],
            ),
        )
        return token

    def change_password(self, identity, current, new):
        if password_errors(new):
            return False, "Password does not meet the requirements."
        row = self.user(identity)
        if not row or not matches(current, row["password_hash"]):
            return False, "Current password is incorrect."
        if self.is_locked(identity):
            return False, LOCKED_MESSAGE
        if matches(new, row["password_hash"]):
            return False, "Choose a password different from your current password."
        new_hash = hashed(new)
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            current_row = c.execute(
                "SELECT * FROM users WHERE id=?", (row["id"],)
            ).fetchone()
            if (
                current_row["account_locked"]
                or current_row["session_version"] != row["session_version"]
            ):
                return False, "Session changed. Sign in again."
            self._set_password(c, current_row, new_hash)
        return True, "Password updated. Sign in again."

    def _set_password(self, conn, row, new_hash):
        conn.execute(
            """UPDATE users SET password_hash=?,updated_at=?,
            session_version=session_version+1,otp_failures=0 WHERE id=?""",
            (new_hash, utcnow(), row["id"]),
        )
        for table in (
            "resets",
            "email_verifications",
            "reset_grants",
            "otp_policy",
            "code_dispatch",
        ):
            conn.execute(f"DELETE FROM {table} WHERE email=?", (row["email"],))
        conn.execute(
            "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
            (row["username"], "password_changed", utcnow()),
        )

    def reset_password(self, email, new_password, grant=None):
        if password_errors(new_password):
            return False, "Password does not meet the requirements."
        row = self.user(email)
        if not row or not grant:
            return False, "Verify your identity again."
        if self.is_locked(email):
            return False, LOCKED_MESSAGE
        new_hash = hashed(new_password)
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
            saved = c.execute(
                "SELECT * FROM reset_grants WHERE email=?", (row["email"],)
            ).fetchone()
            if row["account_locked"]:
                return False, LOCKED_MESSAGE
            if (
                not saved
                or saved["expires_at"] <= int(time.time())
                or saved["version"] != row["session_version"]
                or not hmac.compare_digest(
                    saved["token_hash"], hashlib.sha256(grant.encode()).hexdigest()
                )
            ):
                return False, "Verification expired. Verify your identity again."
            if matches(new_password, row["password_hash"]):
                return False, "Choose a password different from your current password."
            self._set_password(c, row, new_hash)
        return True, "Password updated. Sign in again."

    def security_question(self, username):
        row = self.user(username)
        if not row or self.is_locked(username):
            return None
        return (
            row["security_question"]
            if row["username"].casefold() == username.strip().casefold()
            else None
        )

    def verify_answer(self, username, answer):
        if answer_error(answer):
            return False
        key = "question:" + username.strip().casefold()
        if self.limited(key) or self.is_locked(username):
            return False
        row = self.user(username)
        ok = bool(
            row
            and row["username"].casefold() == username.strip().casefold()
            and matches(clean_answer(answer), row["answer_hash"])
        )
        if not ok:
            self.failure(key)
            return False
        self.clear_limit(key)
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
            if row["account_locked"]:
                return False
            return self._new_grant(c, row)

    def code_status(self, email, purpose="reset"):
        row = self.user(email)
        empty = {
            "locked": False,
            "requests": 0,
            "failures": 0,
            "resend_in": 0,
            "expires_in": 0,
        }
        if not row:
            return empty
        locked = self.is_locked(email)
        row = self.user(email)
        table = "resets" if purpose == "reset" else "email_verifications"
        with self.db() as c:
            policy = c.execute(
                "SELECT * FROM otp_policy WHERE email=? AND purpose=?",
                (row["email"], purpose),
            ).fetchone()
            code = c.execute(
                f"SELECT expires_at FROM {table} WHERE email=?", (row["email"],)
            ).fetchone()
        now = int(time.time())
        return {
            "locked": locked,
            "requests": policy["requests"] if policy else 0,
            "failures": row["otp_failures"],
            "resend_in": max(0, policy["next_request_at"] - now) if policy else 0,
            "expires_in": max(0, code["expires_at"] - now) if code else 0,
        }

    def _begin_code(self, email, secret, table, purpose):
        if not valid_email(email) or len(secret) < 32:
            return None, "Enter a valid email address."
        row = self.user(email)
        if not row or (purpose == "verify" and row["email_verified"]):
            return None, "If this address is eligible, a code will be sent."
        if self.is_locked(email):
            return None, LOCKED_MESSAGE
        now = int(time.time())
        code = f"{secrets.randbelow(1000000):06d}"
        salt = secrets.token_hex(16)
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
            if row["account_locked"]:
                return None, LOCKED_MESSAGE
            old = c.execute(
                "SELECT * FROM otp_policy WHERE email=? AND purpose=?",
                (row["email"], purpose),
            ).fetchone()
            if old and old["next_request_at"] > now:
                return (
                    None,
                    f"Request another code in {old['next_request_at'] - now} seconds.",
                )
            if old and old["requests"] >= MAX_OTP_REQUESTS:
                self._lock(c, row, "account_locked_otp_budget")
                return None, LOCKED_MESSAGE
            number = (old["requests"] if old else 0) + 1
            delay = 60 if number <= 3 else 300
            c.execute(
                "INSERT OR REPLACE INTO otp_policy VALUES(?,?,?,?)",
                (row["email"], purpose, number, now + delay),
            )
            c.execute(
                f"""INSERT OR REPLACE INTO {table}
                (email,code_hash,salt,expires_at,attempts,sent_at) VALUES(?,?,?,?,0,?)""",
                (
                    row["email"],
                    otp_digest(code, salt, secret, purpose),
                    salt,
                    now + OTP_TTL,
                    now,
                ),
            )
            c.execute("DELETE FROM reset_grants WHERE email=?", (row["email"],))
            c.execute(
                "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
                (row["username"], "otp_requested:" + purpose, utcnow()),
            )
        return code, None

    def begin_otp(self, email, secret):
        return self._begin_code(email, secret, "resets", "reset")

    def begin_email_verification(self, email, secret):
        return self._begin_code(email, secret, "email_verifications", "verify")

    def cancel_otp(self, email):
        self._cancel_code(email, "resets")

    def cancel_email_verification(self, email):
        self._cancel_code(email, "email_verifications")

    def _cancel_code(self, email, table):
        # Retain rate limits when SMTP fails; failures must not bypass cooldowns.
        row = self.user(email)
        if row:
            with self.db() as c:
                c.execute(f"DELETE FROM {table} WHERE email=?", (row["email"],))

    def _verify_code(self, email, code, secret, table, purpose):
        row = self.user(email)
        if not row or not str(code).strip() or self.is_locked(email):
            return False
        with self.db() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
            if row["account_locked"]:
                return False
            rec = c.execute(
                f"SELECT * FROM {table} WHERE email=?", (row["email"],)
            ).fetchone()
            if not rec or rec["expires_at"] <= int(time.time()):
                return False
            ok = bool(re.fullmatch(r"[0-9]{6}", str(code))) and hmac.compare_digest(
                otp_digest(str(code), rec["salt"], secret, purpose), rec["code_hash"]
            )
            if not ok:
                failures = row["otp_failures"] + 1
                c.execute(
                    "UPDATE users SET otp_failures=? WHERE id=?", (failures, row["id"])
                )
                c.execute(
                    f"UPDATE {table} SET attempts=attempts+1 WHERE email=?",
                    (row["email"],),
                )
                if failures >= MAX_OTP_FAILURES:
                    self._lock(c, row, "account_locked_otp_failures")
                return False
            c.execute(f"DELETE FROM {table} WHERE email=?", (row["email"],))
            if purpose == "verify":
                c.execute(
                    "UPDATE users SET email_verified=1,otp_failures=0,updated_at=? WHERE id=?",
                    (utcnow(), row["id"]),
                )
                c.execute(
                    "DELETE FROM otp_policy WHERE email=? AND purpose='verify'",
                    (row["email"],),
                )
                c.execute(
                    "INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)",
                    (row["username"], "email_verified", utcnow()),
                )
                return True
            return self._new_grant(c, row)

    def verify_otp(self, email, code, secret):
        """Return a short-lived reset grant on success, otherwise False."""
        return self._verify_code(email, code, secret, "resets", "reset")

    def verify_email(self, email, code, secret):
        return self._verify_code(email, code, secret, "email_verifications", "verify")

    def recent_events(self, limit=50):
        with self.db() as c:
            return [
                dict(x)
                for x in c.execute(
                    "SELECT actor,event,occurred_at FROM audit ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            ]

    def account_events(self, username, limit=30):
        with self.db() as c:
            return [
                dict(x)
                for x in c.execute(
                    """SELECT event,occurred_at FROM audit WHERE actor=? COLLATE NOCASE
                                              ORDER BY id DESC LIMIT ?""",
                    (username, limit),
                )
            ]

    def list_users(self):
        with self.db() as c:
            return [
                dict(x)
                for x in c.execute(
                    """SELECT id,username,email,role,email_verified,account_locked,otp_failures,created_at,
                previous_login,last_login,login_count FROM users ORDER BY id DESC"""
                )
            ]

    def delete_user(self, user_id):
        with self.db() as c:
            c.execute("DELETE FROM users WHERE id=?", (user_id,))


def issue_token(
    subject,
    secret,
    role="customer",
    lifetime=7200,
    version=0,
    kind="account",
    credential_tag="",
):
    now = dt.datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(subject),
            "role": role,
            "kind": kind,
            "credential_tag": credential_tag,
            "ver": int(version),
            "iat": now,
            "exp": now + dt.timedelta(seconds=lifetime),
            "jti": secrets.token_hex(16),
        },
        secret,
        algorithm="HS256",
    )


def decode_token(token, secret):
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
