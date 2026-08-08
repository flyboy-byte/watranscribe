# WAtranscribe

A mobile-first web app that transcribes WhatsApp voice messages and generates AI-powered summaries. Share audio straight from WhatsApp via the installable PWA, or upload files manually — WAtranscribe transcribes them with word-level timestamps and lets you generate a summary at whatever condensation level you choose.

Flask app, deployed at **transcribe.flyboybyte.com**.

**Privacy by design: there is no database.** Everything (audio, transcript,
summary) lives only in server-side session storage for **30 minutes**,
then expires — nothing is ever persisted long-term. See `app/config.py`'s
`PERMANENT_SESSION_LIFETIME` and `deploy/DEPLOY.md`'s session-purge cron
job.

See `ARCHITECTURE.md` for a system overview (this app + the two
subprojects below) and `DECISIONS.md` for the reasoning behind specific
choices.

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
| `PLAN.md` | Chronological migration/implementation/debugging history |
| `ARCHITECTURE.md` | Current system overview |
| `DECISIONS.md` | Why things are the way they are, by decision |

## Deployment

See `PLAN.md` and `deploy/DEPLOY.md` (bare systemd + gunicorn + nginx + certbot, no Docker).

## Related subprojects in this repo

Two related-but-independent projects live as subdirectories here. They're
not part of the Flask app above and have their own dependencies/build
tooling — see each one's own docs before working in it.

### `watranscribe-twa/` — Android app

A native Android [Trusted Web Activity](https://developer.chrome.com/docs/android/trusted-web-activity)
wrapping this site, built with Google's `bubblewrap` CLI. It exists because
installing the PWA through Chrome doesn't reliably register as a WhatsApp
share target on every device/OS combination (e.g. GrapheneOS blocks the
WebAPK-minting round-trip Chrome needs) — a locally-built, signed APK with
the share intent-filter compiled directly into the manifest sidesteps that.

See `watranscribe-twa/STATUS.md` for build steps, signing setup, and
known issues. Signed APKs are published under this repo's
[Releases](https://github.com/flyboy-byte/watranscribe/releases).

### `watranscribe-bot/` — WhatsApp bot (fully shelved)

An early-stage spike exploring a WhatsApp Business Cloud API bot that
transcribes voice notes sent directly to it, as an alternative to the PWA
share flow. **Fully shelved, not just paused** — scaffolded and
unit-tested with mocked external calls only, never deployed or exercised
against real Meta/Deepgram traffic. The PWA + TWA combination above ended
up solving the real use case without routing anything through Meta; see
`DECISIONS.md` D-012 for the full reasoning.

See `watranscribe-bot/PROJECT_STATE.md`, `DECISIONS.md`, and
`RESUME_CHECKLIST.md` before resuming work here.
