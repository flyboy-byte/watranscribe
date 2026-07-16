"""TranscriptionSession model — ported unchanged from the original database.py,
plus a small repository layer (save/list/get/delete) that replaces the old
module-level functions, using the Flask-scoped SQLAlchemy session from app.db.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON

from app.db import Base, get_session


class TranscriptionSession(Base):
    __tablename__ = "transcription_sessions"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_names = Column(JSON)
    transcriptions = Column(JSON)
    summaries = Column(JSON)
    summary_style = Column(String, default="standard")
    audio_files = Column(JSON)
    word_timestamps = Column(JSON)


def save_session(
    file_names,
    transcriptions,
    summaries=None,
    summary_style="standard",
    audio_files=None,
    word_timestamps=None,
):
    """Save a transcription session to the database."""
    session = get_session()
    try:
        new_session = TranscriptionSession(
            file_names=file_names,
            transcriptions=transcriptions,
            summaries=summaries or {},
            summary_style=summary_style,
            audio_files=audio_files or [],
            word_timestamps=word_timestamps or [],
        )
        session.add(new_session)
        session.commit()
        return new_session.id
    finally:
        session.close()


def get_all_sessions():
    """Get all transcription sessions, newest first."""
    session = get_session()
    try:
        return (
            session.query(TranscriptionSession)
            .order_by(TranscriptionSession.created_at.desc())
            .all()
        )
    finally:
        session.close()


def get_session_by_id(session_id):
    session = get_session()
    try:
        return (
            session.query(TranscriptionSession)
            .filter(TranscriptionSession.id == session_id)
            .first()
        )
    finally:
        session.close()


def delete_session(session_id):
    session = get_session()
    try:
        session.query(TranscriptionSession).filter(
            TranscriptionSession.id == session_id
        ).delete()
        session.commit()
    finally:
        session.close()
