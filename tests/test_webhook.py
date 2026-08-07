import hashlib
import hmac
import json
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("WHATSAPP_APP_SECRET", "test-app-secret")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test-access-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "1234567890")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")

from app import create_app  # noqa: E402

APP_SECRET = "test-app-secret"

AUDIO_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "16505551111",
                            "phone_number_id": "1234567890",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Test User"},
                                "wa_id": "16505552222",
                            }
                        ],
                        "messages": [
                            {
                                "from": "16505552222",
                                "id": "wamid.ABC123",
                                "timestamp": "1700000000",
                                "type": "audio",
                                "audio": {
                                    "id": "MEDIA_ID_123",
                                    "mime_type": "audio/ogg; codecs=opus",
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


def sign(body_bytes: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_handshake_success(client):
    resp = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.data == b"12345"


def test_verify_handshake_wrong_token(client):
    resp = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 403


def test_post_without_signature_rejected(client):
    with patch("app.webhook._process_payload") as mock_process:
        resp = client.post("/webhook", json=AUDIO_MESSAGE_PAYLOAD)
        assert resp.status_code == 403
        mock_process.assert_not_called()


def test_post_with_bad_signature_rejected(client):
    with patch("app.webhook._process_payload") as mock_process:
        body = json.dumps(AUDIO_MESSAGE_PAYLOAD).encode()
        resp = client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": "sha256=deadbeef"},
        )
        assert resp.status_code == 403
        mock_process.assert_not_called()


def test_post_with_valid_signature_processes_audio_message(client):
    body = json.dumps(AUDIO_MESSAGE_PAYLOAD).encode()
    signature = sign(body)

    with patch("app.webhook.download_media") as mock_download, patch(
        "app.webhook.transcribe_audio"
    ) as mock_transcribe, patch("app.webhook.send_text_message") as mock_send:
        mock_download.return_value = b"fake-audio-bytes"
        mock_transcribe.return_value = {"text": "hello world", "error": None}

        resp = client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": signature},
        )

        assert resp.status_code == 200
        mock_download.assert_called_once_with("MEDIA_ID_123", "test-access-token")
        mock_transcribe.assert_called_once_with(b"fake-audio-bytes", "test-deepgram-key")
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert kwargs["to_phone_number"] == "16505552222"
        assert kwargs["body_text"] == "hello world"


def test_post_with_valid_signature_non_audio_message_gets_nudge(client):
    text_payload = json.loads(json.dumps(AUDIO_MESSAGE_PAYLOAD))
    msg = text_payload["entry"][0]["changes"][0]["value"]["messages"][0]
    del msg["audio"]
    msg["type"] = "text"
    msg["text"] = {"body": "hi"}

    body = json.dumps(text_payload).encode()
    signature = sign(body)

    with patch("app.webhook.send_text_message") as mock_send, patch(
        "app.webhook.transcribe_audio"
    ) as mock_transcribe:
        resp = client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": signature},
        )
        assert resp.status_code == 200
        mock_transcribe.assert_not_called()
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert "voice note" in kwargs["body_text"]


def test_post_status_update_event_ignored_without_error(client):
    status_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wamid.ABC123",
                                    "status": "delivered",
                                    "timestamp": "1700000000",
                                    "recipient_id": "16505552222",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    body = json.dumps(status_payload).encode()
    signature = sign(body)

    resp = client.post(
        "/webhook",
        data=body,
        content_type="application/json",
        headers={"X-Hub-Signature-256": signature},
    )
    assert resp.status_code == 200
