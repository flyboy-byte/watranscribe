# WAtranscribe → Flask migration & deployment plan

**Status:** Steps 1-8 done (scaffold, DB, services, auth, transcribe route+player,
history route, PWA assets, local smoke test all implemented and verified
booting under both `flask`/test-client and `gunicorn`). Steps 9-11 (deploy
files, doc updates, retiring the old Streamlit folder) still pending — resume
there.
**Goal:** Reorganize the existing Streamlit app (currently unpacked at
`WAtranscribe-claude-public-app-clone-v1-u1ubpf/`, originally from
`WAtranscribe-claude-public-app-clone-v1-u1ubpf.zip`) into a Flask app living
directly under `/home/logan/projects/trans/`, deployable on the user's VPS at
**transcribe.flyboybyte.com**, running alongside other projects on the same box.

## Decisions already made with the user (do not re-ask)

- **Deploy method:** bare systemd + gunicorn (no Docker). nginx reverse-proxies
  a local port to the public subdomain.
- **UI scope:** port everything as-is — PWA share-target (WhatsApp share →
  IndexedDB → auto file-upload), waveform/word-click audio player, summary
  hero card with condensation levels 1–5, light/dark theme toggle via cookie,
  history tab, password-gate auth. Reimplement as Flask routes + Jinja
  templates + static JS (no more `st.markdown(unsafe_allow_html=True)` /
  `components.html` hacks — real templates and a real static JS file).
- **nginx/TLS:** assume a standard Debian/Ubuntu + nginx + certbot setup;
  write a self-contained `sites-available` server block + certbot notes. User
  will adjust paths if their actual layout differs.
- **Domain:** transcribe.flyboybyte.com, deployed as one of several projects
  on the same VPS (i.e. it needs its own systemd unit + nginx server block +
  own venv, not fight other projects for ports).

## Source-of-truth facts gathered from the existing code

Read in full already: `app.py` (~1700 lines), `database.py`,
`claude_integration.py`, `deepgram_integration.py`, `summary_mapper.py`,
`README.md`, `replit.md`, `pyproject.toml`, `.replit`,
`.streamlit/config.toml`.

- **APIs required:**
  - **Deepgram** (`DEEPGRAM_API_KEY`) — transcription, Nova-2 model, word-level
    timestamps, smart formatting/punctuation. Used via `deepgram-sdk`
    (`DeepgramClient().listen.v1.media.transcribe_file(...)`).
  - **Anthropic Claude** (`ANTHROPIC_API_KEY`, or legacy
    `AI_INTEGRATIONS_ANTHROPIC_API_KEY` + optional
    `AI_INTEGRATIONS_ANTHROPIC_BASE_URL`) — summarization,
    `model="claude-sonnet-4-6"`, wrapped in tenacity retry (7 attempts,
    2s→128s backoff, retries only on 429/rate-limit).
  - No other external API. `pydub`/`speechrecognition`/ffmpeg are listed in
    `pyproject.toml` but **grepped `app.py` for pydub/ffmpeg/AudioSegment
    usage and found none** — they're vestigial from a template and can likely
    be dropped (confirm nothing in `deepgram_integration.py` needs them
    either — it doesn't; Deepgram is fed the raw uploaded bytes directly).
    FFmpeg is therefore **not required** on the VPS unless we decide to add
    format-conversion/compression later.
- **Data model:** one Postgres table `transcription_sessions` (SQLAlchemy):
  id, created_at, file_names (JSON list), transcriptions (JSON list),
  summaries (JSON dict, keyed by file index + `"all"` for multi-file
  catch-up), summary_style, audio_files (JSON list of base64 audio),
  word_timestamps (JSON list of Deepgram word objects).
- **Session state (Streamlit-only, needs a Flask equivalent):**
  `transcriptions`, `file_names`, `summaries`, `audio_files`,
  `word_timestamps`, `selected_file_index`, `condensation_level`, `theme`.
  In Flask this becomes: server-side Flask session (signed cookie) holding
  just the *active* in-progress transcribe session (small IDs/state), with
  actual transcript/audio blobs held either in the session or a lightweight
  server-side store keyed by a session id — needs a decision at
  implementation time (see Open Questions below). Theme should stay a plain
  cookie like today.
- **Auth model to port:**
  - `require_password()` — active only if `APP_PASSWORD` env var set. sha256
    token compared, stored client-side as a cookie, attempt-count lockout
    (`_MAX_ATTEMPTS`, `_LOCKOUT_SECS` — check exact constants in old
    `app.py` near line ~750 before porting). In Flask: implement as a
    `before_request` hook / decorator, with the token cookie set via
    `Set-Cookie` header (not injected JS — this was a Streamlit workaround,
    Flask can just set cookies natively). Add CSRF protection on the login
    POST.
  - `require_auth()` (Replit proxy header check) is Replit-specific — **drop
    it**, not relevant off Replit. VPS deployment should rely solely on the
    password gate (and optionally IP allowlisting / basic auth at the nginx
    layer if the user wants a second layer — flag this as an option, don't
    assume).
- **PWA / WhatsApp share:** `static/manifest.json` (Web Share Target API),
  `static/sw.js` (service worker, IndexedDB store
  `watranscribe-shared-files`), and injected JS in `app.py` that reads
  IndexedDB on load and programmatically populates the file `<input>`. Port
  manifest/sw.js mostly unchanged; the "populate file input" JS becomes a
  static `.js` file loaded normally by the Jinja template instead of being
  string-concatenated into `st.markdown`.
- **Interactive player:** `render_audio_player_with_words()` in `app.py`
  builds one big HTML/JS blob (waveform scrubber + summary hero + peek sheet
  with per-word click-to-seek). Port this to a proper template
  (`templates/partials/player.html`) + static JS module, with data passed as
  a JSON `<script type="application/json">` block instead of inline string
  interpolation — reduces XSS risk from transcript/summary text.
- **Condensation levels 1–5** and their instruction strings are in
  `claude_integration.get_condensation_instruction()` — port unchanged.
- **Timestamp mapping** (`summary_mapper.py`) is pure/stateless — port
  unchanged as-is, no framework dependency.

## Target directory structure (under `/home/logan/projects/trans/`)

```
trans/
├── CLAUDE.md                     # already exists, will need updating for Flask
├── PLAN.md                       # this file
├── README.md                     # updated for Flask/VPS deployment
├── pyproject.toml                # trim deps: flask, gunicorn, deepgram-sdk,
│                                  # anthropic, tenacity, sqlalchemy,
│                                  # psycopg2-binary (or drop if using SQLite),
│                                  # flask-wtf (CSRF), python-dotenv
├── .env.example                  # DEEPGRAM_API_KEY, ANTHROPIC_API_KEY,
│                                  # DATABASE_URL, APP_PASSWORD, SECRET_KEY
├── .gitignore
├── wsgi.py                       # gunicorn entrypoint: `from app import create_app; app = create_app()`
├── app/
│   ├── __init__.py                # create_app() factory, config load, blueprint registration
│   ├── config.py                  # Config class reading env vars
│   ├── auth.py                    # password-gate decorator/before_request, lockout logic
│   ├── db.py                      # SQLAlchemy engine/session setup
│   ├── models.py                  # TranscriptionSession model (ported from database.py)
│   ├── services/
│   │   ├── deepgram_client.py     # ported deepgram_integration.py
│   │   ├── claude_client.py       # ported claude_integration.py
│   │   └── summary_mapper.py      # ported unchanged
│   ├── routes/
│   │   ├── transcribe.py          # upload, transcribe, summarize, redo-summary endpoints
│   │   └── history.py             # list/view/delete/export endpoints
│   ├── templates/
│   │   ├── base.html              # shared layout, theme toggle, header
│   │   ├── index.html             # transcribe tab
│   │   ├── history.html           # history tab
│   │   ├── auth.html              # password gate screen
│   │   └── partials/
│   │       └── player.html        # waveform + summary hero + peek sheet
│   └── static/
│       ├── css/app.css            # extracted design-system CSS (was inline in app.py)
│       ├── js/
│       │   ├── player.js          # word-click seek, waveform, summary hero interactions
│       │   ├── share-target.js    # IndexedDB read + auto file-input population
│       │   └── theme.js           # theme toggle cookie logic
│       ├── manifest.json          # ported
│       ├── sw.js                  # ported
│       └── icons/                 # apple-touch-icon.png, icon-192.png, icon-512.png
├── deploy/
│   ├── transcribe.service         # systemd unit (gunicorn, User=, WorkingDirectory=,
│   │                               # EnvironmentFile=/…/.env, ExecStart=venv/bin/gunicorn wsgi:app)
│   ├── nginx_transcribe.conf      # server block for transcribe.flyboybyte.com,
│   │                               # proxy_pass to 127.0.0.1:<port>, security headers,
│   │                               # client_max_body_size bump for audio uploads
│   └── DEPLOY.md                  # step-by-step: clone repo, venv, migrate, systemd
│                                   # enable, nginx symlink + certbot --nginx -d …
└── instance/                      # gitignored: local SQLite db (if used), not committed
```

Old files retire once ported: delete
`WAtranscribe-claude-public-app-clone-v1-u1ubpf/` directory and the original
`.zip` after the port is verified working (or move them to
`legacy/streamlit-original/` if the user wants a reference copy kept —
confirm at implementation time, default to deleting since git history will
preserve it once committed).

## Security hardening to add beyond the original Streamlit app

- Flask `SECRET_KEY` from env, required (fail fast if missing in prod).
- CSRF protection (Flask-WTF or manual token) on the password-login form and
  any state-changing POST (delete session, etc.).
- Security headers (Content-Security-Policy, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy) — either in Flask
  (`flask-talisman`) or in the nginx server block; prefer nginx so it applies
  uniformly.
- Rate-limit the password form server-side (port the existing lockout logic)
  — currently client/session-based only; consider also limiting by IP at
  nginx (`limit_req`).
- File upload validation: enforce allowed extensions
  (opus/m4a/mp3/wav/ogg/oga) server-side (was client-side `type=` hint only
  in Streamlit — must re-validate on the Flask side) and a max upload size
  (`MAX_CONTENT_LENGTH` in Flask + `client_max_body_size` in nginx).
  `.replit`'s old `maxUploadSize = 500` (MB) — pick a sane real limit (e.g.
  50–100MB per voice note) rather than copying 500MB.
- Store `APP_PASSWORD` as a hash in env or a proper `werkzeug.security`
  hash rather than comparing plaintext, and use `secrets.compare_digest`
  for the token/cookie comparison to avoid timing attacks.
- Ensure cookies (auth token, theme) are set `HttpOnly`, `Secure`, `SameSite`
  as appropriate — the Streamlit version's `_set_cookie_js` was JS-based;
  Flask can set these natively via response headers, which also allows
  `HttpOnly` for the auth cookie (JS-set cookies can't be HttpOnly).
- Run gunicorn as a non-root systemd user, `ProtectSystem=strict` /
  `NoNewPrivileges=true` in the unit file where practical.

## Open questions to resolve at implementation time (not blocking, but decide before/while coding)

1. **Database:** keep Postgres (matches original, good if other VPS projects
   already share a Postgres instance) vs. switch default to SQLite for
   simplicity on a single small VPS. Recommend: support both via
   `DATABASE_URL` (SQLAlchemy handles either), default to a local SQLite file
   under `instance/` if `DATABASE_URL` is unset, so first deploy doesn't
   require standing up Postgres.
2. **In-progress session storage:** for a multi-user public-ish deployment,
   holding full base64 audio + transcripts in the signed Flask cookie session
   won't scale (cookie size limits ~4KB). Recommend server-side session
   store (Flask-Session with filesystem or Postgres backend) keyed by a
   session id cookie, holding the same shape of data the Streamlit
   `st.session_state` did.
3. Whether to keep the original repo's zip / extracted Streamlit folder
   around as a reference (`legacy/`) or delete outright once the Flask port
   is verified working.
4. Confirm real nginx `server_name`/cert path conventions on the actual VPS
   before applying `deploy/nginx_transcribe.conf` — plan assumes standard
   `/etc/nginx/sites-available/` + `certbot --nginx`.

## Implementation order (for the resuming session)

1. [x] Scaffold `app/` package structure and `pyproject.toml` deps; get a bare
   Flask app booting locally. (`.venv` created with `python3 -m venv`;
   Python 3.14 on this machine, `requires-python = ">=3.11"`.)
2. [x] Port `database.py` → `app/models.py` + `app/db.py`, decide DB default
   (see Open Question 1 — resolved: SQLAlchemy engine picks Postgres or
   SQLite from `DATABASE_URL`, defaults to `instance/watranscribe.db`).
3. [x] Port `claude_integration.py`, `deepgram_integration.py`,
   `summary_mapper.py` into `app/services/` largely unchanged.
4. [x] Build `app/auth.py` password gate + templates/auth.html, with the
   security hardening above.
5. [x] Build transcribe route/template/player JS (the biggest chunk — this is
   where `render_audio_player_with_words()` gets decomposed into template +
   static JS + JSON data island).
6. [x] Build history route/template (list/view/delete/export TXT+JSON).
7. [x] Port PWA assets (manifest.json, sw.js, icons) and share-target JS.
8. [x] Local end-to-end test: booted the app under the Flask test client and
   under `gunicorn wsgi:app` (see verification notes below); upload/transcribe
   with *real* audio + real API keys was **not** exercised (no API keys
   available in this environment) — flagged for the user to verify manually.
9. [ ] Write `deploy/transcribe.service`, `deploy/nginx_transcribe.conf`,
   `deploy/DEPLOY.md`.
10. [ ] Update root `CLAUDE.md` and `README.md` to describe the new Flask
    architecture and deployment (existing `CLAUDE.md` at
    `WAtranscribe-claude-public-app-clone-v1-u1ubpf/CLAUDE.md` documents the
    *old* Streamlit architecture — supersede it, don't leave both).
11. [ ] Retire the old Streamlit folder/zip per decision in Open Question 3.

## Verification plan

- `flask run` locally with real `DEEPGRAM_API_KEY`/`ANTHROPIC_API_KEY` env
  vars (or dummy keys + mocked responses if the user doesn't want to spend
  API credits during dev) — upload a short real audio clip, confirm
  transcript + word timestamps + summary + click-to-seek all work.
- Verify password gate: correct/incorrect password, lockout after N
  attempts, cookie persists across reload, `HttpOnly`/`Secure` flags present
  (check via browser devtools or `curl -v`).
- Verify history: save, list, delete, export TXT/JSON.
- Before declaring deploy-ready: run `gunicorn wsgi:app` locally the same way
  systemd will invoke it, confirm it serves correctly, then dry-run the
  nginx config with `nginx -t` if testing on a machine with nginx installed.

### What was actually verified in the steps 1-8 pass (no API keys available)

- App factory boots cleanly (`create_app()`), no import errors.
- `flask` test client: unauthenticated `GET /` redirects to `/login`; login
  page renders with a CSRF token; wrong password shows "Incorrect password";
  5 wrong attempts triggers the lockout page; correct password sets the
  `wa_auth` cookie with `HttpOnly` + `SameSite=Lax` (and `Secure` when
  `request.is_secure`/production) and redirects to `/`; with `APP_PASSWORD`
  unset the gate is bypassed entirely (matches original behavior).
- `GET /` (transcribe/index) and `GET /history` render successfully once
  authed.
- File upload extension validation: `.exe` rejected server-side with a flash
  message; `.opus` accepted and flows through the (key-less) Deepgram call,
  which fails gracefully and stores the error text as the transcript instead
  of crashing the request.
- SQLite auto-creation confirmed: `instance/watranscribe.db` created on
  first `init_db()` call with no `DATABASE_URL` set.
- `gunicorn -w 1 -b 127.0.0.1:8931 wsgi:app` served `/`, `/history`,
  `/static/manifest.json`, `/static/sw.js` all with 200s.
- **Not verified** (no `DEEPGRAM_API_KEY`/`ANTHROPIC_API_KEY` in this
  environment): a real transcription round-trip, real Claude summarization,
  the redo-summary/level-pill flow, multi-file catch-up summarization, the
  in-browser waveform/word-click player (needs a browser, not just the test
  client), the PWA share-target flow end-to-end on a phone, and the theme
  toggle's client-side cookie + reload behavior in an actual browser.
