"""Password gate — ported faithfully from the original app.py's
require_password() (the Replit-only require_auth() proxy-header check is
dropped entirely per PLAN.md).

Differences from the Streamlit version (all intentional, see PLAN.md
"Security hardening"):
  - The auth token cookie is set via a native Set-Cookie response header
    (HttpOnly, Secure when the request is HTTPS, SameSite=Lax) instead of
    Streamlit's JS-injection workaround — this also makes it HttpOnly, which
    a JS-set cookie cannot be.
  - The login POST is CSRF-protected (Flask-WTF).
  - Token comparison uses secrets.compare_digest to avoid timing attacks.
  - The password itself is never stored in plaintext: APP_PASSWORD_HASH holds
    a werkzeug salted hash (see .env.example for how to generate one), and
    login checks it with check_password_hash instead of comparing a raw
    password from the environment.
  - Attempt count / lockout timestamp are kept in the server-side Flask
    session (Flask-Session) rather than Streamlit's in-memory session_state,
    so they persist correctly across requests.
"""
import hashlib
import secrets
import time

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

# Exact constants from the original Streamlit app.py (near line ~750).
AUTH_COOKIE_NAME = "wa_auth"
MAX_ATTEMPTS = 5
LOCKOUT_SECS = 300

auth_bp = Blueprint("auth", __name__)

# Paths that must always be reachable without the password gate.
# transcribe.assetlinks: Digital Asset Links file for the TWA (Android app) —
# Android/Chrome fetch it unauthenticated to verify the app is allowed to
# open this domain without a browser address bar. Not sensitive content.
_EXEMPT_ENDPOINTS = {"auth.login", "static", "transcribe.assetlinks"}


def _auth_token(password_hash: str) -> str:
    # Derived from the stored hash, never the raw password — the cookie
    # value can be recomputed by anyone holding APP_PASSWORD_HASH, but that's
    # the same trust boundary as the env var itself, and the raw password is
    # never needed again after the initial check_password_hash() at login.
    return hashlib.sha256(password_hash.encode()).hexdigest()


def _cookie_is_valid(password_hash: str) -> bool:
    expected = _auth_token(password_hash)
    supplied = request.cookies.get(AUTH_COOKIE_NAME, "")
    # secrets.compare_digest requires equal-length inputs to be fully
    # constant-time; both sides are always 64-char hex digests here.
    return secrets.compare_digest(supplied, expected)


def enforce_password_gate():
    """Flask before_request hook: the Flask equivalent of require_password().

    Returns None to let the request proceed, or a Response (redirect) to
    short-circuit it.
    """
    password_hash = current_app.config.get("APP_PASSWORD_HASH")
    if not password_hash:
        return None  # gate disabled entirely, matches original behavior

    if request.endpoint in _EXEMPT_ENDPOINTS:
        return None

    if request.path.startswith("/static/"):
        return None

    if session.get("password_ok") and _cookie_is_valid(password_hash):
        return None

    if _cookie_is_valid(password_hash):
        session["password_ok"] = True
        return None

    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    password_hash = current_app.config.get("APP_PASSWORD_HASH")
    if not password_hash:
        return redirect(url_for("transcribe.index"))

    # Already authed (e.g. visited /login directly) — bounce to the app.
    if session.get("password_ok") and _cookie_is_valid(password_hash):
        return redirect(url_for("transcribe.index"))

    now = time.time()
    lockout_until = session.get("_auth_lockout", 0)
    error = None
    locked_out_for = 0

    if request.method == "POST":
        if lockout_until > now:
            locked_out_for = int(lockout_until - now)
        else:
            entered = request.form.get("password", "")
            if check_password_hash(password_hash, entered):
                session["password_ok"] = True
                session["_auth_attempts"] = 0
                resp = redirect(url_for("transcribe.index"))
                token = _auth_token(password_hash)
                resp.set_cookie(
                    AUTH_COOKIE_NAME,
                    token,
                    max_age=60 * 60 * 24 * 365,
                    httponly=True,
                    secure=request.is_secure or current_app.config["IS_PRODUCTION"],
                    samesite="Lax",
                    path="/",
                )
                return resp
            else:
                attempts = session.get("_auth_attempts", 0) + 1
                session["_auth_attempts"] = attempts
                if attempts >= MAX_ATTEMPTS:
                    session["_auth_lockout"] = time.time() + LOCKOUT_SECS
                    session["_auth_attempts"] = 0
                    locked_out_for = LOCKOUT_SECS
                error = "Incorrect password"

    if lockout_until > now:
        locked_out_for = int(lockout_until - now)

    return render_template(
        "auth.html",
        error=error,
        locked_out_for=locked_out_for,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("password_ok", None)
    resp = redirect(url_for("auth.login"))
    resp.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return resp
