"""Deepgram transcription — ported from the original deepgram_integration.py,
unchanged apart from the module name/import path.
"""
from deepgram import DeepgramClient


def transcribe_audio_with_deepgram(audio_file_path: str) -> dict:
    """Transcribe audio file using Deepgram with word-level timestamps.

    Args:
        audio_file_path: Path to the audio file

    Returns:
        dict with 'text' (full transcription) and 'words' (list of word objects with timestamps)
    """
    try:
        deepgram = DeepgramClient()

        with open(audio_file_path, "rb") as audio:
            buffer_data = audio.read()

            response = deepgram.listen.v1.media.transcribe_file(
                request=buffer_data,
                model="nova-2",
                smart_format=True,
                utterances=True,
                punctuate=True,
                diarize=False
            )

            if hasattr(response, 'results') and response.results:
                if hasattr(response.results, 'channels') and len(response.results.channels) > 0:
                    channel = response.results.channels[0]
                    if hasattr(channel, 'alternatives') and len(channel.alternatives) > 0:
                        alternative = channel.alternatives[0]

                        transcription_text = alternative.transcript if hasattr(alternative, 'transcript') else ''

                        words_data = []
                        if hasattr(alternative, 'words') and alternative.words:
                            for word in alternative.words:
                                if hasattr(word, 'word'):
                                    words_data.append({
                                        "word": word.word,
                                        "start": word.start if hasattr(word, 'start') else 0,
                                        "end": word.end if hasattr(word, 'end') else 0,
                                        "confidence": word.confidence if hasattr(word, 'confidence') else 0
                                    })

                        return {
                            "text": transcription_text,
                            "words": words_data
                        }

            return {
                "text": "",
                "words": [],
                "error": "Deepgram returned no transcript for this file.",
            }

    except Exception as e:
        print(f"Deepgram error: {str(e)}")
        return {
            "text": "",
            "words": [],
            "error": str(e),
        }
