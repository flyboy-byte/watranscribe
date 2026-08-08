# WAtranscribe — architecture overview

This is the map for someone (human or Claude) picking this project back
up after a break. For day-to-day command/module reference, see
`CLAUDE.md`. For the reasoning behind specific choices, see
`DECISIONS.md`. For the chronological build/debug history, see `PLAN.md`.

## What this is

A WhatsApp/Signal voice-note transcription + AI-summarization tool, live
at **transcribe.flyboybyte.com**. One Flask backend, three ways to reach
it:

```
                         ┌─────────────────────────┐
                         │   Flask app (app/)       │
                         │   Deepgram + Claude       │
                         │   server-side session      │
                         │   (30 min TTL, no DB)       │
                         └───────────┬─────────────┘
                                     │ HTTPS
              ┌──────────────────────┼──────────────────────┐
              │                      │                       │
       Browser / PWA          Android TWA              (parked) WhatsApp bot
   app/templates + static/   watranscribe-twa/          watranscribe-bot/
   Web Share Target API      Trusted Web Activity        Meta Cloud API webhook
   (any platform)            (Android only, real         vendored Deepgram client
                              OS share-sheet entry)       never deployed
```

All three surfaces are in this one repo (`github.com/flyboy-byte/watranscribe`,
public) — `watranscribe-bot/` and `watranscribe-twa/` are subdirectories
with their own build tooling/dependencies, merged in via `git subtree` to
keep their commit history rather than three separate repos. See
`DECISIONS.md` D-011 for why they're one repo, not three.

## The Flask app (`app/`)

Request flow: upload → Deepgram transcription (immediate) → user picks a
condensation level → Claude summarization (only on request, never
automatic). Everything lives in server-side session storage
(Flask-Session, filesystem backend) for 30 minutes, then expires — no
database, ever. See `CLAUDE.md`'s "Module layout" section for the file-by-file
breakdown; not duplicated here.

**Audio serving**: `GET /audio/<idx>` streams the session's stored audio
via `send_file(BytesIO(...), conditional=True)` — a real HTTP resource
with proper `Content-Type` and Range-request support for seeking. This
replaced an earlier design that embedded audio as a base64 `data:` URI
directly in the page, which turned out to be unreliable on real mobile
devices (see `DECISIONS.md` D-013 for the full story — that bug took
several rounds to actually root-cause).

## Browser / PWA (`app/templates/`, `app/static/`)

Works everywhere (Android, iOS, desktop) with zero install requirement,
and installs as a real PWA with a Web Share Target (`manifest.json`'s
`share_target` + `sw.js` intercepting the share POST) so voice notes can
be shared to it directly from WhatsApp/Signal on platforms that support
that API. iOS never gets a real share-target entry (Apple doesn't expose
that API to PWAs) but the site still works fine there manually.

## Android TWA (`watranscribe-twa/`)

A native, signed Android APK wrapping the same site as a [Trusted Web
Activity](https://developer.chrome.com/docs/android/trusted-web-activity) —
built with Google's `bubblewrap` CLI. Exists because Chrome's PWA install
on Android only creates a *real* OS-level share-target registration if it
successfully mints a WebAPK via a round-trip to Google's server — some
environments (GrapheneOS, confirmed) block that, so the PWA install looks
successful but the share target never actually registers with Android.
The TWA sidesteps this: the share intent-filter is compiled directly into
`AndroidManifest.xml` at build time, no Google server involved.

See `watranscribe-twa/STATUS.md` for exact build/signing/reproduction
steps. Signed releases are published under this repo's GitHub Releases
tab (`twa-v*` tags) — that's the intended install path (download the APK
link on the phone), not chat file transfer (corrupts the file) and not
`adb install` (works, but needs a USB/wireless-debugging connection).

## WhatsApp bot (`watranscribe-bot/`) — fully shelved

An early-stage spike for a Meta WhatsApp Business Cloud API bot that
would transcribe voice notes sent directly to it. Scaffolded, unit-tested
with mocked external calls, **never deployed, never exercised against
real Meta/Deepgram traffic**. Fully shelved — not "paused with intent to
resume soon," genuinely deprioritized — once the PWA+TWA combination
turned out to solve the actual use case (WhatsApp voice note →
transcript, conveniently) without ever routing anything through Meta as
a data processor. See `DECISIONS.md` D-012 for the full reasoning. The
code and docs are kept (not deleted) in case the calculus changes later,
but there's no active plan to resume it.

## Security model

- Password gate (`app/auth.py`) in front of the whole app.
- CSRF protection (Flask-WTF) on all state-changing POSTs.
- File upload extension allowlist enforced server-side.
- Security headers (CSP, X-Frame-Options, etc.) applied at the nginx
  layer, not in Flask.
- No database, no persistent storage of user audio, 30-minute session
  TTL + a matching VPS cron purge job — see `DECISIONS.md` D-001/D-014.
- Deployed alongside other unrelated projects (a budget/finance tracker,
  a stock-trading experiment) on one shared VPS — every isolation
  decision in `DECISIONS.md` that mentions "shared VPS risk" is about
  not letting a compromise here reach those.
