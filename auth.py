"""
auth.py
-------
Flask Blueprint for authentication routes:
  GET/POST  /login     → login form + handler
  GET/POST  /register  → registration form + handler
  GET       /logout    → clears session cookie

Session token is stored in a secure HTTP-only cookie.
All routes are self-contained — no templates directory needed
(HTML is rendered inline for easy portability).

Future API integration:
  Replace the rendered HTML responses with JSON (return jsonify(...))
  and use Authorization: Bearer <token> headers instead of cookies.
"""

from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    make_response,
    render_template_string,
)
from models import authenticate_user, create_user, create_session, delete_session

auth_bp = Blueprint("auth", __name__)

SESSION_COOKIE = "inv_session"


# ---------------------------------------------------------------------------
# Shared HTML shell (login + register pages use same layout)
# ---------------------------------------------------------------------------
_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{ title }} — Invoice Processor</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f4f5f7;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      border: 1px solid #e2e5e9;
      padding: 2.5rem 2rem;
      width: 100%;
      max-width: 400px;
    }
    .logo {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 1.75rem;
    }
    .logo-icon {
      width: 36px; height: 36px;
      background: #1a56db;
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
    }
    .logo-icon svg { fill: #fff; }
    .logo-text { font-size: 15px; font-weight: 600; color: #111; }
    h1 { font-size: 20px; font-weight: 600; color: #111; margin-bottom: 0.25rem; }
    .subtitle { font-size: 13px; color: #6b7280; margin-bottom: 1.75rem; }
    label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 5px; }
    input[type=text], input[type=email], input[type=password] {
      width: 100%; padding: 9px 12px;
      border: 1px solid #d1d5db;
      border-radius: 7px;
      font-size: 14px; color: #111;
      outline: none;
      margin-bottom: 1rem;
      transition: border-color 0.15s;
    }
    input:focus { border-color: #1a56db; box-shadow: 0 0 0 3px rgba(26,86,219,0.12); }
    .btn {
      width: 100%; padding: 10px;
      background: #1a56db; color: #fff;
      border: none; border-radius: 7px;
      font-size: 14px; font-weight: 500;
      cursor: pointer;
      margin-top: 0.25rem;
      transition: background 0.15s;
    }
    .btn:hover { background: #1446b8; }
    .error {
      background: #fef2f2; border: 1px solid #fecaca;
      color: #b91c1c; font-size: 13px;
      border-radius: 7px; padding: 9px 12px;
      margin-bottom: 1rem;
    }
    .success {
      background: #f0fdf4; border: 1px solid #bbf7d0;
      color: #15803d; font-size: 13px;
      border-radius: 7px; padding: 9px 12px;
      margin-bottom: 1rem;
    }
    .divider { border: none; border-top: 1px solid #f0f0f0; margin: 1.5rem 0; }
    .link-row { text-align: center; font-size: 13px; color: #6b7280; }
    .link-row a { color: #1a56db; text-decoration: none; font-weight: 500; }
    .link-row a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">
      <div class="logo-icon">
        <svg viewBox="0 0 20 20" width="18" height="18">
          <path d="M4 3h12a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V4a1 1 0 011-1zm1 2v10h10V5H5zm2 2h6v1.5H7V7zm0 3h6v1.5H7V10zm0 3h4v1.5H7V13z"/>
        </svg>
      </div>
      <span class="logo-text">Invoice Processor</span>
    </div>

    <h1>{{ title }}</h1>
    <p class="subtitle">{{ subtitle }}</p>

    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    {% if success %}<div class="success">{{ success }}</div>{% endif %}

    {{ form_content }}

    <hr class="divider" />
    <p class="link-row">{{ link_text }}</p>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
_LOGIN_FORM = """
<form method="POST" action="/login">
  <label for="username">Username</label>
  <input type="text" id="username" name="username" placeholder="your_username" autocomplete="username" required />
  <label for="password">Password</label>
  <input type="password" id="password" name="password" placeholder="••••••••" autocomplete="current-password" required />
  <button class="btn" type="submit">Sign in</button>
</form>
"""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(username, password)
        if user:
            token = create_session(user["id"])
            resp = make_response(redirect(url_for("dashboard")))
            resp.set_cookie(
                SESSION_COOKIE, token,
                httponly=True, samesite="Lax", max_age=60 * 60 * 8  # 8 hours
            )
            return resp
        else:
            error = "Invalid username or password."

    html = render_template_string(
        _PAGE,
        title="Sign in",
        subtitle="Process and export invoice data",
        error=error,
        success=None,
        form_content=_LOGIN_FORM,
        link_text='No account? <a href="/register">Create one</a>',
    )
    return html


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
_REGISTER_FORM = """
<form method="POST" action="/register">
  <label for="username">Username</label>
  <input type="text" id="username" name="username" placeholder="your_username" autocomplete="username" required />
  <label for="email">Email</label>
  <input type="email" id="email" name="email" placeholder="you@email.com" autocomplete="email" required />
  <label for="password">Password</label>
  <input type="password" id="password" name="password" placeholder="Min 6 characters" autocomplete="new-password" required />
  <button class="btn" type="submit">Create account</button>
</form>
"""


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            error = "Password must be at least 6 characters."
        elif not username or not email:
            error = "All fields are required."
        else:
            try:
                create_user(username, email, password)
                success = "Account created! You can now sign in."
            except ValueError as e:
                error = str(e)

    html = render_template_string(
        _PAGE,
        title="Create account",
        subtitle="Set up your Invoice Processor account",
        error=error,
        success=success,
        form_content=_REGISTER_FORM,
        link_text='Already have an account? <a href="/login">Sign in</a>',
    )
    return html


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout")
def logout():
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(token)
    resp = make_response(redirect(url_for("auth.login")))
    resp.delete_cookie(SESSION_COOKIE)
    return resp
