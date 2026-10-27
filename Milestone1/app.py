"""FreightQuote AI | Maritime freight workspace · Milestone 1 authentication."""

import time
import html
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import streamlit as st
from auth_core import (
    QUESTIONS,
    ROLES,
    can,
    admin_credential_tag,
    Store,
    decode_token,
    issue_token,
    password_errors,
    valid_email,
    answer_error,
    LOCKED_MESSAGE,
)

st.set_page_config(
    page_title="FreightQuote AI | Maritime Intelligence",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="auto",
)

JWT_SECRET = os.getenv("JWT_SECRET", "")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
REQUIRE_EMAIL_VERIFICATION = os.getenv(
    "REQUIRE_EMAIL_VERIFICATION", "1"
).lower() not in ("0", "false", "no")
store = Store(os.getenv("DATABASE_PATH", "auth.db"))
BASE_DIR = Path(__file__).resolve().parent


ROUTES = {
    "login",
    "locked",
    "signup",
    "forgot",
    "dashboard",
    "admin-dashboard",
    "verify-email",
}
requested = str(st.query_params.get("view", "login"))
if requested not in ROUTES:
    requested = "login"
for key, initial in {
    "view": requested,
    "theme": "Light",
    "motion_enabled": True,
    "jwt": None,
    "reset_verified": False,
    "reset_identity": None,
    "reset_method": None,
    "question_user": None,
    "flash": None,
    "reset_grant": None,
    "verify_email_address": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = initial
if st.session_state.view != requested:
    st.session_state.view = requested
    st.session_state.reset_verified = False
    st.session_state.reset_identity = None
    st.session_state.question_user = None
    st.session_state.reset_grant = None

DARK = st.session_state.theme == "Dark"
PALETTE = (
    {
        "bg": "#101522",
        "card": "#182032",
        "ink": "#eef3ff",
        "sub": "#aebbd1",
        "line": "#303d54",
        "accent": "#79d5cd",
        "soft": "#242e46",
    }
    if DARK
    else {
        "bg": "#f5f7fb",
        "card": "#ffffff",
        "ink": "#202b43",
        "sub": "#617087",
        "line": "#e0e6f0",
        "accent": "#167b83",
        "soft": "#eef0f9",
    }
)
css_variables = (
    ":root{"
    + ";".join("--pw-" + key + ":" + value for key, value in PALETTE.items())
    + "}"
)
st.markdown(
    "<style>" + css_variables + (BASE_DIR / "motion.css").read_text() + "</style>",
    unsafe_allow_html=True,
)
if not st.session_state.motion_enabled:
    st.markdown(
        "<style>*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}</style>",
        unsafe_allow_html=True,
    )


def navigate(view):
    if view != st.session_state.view:
        for key in ("reset_identity", "question_user", "reset_grant"):
            st.session_state[key] = None
        st.session_state.reset_verified = False
    st.session_state.view = view
    st.query_params["view"] = view
    st.rerun()


def flash():
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None


def current_user():
    return store.session(
        st.session_state.jwt, JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD
    )


def log_out():
    account = current_user()
    if account:
        store.audit(account["username"], "logout")
    for key in list(st.session_state):
        del st.session_state[key]
    st.query_params["view"] = "login"
    st.rerun()


def password_ok(password, confirmation):
    missing = password_errors(password)
    if missing:
        st.error("Password must contain " + ", ".join(missing) + ".")
        return False
    if password != confirmation:
        st.error("Passwords do not match.")
        return False
    return True


def send_code(recipient, code, purpose="reset"):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return False, "Email delivery is unavailable. Contact the administrator."
    mail = EmailMessage()
    mail["From"] = EMAIL_ADDRESS
    mail["To"] = recipient
    title = (
        "Verify your FreightQuote AI email"
        if purpose == "signup"
        else "FreightQuote AI password recovery"
    )
    mail["Subject"] = title
    mail.set_content(
        f"Your FreightQuote AI six-digit code is {code}. It expires in five minutes. If you didn't request it, ignore this email."
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(EMAIL_ADDRESS.strip(), EMAIL_PASSWORD.replace(" ", ""))
            refused = smtp.send_message(mail)
            if refused:
                return (
                    False,
                    "The email service refused the recipient. Check the address and try again.",
                )
        return True, None
    except smtplib.SMTPAuthenticationError:
        return (
            False,
            "Gmail rejected the sender login. Verify the Gmail App Password in Colab Secrets.",
        )
    except (smtplib.SMTPException, OSError):
        return (
            False,
            "Email sending failed. Check the sender settings and SMTP connectivity in Colab.",
        )


def topbar():
    with st.container(key="topbar"):
        left, theme_control = st.columns(
            [8, 1.2], vertical_alignment="center"
        )
        with left:
            st.markdown(
                '<div class="top-brand"><span class="brand-symbol">FQ</span> FreightQuote AI <small>FREIGHT INTELLIGENCE</small></div>',
                unsafe_allow_html=True,
            )
        with theme_control:
            if st.button("☀ Light" if DARK else "☾ Dark", width="stretch"):
                st.session_state.theme = "Light" if DARK else "Dark"
                st.rerun()


def left_panel():
    st.markdown(
        """<section class="auth-hero freight-scene">
<div class="freight-photo"></div><div class="freight-shade"></div>
<div class="freight-copy"><div class="hero-eyebrow">FREIGHT INTELLIGENCE, CONNECTED</div>
<h1>A world in motion.<br><em>A smarter way forward.</em></h1>
<p class="hero-copy">Your freight team. One connected workspace.</p></div>
</section>""",
        unsafe_allow_html=True,
    )


def login():
    st.markdown('<div class="fq-intro"><p class="fq-kicker">Sign in</p><h3>Welcome back</h3></div>', unsafe_allow_html=True)
    st.caption("Sign in to your FreightQuote AI workspace.")
    flash()
    with st.form("login_form"):
        identity = st.text_input(
            "Username or email",
            placeholder="Enter your username or email",
            max_chars=254,
        )
        password = st.text_input(
            "Password", type="password", placeholder="Enter your password", max_chars=72
        )
        submit = st.form_submit_button("Sign in →", type="primary", width="stretch")
    if submit:
        if not identity.strip() or not password:
            st.error("Both fields are required.")
        else:
            account, error = store.sign_in(
                identity, password, ADMIN_USERNAME, ADMIN_PASSWORD
            )
            if error:
                st.error(error)
            else:
                st.session_state.jwt = issue_token(
                    account["email"] or account["username"],
                    JWT_SECRET,
                    role=account["role"],
                    version=account["session_version"],
                    kind=account["principal_type"],
                    credential_tag=(
                        admin_credential_tag(ADMIN_PASSWORD, JWT_SECRET)
                        if account["principal_type"] == "configured_admin"
                        else ""
                    ),
                )
                navigate("dashboard")
    a, b = st.columns(2)
    with a:
        if st.button("Create account", width="stretch"):
            navigate("signup")
    with b:
        if st.button("Forgot password?", width="stretch"):
            navigate("forgot")
    with st.expander("Verify your email"):
        if st.button("Verify a registered email address", width="stretch"):
            navigate("verify-email")


def signup():
    st.markdown('<div class="fq-intro"><p class="fq-kicker">Create account</p><h3>Join the workspace</h3></div>', unsafe_allow_html=True)
    st.caption(
        "Create your customer account. Your administrator can assign team access."
    )
    with st.form("signup_form"):
        username = st.text_input("Username", max_chars=50)
        email = st.text_input("Email address", max_chars=254)
        a, b = st.columns(2)
        with a:
            password = st.text_input("Password", type="password", max_chars=72)
        with b:
            confirm = st.text_input("Confirm password", type="password", max_chars=72)
        question = st.selectbox(
            "Security question", QUESTIONS, index=None, placeholder="Choose a question"
        )
        answer = st.text_input("Security answer", type="password", max_chars=72)
        st.caption("8+ characters: uppercase, lowercase, number and symbol. No spaces.")
        submit = st.form_submit_button(
            "Create account →", type="primary", width="stretch"
        )
    if submit:
        if not all(
            (
                username.strip(),
                email.strip(),
                password,
                confirm,
                question,
                answer.strip(),
            )
        ):
            st.error("Complete all required fields.")
        elif answer_error(answer):
            st.error(answer_error(answer))
        elif not valid_email(email):
            st.error("Enter a valid email, such as ab@cd.ef.")
        elif password_ok(password, confirm):
            if REQUIRE_EMAIL_VERIFICATION and not (EMAIL_ADDRESS and EMAIL_PASSWORD):
                st.error("Email delivery is unavailable. Contact the administrator.")
                return
            ok, message = store.signup(
                username,
                email,
                password,
                question,
                answer,
                require_verification=REQUIRE_EMAIL_VERIFICATION,
                reserved_identity=ADMIN_USERNAME,
            )
            if ok:
                if REQUIRE_EMAIL_VERIFICATION:
                    st.session_state.verify_email_address = email.strip().lower()
                    sent = deliver_code(email.strip().lower(), "verify")
                    st.session_state.flash = (
                        "Account created. Check your email for the code."
                        if sent
                        else "Account created. Email delivery failed; request a new code after the cooldown."
                    )
                    navigate("verify-email")
                else:
                    st.session_state.flash = message
                    navigate("login")
            else:
                st.error(message)
    if st.button("← Back to sign in"):
        navigate("login")


def close_recovery():
    """End the recovery flow and show one account-lock notice."""
    for key in (
        "reset_identity",
        "reset_grant",
        "question_user",
        "verify_email_address",
    ):
        st.session_state[key] = None
    st.session_state.reset_verified = False
    st.session_state.view = "locked"
    st.query_params["view"] = "locked"
    st.rerun(scope="app")


def locked_page():
    st.markdown('<div class="fq-intro"><p class="fq-kicker">Account access</p><h3>Account locked</h3></div>', unsafe_allow_html=True)
    st.error(LOCKED_MESSAGE)
    if st.button("Back to sign in", key="locked_back"):
        navigate("login")


def deliver_code(address, purpose="reset"):
    if store.is_locked(address):
        close_recovery()
    begin = store.begin_otp if purpose == "reset" else store.begin_email_verification
    code, message = begin(address, JWT_SECRET)
    if not code:
        if store.is_locked(address):
            close_recovery()
        st.info(message)
        return False
    sent, error = send_code(address, code, "reset" if purpose == "reset" else "signup")
    if not sent:
        cancel = (
            store.cancel_otp if purpose == "reset" else store.cancel_email_verification
        )
        cancel(address)
        st.error(error)
        return False
    st.success("Code sent. Check your inbox and spam folder.")
    return True


@st.fragment(run_every="1s")
def code_panel(address, purpose="reset"):
    status = store.code_status(address, purpose)
    if status["locked"]:
        close_recovery()
        return
    expiry = status["expires_in"]
    cooldown = status["resend_in"]
    minutes, seconds = divmod(expiry, 60)
    st.caption(
        f"Code expires in {minutes:02d}:{seconds:02d}"
        if expiry
        else "No active code. Request a new one when available."
    )
    if cooldown:
        minutes, seconds = divmod(cooldown, 60)
        st.caption(f"Resend available in {minutes:02d}:{seconds:02d}")
    st.caption(
        f"Code request {status['requests']} of 5 · Incorrect entries {status['failures']} of 5"
    )
    if st.button(
        "Resend code",
        key="resend_" + purpose,
        disabled=cooldown > 0 or status["requests"] >= 5,
        width="stretch",
    ):
        deliver_code(address, purpose)
        st.rerun()
    if status["requests"] >= 5:
        st.caption("This is your last code. If it expires, contact the administrator.")


def verify_email_page():
    st.markdown('<div class="fq-intro"><p class="fq-kicker">Email verification</p><h3>Check your inbox</h3></div>', unsafe_allow_html=True)
    st.caption("Enter the code sent to your registered email.")
    flash()
    with st.form("email_verification_request"):
        address = st.text_input(
            "Registered email address",
            value=st.session_state.verify_email_address or "",
            max_chars=254,
        )
        request = st.form_submit_button("Send code", type="primary", width="stretch")
    if request:
        if not valid_email(address):
            st.error("Enter a valid email address.")
        else:
            address = address.strip().lower()
            if deliver_code(address, "verify"):
                st.session_state.verify_email_address = address
                st.rerun()
    address = st.session_state.verify_email_address
    if address:
        status = store.code_status(address, "verify")
        if status["requests"]:
            code_panel(address, "verify")
            with st.form("verify_signup_code"):
                code = st.text_input("Six-digit code", max_chars=6)
                confirm = st.form_submit_button(
                    "Verify email", type="primary", width="stretch"
                )
            if confirm:
                if not code.strip():
                    st.error("Enter the six-digit code.")
                elif store.verify_email(address, code.strip(), JWT_SECRET):
                    st.session_state.verify_email_address = None
                    st.session_state.flash = "Email verified. Sign in to continue."
                    navigate("login")
                elif store.is_locked(address):
                    close_recovery()
                else:
                    st.error("Invalid or expired code.")
    if st.button("Back to sign in", key="verify_back"):
        navigate("login")


def forgot():
    st.markdown('<div class="fq-intro"><p class="fq-kicker">Recovery</p><h3>Reset your password</h3></div>', unsafe_allow_html=True)
    method = st.radio(
        "Recovery method", ["Email OTP", "Security question"], horizontal=True
    )
    kind = "otp" if method == "Email OTP" else "question"
    if st.session_state.reset_method != kind:
        st.session_state.reset_method = kind
        st.session_state.reset_verified = False
        st.session_state.reset_identity = None
        st.session_state.question_user = None
        st.session_state.reset_grant = None
    address = st.session_state.reset_identity
    if address and store.is_locked(address):
        st.session_state.reset_grant = None
        st.session_state.reset_verified = False
        close_recovery()
    elif st.session_state.reset_verified:
        st.caption("Choose a new password. Verification is valid for five minutes.")
        with st.form("new_password_form"):
            pw = st.text_input("New password", type="password", max_chars=72)
            confirm = st.text_input(
                "Confirm new password", type="password", max_chars=72
            )
            submit = st.form_submit_button(
                "Reset password", type="primary", width="stretch"
            )
        if submit and password_ok(pw, confirm):
            ok, message = store.reset_password(
                address, pw, st.session_state.reset_grant
            )
            if ok:
                st.session_state.jwt = None
                st.session_state.flash = message
                navigate("login")
            else:
                st.error(message)
                if "Verification expired" in message:
                    st.session_state.reset_verified = False
                    st.session_state.reset_grant = None
        if st.button("Verify again"):
            st.session_state.reset_verified = False
            st.session_state.reset_grant = None
            st.rerun()
    elif kind == "otp":
        st.caption(
            "Codes expire after five minutes. Five incorrect entries lock your account."
        )
        st.caption(
            "Resend delay: 1 minute for requests 1–3, then 5 minutes. Maximum 5 requests."
        )
        with st.form("send_otp_form"):
            address = st.text_input("Registered email", max_chars=254)
            send = st.form_submit_button("Send code", type="primary", width="stretch")
        if send:
            if not valid_email(address):
                st.error("Enter a valid email address.")
            elif not EMAIL_ADDRESS or not EMAIL_PASSWORD:
                st.error("Email delivery is unavailable. Contact the administrator.")
            else:
                address = address.strip().lower()
                sent = deliver_code(address)
                # Restore the countdown from SQLite after a page refresh.
                if sent:
                    st.session_state.reset_identity = address
                    st.rerun()
                elif store.code_status(address)["requests"]:
                    st.session_state.reset_identity = address
        address = st.session_state.reset_identity
        if address:
            code_panel(address)
            with st.form("verify_otp_form"):
                code = st.text_input("Six-digit OTP", max_chars=6)
                verify = st.form_submit_button(
                    "Verify code", type="primary", width="stretch"
                )
            if verify:
                if not code.strip():
                    st.error("Enter the six-digit code.")
                else:
                    grant = store.verify_otp(address, code.strip(), JWT_SECRET)
                    if grant:
                        st.session_state.reset_grant = grant
                        st.session_state.reset_verified = True
                        st.rerun()
                    elif store.is_locked(address):
                        close_recovery()
                    else:
                        st.error("Invalid or expired code.")
    else:
        with st.form("find_question_form"):
            username = st.text_input("Registered username", max_chars=50)
            find = st.form_submit_button(
                "Find security question", type="primary", width="stretch"
            )
        if find:
            if not username.strip():
                st.error("Enter your registered username.")
            elif store.is_locked(username):
                close_recovery()
            elif store.security_question(username):
                st.session_state.question_user = username.strip()
            else:
                st.error("Unable to verify that username.")
        user = st.session_state.question_user
        if user and store.security_question(user):
            st.info(store.security_question(user))
            with st.form("answer_question_form"):
                answer = st.text_input("Your answer", type="password", max_chars=72)
                verify = st.form_submit_button(
                    "Verify answer", type="primary", width="stretch"
                )
            if verify:
                if answer_error(answer):
                    st.error(answer_error(answer))
                else:
                    grant = store.verify_answer(user, answer)
                    if grant:
                        st.session_state.reset_identity = store.user(user)["email"]
                        st.session_state.reset_grant = grant
                        st.session_state.reset_verified = True
                        st.rerun()
                    else:
                        st.error("Incorrect answer or too many attempts.")
    if st.button("Back to sign in"):
        navigate("login")


ROLE_SUMMARIES = {
    "customer": "Your account, activity and freight workspace.",
    "operations_manager": "Your workspace for coordinating freight operations.",
    "freight_broker": "Your workspace for coordinating quotes and carriers.",
    "auditor": "Review account activity with read-only audit access.",
    "admin": "Manage people, access and account security.",
}
ROLE_MODULES = {
    "customer": [
        ("Shipment overview", "Track your shipments and delivery updates."),
        ("Quotes", "Review freight options for your cargo."),
    ],
    "operations_manager": [
        ("Command Center", "Coordinate operations, tickets and approvals."),
        ("Route AI", "Review routes, fleet activity and weather risk."),
    ],
    "freight_broker": [
        ("Spot Quotes", "Compare freight quotes and margins."),
        ("Carriers", "Review carrier options and availability."),
    ],
    "auditor": [
        ("Reports", "Review operational reports and decisions."),
        ("Knowledge Graph", "Explore relationships across freight activity."),
    ],
    "admin": [
        ("Platform overview", "Connect teams to the freight platform."),
        ("Data Feed Center", "Review connected data sources."),
    ],
}


def event_table(events):
    if not events:
        st.info("No activity recorded yet.")
        return
    labels = {
        "signup": "Account created",
        "login_success": "Signed in",
        "login_failed": "Sign-in unsuccessful",
        "logout": "Signed out",
        "email_verified": "Email verified",
        "password_changed": "Password changed",
        "account_locked_otp_failures": "Account locked · incorrect codes",
        "account_locked_otp_budget": "Account locked · code limit",
        "admin_login": "Administrator signed in",
        "admin_login_failed": "Sign-in unsuccessful",
    }
    rows = []
    for event in events:
        raw = event["event"]
        parts = raw.split(":")
        if parts[0] == "role_changed" and len(parts) == 3:
            text = f"Role changed · {parts[1]} → {ROLES.get(parts[2], parts[2])}"
        elif parts[0] == "account_unlocked" and len(parts) == 2:
            text = f"Account unlocked · {parts[1]}"
        elif parts[0] == "otp_requested":
            text = (
                "Verification code requested"
                if parts[-1] == "verify"
                else "Recovery code requested"
            )
        else:
            text = labels.get(raw, raw.replace("_", " ").capitalize())
        row = {
            "Activity": text,
            "Time (UTC)": event["occurred_at"].replace("T", " ")[:19],
        }
        if "actor" in event:
            row = {"Account": event["actor"], **row}
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def security_settings(account):
    st.subheader("Account security")
    if account["principal_type"] == "configured_admin":
        st.info(
            "The platform owner manages this administrator's credentials in the deployment settings."
        )
        return
    st.caption("Changing your password ends all existing sessions.")
    with st.form("change_password_form"):
        current = st.text_input("Current password", type="password", max_chars=72)
        new = st.text_input("New password", type="password", max_chars=72)
        confirm = st.text_input("Confirm new password", type="password", max_chars=72)
        st.caption("8+ characters: uppercase, lowercase, number and symbol. No spaces.")
        save = st.form_submit_button("Update password", type="primary")
    if save:
        if not current:
            st.error("Enter your current password.")
        elif password_ok(new, confirm):
            ok, message = store.change_password(account["email"], current, new)
            if ok:
                st.session_state.jwt = None
                st.session_state.flash = message
                navigate("login")
            else:
                st.error(message)


def manage_users(account):
    users = store.visible_users(
        st.session_state.jwt, JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD
    )
    for member in users:
        store.is_locked(member["email"])
    users = store.visible_users(
        st.session_state.jwt, JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD
    )
    metrics = st.columns(3)
    metrics[0].metric("Registered accounts", len(users))
    metrics[1].metric("Verified", sum(bool(u["email_verified"]) for u in users))
    metrics[2].metric("Locked", sum(bool(u["account_locked"]) for u in users))
    directory, access = st.tabs(["Directory", "Access controls"])
    with directory:
        a, b = st.columns([2, 1])
        query = a.text_input("Search users", placeholder="Username or email")
        role_filter = b.selectbox("Filter by role", ["All roles", *ROLES.values()])
        rows = [
            {
                "Username": u["username"],
                "Email": u["email"],
                "Role": ROLES.get(u["role"], "Unassigned"),
                "Status": (
                    "Locked"
                    if u["account_locked"]
                    else "Active" if u["email_verified"] else "Awaiting verification"
                ),
                "Last sign-in (UTC)": (
                    u["last_login"].replace("T", " ")[:16] if u["last_login"] else "—"
                ),
            }
            for u in users
            if query.casefold() in (u["username"] + " " + u["email"]).casefold()
            and (role_filter == "All roles" or ROLES.get(u["role"]) == role_filter)
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info(
                "No accounts match your search."
                if users
                else "No registered accounts yet. New accounts will appear here."
            )
    with access:
        locked = [u["username"] for u in users if u["account_locked"]]
        st.markdown("#### Unlock an account")
        if locked:
            selected = st.selectbox("Account to unlock", locked)
            if st.button("Unlock account", type="primary"):
                ok, message = store.unlock_account(
                    selected,
                    st.session_state.jwt,
                    JWT_SECRET,
                    ADMIN_USERNAME,
                    ADMIN_PASSWORD,
                )
                if ok:
                    st.session_state.flash = message
                    st.rerun()
                st.error(message)
        else:
            st.caption("No locked accounts.")
        st.divider()
        st.markdown("#### Assign a role")
        eligible = [
            u
            for u in users
            if u["email_verified"]
            and not u["account_locked"]
            and u["username"] != account["username"]
        ]
        if eligible:
            names = {u["username"]: u for u in eligible}
            selected = st.selectbox("Account", list(names), key="role_account")
            current_role = names[selected]["role"]
            st.caption("Current role: " + ROLES.get(current_role, "Unassigned"))
            with st.form("assign_role_form"):
                role = st.selectbox(
                    "New role",
                    list(ROLES),
                    format_func=ROLES.get,
                    index=None,
                    placeholder="Choose a role",
                )
                confirmed = st.checkbox(
                    "I confirm this account should receive the selected access."
                )
                save = st.form_submit_button("Save role", type="primary")
            if save:
                if not role or not confirmed:
                    st.error("Choose a role and confirm the access change.")
                else:
                    ok, message = store.assign_role(
                        selected,
                        role,
                        st.session_state.jwt,
                        JWT_SECRET,
                        ADMIN_USERNAME,
                        ADMIN_PASSWORD,
                    )
                    if ok:
                        st.session_state.flash = message
                        st.rerun()
                    st.error(message)
            st.caption(
                "Role changes end the user's existing sessions. Admins can manage all accounts; Auditors can read the audit trail."
            )
        else:
            st.caption(
                "A verified, unlocked account is required. You cannot change your own role."
            )


def workspace(account):
    # Revalidate every rerun; the sidebar is presentation, never the permission check.
    account = current_user()
    if not account:
        navigate("login")
    role_label = ROLES[account["role"]]
    items = ["Workspace", "My profile", "Security"]
    if can(account, "users"):
        items.append("User management")
    if can(account, "audit"):
        items.append("Audit trail")
    with st.sidebar:
        st.markdown("### Your workspace")
        st.caption(role_label)
        if st.session_state.get("workspace_page") not in items:
            st.session_state.workspace_page = "Workspace"
        selected = st.radio(
            "Navigation", items, key="workspace_page", label_visibility="collapsed"
        )
        st.divider()
        st.write(account["username"])
        st.caption("Signed in")
        if st.button("Log out", width="stretch"):
            log_out()
    flash()
    st.markdown(
        f'<div class="workspace-heading"><div><div class="eyebrow">FreightQuote AI / WORKSPACE</div><h2>{html.escape(selected)}</h2></div><span class="role-badge">{html.escape(role_label)}</span></div>',
        unsafe_allow_html=True,
    )
    if selected == "Workspace":
        st.markdown(
            f'<section class="welcome-panel"><div class="eyebrow">WELCOME BACK</div><h2>Hello, {html.escape(account["username"])}.</h2><p>{ROLE_SUMMARIES[account["role"]]}</p></section>',
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        cols[0].metric("Your role", role_label)
        cols[1].metric("Account", "Active")
        payload = decode_token(st.session_state.jwt, JWT_SECRET)
        cols[2].metric(
            "Session remaining",
            str(max(0, (payload["exp"] - int(time.time())) // 60)) + " min",
        )
        st.markdown("#### Freight workspace")
        st.caption("The following modules are planned for dashboard integration.")
        cards = "".join(
            f'<article class="module-card"><span class="module-label">PLANNED</span><h4>{name}</h4><p>{description}</p></article>'
            for name, description in ROLE_MODULES[account["role"]]
        )
        st.markdown(
            '<div class="module-grid">' + cards + "</div>", unsafe_allow_html=True
        )
        st.markdown("#### Recent account activity")
        event_table(store.account_events(account["username"], 8))
    elif selected == "My profile":
        with st.container(border=True):
            st.write("**Username:**", account["username"])
            st.write("**Role:**", role_label)
            if account["email"]:
                st.write("**Email:**", account["email"])
                st.write("**Email status:** Verified")
                st.write("**Member since:**", account["created_at"][:10])
                st.write("**Successful sign-ins:**", account["login_count"])
            else:
                st.caption(
                    "Platform administrator · configured by the deployment owner."
                )
        st.caption("Contact an administrator if your role needs to change.")
    elif selected == "Security":
        security_settings(account)
    elif selected == "User management" and can(account, "users"):
        manage_users(account)
    elif selected == "Audit trail" and can(account, "audit"):
        st.caption("Latest 100 account events. Read-only; all times are UTC.")
        event_table(
            store.audit_events(
                st.session_state.jwt, JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD
            )
        )


@st.fragment(run_every="5s")
def session_watch():
    if st.session_state.jwt and not current_user():
        st.session_state.jwt = None
        st.session_state.flash = (
            "Session ended. Sign in again or contact the administrator."
        )
        navigate("login")


if len(JWT_SECRET) < 32:
    st.error(
        "JWT signing key is not configured. Run the Colab configuration cell first."
    )
    st.stop()

topbar()
viewer = current_user()
if viewer:
    session_watch()
if viewer:
    if st.session_state.view != "dashboard":
        navigate("dashboard")
    workspace(viewer)
else:
    if st.session_state.jwt:
        st.session_state.jwt = None
    with st.container(key="auth_shell"):
        left, right = st.columns([1.12, 1], gap="small", vertical_alignment="center")
        with left:
            left_panel()
        with right, st.container(key="auth_glass"):
            route = st.session_state.view
            if route == "locked":
                locked_page()
            elif route == "signup":
                signup()
            elif route == "forgot":
                forgot()
            elif route == "verify-email":
                verify_email_page()
            else:
                login()

build_label = (
    " · <strong>Build: FreightQuote AI-AUTH-03</strong>"
    if os.getenv("SHOW_BUILD_ID", "0") == "1"
    else ""
)
st.markdown(
    '<div class="footer-note">FreightQuote AI · Freight intelligence'
    + build_label
    + "</div>",
    unsafe_allow_html=True,
)
