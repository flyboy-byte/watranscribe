"""History tab: list/view/delete/export endpoints."""
import json

from flask import Blueprint, Response, flash, redirect, render_template, session, url_for

from app.models import delete_session, get_all_sessions, get_session_by_id, save_session
from app.routes.transcribe import _build_player_context, _ensure_state

history_bp = Blueprint("history", __name__)


@history_bp.route("/history", methods=["GET"])
def index():
    try:
        sessions = get_all_sessions()
    except Exception as e:
        sessions = []
        flash(f"Could not load history: {e}")

    entries = []
    for sess in sessions:
        files = sess.file_names or []
        txs = sess.transcriptions or []
        summs = sess.summaries or {}
        audio_list = sess.audio_files or []
        words_list = sess.word_timestamps or []

        file_label = ", ".join(f[:28] for f in files) if files else "Untitled session"
        preview = ""
        if summs:
            first_sum = next((v for v in summs.values() if isinstance(v, str) and v.strip()), "")
            if first_sum:
                preview = first_sum.strip().split("\n")[0][:120]
        if not preview and txs:
            preview = txs[0][:120] if txs[0] else ""

        players = []
        if audio_list and txs:
            for i, (ab64, fname) in enumerate(zip(audio_list, files)):
                if not ab64:
                    continue
                words = words_list[i] if i < len(words_list) else []
                file_summary = str(summs.get(str(i), summs.get(i, "")))
                players.append(
                    _build_player_context(
                        unique_id=f"h{sess.id}_{i}",
                        file_name=fname,
                        audio_b64=ab64,
                        words=words,
                        summary_text=file_summary,
                    )
                )

        entries.append(
            {
                "id": sess.id,
                "created": sess.created_at.strftime("%b %d, %Y %H:%M") if sess.created_at else "Unknown",
                "file_label": file_label,
                "preview": preview,
                "players": players,
                "transcripts": txs if not audio_list else [],
                "files": files,
            }
        )

    return render_template("history.html", entries=entries)


@history_bp.route("/history/save", methods=["POST"])
def save():
    _ensure_state()
    txs = session.get("transcriptions", [])
    if txs and any(t.strip() for t in txs):
        try:
            save_session(
                file_names=session.get("file_names", []),
                transcriptions=txs,
                summaries=session.get("summaries", {}),
                summary_style=str(session.get("condensation_level", 3)),
                audio_files=session.get("audio_files", []),
                word_timestamps=session.get("word_timestamps", []),
            )
            flash("Session saved.")
        except Exception as e:
            flash(f"Save failed: {e}")
    else:
        flash("Nothing to save — transcribe an audio file first.")
    return redirect(url_for("history.index"))


@history_bp.route("/history/<int:session_id>/delete", methods=["POST"])
def delete(session_id):
    try:
        delete_session(session_id)
    except Exception as e:
        flash(f"Delete failed: {e}")
    return redirect(url_for("history.index"))


@history_bp.route("/history/<int:session_id>/export.txt", methods=["GET"])
def export_txt(session_id):
    sess = get_session_by_id(session_id)
    if not sess:
        return ("Not found", 404)

    lines = []
    files = sess.file_names or []
    txs = sess.transcriptions or []
    summs = sess.summaries or {}
    for i, tx in enumerate(txs):
        fname = files[i] if i < len(files) else f"File {i + 1}"
        lines.append(f"=== {fname} ===")
        lines.append(tx or "")
        summary = summs.get(str(i), summs.get(i, ""))
        if summary:
            lines.append("")
            lines.append("--- Summary ---")
            lines.append(summary)
        lines.append("")
    if "all" in summs:
        lines.append("=== Catch-up summary (all files) ===")
        lines.append(summs["all"])

    body = "\n".join(lines)
    return Response(
        body,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=session-{session_id}.txt"},
    )


@history_bp.route("/history/<int:session_id>/export.json", methods=["GET"])
def export_json(session_id):
    sess = get_session_by_id(session_id)
    if not sess:
        return ("Not found", 404)

    data = {
        "id": sess.id,
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "file_names": sess.file_names,
        "transcriptions": sess.transcriptions,
        "summaries": sess.summaries,
        "summary_style": sess.summary_style,
        "word_timestamps": sess.word_timestamps,
        # audio_files (base64) intentionally omitted from JSON export — large
        # and not useful outside the app; use the in-app player instead.
    }
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=session-{session_id}.json"},
    )
