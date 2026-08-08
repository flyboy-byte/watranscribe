# WAtranscribe → Flask migration & deployment plan

**Status: Deployed and live at https://transcribe.flyboybyte.com** (2026-07-16).
All 11 implementation steps done, full local verification with real API keys
and real audio passed, VPS recon-based deploy config written, and the actual
deployment (DNS, systemd user unit, nginx site, certbot TLS) completed and
verified. No password gate — open access, per explicit user decision.

**Product pivot (2026-07-16, post-launch):** a real-browser UI audit (see
below) surfaced both cosmetic bugs and a real product problem — the app was
persisting other people's WhatsApp voice messages to a database
indefinitely via the History feature, which the user correctly called out
as a bad default for a tool anyone can upload personal audio to. Response:
**removed the database and History feature entirely.** `app/db.py`,
`app/models.py`, `app/routes/history.py`, `app/templates/history.html` are
deleted; `sqlalchemy`/`psycopg2-binary` dropped from `pyproject.toml`.
Everything now lives only in server-side session storage
(`PERMANENT_SESSION_LIFETIME` cut from 7 days to 6 hours) with a cron job
(see `deploy/DEPLOY.md`) to purge expired session files promptly — there is
no persistent storage of user audio anywhere in this app, by design. Also
decoupled transcription from summarization: uploading only transcribes now;
summarization happens only when the user explicitly picks a condensation
level (previously it auto-summarized immediately on upload). Added a
privacy banner to the page ("we don't keep your data"). Also fixed 3 bugs
found during the same UI audit: stray markdown `**` artifacts in every
summary bullet (Claude's mid-line bold markers weren't fully stripped),
the history preview leaking a raw `"# Summary"` heading (moot now that
history is gone), and filenames truncating mid-extension.

**Not yet done:** redeploying this pivot to the live VPS (code is committed
locally; the production instance still runs the pre-pivot build with the
old database, including one real test session saved during the UI audit —
delete `~/watranscribe/instance/watranscribe.db` on the VPS as part of
deploying this, don't leave it behind).
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
- ~~Run gunicorn as a non-root systemd user, `ProtectSystem=strict` /
  `NoNewPrivileges=true` in the unit file where practical.~~ Superseded by
  actual VPS recon below — this box doesn't use per-app system users or
  sandboxed system units for any project, so `deploy/transcribe.service`
  matches the established `systemctl --user` pattern instead. Revisit only if
  the user explicitly wants to harden beyond this box's existing convention.

## VPS recon findings (2026-07-16, resolves Open Question 4)

SSH'd into `ubuntu@flyboybyte.com` (51.81.80.126) and inspected the actual
setup rather than assuming. Findings that changed the deploy plan:

- **No system-wide systemd units, no dedicated per-app system user.**
  Every project on this box (`budget`, `disc_tracker`, `moomoo`, etc.) runs
  as the `ubuntu` user via **user-level systemd** (`~/.config/systemd/user/`,
  managed with `systemctl --user`). Lingering is enabled
  (`loginctl show-user ubuntu` → `Linger=yes`), so user units survive
  reboot/logout without needing root units.
- **Projects live directly in `/home/ubuntu/<project>/`** (not `/srv/`),
  each with its own `.venv/`.
- **nginx**: site files at `/etc/nginx/sites-available/<domain>` (no `.conf`
  extension), minimal server blocks, TLS lines added by
  `certbot --nginx` (don't hand-write them), a shared
  `include snippets/security-headers.conf` (HSTS, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy — no CSP anywhere on this box), and
  one global `limit_req_zone ... zone=login` (in `/etc/nginx/nginx.conf`)
  that every app's `/login` route reuses.
- **Ports already in use**: 5757 (disc_tracker), 5758 (budget/uvicorn), 8080
  (trading dashboard), 11111/22222 (OpenD). **5759** is free and continues
  the existing numbering — used in `deploy/transcribe.service` and
  `deploy/nginx_transcribe.conf`.
- **Deploy pattern**: a per-repo `deploy.sh` (see `~/budget/deploy.sh` on the
  VPS) that pushes to GitHub locally, then SSHes in, `git pull`s, reinstalls
  deps, and `systemctl --user restart <name>.service`. `/home/logan/projects/trans/deploy.sh`
  mirrors this.
- Python 3.12.3 is available system-wide on the VPS — compatible with this
  project's `requires-python = ">=3.11"`.
- `transcribe.flyboybyte.com` has **no DNS record yet** — must be added
  before running `certbot --nginx` (HTTP-01 challenge needs it resolvable).

`deploy/transcribe.service`, `deploy/nginx_transcribe.conf`, and
`deploy/DEPLOY.md` have all been rewritten to match the above exactly,
replacing the earlier assumed-convention drafts.

## Open questions — resolved

1. **Database:** resolved — SQLAlchemy picks Postgres or SQLite from
   `DATABASE_URL`, defaults to `instance/watranscribe.db` (SQLite) if unset.
   No Postgres instance needed on the VPS for this app.
2. **In-progress session storage:** resolved — server-side Flask-Session
   (filesystem backend) keyed by a session-id cookie, holding the same
   shape of data the Streamlit `st.session_state` did.
3. **Old Streamlit folder/zip:** resolved — extracted folder deleted, zip
   kept on disk (gitignored, reference only).
4. **Real nginx/systemd conventions:** resolved — see "VPS recon findings"
   above.

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
9. [x] Write `deploy/transcribe.service`, `deploy/nginx_transcribe.conf`,
   `deploy/DEPLOY.md` — rewritten after real VPS recon (see above); also
   added `deploy.sh` at the repo root matching this box's existing
   redeploy pattern.
10. [x] Wrote new root `CLAUDE.md` and `README.md` describing the Flask
    architecture and deployment (old Streamlit `CLAUDE.md` no longer
    exists — it was inside the deleted extracted folder).
11. [x] Retired the old Streamlit folder (deleted); kept the zip on disk,
    gitignored. Repo initialized and pushed to
    `https://github.com/flyboy-byte/watranscribe` (private).

### Deployed (2026-07-16)

**Live at https://transcribe.flyboybyte.com.** DNS A record added by the
user; cloned to `~/watranscribe` on the VPS; production `.env` in place
(real Deepgram + Anthropic keys, `FLASK_ENV=production`) — **no
`APP_PASSWORD_HASH` set, by explicit user decision: the app is open to
anyone, no login gate.** `transcribe.service` installed as a user unit
(`systemctl --user enable --now`, confirmed `enabled` + lingering already on
for `ubuntu`), nginx site installed and reloaded, `certbot --nginx` issued a
real cert (expires 2026-10-14, auto-renews). Verified via curl: HTTPS 200,
HTTP→HTTPS 301, security headers present, `/static/manifest.json` and
`/static/sw.js` 200, `/history` 200.

- [ ] Still worth doing when convenient: verify in a real browser
  (waveform/word-click player, PWA install + WhatsApp share-target on an
  actual phone, theme toggle persistence) — curl can't exercise these.

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
  `request.is_secure`/production) and redirects to `/`; with
  `APP_PASSWORD_HASH` unset the gate is bypassed entirely (matches original
  behavior). Re-verified after the plaintext→hash fix with a real
  `generate_password_hash()` value — login, wrong password, and lockout all
  behave correctly against the hash.
- `GET /` (transcribe/index) and `GET /history` render successfully once
  authed.
- File upload extension validation: `.exe` rejected server-side with a flash
  message; `.opus` accepted.
- SQLite auto-creation confirmed: `instance/watranscribe.db` created on
  first `init_db()` call with no `DATABASE_URL` set.
- `gunicorn -w 1 -b 127.0.0.1:8931 wsgi:app` served `/`, `/history`,
  `/static/manifest.json`, `/static/sw.js` all with 200s.

### Real-API verification pass (with real `DEEPGRAM_API_KEY`/`ANTHROPIC_API_KEY`)

- Real transcription confirmed with a synthetic TTS clip and a real WhatsApp
  voice note (`.opus`) — accurate transcript text + word-level timestamps.
- Real Claude summarization confirmed — switched from `claude-sonnet-4-6` to
  `claude-haiku-4-5-20251001` (far cheaper, plenty capable for this task) with
  per-condensation-level `max_tokens` caps (150–1200) instead of a flat 8192;
  verified good summary quality on both a short synthetic clip and the real
  voice note.
- Fixed a real bug found in this pass: Deepgram failures were being stored as
  fake transcript text (`"Error: ..."`) and then handed to Claude to
  "summarize" — now returns an explicit `error` field, flashed to the user,
  and never summarized or saved as if it were real content.
- Bumped `deepgram-sdk` floor from `>=3.0` to `>=7.0` — the code uses the v5+
  API shape (`listen.v1.media.transcribe_file`) and the old floor could
  resolve an incompatible major version on a fresh install.
- **Still not verified** (needs a real browser, not just curl/test client):
  the in-browser waveform/word-click player, the PWA share-target flow on an
  actual phone, and the theme toggle's client-side cookie + reload behavior.

### PWA share-target flow — now investigated (2026-08-07)

The share-target flow (`app/static/sw.js`, `app/static/js/share-target.js`,
`app/static/manifest.json`'s `share_target`) already existed and was
correct, but was **completely undiscoverable** — the "Share from WhatsApp"
card in `index.html` was dead (`onclick="return false;"`), and nothing
explained that the PWA must be *installed* (not just visited) before
Android's share sheet will offer it. Fixed: `app/static/js/install.js`
drives a real `beforeinstallprompt` install flow, with iOS manual
instructions as a fallback. Deployed and live.

Deeper problem found on GrapheneOS specifically: Chrome/Brave's "Install
app" only creates a real OS-level share target if it successfully mints a
**WebAPK** via a round-trip to Google's server — GrapheneOS blocks that by
design, so install *looks* successful (standalone display, correct icon)
but never actually registers with Android's share sheet. Confirmed via
`chrome://webapks` showing an empty list. Not fixable from the site's code
— it's a Google-infrastructure dependency inherent to Chrome's install
mechanism, not a bug here.

Workaround: a real Android app, `com.flyboybyte.watranscribe`, built as a
Trusted Web Activity (TWA) with the share intent-filter compiled directly
into its manifest — no Google server dependency. Lives in its own repo,
`~/projects/watranscribe-twa/` (own git repo, same isolation pattern as
`watranscribe-bot/`) — see that repo's `STATUS.md` for full build details,
signing key info, and current status. `trans/app/routes/transcribe.py` now
serves `/.well-known/assetlinks.json` (deployed, live) so the TWA can open
full-screen once installed.

**Status: blocked on getting a clean copy of the built APK onto the test
phone** — chat file transfer produced a corrupted copy (Android's "problem
parsing the package"); the APK itself verified clean locally
(`apksigner verify`, zip integrity, no ABI issues). Next step is `adb
install` once the phone is connected — see `watranscribe-twa/STATUS.md`
for the exact resume steps.

*(Superseded by the sections below — the APK transfer issue and the repo
layout described above are no longer current.)*

### TWA fixed, verified working end-to-end (2026-08-07/08)

The "problem parsing the package" install failure was **not** transfer
corruption (ruled out with a byte-identical re-download) — real cause was
a malformed `AndroidManifest.xml`: bubblewrap translated the site's
`share_target.params.files[0].accept` list (which mixed real MIME types
with bare file extensions like `.opus`) verbatim into `<data
android:mimeType="...">` entries. Android's manifest parser throws on the
first invalid one, failing the *entire* package parse — same error
regardless of signing, SDK level, or transfer method. Fixed at the source
(`app/static/manifest.json` now lists only real MIME types) and confirmed
working: installs clean, opens full-screen, WhatsApp share-to-app works.

**Repo consolidation (2026-08-07)**: `watranscribe-twa/` and
`watranscribe-bot/` were briefly separate GitHub repos/git repos nested on
disk under `trans/`. The user explicitly didn't want that ("why tf did u
make 3 separate ones") — merged back into this single repo via `git
subtree add` (preserves each one's commit history rather than flattening
it). All three — this repo, the bot, the TWA — now live at
`github.com/flyboy-byte/watranscribe`, public. See
[[feedback-dont-split-repos-by-default]] in memory. TWA APK releases are
published under this repo's GitHub Releases tab (`twa-v*` tags).

### Audio playback bug hunt → architecture fix (2026-08-08)

Once the TWA installed, audio playback didn't work at all — a multi-round
debugging chase (documented in full in `DECISIONS.md` under D-013) that
went through several wrong theories (transfer corruption, SDK level,
codec MIME params) before landing on the real cause: audio was embedded
as a giant base64 `data:` URI directly in the page. That's fundamentally
the wrong architecture for anything beyond a tiny clip — it can't be
duration-probed reliably, isn't seekable, and `fetch()` on the resulting
URI failed outright on the user's mobile device for a multi-MB payload.

**Fix**: audio is now served from a real HTTP endpoint,
`GET /audio/<idx>`, streamed via `send_file(BytesIO(...),
conditional=True)` for proper `Content-Type`/Range-request support. The
`<audio>` tag just points `src=` at that URL — no client-side
base64/Blob/data-URI handling anywhere anymore. Verified end-to-end with
a local repro harness (real Flask app, real `/upload`, real Deepgram
transcription of an actual WhatsApp voice note, real static JS, driven
through actual Chromium via Playwright) before shipping: playback,
duration, and click-to-seek all confirmed working, not just assumed.

### Privacy window shortened (2026-08-08)

`PERMANENT_SESSION_LIFETIME` cut from 6 hours to **30 minutes** — the
user's explicit call, on the theory that a privacy-first tool doing a
quick "upload → transcribe → maybe summarize → done" flow shouldn't hold
data any longer than it takes to actually use it. The VPS purge cron job
was updated to match (`*/10 * * * * find ... -mmin +30 -delete`, was `15
* * * * find ... -mmin +360 -delete`) — both the app-side expiry and the
on-disk cleanup cadence need to move together or the privacy banner's
claim stops being true.

### UI pass: numbered summary points, more breathing room (2026-08-08)

Cousin's live-test feedback plus a reference screenshot of a differently
laid-out sibling deployment (`watranscribe.replit.app`, same backend
logic, different frontend) prompted two things: (1) replacing the
checkmark-box bullet style for summary points with numbered points (01,
02, 03) + thin dividers — this also fixed a real visual bug where
Detailed/Full-level summaries (which sometimes include section-header-like
lines from Claude, e.g. "Main Themes:") got an awkward checkmark glued in
front of them; (2) a light spacing pass (more margin/padding on the
privacy banner, dropzone, hero card, action row) since the page felt
cramped. Explicitly **not** a full redesign — the user was clear about
that ("not asking for a full complete ui rework, just suggesting ideas").

See `ARCHITECTURE.md` for a current system overview and `DECISIONS.md`
for the full decision log (including why the Meta WhatsApp bot is fully
shelved, and why both the PWA and the TWA are kept rather than picking
one).
