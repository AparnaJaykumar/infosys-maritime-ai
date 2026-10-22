# PORTWISE — Milestone 1

This milestone builds the user authentication module for PORTWISE, a maritime freight project. Freight pricing and route optimization are planned for later milestones. The current app covers account creation, sign-in, account recovery, and separate user and administrator dashboards.

## Features

- Signup with a unique username and email, password confirmation, and a saved security question.
- Login with username or email; the same error is shown for an incorrect username or password.
- Signed JWT sessions, protected dashboards, logout, and session invalidation after password changes.
- Password recovery using a security answer or a six-digit email OTP valid for five minutes.
- Separate administrator sign-in and a registered-user directory without passwords or hashes.
- Hashed passwords and recovery answers, OTP attempt limits, login throttling, and account activity records.
- Light and dark maritime backgrounds. Email verification at signup is an extra feature.

## Stack

Python, Streamlit, SQLite, bcrypt, PyJWT, pandas, Gmail SMTP, and pyngrok for the Colab tunnel.

## Run in Google Colab

1. Open `PORTWISE_Final_All_in_One_Colab.ipynb` in Colab.
2. In the Secrets panel, add `JWT_SECRET` (a random key of at least 32 characters), `NGROK_AUTHTOKEN`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, and `ADMIN_PASSWORD` (at least 12 characters). Enable notebook access for each. `ADMIN_USERNAME` is optional and defaults to `admin`.
3. Use a Gmail App Password for `EMAIL_PASSWORD`; enable Google 2-Step Verification first. The email address is the sending account, not the recipient.
4. Run the cells from top to bottom. The notebook writes the app, installs its artwork, runs tests, checks SMTP login, and opens a public ngrok link.
5. Create an account, open the email verification page, request a code, verify the email, and sign in. Try both recovery methods and the separate admin sign-in.
6. Keep Colab connected during the demo. The SQLite database is temporary and can disappear when the runtime is deleted.
7. Before submitting an executed copy, clear all outputs and check that credentials and tunnel URLs are absent.

All four secrets named in the brief should be configured explicitly even though the notebook can generate a temporary JWT key. No real credentials are included.

## Run locally

Use Python 3.12. From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env privately, then load it:
set -a
source .env
set +a
streamlit run app.py
```

On Windows, activate `.venv` and set the same environment variables in PowerShell instead. Open http://localhost:8501. `DATABASE_PATH=./portwise_auth.db` is suitable locally. The notebook uses its own Colab path.

## Tests

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py auth_core.py
```

These tests do not establish real email delivery or a successful Colab/ngrok run. Those require the owner's configured accounts.

## Files

`app.py` contains the interface and routing; `auth_core.py` handles accounts, OTPs, and JWTs. `static/` contains the backgrounds, `.streamlit/` the configuration, and `tests/` the checks. The notebook is self-contained and recreates the runnable files. Docker files are optional; for Docker, set `DATABASE_PATH=/data/portwise_auth.db` in your private `.env` so the supplied volume retains the database.

## Submission status

Extract this ZIP and upload the **Milestone1 folder and its contents** into your personal Infosys repository. Do not upload the ZIP alone. This package contains the cleaned final notebook and extracted source, not the two older reference notebooks. See `REVIEW.md` for the comparison and remaining checks.

The brief asks for admin credentials directly in code but later asks for the admin password to be removed. This submission keeps the admin separate from signup users and reads its password from Secrets. Confirm that interpretation with the mentor if literal hard-coded credentials are expected.

## Screenshots

The following are the required screenshot destinations. Images are pending; add your own live captures before submission. Once files are added, the links will display them. Use a test account and redact personal addresses, passwords, OTP digits, tokens, and tunnel URLs.

| Capture | Image |
|---|---|
| Login | ![Login](screenshots/login.png) |
| Signup | ![Signup](screenshots/signup.png) |
| Forgot Password — security question | ![Security question recovery](screenshots/forgot_security_question.png) |
| Forgot Password — OTP | ![OTP recovery](screenshots/forgot_otp.png) |
| OTP email received | ![OTP email](screenshots/otp_email.png) |
| User dashboard | ![User dashboard](screenshots/user_dashboard.png) |
| Admin dashboard | ![Admin dashboard](screenshots/admin_dashboard.png) |
