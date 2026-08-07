import logging

from dotenv import load_dotenv
from flask import Flask

from app.config import Config


def create_app() -> Flask:
    load_dotenv()  # no-op if .env doesn't exist (e.g. real env vars in prod)
    Config.validate()

    app = Flask(__name__)
    app.config["WA_CONFIG"] = Config

    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    from app.webhook import bp as webhook_bp
    app.register_blueprint(webhook_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
