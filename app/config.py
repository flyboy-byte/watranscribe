import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

ALLOWED_AUDIO_EXTENSIONS = {"opus", "m4a", "mp3", "wav", "ogg", "oga"}


class Config:
    """Reads all configuration from environment variables.

    See .env.example for the full list. python-dotenv loads .env in
    create_app() before this class is instantiated, so os.environ already
    has values from .env by the time this runs.
    """

    ENV = os.environ.get("FLASK_ENV", "development")
    IS_PRODUCTION = ENV == "production"

    # --- Secret key -----------------------------------------------------
    # Required in production: Flask signs the session cookie and CSRF
    # tokens with this. Fail fast rather than silently running insecurely.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError(
                "SECRET_KEY environment variable is required in production. "
                "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # Fine for local dev only — sessions won't survive a process restart.
        SECRET_KEY = "dev-only-insecure-secret-key-change-me"

    # --- Database ---------------------------------------------------------
    # Open Question 1 resolution: support both Postgres and SQLite via
    # SQLAlchemy. Default to a local SQLite file under instance/ so a first
    # deploy doesn't require standing up Postgres.
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{INSTANCE_DIR / 'watranscribe.db'}"

    # --- Auth / password gate ---------------------------------------------
    # Salted hash, not the raw password — generate with:
    #   python3 -c "from werkzeug.security import generate_password_hash as g; print(g('yourpassword'))"
    APP_PASSWORD_HASH = os.environ.get("APP_PASSWORD_HASH")

    # --- API keys (read by services/, kept here for visibility) -----------
    DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "AI_INTEGRATIONS_ANTHROPIC_API_KEY"
    )

    # --- Session storage ----------------------------------------------------
    # Open Question 2 resolution: server-side session store (Flask-Session,
    # filesystem backend) keyed by a session-id cookie, holding the same
    # shape of data the old st.session_state did (transcriptions, file_names,
    # summaries, audio_files as base64, word_timestamps, selected_file_index,
    # condensation_level). Filesystem backend is fine for a single VPS.
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = str(INSTANCE_DIR / "flask_session")
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_NAME = "wa_session"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days

    # --- Cookie security flags ----------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    # --- File upload validation ----------------------------------------------
    ALLOWED_AUDIO_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS
    MAX_CONTENT_LENGTH = 75 * 1024 * 1024  # 75MB per request

    # --- Auth cookie / lockout (ported from the original app.py) -------------
    AUTH_COOKIE_NAME = "wa_auth"
    THEME_COOKIE_NAME = "wa_theme"
    # Exact constants from the original Streamlit app.py (near line ~750):
    AUTH_MAX_ATTEMPTS = 5
    AUTH_LOCKOUT_SECS = 300

    WTF_CSRF_ENABLED = True
