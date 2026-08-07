"""Configuration for the Stage-0 WhatsApp bot.

Plain environment variables, no Flask app.config — this is deliberately
decoupled from the trans/ (WAtranscribe) repo, which this project does not
import from or depend on. Fails fast at import time if a required variable
is missing, so a misconfigured deploy never silently starts up half-broken.
"""
import os

REQUIRED_VARS = [
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "DEEPGRAM_API_KEY",
]


class Config:
    WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET")
    WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")

    @classmethod
    def validate(cls):
        missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                f"{', '.join(missing)}. Copy .env.example to .env and fill "
                "them in."
            )
