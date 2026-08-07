"""Helpers for the WhatsApp Business Cloud API (Graph API)."""
import requests

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


def download_media(media_id: str, access_token: str) -> bytes:
    """Download media (e.g. a voice note) referenced by a webhook message.

    WhatsApp's Graph API is a two-step fetch: first a GET to the media
    endpoint (authenticated with the access token) to get a short-lived
    download URL, then a second GET to that URL for the actual bytes.
    """
    meta_resp = requests.get(
        f"{GRAPH_API_BASE}/{media_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    meta_resp.raise_for_status()
    download_url = meta_resp.json()["url"]

    media_resp = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    media_resp.raise_for_status()
    return media_resp.content


def send_text_message(
    to_phone_number: str,
    body_text: str,
    phone_number_id: str,
    access_token: str,
) -> None:
    """Send a free-form text message reply via the Cloud API."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone_number,
        "type": "text",
        "text": {"body": body_text},
    }
    resp = requests.post(
        f"{GRAPH_API_BASE}/{phone_number_id}/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
