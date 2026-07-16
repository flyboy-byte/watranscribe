"""Flask application factory."""
import os

from dotenv import load_dotenv
from flask import Flask, request
from flask_session import Session
from flask_wtf import CSRFProtect

load_dotenv()  # populate os.environ from .env before Config reads it


def create_app():
    from app.config import Config

    app = Flask(__name__)
    app.config.from_object(Config)

    Session(app)
    CSRFProtect(app)

    from app.auth import auth_bp, enforce_password_gate
    from app.routes.transcribe import transcribe_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(transcribe_bp)

    app.before_request(enforce_password_gate)

    @app.context_processor
    def inject_theme():
        theme = request.cookies.get(app.config["THEME_COOKIE_NAME"], "dark")
        if theme not in ("dark", "light"):
            theme = "dark"
        return {"theme": theme}

    @app.errorhandler(413)
    def too_large(_e):
        max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return (f"File too large. Max upload size is {max_mb}MB.", 413)

    return app
