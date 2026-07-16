# WAtranscribe

A mobile-first web app that transcribes WhatsApp voice messages and generates AI-powered summaries. Share audio straight from WhatsApp via the installable PWA, or upload files manually — WAtranscribe transcribes them with word-level timestamps and lets you generate a summary at whatever condensation level you choose.

Flask app, deployed at **transcribe.flyboybyte.com**.

**Privacy by design: there is no database.** Everything (audio, transcript,
summary) lives only in server-side session storage for the duration of one
browsing session (a few hours), then expires — nothing is ever persisted
long-term. See `app/config.py`'s `PERMANENT_SESSION_LIFETIME` and
`deploy/DEPLOY.md`'s session-purge cron job.

## Features

- **Automatic transcription** — Deepgram Nova-2 with smart formatting, punctuation, and word-level timestamps, as soon as you upload
- **Explicit, opt-in summarization** — nothing is summarized automatically; pick a condensation level (1 = one-liner, 5 = comprehensive) and Claude (Haiku) generates it on demand
- **Interactive playback** — click any word in a transcript to jump to that moment in the audio
- **Share from WhatsApp** — install as a PWA and share voice notes directly to the app via the Web Share Target API
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
| `APP_PASSWORD_HASH` | No | Enables the password gate — must be a werkzeug hash, not plaintext |
| `FLASK_ENV` | No | Set to `production` on the VPS |

## Project layout

| Path | Purpose |
|---|---|
| `app/__init__.py` | Flask application factory |
| `app/auth.py` | Password gate (hashed password, lockout, CSRF) |
| `app/services/` | Deepgram client, Claude client, summary-to-timestamp mapper |
| `app/routes/transcribe.py` | Upload/transcribe/summarize/clear — the only blueprint besides auth |
| `app/templates/`, `app/static/` | Jinja templates, CSS, JS, PWA assets |
| `deploy/` | systemd unit, nginx config, deployment steps |
| `PLAN.md` | Migration/implementation plan and status |

## Deployment

See `PLAN.md` and `deploy/DEPLOY.md` (bare systemd + gunicorn + nginx + certbot, no Docker).
