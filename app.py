"""Portwise | Maritime freight workspace · Milestone 1 authentication."""
import hmac
import html
import os
import re
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import streamlit as st
from auth_core import QUESTIONS, Store, decode_token, issue_token, password_errors, valid_email, matches

st.set_page_config(page_title="Portwise | Maritime Intelligence", page_icon="⚓", layout="wide", initial_sidebar_state="collapsed")

JWT_SECRET = os.getenv("JWT_SECRET", "")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "1").lower() not in ("0", "false", "no")
store = Store(os.getenv("DATABASE_PATH", "auth.db"))
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"


# Streamlit serves files in ./static at /app/static when static serving is enabled.
# Keeping the artwork outside the HTML/CSS prevents multi-megabyte style tags.
LIGHT_BG = "/app/static/portwise_light_bg.png"
DARK_BG = "/app/static/portwise_dark_bg.png"

ROUTES = {"login", "signup", "forgot", "admin", "dashboard", "admin-dashboard", "demo-login", "demo-otp", "verify-email"}
requested = str(st.query_params.get("view", "login"))
if requested not in ROUTES:
    requested = "login"
for key, initial in {"view": requested, "theme": "Light", "jwt": None,
                     "reset_verified": False, "reset_identity": None,
                     "reset_method": None, "question_user": None, "flash": None,
                     "verify_email_address": None, "verify_email_until": 0}.items():
    if key not in st.session_state:
        st.session_state[key] = initial
if st.session_state.view != requested:
    st.session_state.view = requested
    st.session_state.reset_verified = False
    st.session_state.reset_identity = None
    st.session_state.question_user = None

DARK = st.session_state.theme == "Dark"
BG_URI = DARK_BG if DARK else LIGHT_BG
BG, CARD, INK, SUB, LINE, INPUT = (
    ("#04111b", "rgba(8,24,38,.64)", "#edf6fb", "#a9bfd0", "rgba(116,161,186,.26)", "#10283c") if DARK
    else ("#eef4f6", "rgba(255,255,255,.77)", "#102b37", "#5d7584", "rgba(148,183,196,.38)", "#ffffff")
)
SHELL = "rgba(255,255,255,.06)" if DARK else "rgba(255,255,255,.34)"
AUTH_BACKGROUND = f"linear-gradient({'rgba(3,15,24,.08),rgba(3,15,24,.05)' if DARK else 'rgba(255,255,255,.03),rgba(255,255,255,.08)'}), url('{BG_URI}')"
DASHBOARD_BACKGROUND = ("radial-gradient(ellipse at 80% 18%,rgba(20,144,172,.28),transparent 42%),linear-gradient(135deg,#061425,#0b304a 68%,#071322)" if DARK else "radial-gradient(ellipse at 75% 12%,rgba(125,211,225,.35),transparent 42%),linear-gradient(145deg,#eef9fc,#cde8ef 55%,#eaf7f8)")


st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [data-testid='stApp'] {{font-family:'DM Sans',sans-serif; color:{INK};}}
[data-testid='stApp'] {{
    background-color:{BG};
    background-image:{DASHBOARD_BACKGROUND if st.session_state.view in ("dashboard", "admin-dashboard") else AUTH_BACKGROUND}!important;
    /* Keep the working wallpapers as the permanent fallback. Only their scale
       and position change gently on authentication pages. */
    background-size:cover;
    background-position:center center;
    background-attachment:fixed;
    animation:{'portwiseOceanPan 26s cubic-bezier(.45,0,.55,1) infinite alternate' if st.session_state.view not in ('dashboard','admin-dashboard') else 'none'};
}}
[data-testid='stAppViewContainer'],[data-testid='stMain'],[data-testid='stMainBlockContainer'] {{background:transparent!important;}}
[data-testid='stHeader'] {{background:transparent!important;}}
/* The atmospheric glow moves independently of the wallpaper. */
[data-testid='stApp']::after {{
    content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
    background:radial-gradient(ellipse 65% 80% at 12% 78%, {'rgba(24,194,206,.13)' if DARK else 'rgba(255,255,255,.25)'}, transparent 72%),
               linear-gradient(110deg,transparent 23%,{'rgba(102,204,229,.07)' if DARK else 'rgba(255,255,255,.12)'} 51%,transparent 77%);
    background-size:145% 145%,220% 100%;
    animation:portwiseShimmer 18s ease-in-out infinite alternate;
}}
[data-testid='stAppViewContainer'] {{position:relative;z-index:1;}}
@keyframes portwiseShimmer {{
    0% {{background-position:0% 43%,0% 50%;opacity:.5;}}
    100% {{background-position:12% 53%,100% 50%;opacity:.88;}}
}}
/* A small cinematic push-in/pull-back; not a spinning or distracting effect. */
@keyframes portwiseOceanPan {{
    0% {{background-size:103% 103%; background-position:47% 50%;}}
    100% {{background-size:111% 111%; background-position:54% 48%;}}
}}
[data-testid='stHeader'] {{background:transparent;}}
.block-container {{max-width:1280px; padding-top:1.5rem; padding-bottom:1.2rem;}}
h1,h2,h3 {{font-family:'Manrope',sans-serif;letter-spacing:-.045em;color:{INK}!important;}}
p,label,[data-testid='stCaptionContainer'] {{color:{SUB};}}
[data-testid='stForm'] {{background:{CARD};border:1px solid {LINE};border-radius:22px;padding:1.15rem 1.35rem;backdrop-filter: blur(18px); box-shadow:0 20px 60px rgba(0,0,0,.10);}}
[data-testid='stVerticalBlockBorderWrapper'] > div {{background:{CARD};border-color:{LINE}!important;border-radius:20px!important;backdrop-filter: blur(18px);}}
/* Streamlit uses nested BaseWeb containers. Style the actual filled control,
   not only the outer wrapper: this prevents black fields in light mode. */
[data-testid='stTextInput'] div[data-baseweb='input'],
[data-testid='stTextInput'] div[data-baseweb='base-input'],
[data-testid='stTextInput'] div[data-baseweb='input'] > div,
[data-testid='stTextArea'] div[data-baseweb='textarea'],
[data-testid='stSelectbox'] div[data-baseweb='select'] > div {{
  background-color:{INPUT}!important;background-image:none!important;
  border-color:{LINE}!important;border-radius:12px!important;
  color:{INK}!important;
}}
[data-testid='stTextInput'] input, [data-testid='stTextArea'] textarea {{color:{INK}!important; -webkit-text-fill-color:{INK}!important; caret-color:{INK}!important; background-color:{INPUT}!important; font-weight:500!important; letter-spacing:normal!important; line-height:1.5!important;}}
[data-testid='stTextInput'] input::placeholder,[data-baseweb='input'] input::placeholder,textarea::placeholder {{color:{SUB}!important; -webkit-text-fill-color:{SUB}!important; opacity:1!important;}}
[data-baseweb='select'] > div,[data-baseweb='textarea'] > div {{background:{INPUT}!important; color:{INK}!important; border:1px solid {LINE}!important;}}
[data-baseweb='select'] [role='combobox'], [data-baseweb='select'] [role='option'] {{color:{INK}!important;}}
[data-testid='stTextInput'] label p, [data-testid='stForm'] label p, [data-testid='stSelectbox'] label p, [data-testid='stRadio'] label p {{color:{INK}!important; font-weight:600;}}
[data-testid='stButton'] button p, [data-testid='stFormSubmitButton'] button p {{color:inherit!important; font-size:14px!important; font-weight:600!important;}}
[data-testid='stWidgetLabel'] p {{color:{INK}!important;}}

[data-testid='stButton'] button,[data-testid='stFormSubmitButton'] button {{border-radius:12px;min-height:46px;border:1px solid {LINE};}}
[data-testid='stButton'] button:not([kind='primary']),[data-testid='stFormSubmitButton'] button:not([kind='primary']) {{background:{'rgba(255,255,255,.88)' if not DARK else 'rgba(12,27,44,.78)'}!important;color:{'#123448' if not DARK else '#f1f8ff'}!important;border:1px solid {LINE}!important;backdrop-filter:blur(12px);font-weight:600;}}
[data-testid='stButton'] button:not([kind='primary']) *,[data-testid='stFormSubmitButton'] button:not([kind='primary']) * {{color:{'#123448' if not DARK else '#f1f8ff'}!important;opacity:1!important;}}
[data-testid='stButton'] button[kind='primary'],[data-testid='stFormSubmitButton'] button[kind='primary'] {{background:#ff5a57;color:white;border:0;font-weight:700; box-shadow:0 12px 24px rgba(255,90,87,.18);}}
[data-testid='stButton'] button,[data-testid='stFormSubmitButton'] button {{
    transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease,background-color .22s ease;
}}
[data-testid='stButton'] button:hover,[data-testid='stFormSubmitButton'] button:hover {{
    transform:translateY(-2px);box-shadow:0 10px 25px rgba(0,113,151,.16);
}}
[data-testid='stButton'] button:active,[data-testid='stFormSubmitButton'] button:active {{transform:translateY(0);}}
[data-testid='stButton'] button:focus-visible,[data-testid='stFormSubmitButton'] button:focus-visible {{
    outline:3px solid rgba(25,171,184,.55);outline-offset:3px;
}}
[data-testid='stTextInput'] div[data-baseweb='input']:focus-within,
[data-testid='stSelectbox'] div[data-baseweb='select']:focus-within {{
    border-color:#20aeb6!important;box-shadow:0 0 0 3px rgba(32,174,182,.12)!important;
}}
[data-testid='stMetric'] {{background:{CARD};border:1px solid {LINE};border-radius:16px;padding:19px; backdrop-filter: blur(16px);}}
[data-testid='stMetricValue'] {{color:{INK}!important;}}
.top-brand {{font-size:20px;font-weight:800;font-family:Manrope;color:{INK};letter-spacing:-.04em}}
.top-brand span {{color:#20aeb6;}}
.top-brand small {{font-size:11px;letter-spacing:.12em;opacity:.68;}}
.hero-wrap {{padding:1rem .4rem 1rem 0;}}
.kicker {{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.18em;color:#28aeb7;margin-bottom:12px;}}
.headline {{font-family:Manrope;font-size:clamp(42px,5vw,76px);letter-spacing:-.06em;font-weight:800;line-height:1.04;color:{INK};margin:12px 0 18px;}}
.headline em {{color:#24aeb4;font-style:normal;}}
.intro-copy {{max-width:520px;font-size:16px;line-height:1.8;color:{SUB};}}
.pill {{display:inline-block;border:1px solid {LINE};background:{SHELL};backdrop-filter: blur(12px);border-radius:999px;padding:9px 14px;font-size:11px;font-weight:700;letter-spacing:.075em;color:{SUB};margin:8px 8px 0 0;}}
.hero-card {{margin-top:24px; max-width:560px; border:1px solid {LINE}; border-radius:24px; background:{CARD}; backdrop-filter: blur(18px); padding:22px 24px; box-shadow:0 24px 70px rgba(0,0,0,.08);}}
.hero-card h4 {{font-family:Manrope; font-size:20px; margin:0 0 10px; color:{INK};}}
.hero-card p {{font-size:14px; line-height:1.8; color:{SUB}; margin:0 0 16px;}}
.signal-grid {{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px;}}
.signal-tile {{border:1px solid {LINE}; border-radius:16px; padding:14px 14px 12px; background:transparent;}}
.signal-tile strong {{display:block; font-family:Manrope; color:{INK}; font-size:15px; margin-bottom:3px;}}
.signal-tile span {{display:block; color:{SUB}; font-size:12px; line-height:1.55;}}
.side-note {{max-width:560px; margin-top:14px; color:{SUB}; font-size:12px; line-height:1.7;}}
.flow-card {{border:1px solid {LINE};background:{CARD};backdrop-filter: blur(16px);border-radius:16px;padding:19px 20px;margin-bottom:13px;}}
.flow-card b {{color:{INK};font-family:Manrope;}}
.flow-card p {{font-size:13px;margin:6px 0 0;}}
.step-num {{display:inline-block;background:#087f8a;color:white;border-radius:50%;width:25px;height:25px;text-align:center;line-height:25px;margin-right:10px;font-weight:700;}}

.otp-status {{display:flex;justify-content:space-between;align-items:center;background:{CARD};border:1px solid {LINE};border-radius:14px;padding:16px 19px;margin:8px 0 14px;}}
.otp-status strong {{font-size:25px;font-family:Manrope;color:#16afb8;letter-spacing:.06em;}}
.dashboard-hero {{background:{CARD};backdrop-filter:blur(16px);border:1px solid {LINE};border-radius:24px;padding:30px;margin:8px 0 20px;box-shadow:0 20px 55px rgba(0,0,0,.07);animation:portwiseEnter .8s ease both;}}
.dashboard-hero h2 {{margin:9px 0;font-size:clamp(27px,3vw,42px);}}
.footer-note {{margin-top:36px;text-align:center;color:{SUB};font-size:12px;}}
/* Entrance hierarchy: branding -> message -> form. Reruns keep their fields. */
.top-brand {{animation:portwiseFadeIn .65s ease-out both;}}
.hero-wrap {{animation:portwiseEnter .92s cubic-bezier(.22,.7,.28,1) .1s both;}}
.kicker {{animation:portwiseFadeIn .85s ease-out .18s both;}}
.headline em {{display:inline-block; animation:portwiseTint 6s ease-in-out infinite alternate;}}
[data-testid='stForm'] {{animation:portwiseEnter .72s cubic-bezier(.22,.7,.28,1) .16s both;}}
.dashboard-hero {{animation:portwiseEnter .75s cubic-bezier(.22,.7,.28,1) both;}}
[data-testid='stMetric'] {{transition:transform .25s ease,box-shadow .25s ease;}}
[data-testid='stMetric']:hover {{transform:translateY(-2px);box-shadow:0 14px 32px rgba(2,33,46,.09);}}
@keyframes portwiseEnter {{
  from {{opacity:0;transform:translate3d(0,18px,0);}}
  to {{opacity:1;transform:translate3d(0,0,0);}}
}}
@keyframes portwiseFadeIn {{from {{opacity:0;}} to {{opacity:1;}}}}
@keyframes portwiseTint {{
  from {{filter:brightness(1);}}
  to {{filter:brightness(1.17);}}
}}
@media (prefers-reduced-motion: reduce) {{
  [data-testid='stApp'],[data-testid='stApp']::after,.top-brand,.hero-wrap,.kicker,.headline em,
  [data-testid='stForm'],.dashboard-hero,[data-testid='stMetric'],
  [data-testid='stButton'] button,[data-testid='stFormSubmitButton'] button {{
     animation:none!important;transition:none!important;transform:none!important;
  }}
}}
@media (max-width: 700px) {{
    /* Don't crop or stretch the art on narrow/mobile screens. */
    [data-testid='stApp'] {{background-size:cover!important;animation:none!important;}}
}}
@media (max-width: 992px) {{
  .block-container {{padding-top:1rem;}}
  .hero-wrap {{padding-right:0;}}
  .headline {{font-size:clamp(34px,8vw,54px);}}
}}
</style>""", unsafe_allow_html=True)


def navigate(view):
    st.session_state.view = view
    st.query_params["view"] = view
    st.rerun()


def flash():
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None


def current_user():
    token = st.session_state.jwt
    payload = decode_token(token, JWT_SECRET) if token else None
    if not payload:
        return None
    if payload.get("role") == "admin":
        return {"role": "admin", "username": ADMIN_USERNAME} if payload.get("sub") == ADMIN_USERNAME else None
    row = store.user(payload.get("sub", ""))
    return (dict(row) | {"role": "user"}) if row and row["email_verified"] and payload.get("ver") == row["session_version"] and payload.get("role") == "user" else None


def log_out():
    account = current_user()
    if account:
        store.audit(account["username"], "logout")
    st.session_state.jwt = None
    st.session_state.reset_verified = False
    navigate("login")


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
        return False, "Gmail SMTP sending credentials have not been configured."
    mail = EmailMessage()
    mail["From"] = EMAIL_ADDRESS
    mail["To"] = recipient
    title = "Verify your PORTWISE email" if purpose == "signup" else "PORTWISE password recovery"
    mail["Subject"] = title
    mail.set_content(f"Your PORTWISE six-digit code is {code}. It expires in five minutes. If you didn't request it, ignore this email.")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(EMAIL_ADDRESS.strip(), EMAIL_PASSWORD.replace(" ", ""))
            refused = smtp.send_message(mail)
            if refused:
                return False, "The email service refused the recipient. Check the address and try again."
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail rejected the sender login. Verify the Gmail App Password in Colab Secrets."
    except (smtplib.SMTPException, OSError):
        return False, "Email sending failed. Check the sender settings and SMTP connectivity in Colab."


def topbar():
    left, right = st.columns([5, 1], vertical_alignment="center")
    with left:
        st.markdown('<div class="top-brand">◈ PORT<span>WISE</span> <small>/ MARITIME INTELLIGENCE</small></div>', unsafe_allow_html=True)
    with right:
        if st.button("☀ Light" if DARK else "☾ Dark", use_container_width=True):
            st.session_state.theme = "Light" if DARK else "Dark"
            st.rerun()


def left_panel():
    st.markdown(
        '<div class="hero-wrap">'
        '<div class="kicker">Agentic AI / Freight intelligence</div>'
        '<div class="headline">Navigate freight.<br><em>Intelligently.</em></div>'
        '<p class="intro-copy">A secure entry point for the next generation of maritime freight pricing and route optimization. Connecting people, ports and decisions.</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def login():
    st.markdown("### Sign in to Portwise")
    st.caption("Welcome back. Enter your credentials to continue.")
    flash()
    with st.form("login_form"):
        identity = st.text_input("Username or email", placeholder="Your username or work email")
        password = st.text_input("Password", type="password", placeholder="Your password")
        submit = st.form_submit_button("Sign in →", type="primary", use_container_width=True)
    if submit:
        if not identity.strip() or not password:
            st.error("Both fields are required.")
        else:
            account, error = store.authenticate(identity, password)
            if error:
                st.error(error)
            else:
                st.session_state.jwt = issue_token(account["email"], JWT_SECRET, version=account["session_version"])
                navigate("dashboard")
    a, b = st.columns(2)
    with a:
        if st.button("Create account", use_container_width=True):
            navigate("signup")
    with b:
        if st.button("Forgot password?", use_container_width=True):
            navigate("forgot")
    st.divider()
    if st.button("Admin sign in", use_container_width=True):
        navigate("admin")
    with st.expander("Account help"):
        if st.button("Verify a registered email address", use_container_width=True):
            navigate("verify-email")
        if st.button("Login demonstration", use_container_width=True):
            navigate("demo-login")


def signup():
    st.markdown("### Create an account")
    st.caption("Set up your secure Portwise profile.")
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email address")
        a, b = st.columns(2)
        with a:
            password = st.text_input("Password", type="password")
        with b:
            confirm = st.text_input("Confirm password", type="password")
        question = st.selectbox("Security question", QUESTIONS, index=None, placeholder="Choose a question")
        answer = st.text_input("Security answer", type="password")
        st.caption("Password: 8+ characters, uppercase, lowercase, digit and special character.")
        submit = st.form_submit_button("Create account →", type="primary", use_container_width=True)
    if submit:
        if not all((username.strip(), email.strip(), password, confirm, question, answer.strip())):
            st.error("Complete all required fields.")
        elif not valid_email(email):
            st.error("Enter a valid email, such as ab@cd.ef.")
        elif password_ok(password, confirm):
            if REQUIRE_EMAIL_VERIFICATION and not (EMAIL_ADDRESS and EMAIL_PASSWORD):
                st.error("Email verification is enabled but the sending account has not been configured. Ask the administrator to configure the email service.")
                return
            ok, message = store.signup(username, email, password, question, answer,
                                       require_verification=REQUIRE_EMAIL_VERIFICATION)
            if ok:
                if REQUIRE_EMAIL_VERIFICATION:
                    st.session_state.verify_email_address = email.strip().lower()
                    # Attempt delivery; resend remains available if SMTP cannot accept.
                    st.session_state.flash = message
                    navigate("verify-email")
                else:
                    st.session_state.flash = message
                    navigate("login")
            else:
                st.error(message)
    if st.button("← Back to sign in"):
        navigate("login")


@st.fragment(run_every="1s")
def otp_timer():
    remaining = max(0, int(st.session_state.get("otp_expires_at", 0) - time.time()))
    mins, secs = divmod(remaining, 60)
    if remaining:
        st.markdown(f'<div class="otp-status"><span>⏱ Code expires in</span><strong>{mins:02d}:{secs:02d}</strong></div>', unsafe_allow_html=True)
    else:
        st.warning("Your verification code has expired. You can request another one.")
    resend = st.button("Resend verification code", disabled=remaining > 0, use_container_width=True, key="resend_otp")
    if resend:
        address = st.session_state.get("reset_identity")
        if address:
            deliver_otp(address)
            st.rerun()


def deliver_otp(address):
    code, message = store.begin_otp(address, JWT_SECRET)
    if not code:
        st.info(message or "If the address is registered, check your inbox. If no verification form appears, confirm this account was created in the current Colab database.")
        return
    sent, issue = send_code(address, code)
    if not sent:
        store.cancel_otp(address)
        st.error(issue or "Email delivery could not be accepted by the sending server.")
        return
    st.session_state.reset_identity = address
    st.session_state.otp_expires_at = time.time() + 300
    st.success("Code request accepted by the email server. Check Inbox, Promotions and Spam. Delivery can take a moment.")



def send_signup_verification(address):
    code, note = store.begin_email_verification(address, JWT_SECRET)
    if not code:
        st.info(note or "If your account is eligible, check your email.")
        return False
    accepted, problem = send_code(address, code, purpose="signup")
    if not accepted:
        store.cancel_email_verification(address)
        st.error(problem or "The email server did not accept the verification message.")
        return False
    st.session_state.verify_email_address = address
    st.session_state.verify_email_until = time.time() + 300
    st.success("Verification email accepted by the sending server. Check your inbox and spam folder.")
    return True


@st.fragment(run_every="1s")
def signup_verification_countdown():
    remaining = max(0, int(st.session_state.get("verify_email_until", 0) - time.time()))
    if remaining:
        mins, secs = divmod(remaining, 60)
        st.markdown(f'<div class="otp-status"><span>⏱ Code expires in</span><strong>{mins:02d}:{secs:02d}</strong></div>', unsafe_allow_html=True)
    else:
        st.caption("You can request a new verification code.")
    if st.button("Resend email verification", disabled=remaining > 0, key="resend_signup_verify"):
        if st.session_state.verify_email_address:
            send_signup_verification(st.session_state.verify_email_address)
            st.rerun()


def verify_email_page():
    st.markdown("### Verify your email")
    st.caption("Confirm your email address before signing in to PORTWISE.")
    flash()
    with st.form("email_verification_request"):
        address = st.text_input("Registered email address", value=st.session_state.verify_email_address or "")
        request = st.form_submit_button("Send verification code", type="primary", use_container_width=True)
    if request:
        if not valid_email(address):
            st.error("Enter a valid email address.")
        elif not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            st.error("Email delivery is not configured yet.")
        else:
            send_signup_verification(address.strip().lower())
    if st.session_state.verify_email_address and st.session_state.verify_email_until:
        signup_verification_countdown()
        with st.form("verify_signup_code"):
            code = st.text_input("Six-digit code", max_chars=6, placeholder="000000")
            confirm = st.form_submit_button("Verify email →", type="primary", use_container_width=True)
        if confirm:
            if store.verify_email(st.session_state.verify_email_address, code.strip(), JWT_SECRET):
                st.session_state.verify_email_until = 0
                st.session_state.verify_email_address = None
                st.session_state.flash = "Email verified. Sign in to continue."
                navigate("login")
            else:
                st.error("Code invalid or expired. Check your message or request a new code after the timer ends.")
    if st.button("← Return to login", key="verify_back"):
        navigate("login")


def forgot():
    st.markdown("### Recover your account")
    st.caption("Choose email verification or your saved security question. Codes are six digits and valid for five minutes.")
    method = st.radio("Recovery method", ["Email OTP", "Security question"], horizontal=True)
    kind = "otp" if method == "Email OTP" else "question"
    if st.session_state.reset_method != kind:
        st.session_state.reset_method = kind
        st.session_state.reset_verified = False
        st.session_state.reset_identity = None
        st.session_state.question_user = None
        st.session_state.otp_expires_at = 0
    if st.session_state.reset_verified:
        st.success("Identity verified. Set a new password.")
        with st.form("new_password_form"):
            pw = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm new password", type="password")
            submit = st.form_submit_button("Reset password →", type="primary", use_container_width=True)
        if submit and password_ok(pw, confirm):
            ok, message = store.reset_password(st.session_state.reset_identity, pw)
            if ok:
                st.session_state.reset_verified = False
                st.session_state.reset_identity = None
                st.session_state.question_user = None
                st.session_state.flash = message
                navigate("login")
            else:
                st.error(message)
    elif method == "Email OTP":
        with st.form("send_otp_form"):
            address = st.text_input("Registered email", placeholder="you@gmail.com or you@outlook.com")
            send = st.form_submit_button("Send verification code", type="primary", use_container_width=True)
        if send:
            if not valid_email(address):
                st.error("Enter a valid email address.")
            elif not EMAIL_ADDRESS or not EMAIL_PASSWORD:
                st.error("Email OTP requires EMAIL_ADDRESS and EMAIL_PASSWORD in the server configuration.")
            else:
                deliver_otp(address.strip().lower())
        if st.session_state.reset_identity:
            st.info("A six-digit code was requested for " + st.session_state.reset_identity + ". If it does not arrive, check Spam or Promotions and verify your sender configuration.")
            st.markdown("#### Verify your email")
            otp_timer()
            with st.form("verify_otp_form"):
                code = st.text_input("Six-digit OTP", max_chars=6, placeholder="Enter the code from your email")
                verify = st.form_submit_button("Verify OTP →", type="primary", use_container_width=True)
            if verify:
                if not re.fullmatch(r"[0-9]{6}", code.strip()):
                    st.error("Enter the complete six-digit code.")
                elif store.verify_otp(st.session_state.reset_identity, code.strip(), JWT_SECRET):
                    st.session_state.reset_verified = True
                    st.rerun()
                else:
                    st.error("The code was incorrect, expired, or exceeded the maximum attempts. You can request another code after the resend delay.")
    else:
        with st.form("find_question_form"):
            username = st.text_input("Registered username")
            find = st.form_submit_button("Find security question", type="primary", use_container_width=True)
        if find:
            question = store.security_question(username)
            if question:
                st.session_state.question_user = username.strip()
            else:
                st.error("Unable to verify that username.")
        user = st.session_state.question_user
        if user:
            question = store.security_question(user)
            if question:
                st.info(question)
                with st.form("answer_question_form"):
                    answer = st.text_input("Your answer", type="password")
                    verify = st.form_submit_button("Verify answer →", type="primary", use_container_width=True)
                if verify:
                    if store.verify_answer(user, answer):
                        st.session_state.reset_identity = store.user(user)["email"]
                        st.session_state.reset_verified = True
                        st.rerun()
                    else:
                        st.error("Incorrect answer or too many attempts.")
    a, b = st.columns(2)
    with a:
        if st.button("← Sign in", use_container_width=True):
            navigate("login")
    with b:
        if st.button("OTP walkthrough", use_container_width=True):
            navigate("demo-otp")


def admin_login():
    st.markdown("### Administration")
    st.caption("Restricted access for milestone reviewers and administrators.")
    if not ADMIN_PASSWORD:
        st.warning("Configure ADMIN_PASSWORD to enable administrator access.")
    with st.form("admin_login_form"):
        username = st.text_input("Admin username")
        password = st.text_input("Admin password", type="password")
        submit = st.form_submit_button("Open admin dashboard →", type="primary", use_container_width=True)
    if submit:
        if not ADMIN_PASSWORD:
            st.error("Admin login is not yet configured.")
        elif store.limited("admin-login"):
            st.error("Too many administrator sign-in attempts. Try again in 15 minutes.")
        elif hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(password, ADMIN_PASSWORD):
            store.clear_limit("admin-login")
            st.session_state.jwt = issue_token(ADMIN_USERNAME, JWT_SECRET, role="admin", lifetime=3600)
            store.audit(ADMIN_USERNAME, "admin_login")
            navigate("admin-dashboard")
        else:
            store.failure("admin-login")
            store.audit("admin", "admin_login_failed")
            st.error("Invalid administrator credentials.")
    if st.button("← Back to sign in"):
        navigate("login")


def user_dashboard(account):
    top, out = st.columns([5, 1], vertical_alignment="center")
    with top:
        st.markdown('<div class="kicker">PORTWISE / Your maritime workspace</div>', unsafe_allow_html=True)
    with out:
        if st.button("Log out", use_container_width=True):
            log_out()
    username = html.escape(account["username"])
    last_visit = account["previous_login"]
    visit_note = ("Your previous successful sign-in was " + html.escape(last_visit.replace("T", " ")[:16]) + " UTC."
                  if last_visit else "Welcome to your PORTWISE workspace. This is your first recorded sign-in.")
    st.markdown(f'<div class="dashboard-hero"><div class="kicker">WELCOME BACK</div><h2>Good to see you, {username}.</h2><p>{visit_note}</p></div>', unsafe_allow_html=True)
    events = store.account_events(account["username"], 50)
    a, b, c = st.columns(3)
    a.metric("Account status", "Active")
    b.metric("Successful logins", account["login_count"])
    c.metric("Recent account events", len(events))
    activity, profile, security = st.tabs(["Recent activity", "Your profile", "Security settings"])
    with activity:
        if events:
            st.dataframe(pd.DataFrame(events)[["event", "occurred_at"]], use_container_width=True, hide_index=True)
        else:
            st.info("No recent account activity has been recorded yet.")
        st.caption("This is actual recorded account activity—not simulated shipping data.")
    with profile:
        st.write("**Username:**", account["username"])
        st.write("**Email:**", account["email"])
        st.write("**Member since:**", account["created_at"][:10])
    with security:
        st.subheader("Change password")
        st.caption("Your current password is required. Changing it signs you out of all existing sessions.")
        with st.form("change_password_form"):
            current = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm new password", type="password")
            save = st.form_submit_button("Update password", type="primary")
        if save:
            if not current:
                st.error("Enter your current password.")
            elif password_ok(new, confirm):
                ok, message = store.change_password(account["email"], current, new)
                if ok:
                    st.session_state.jwt = None
                    st.session_state.flash = "Password changed. Sign in again with the new password."
                    navigate("login")
                else:
                    st.error(message)
    st.caption("Freight pricing and route optimization will be added in later milestones.")


def admin_dashboard():
    top, out = st.columns([5, 1], vertical_alignment="center")
    with top:
        st.markdown('<div class="kicker">Restricted access / administrator</div>', unsafe_allow_html=True)
        st.title("Platform administration")
    with out:
        if st.button("Log out", use_container_width=True):
            log_out()
    users = store.list_users()
    events = store.recent_events(50)
    a, b, c = st.columns(3)
    a.metric("Registered members", len(users))
    b.metric("Total logins", sum(item["login_count"] for item in users))
    c.metric("Recent audit events", len(events))
    members, activity = st.tabs(["Registered users", "Activity history"])
    with members:
        query = st.text_input("Search users", placeholder="Username or email")
        matching = [u for u in users if query.casefold() in (u["username"] + " " + u["email"]).casefold()]
        if matching:
            st.dataframe(pd.DataFrame(matching)[["username", "email", "email_verified", "created_at", "last_login", "login_count"]], use_container_width=True, hide_index=True)
        else:
            st.info("No users found.")
    with activity:
        if events:
            st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
        else:
            st.info("No activity yet.")


def walkthrough(which):
    if which == "login":
        st.markdown('<div class="kicker">Demonstration 01 / account access</div>', unsafe_allow_html=True)
        st.title("Login & signup walkthrough")
        steps = [("01", "Create an account", "Provide username, email, strong password and security question."),
                 ("02", "Sign in", "Enter either your registered username or email plus your password."),
                 ("03", "JWT session", "A signed token is issued only after valid authentication."),
                 ("04", "Dashboard & logout", "The protected dashboard opens; logout clears the session.")]
    else:
        st.markdown('<div class="kicker">Demonstration 02 / account recovery</div>', unsafe_allow_html=True)
        st.title("Email OTP & recovery walkthrough")
        steps = [("01", "Register your email", "Create an account with an email inbox you can access."),
                 ("02", "Request the code", "On Forgot Password, choose Email OTP and supply that email."),
                 ("03", "Verify", "Gmail SMTP sends a six-digit code; it expires in five minutes."),
                 ("04", "Choose a new password", "After verification, reset your password and log in again.")]
    st.caption("This is a guided demonstration page. Use the buttons below to test the actual forms.")
    for number, title, description in steps:
        st.markdown(f'<div class="flow-card"><span class="step-num">{number[-1]}</span><b>{html.escape(title)}</b><p>{html.escape(description)}</p></div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        if st.button("Start live " + ("login" if which == "login" else "OTP") + " demo →", type="primary", use_container_width=True):
            navigate("login" if which == "login" else "forgot")
    with b:
        if st.button("View other walkthrough", use_container_width=True):
            navigate("demo-otp" if which == "login" else "demo-login")


if len(JWT_SECRET) < 32:
    st.error("JWT signing key is not configured. Run the Colab configuration cell first.")
    st.stop()

topbar()
viewer = current_user()
if viewer and viewer["role"] == "admin":
    if st.session_state.view != "admin-dashboard":
        navigate("admin-dashboard")
    admin_dashboard()
elif viewer:
    if st.session_state.view != "dashboard":
        navigate("dashboard")
    user_dashboard(viewer)
else:
    if st.session_state.jwt:
        st.session_state.jwt = None
    left, right = st.columns([1.05, .95], gap="large", vertical_alignment="center")
    with left:
        left_panel()
    with right:
        route = st.session_state.view
        if route == "signup":
            signup()
        elif route == "forgot":
            forgot()
        elif route == "verify-email":
            verify_email_page()
        elif route == "admin":
            admin_login()
        elif route == "demo-login":
            walkthrough("login")
        elif route == "demo-otp":
            walkthrough("otp")
        else:
            login()
build_label = ' · <strong>Build: PORTWISE-FINAL-01</strong>' if os.getenv('SHOW_BUILD_ID', '0') == '1' else ''
st.markdown('<div class="footer-note">PORTWISE · Agentic AI for Maritime Freight Pricing and Route Optimization' + build_label + '</div>', unsafe_allow_html=True)
