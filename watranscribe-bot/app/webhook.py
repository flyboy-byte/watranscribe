"""WhatsApp webhook: verification handshake + incoming-message handling.

Security note: the POST handler validates X-Hub-Signature-256 *before*
touching the request body/JSON in any way. That check is structured to be
the very first thing that happens in the view function and to return early
(403) on any failure, so no unauthenticated payload is ever parsed.
"""
import hashlib
import hmac
import logging
import traceback

from flask import Blueprint, current_app, request

from app.deepgram_client import transcribe_audio
from app.whatsapp import download_media, send_text_message

logger = logging.getLogger(__name__)

bp = Blueprint("webhook", __name__)

NO_VOICE_NOTE_REPLY = "Send me a voice note and I'll transcribe it."


@bp.route("/webhook", methods=["GET"])
def verify():
    """One-time handshake Meta uses to confirm you own this webhook URL."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    config = current_app.config["WA_CONFIG"]

    if mode == "subscribe" and token and hmac.compare_digest(
        token, config.WHATSAPP_VERIFY_TOKEN
    ):
        return challenge or "", 200, {"Content-Type": "text/plain"}

    return "Forbidden", 403


def _valid_signature(raw_body: bytes, header_value: str, app_secret: str) -> bool:
    if not header_value or not header_value.startswith("sha256="):
        return False
    provided_digest = header_value.split("=", 1)[1]
    expected_digest = hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(provided_digest, expected_digest)


@bp.route("/webhook", methods=["POST"])
def receive():
    config = current_app.config["WA_CONFIG"]

    # --- Signature check FIRST, before any body/JSON parsing. -------------
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not _valid_signature(request.get_data(), signature_header, config.WHATSAPP_APP_SECRET):
        return "Forbidden", 403

    # From here on, the request is authenticated as coming from Meta.
    try:
        _process_payload(request.get_json(silent=True) or {}, config)
    except Exception:
        # Log server-side only (no transcript/audio content ever logged),
        # still ack quickly so Meta doesn't retry forever.
        logger.exception("Error processing WhatsApp webhook payload")

    return "OK", 200


def _process_payload(payload: dict, config) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                _handle_message(message, config)
            # Non-message events (e.g. "statuses" delivery/read receipts)
            # simply have no "messages" key here — nothing to do.


def _handle_message(message: dict, config) -> None:
    from_number = message.get("from")
    if not from_number:
        return

    msg_type = message.get("type")

    if msg_type == "audio" and message.get("audio", {}).get("id"):
        _handle_audio_message(from_number, message["audio"]["id"], config)
        return

    # Any other message type (text, image, etc.) gets a friendly nudge.
    try:
        send_text_message(
            to_phone_number=from_number,
            body_text=NO_VOICE_NOTE_REPLY,
            phone_number_id=config.WHATSAPP_PHONE_NUMBER_ID,
            access_token=config.WHATSAPP_ACCESS_TOKEN,
        )
    except Exception:
        logger.exception("Failed to send nudge reply to WhatsApp")


def _handle_audio_message(from_number: str, media_id: str, config) -> None:
    try:
        audio_bytes = download_media(media_id, config.WHATSAPP_ACCESS_TOKEN)
    except Exception:
        logger.exception("Failed to download WhatsApp media")
        _safe_reply(from_number, "Sorry, I couldn't download that voice note.", config)
        return

    try:
        result = transcribe_audio(audio_bytes, config.DEEPGRAM_API_KEY)
    finally:
        # Zero retention: drop the in-memory audio reference as soon as
        # we're done with it. Nothing here is written to disk or logged.
        del audio_bytes

    if result.get("error") or not result.get("text"):
        _safe_reply(
            from_number,
            "Sorry, I couldn't transcribe that voice note.",
            config,
        )
        return

    _safe_reply(from_number, result["text"], config)


def _safe_reply(to_number: str, body_text: str, config) -> None:
    try:
        send_text_message(
            to_phone_number=to_number,
            body_text=body_text,
            phone_number_id=config.WHATSAPP_PHONE_NUMBER_ID,
            access_token=config.WHATSAPP_ACCESS_TOKEN,
        )
    except Exception:
        logger.exception("Failed to send WhatsApp reply")
