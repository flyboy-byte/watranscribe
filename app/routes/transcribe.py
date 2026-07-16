"""Transcribe tab: upload, transcribe, summarize, redo-summary endpoints.

Session state (Flask-Session, server-side filesystem backend keyed by a
session-id cookie) holds the same shape of data the old st.session_state did:
transcriptions, file_names, summaries, audio_files (base64), word_timestamps,
selected_file_index, condensation_level. Theme stays a plain client cookie
(set directly by static/js/theme.js), never touches the server session.
"""
import base64
import os
import tempfile
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.services.claude_client import has_api_key, summarize_conversation, summarize_text
from app.services.deepgram_client import transcribe_audio_with_deepgram

transcribe_bp = Blueprint("transcribe", __name__)

LEVEL_LABELS = {1: "Quick", 2: "Brief", 3: "Balanced", 4: "Detailed", 5: "Full"}

# Markdown decoration Claude sometimes wraps summary lines in (bold
# sub-headers like "**Key Points:**", "# " headings, bullet markers). Bold
# markers can land mid-line (e.g. "**Overall Theme:** the rest of the
# sentence"), not just at the very start/end, so a plain .strip(chars) isn't
# enough — strip "**" anywhere, then trim leading heading/bullet decoration.
_MD_DECORATION = " *#•-"


def _clean_summary_line(line: str) -> str:
    return line.replace("**", "").strip(_MD_DECORATION).strip()

_DEFAULTS = {
    "transcriptions": [],
    "file_names": [],
    "audio_files": [],
    "word_timestamps": [],
    "summaries": {},
    "condensation_level": 3,
    "selected_file_index": 0,
}


def _ensure_state():
    for key, default in _DEFAULTS.items():
        if key not in session:
            session[key] = list(default) if isinstance(default, list) else (
                dict(default) if isinstance(default, dict) else default
            )


def _reset_state():
    for key, default in _DEFAULTS.items():
        session[key] = list(default) if isinstance(default, list) else (
            dict(default) if isinstance(default, dict) else default
        )
    session.modified = True


def _allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in current_app.config["ALLOWED_AUDIO_EXTENSIONS"]


@transcribe_bp.route("/", methods=["GET"])
def index():
    _ensure_state()

    if "file" in request.args:
        try:
            idx = int(request.args["file"])
            n = len(session["file_names"])
            if 0 <= idx < n:
                session["selected_file_index"] = idx
                session.modified = True
        except (TypeError, ValueError):
            pass

    file_names = session["file_names"]
    n = len(file_names)
    selected_idx = min(session.get("selected_file_index", 0), max(n - 1, 0))

    player = None
    if n:
        file_name = file_names[selected_idx]
        words = (
            session["word_timestamps"][selected_idx]
            if selected_idx < len(session["word_timestamps"])
            else []
        )
        audio_b64 = (
            session["audio_files"][selected_idx]
            if selected_idx < len(session["audio_files"])
            else None
        )
        summary_text = str(session["summaries"].get(str(selected_idx), session["summaries"].get(selected_idx, "")))
        player = _build_player_context(
            unique_id=f"t{selected_idx}",
            file_name=file_name,
            audio_b64=audio_b64,
            words=words,
            summary_text=summary_text,
        )

    return render_template(
        "index.html",
        file_names=file_names,
        n=n,
        selected_idx=selected_idx,
        transcript=session["transcriptions"][selected_idx] if n else "",
        player=player,
        has_api_key=has_api_key(),
        condensation_level=session["condensation_level"],
        level_labels=LEVEL_LABELS,
        all_summary=session["summaries"].get("all"),
        wa_shared=bool(request.args.get("wa_shared")),
    )


def _build_player_context(unique_id, file_name, audio_b64, words, summary_text):
    mime_types = {
        "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
        "opus": "audio/ogg", "m4a": "audio/mp4", "oga": "audio/ogg",
    }
    ext = Path(file_name).suffix.lstrip(".").lower() or "opus"
    mime = mime_types.get(ext, "audio/ogg")

    clean_words = [
        {"word": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", w.get("start", 0) + 0.3)}
        for w in (words or [])
        if isinstance(w, dict) and w.get("word")
    ]

    summary_text = str(summary_text or "")
    tldr, points = "", []
    if summary_text.strip():
        lines = [l.strip() for l in summary_text.strip().split("\n") if l.strip()]
        tldr = _clean_summary_line(lines[0]) if lines else summary_text
        points = [_clean_summary_line(l) for l in lines[1:] if l.strip()]

    return {
        "id": unique_id,
        "file_name": file_name,
        "audio_b64": audio_b64,
        "mime": mime,
        "words": clean_words,
        "full": summary_text,
        "tldr": tldr,
        "points": points,
        "has_summary": bool(tldr),
        "has_words": bool(clean_words),
    }


@transcribe_bp.route("/upload", methods=["POST"])
def upload():
    _ensure_state()

    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        flash("No files selected.")
        return redirect(url_for("transcribe.index"))

    for uf in files:
        if not _allowed_file(uf.filename):
            flash(f"Skipped {uf.filename}: unsupported file type.")
            continue

        suffix = Path(uf.filename).suffix or ".opus"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            uf.save(tmp.name)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as fh:
                raw = fh.read()
            result = transcribe_audio_with_deepgram(tmp_path)
        finally:
            os.remove(tmp_path)

        idx = len(session["file_names"])
        text = result.get("text", "")
        error = result.get("error")
        if error:
            flash(f"Transcription failed for {uf.filename}: {error}")

        session["file_names"].append(uf.filename)
        session["transcriptions"].append(text)
        session["audio_files"].append(base64.b64encode(raw).decode())
        session["word_timestamps"].append(result.get("words", []))

        if not error and has_api_key() and text.strip():
            try:
                session["summaries"][str(idx)] = summarize_text(
                    text, condensation=session["condensation_level"]
                )
            except Exception:
                pass

    session["selected_file_index"] = len(session["file_names"]) - 1
    session.modified = True
    return redirect(url_for("transcribe.index"))


@transcribe_bp.route("/transcript/<int:idx>", methods=["POST"])
def update_transcript(idx):
    _ensure_state()
    if 0 <= idx < len(session["transcriptions"]):
        session["transcriptions"][idx] = request.form.get("text", session["transcriptions"][idx])
        session.modified = True
    return redirect(url_for("transcribe.index", file=idx))


@transcribe_bp.route("/summarize/<int:idx>", methods=["POST"])
def summarize(idx):
    _ensure_state()
    if not has_api_key():
        flash("ANTHROPIC_API_KEY is not set — summaries unavailable.")
        return redirect(url_for("transcribe.index", file=idx))

    try:
        level = int(request.form.get("level", session["condensation_level"]))
    except (TypeError, ValueError):
        level = session["condensation_level"]
    level = max(1, min(5, level))

    if 0 <= idx < len(session["transcriptions"]):
        transcript = session["transcriptions"][idx]
        if transcript.strip():
            try:
                session["summaries"][str(idx)] = summarize_text(transcript, condensation=level)
                session["condensation_level"] = level
                session.modified = True
            except Exception as e:
                flash(f"Summarize failed: {e}")

    return redirect(url_for("transcribe.index", file=idx))


@transcribe_bp.route("/summarize-all", methods=["POST"])
def summarize_all():
    _ensure_state()
    if not has_api_key():
        flash("ANTHROPIC_API_KEY is not set — summaries unavailable.")
        return redirect(url_for("transcribe.index"))

    try:
        level = int(request.form.get("level", session["condensation_level"]))
    except (TypeError, ValueError):
        level = session["condensation_level"]
    level = max(1, min(5, level))

    try:
        overall = summarize_conversation(session["transcriptions"], condensation=level)
        session["summaries"]["all"] = overall
        session["condensation_level"] = level
        session.modified = True
    except Exception as e:
        flash(f"Summarize failed: {e}")

    return redirect(url_for("transcribe.index"))


@transcribe_bp.route("/clear", methods=["POST"])
def clear():
    _reset_state()
    return redirect(url_for("transcribe.index"))
