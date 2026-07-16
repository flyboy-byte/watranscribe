# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up (once)
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # fill in SECRET_KEY, DEEPGRAM_API_KEY, ANTHROPIC_API_KEY, etc.

# Run locally
source .venv/bin/activate
flask --app wsgi.py run

# Run the way production (gunicorn) will
gunicorn wsgi:app
```

There is no test suite, linter, or CI config in this repo. `PLAN.md` is the
living implementation/migration plan and status tracker — read it before
starting new work here, and keep it updated as work progresses.

## Architecture

This is a Flask port of an original Streamlit app (WhatsApp voice-note
transcription + AI summarization). The app factory lives in
`app/__init__.py` (`create_app()`), wired up in `wsgi.py` for gunicorn.

### Module layout
- `app/config.py` — all configuration from environment variables (see
  `.env.example`). Fails fast on missing `SECRET_KEY` when `FLASK_ENV=production`.
- `app/auth.py` — password gate (`enforce_password_gate`, a `before_request`
  hook). `APP_PASSWORD_HASH` must be a werkzeug salted hash, not plaintext —
  generate with `werkzeug.security.generate_password_hash`. Login sets an
  `HttpOnly`/`SameSite=Lax` cookie (`wa_auth`) whose value is derived from the
  stored hash (`sha256(APP_PASSWORD_HASH)`), so the raw password is never
  needed again after the initial `check_password_hash()` check. Failed
  attempts lock out for `LOCKOUT_SECS` after `MAX_ATTEMPTS`.
- `app/db.py`, `app/models.py` — SQLAlchemy engine/session setup plus the
  `TranscriptionSession` model and its repository functions
  (`save_session`, `get_all_sessions`, `get_session_by_id`, `delete_session`).
  `DATABASE_URL` accepts either a Postgres DSN or is left unset, in which
  case a local SQLite file under `instance/` is used.
- `app/services/`
  - `deepgram_client.py` — `transcribe_audio_with_deepgram()`, wraps the
    Deepgram SDK (`listen.v1.media.transcribe_file`, Nova-2 model). Returns
    `{"text", "words", "error"}` — callers must check `error` rather than
    treating `text` as always-valid transcript content (a Deepgram failure
    does not get silently summarized).
  - `claude_client.py` — `summarize_text()` / `summarize_conversation()`,
    using `claude-haiku-4-5-20251001` (cheap, sufficient for condensing a
    transcript) with per-condensation-level `max_tokens` caps, wrapped in
    `tenacity` retry on rate-limit errors only.
  - `summary_mapper.py` — pure/stateless keyword-overlap matching that maps
    summary sentences back to Deepgram word timestamps, for click-to-seek.
- `app/routes/transcribe.py` — upload/transcribe/summarize/redo-summary
  endpoints. In-progress session state (transcriptions, file_names,
  summaries, audio_files as base64, word_timestamps, selected_file_index,
  condensation_level) lives in the server-side Flask session (Flask-Session,
  filesystem backend), not the signed cookie — the payload is too large for
  a cookie. `_build_player_context()` shapes data for the player template.
- `app/routes/history.py` — list/save/delete/export(txt+json) for persisted
  sessions; reuses `transcribe._build_player_context`/`_ensure_state`.
- `app/templates/partials/player.html` + `app/static/js/player.js` — the
  interactive waveform/word-click player. Transcript/summary data is passed
  via a `<script type="application/json">` island (`| tojson | safe`, which
  Jinja/Flask HTML-escapes) and rendered client-side with `textContent`,
  never `innerHTML` — this is the deliberate XSS mitigation for
  user-supplied transcript content; don't reintroduce string-interpolated
  HTML/JS here.
- `app/static/sw.js` + `app/static/js/share-target.js` — PWA Web Share
  Target flow. WhatsApp's share sheet POSTs audio to `/static/share`
  (intercepted entirely client-side by the service worker, never reaches
  Flask), which stashes it in IndexedDB (`watranscribe-shared-files`); on
  next load, `share-target.js` reads it back out and auto-submits the
  upload form.

### Request flow
1. Upload (manual or via WhatsApp share) hits `/upload` in
   `app/routes/transcribe.py`.
2. File is validated (extension allowlist, `MAX_CONTENT_LENGTH`), saved to a
   temp path, transcribed via Deepgram.
3. If transcription succeeded and `ANTHROPIC_API_KEY` is set, the transcript
   is immediately summarized at the current condensation level (1–5).
4. Everything is held in the server-side session until explicitly saved to
   the database from the History tab.

### Security notes for future changes
- Security headers (CSP, X-Frame-Options, etc.) are applied at the nginx
  layer (`deploy/nginx_transcribe.conf`), not in Flask — keep it that way
  rather than duplicating in `app/__init__.py`.
- CSRF protection (Flask-WTF) is enabled globally; any new state-changing
  POST route needs a `csrf_token()` in its form.
- File upload extension allowlist is enforced server-side in
  `_allowed_file()` (`app/routes/transcribe.py`) — the client-side `accept=`
  attribute alone is not sufficient.

### Deployment
See `PLAN.md` for the full migration history/status and `deploy/DEPLOY.md`
for the systemd + nginx + certbot setup on the VPS.
