# WAtranscribe

A mobile-first web app that transcribes WhatsApp voice messages and generates AI-powered summaries. Share audio straight from WhatsApp via the installable PWA, or upload files manually — WAtranscribe transcribes them with word-level timestamps and can condense long voice notes into summaries at five levels of detail.

Flask app, deployed at **transcribe.flyboybyte.com**.

## Features

- **Automatic transcription** — Deepgram Nova-2 with smart formatting, punctuation, and word-level timestamps
- **Interactive playback** — click any word in a transcript to jump to that moment in the audio
- **AI summaries** — Claude (Haiku) generates summaries with an adjustable condensation level (1 = one-liner, 5 = comprehensive)
- **Share from WhatsApp** — install as a PWA and share voice notes directly to the app via the Web Share Target API
- **History** — sessions (transcripts, summaries, audio) are stored in SQLite/Postgres for later review and export (TXT/JSON)
- **Password gate** — set `APP_PASSWORD_HASH` to protect the app behind a password

## Requirements

- Python 3.11+
- API keys for [Deepgram](https://deepgram.com) (transcription) and [Anthropic](https://www.anthropic.com) (summaries)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# fill in SECRET_KEY, DEEPGRAM_API_KEY, ANTHROPIC_API_KEY, etc. — see .env.example

flask --app wsgi.py run
```

Then open http://localhost:5000.

### Environment variables

See `.env.example` for the full list and generation commands. Notably:

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes in production | Flask session signing / CSRF |
| `DEEPGRAM_API_KEY` | Yes | Deepgram transcription |
| `ANTHROPIC_API_KEY` | For summaries | Claude summarization |
| `DATABASE_URL` | No | Postgres DSN; defaults to local SQLite under `instance/` |
| `APP_PASSWORD_HASH` | No | Enables the password gate — must be a werkzeug hash, not plaintext |
| `FLASK_ENV` | No | Set to `production` on the VPS |

## Project layout

| Path | Purpose |
|---|---|
| `app/__init__.py` | Flask application factory |
| `app/auth.py` | Password gate (hashed password, lockout, CSRF) |
| `app/db.py`, `app/models.py` | SQLAlchemy engine + `TranscriptionSession` model |
| `app/services/` | Deepgram client, Claude client, summary-to-timestamp mapper |
| `app/routes/` | Transcribe and history blueprints |
| `app/templates/`, `app/static/` | Jinja templates, CSS, JS, PWA assets |
| `deploy/` | systemd unit, nginx config, deployment steps |
| `PLAN.md` | Migration/implementation plan and status |

## Deployment

See `PLAN.md` and `deploy/DEPLOY.md` (bare systemd + gunicorn + nginx + certbot, no Docker).
