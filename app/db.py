"""SQLAlchemy engine/session setup.

Ported from the original database.py, adapted for Flask: engine is created
once in create_app() from app.config.Config.DATABASE_URL (works for both
Postgres and SQLite DSNs), and a scoped_session is torn down at the end of
every request/app-context.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

Base = declarative_base()

engine = None
SessionLocal = None


def init_engine(database_url: str):
    """Create the engine + scoped session factory for the given DSN."""
    global engine, SessionLocal

    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        # SQLite needs this to be usable across threads (gunicorn workers
        # each have their own process, but Flask's dev server / a single
        # worker may use multiple threads).
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_recycle"] = 300
        connect_args = {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }

    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
    SessionLocal = scoped_session(sessionmaker(bind=engine))
    return engine


def init_db(app):
    """Create tables and wire the engine to the Flask app."""
    init_engine(app.config["DATABASE_URL"])
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)

    @app.teardown_appcontext
    def remove_session(exception=None):
        SessionLocal.remove()


def get_session():
    """Return the current scoped SQLAlchemy session."""
    return SessionLocal()
