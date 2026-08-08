# WAtranscribe — decision log

Why things are the way they are, for whoever (human or Claude) resumes
this later. Chronological history/debugging narrative lives in
`PLAN.md`; this file is just the decisions and their reasoning.
`watranscribe-bot/DECISIONS.md` has its own separate, bot-specific
decision log (D-001 through D-012 in *that* file) — don't confuse the
two numbering sequences.

**D-001 — No database, ever.** Everything (transcript, summary,
audio-as-bytes, word timestamps) lives only in server-side session
storage. The app used to have a History tab backed by a DB; the user
called that "kinda dumb" for other people's voice messages and it was
removed entirely. This is a hard product constraint, not a missing
feature — don't reintroduce persistent storage of user-uploaded audio
without discussing it first.

**D-002 — Transcription and summarization are decoupled.** Uploading
only transcribes; summarization happens only when the user explicitly
picks a condensation level. Used to auto-summarize on upload, changed at
the user's request so nothing gets summarized before they've decided
they want it.

**D-003 — Claude Haiku, not Sonnet, for summarization.** Cheap and
plenty capable for condensing a transcript; cost was the deciding factor
over marginal quality gains from a bigger model.

**D-004 — Password gate.** `app/auth.py`, hashed password (never
plaintext) + lockout after repeated failures. Added after the initial
build; the app started with open access and that changed at some point
without every doc getting updated in sync (a stale memory claim caught
and corrected 2026-08-07 — see [[project-watranscribe-flask-migration]]).

**D-005 — Security headers at the nginx layer, not Flask.** CSP,
X-Frame-Options, etc. live in `deploy/nginx_transcribe.conf`. Keeping
them out of `app/__init__.py` avoids two sources of truth for the same
headers.

**D-006 — PWA Web Share Target as the primary WhatsApp-voice-note
delivery mechanism**, not a Meta Business API bot. Lets a user forward a
voice note to the app the same way they'd forward it to a contact, using
only browser-standard APIs (`manifest.json`'s `share_target` + a service
worker), with zero dependency on Meta as an intermediary. This is the
decision that made D-012 (shelving the bot) possible — it wasn't obvious
until this was actually built and tested that it could fully replace
what the bot was for.

**D-007 — Deploy via push-to-GitHub + SSH-pull-and-restart, no Docker.**
Matches the convention already used by other projects on the same VPS
(`~/budget/deploy.sh`) — consistency across projects on a shared box beat
any Docker-specific advantage for a single-process Flask app.

**D-008 — `watranscribe-bot` vendors its own Deepgram/Claude client code
rather than calling the live Flask app's HTTP API.** Driven by the
shared-VPS risk: an HTTP-API approach would make the bot a new
network-facing client of the production app, requiring new auth/rate
limiting/cost-cap design before the bot's actual purpose was even
decided. Vendoring means zero new inbound network path into the
production app, ever — moot now that the bot is fully shelved (D-012),
but the reasoning stands if it's ever picked back up.

**D-009 — Android TWA built specifically to fix a GrapheneOS gap, not to
replace the PWA.** Chrome's PWA install only creates a real OS-level
share-target registration if it successfully mints a WebAPK via a
round-trip to Google's server; GrapheneOS blocks that by design, so
install looks successful but the share target silently never registers.
The TWA (`watranscribe-twa/`) compiles the share intent-filter directly
into `AndroidManifest.xml` at build time — no Google server dependency.

**D-010 — Keep both the PWA and the TWA, don't pick one.** The TWA only
covers Android. Many of the user's contacts are on iPhones, where a PWA
(or nothing at all — Apple doesn't expose a share-target API to web
apps) is the only option; a TWA can't be sent to an iPhone user at all.
The PWA also needs zero build/signing/distribution overhead, so it stays
the default recommendation, with the TWA as the "actually works on my
specific Android + GrapheneOS setup" option.

**D-011 — One repo, not three.** `watranscribe-twa/` and
`watranscribe-bot/` were briefly split into their own GitHub
repos/git repos nested on disk under `trans/`, following an isolation
pattern from earlier deploy-risk discussions (separate systemd
unit/port/secrets per component). The user explicitly rejected this
once it actually happened ("why tf did u make 3 separate ones, thats not
what i wanted, and u knew that") — consolidated back into this single
repo via `git subtree add` (preserves each subproject's commit history
rather than flattening it). Runtime/deploy isolation (separate systemd
units, ports, secrets) is still the right call and is unaffected by this
— only the git/GitHub packaging changed. See
[[feedback-dont-split-repos-by-default]] in memory: default to one repo
per project going forward unless explicitly told otherwise.

**D-012 — Meta WhatsApp Business Cloud API bot is fully shelved**, not
"paused with intent to resume soon." Once D-006 (PWA share target) and
the TWA (D-009) were actually built and confirmed working end-to-end,
they solved the real use case — WhatsApp voice note → transcript,
conveniently — without ever routing anything through Meta as a data
processor, without the multi-week Meta App Review gate, and without the
new-attack-surface concerns of D-008. The user is privacy-conscious
(chose GrapheneOS deliberately) and the bot's core justification
(convenience) stopped being unique to it. Code and docs are kept, not
deleted — see `watranscribe-bot/PROJECT_STATE.md` — in case the
calculus changes, but there's no active plan to resume it.

**D-013 — Audio is served from a real HTTP endpoint (`GET /audio/<idx>`),
not embedded as base64 in the page.** This followed a genuinely long
debugging chase after the TWA installed successfully but audio wouldn't
play — several wrong theories were chased in order (chat-transfer
corruption → ruled out via byte-identical re-download; targeting a
too-new/alpha Android SDK → ruled out once the phone's real Android
version was confirmed; a missing `codecs=opus` MIME param → the actual
proximate error, but adding it broke a different way; Blob-URL
conversion of the `data:` URI → fixed duration but `fetch()` on the raw
`data:` URI failed outright on the real device with a large payload).
The real problem was architectural the whole time: a multi-MB base64
string embedded directly in HTML is ~33% larger than the raw bytes,
isn't a real seekable resource for the browser's audio demuxer to probe,
and apparently isn't even reliably `fetch()`-able on some mobile devices
at that size. Switching to a real streamed HTTP resource
(`send_file(BytesIO(...), conditional=True)`, real Range-request
support) fixed it outright and removed ~35 lines of client-side
data-URI/Blob workaround code that were papering over the real issue.
Verified via a local repro harness (real Flask app + real upload +
real Deepgram transcription of an actual WhatsApp voice note + real
static JS, driven through actual Chromium via Playwright) before
shipping, specifically to stop guessing blind.

**D-014 — Session/privacy window shortened from 6 hours to 30
minutes.** The user's explicit call: a tool meant for "upload →
transcribe → maybe summarize → done" shouldn't hold data any longer than
it takes to actually use it once. `PERMANENT_SESSION_LIFETIME` in
`app/config.py` and the VPS cron purge job
(`*/10 * * * * find .../flask_session -type f -mmin +30 -delete`) were
updated together — they have to move in lockstep or the privacy banner's
claim ("auto-expire within N") stops being accurate.
