"""Deepgram transcription — vendored/adapted from trans/app/services/deepgram_client.py.

Adapted for this standalone repo: the API key is passed explicitly as a
function argument rather than read from Flask's app.config (this project has
no Flask app config, just plain env vars — see app/config.py). Simplified
for a text-reply bot: no word-level timestamps, no diarization concerns —
just the transcript text and an error field.
"""
from deepgram import DeepgramClient


def transcribe_audio(audio_bytes: bytes, api_key: str) -> dict:
    """Transcribe raw audio bytes using Deepgram.

    Args:
        audio_bytes: Raw audio file bytes (already downloaded from WhatsApp).
        api_key: Deepgram API key.

    Returns:
        dict with:
          - "text": the transcript (empty string on failure)
          - "error": None on success, else a short error description
    """
    try:
        deepgram = DeepgramClient(api_key=api_key)

        response = deepgram.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-2",
            smart_format=True,
            punctuate=True,
        )

        if hasattr(response, "results") and response.results:
            channels = getattr(response.results, "channels", None)
            if channels:
                alternatives = getattr(channels[0], "alternatives", None)
                if alternatives:
                    text = getattr(alternatives[0], "transcript", "") or ""
                    if text:
                        return {"text": text, "error": None}

        return {"text": "", "error": "Deepgram returned no transcript for this audio."}

    except Exception as e:
        # Deliberately no logging of audio content here — only the
        # exception type/message, never the transcript or audio bytes.
        return {"text": "", "error": f"Deepgram request failed: {e}"}
