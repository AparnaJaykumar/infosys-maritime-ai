"""PORTWISE account store, JWT sessions and email verification.

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
from contextlib import contextmanager
from pathlib import Path

import bcrypt
import jwt

EMAIL_RE = re.compile(r"^[A-Za-z]{2,}[A-Za-z0-9._%+\-]*@[A-Za-z]{2,}[A-Za-z0-9\-]*(?:\.[A-Za-z]{2,}[A-Za-z0-9\-]*)+$")
QUESTIONS = [
    "What was the name of your first school?",
    "In which city were you born?",
    "What was the name of your first pet?",
    "What is the middle name of your oldest sibling?",
]
GENERIC_LOGIN_ERROR = "Invalid username/email or password."
UTC = dt.timezone.utc


def utcnow():
    return dt.datetime.now(UTC).isoformat()


def valid_email(value):
    return isinstance(value, str) and bool(EMAIL_RE.fullmatch(value.strip()))


def password_errors(password):
    issues = []
    if len(password) < 8: issues.append("at least 8 characters")
    if not re.search(r"[A-Z]", password): issues.append("one uppercase letter")
    if not re.search(r"[a-z]", password): issues.append("one lowercase letter")
    if not re.search(r"\d", password): issues.append("one number")
    if not re.search(r"[^A-Za-z0-9]", password): issues.append("one special character")
    return issues


def hashed(text):
    return bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def matches(text, saved):
    try:
        return bcrypt.checkpw(text.encode("utf-8"), saved.encode("ascii"))
    except (ValueError, TypeError, AttributeError):
        return False


def otp_digest(code, salt, secret, purpose="reset"):
    return hmac.new(secret.encode(), f"{purpose}:{salt}:{code}".encode(), hashlib.sha256).hexdigest()


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
            c.execute("CREATE INDEX IF NOT EXISTS audit_actor_id ON audit(actor,id DESC)")

    def audit(self, actor, event):
        with self.db() as c:
            c.execute("INSERT INTO audit(actor,event,occurred_at) VALUES(?,?,?)", (str(actor)[:100],event,utcnow()))

    def limited(self, subject):
        with self.db() as c:
            r=c.execute("SELECT locked_until FROM limits WHERE subject=?", (subject,)).fetchone()
            return bool(r and r["locked_until"] > int(time.time()))

    def failure(self, subject, maximum=5, period=900):
        now=int(time.time())
        with self.db() as c:
            row=c.execute("SELECT * FROM limits WHERE subject=?",(subject,)).fetchone()
            if not row or now-row["window_start"] >= period:
                c.execute("INSERT OR REPLACE INTO limits VALUES(?,?,?,?)",(subject,1,now,0))
            else:
                n=row["attempts"]+1
                c.execute("UPDATE limits SET attempts=?, locked_until=? WHERE subject=?",
                          (n,now+period if n>=maximum else 0,subject))

    def clear_limit(self,subject):
        with self.db() as c:
            c.execute("DELETE FROM limits WHERE subject=?",(subject,))

    def signup(self, username, email, password, question, answer, *, require_verification=False):
        username=username.strip(); email=email.strip().lower()
        if not re.fullmatch(r"[\w.\-]{3,50}", username, re.UNICODE):
            return False,"Username must be 3–50 letters/digits/dots/dashes/underscores."
        if not valid_email(email): return False,"Enter a valid email address."
        if password_errors(password): return False,"Password does not meet the requirements."
        if question not in QUESTIONS or not answer.strip():
            return False,"Choose a security question and provide an answer."
        now=utcnow()
        try:
            with self.db() as c:
                c.execute("""INSERT INTO users(username,email,password_hash,security_question,
                    answer_hash,created_at,updated_at,email_verified)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (username,email,hashed(password),question,hashed(answer.strip().casefold()),now,now,
                     0 if require_verification else 1))
        except sqlite3.IntegrityError:
            with self.db() as c:
                name_taken=c.execute("SELECT 1 FROM users WHERE username=?",(username,)).fetchone()
            return False,"Username already exists." if name_taken else "Email address already registered."
        self.audit(username,"signup")
        return True,("Account created. Verify your email to activate it." if require_verification
                     else "Account created. Sign in to continue.")

    def user(self, identity):
        identity=str(identity).strip()
        with self.db() as c:
            return c.execute("SELECT * FROM users WHERE username=? OR email=?",(identity,identity)).fetchone()

    def authenticate(self, identity, password):
        key="login:"+identity.strip().casefold()
        if self.limited(key): return None,"Too many attempts. Try again in 15 minutes."
        row=self.user(identity)
        if not row or not matches(password,row["password_hash"]):
            self.failure(key)
            self.audit(identity[:100],"login_failed")
            return None,GENERIC_LOGIN_ERROR
        if not row["email_verified"]:
            return None,"Please verify your registered email before signing in."
        self.clear_limit(key)
        now=utcnow()
        with self.db() as c:
            c.execute("""UPDATE users SET previous_login=last_login,last_login=?,login_count=login_count+1
                         WHERE id=?""",(now,row["id"]))
        self.audit(row["username"],"login_success")
        return self.user(identity),None

    def change_password(self,identity,current,new):
        row=self.user(identity)
        if not row or not matches(current,row["password_hash"]):
            return False,"Current password is incorrect."
        return self.reset_password(row["email"],new)

    def reset_password(self,email,new_password):
        if password_errors(new_password): return False,"Password does not meet requirements."
        row=self.user(email)
        if not row: return False,"Account not found."
        if matches(new_password,row["password_hash"]):
            return False,"Choose a password you have not used previously."
        with self.db() as c:
            c.execute("""UPDATE users SET password_hash=?,updated_at=?,session_version=session_version+1
                         WHERE id=?""",(hashed(new_password),utcnow(),row["id"]))
            c.execute("DELETE FROM resets WHERE email=?",(row["email"],))
        self.audit(row["username"],"password_changed")
        return True,"Password updated. Sign in again."

    def security_question(self,username):
        row=self.user(username)
        return row["security_question"] if row and row["username"].casefold()==username.strip().casefold() else None

    def verify_answer(self,username,answer):
        key="question:"+username.strip().casefold()
        if self.limited(key): return False
        row=self.user(username)
        ok=bool(row and row["username"].casefold()==username.strip().casefold()
                and matches(answer.strip().casefold(),row["answer_hash"]))
        if ok: self.clear_limit(key)
        else: self.failure(key)
        return ok

    def _begin_code(self,email,secret,table,purpose):
        row=self.user(email)
        if not row or (purpose=="verify" and row["email_verified"]):
            return None,"If this address is eligible, a verification email will be sent."
        now=int(time.time())
        with self.db() as c:
            old=c.execute("SELECT sent_at FROM code_dispatch WHERE email=? AND purpose=?",
                          (row["email"],purpose)).fetchone()
            if old and now-old["sent_at"]<300:
                return None,"Please wait five minutes before requesting another code."
        code=f"{secrets.randbelow(1000000):06d}"
        salt=secrets.token_hex(16)
        with self.db() as c:
            c.execute(f"""INSERT OR REPLACE INTO {table}
                       (email,code_hash,salt,expires_at,attempts,sent_at)
                       VALUES(?,?,?,?,0,?)""",
                      (row["email"],otp_digest(code,salt,secret,purpose),salt,now+300,now))
            c.execute("INSERT OR REPLACE INTO code_dispatch(email,purpose,sent_at) VALUES(?,?,?)",
                      (row["email"],purpose,now))
        self.audit(row["username"],"otp_requested" if purpose=="reset" else "email_verification_requested")
        return code,None

    def begin_otp(self,email,secret):
        return self._begin_code(email,secret,"resets","reset")

    def begin_email_verification(self,email,secret):
        return self._begin_code(email,secret,"email_verifications","verify")

    def cancel_otp(self,email):
        self._cancel_code(email,"resets")

    def cancel_email_verification(self,email):
        self._cancel_code(email,"email_verifications")

    def _cancel_code(self,email,table):
        row=self.user(email)
        if row:
            with self.db() as c:
                c.execute(f"DELETE FROM {table} WHERE email=?",(row["email"],))
                purpose = "reset" if table == "resets" else "verify"
                c.execute("DELETE FROM code_dispatch WHERE email=? AND purpose=?",(row["email"],purpose))

    def _verify_code(self,email,code,secret,table,purpose):
        row=self.user(email)
        if not row or not re.fullmatch(r"\d{6}",str(code)): return False
        with self.db() as c:
            rec=c.execute(f"SELECT * FROM {table} WHERE email=?",(row["email"],)).fetchone()
            if not rec or rec["expires_at"] <= int(time.time()) or rec["attempts"] >= 5:
                return False
            ok=hmac.compare_digest(otp_digest(code,rec["salt"],secret,purpose),rec["code_hash"])
            if ok:
                c.execute(f"DELETE FROM {table} WHERE email=?",(row["email"],))
                if purpose=="verify":
                    c.execute("UPDATE users SET email_verified=1,updated_at=? WHERE id=?",(utcnow(),row["id"]))
            else:
                c.execute(f"UPDATE {table} SET attempts=attempts+1 WHERE email=?",(row["email"],))
        if ok and purpose=="verify": self.audit(row["username"],"email_verified")
        return ok

    def verify_otp(self,email,code,secret):
        return self._verify_code(email,code,secret,"resets","reset")

    def verify_email(self,email,code,secret):
        return self._verify_code(email,code,secret,"email_verifications","verify")

    def recent_events(self,limit=50):
        with self.db() as c:
            return [dict(x) for x in c.execute("SELECT actor,event,occurred_at FROM audit ORDER BY id DESC LIMIT ?",(limit,))]

    def account_events(self,username,limit=30):
        with self.db() as c:
            return [dict(x) for x in c.execute("""SELECT event,occurred_at FROM audit WHERE actor=? COLLATE NOCASE
                                              ORDER BY id DESC LIMIT ?""",(username,limit))]

    def list_users(self):
        with self.db() as c:
            return [dict(x) for x in c.execute("""SELECT id,username,email,email_verified,created_at,
                previous_login,last_login,login_count FROM users ORDER BY id DESC""")]

    def delete_user(self,user_id):
        with self.db() as c:
            c.execute("DELETE FROM users WHERE id=?",(user_id,))


def issue_token(subject,secret,role="user",lifetime=7200,version=0):
    now=dt.datetime.now(UTC)
    return jwt.encode({"sub":str(subject),"role":role,"ver":int(version),"iat":now,
                       "exp":now+dt.timedelta(seconds=lifetime),"jti":secrets.token_hex(16)},
                      secret,algorithm="HS256")


def decode_token(token,secret):
    try:
        return jwt.decode(token,secret,algorithms=["HS256"],options={"require":["sub","exp","iat"]})
    except (jwt.InvalidTokenError,TypeError,ValueError):
        return None
