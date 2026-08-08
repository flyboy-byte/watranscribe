# WAtranscribe-bot Decision Log

## D-001: Use direct Meta WhatsApp Cloud API

Date: 2026-07 (original planning session)
Status: Accepted

Decision: Use Meta's official WhatsApp Cloud API directly. Do not add Twilio initially.

Reasons:
- Meta is unavoidable for WhatsApp transport.
- Direct integration minimizes additional processors.
- A test number was already claimed.
- Twilio does not remove sender/business onboarding requirements.
- A small private beta does not need multi-channel abstraction.

Consequences: Logan handles Meta webhook, credentials, and number setup directly.

## D-002: No unofficial WhatsApp Web automation for production

Status: Accepted. Baileys/whatsapp-web.js/WAHA carry account-ban and protocol-breakage risk;
not worth it for a dependable utility.

## D-003: Reuse existing transcription engine, vendored not networked

Status: Accepted. `deepgram_client.py` is vendored into this repo (config passed as plain args)
rather than the bot calling the live Flask app's HTTP API — driven by the explicit VPS-sharing
security concern below (D-005). Zero new inbound network path into the production Flask app.

## D-004: No content retention

Status: Accepted. Audio/transcripts exist only long enough to produce one reply. No session
store, no disk persistence beyond the single request lifecycle, no logs containing raw
transcript text or phone numbers.

## D-005: Full isolation from other VPS projects

Date: 2026-07
Status: Accepted

Decision: Own git repo, own systemd `--user` unit, own port, own `.env`/secrets — no sharing
with the budget/finance tracker or the stock-trading hobby app on the same VPS.

Reasons: A compromise of this bot must not become a stepping-stone to anything
financially-adjacent on the box. This is the single most important constraint on the whole
project and overrides convenience at every turn.

## D-006: Own git repo, nested on disk inside `trans/`

Date: 2026-07-28
Status: Accepted

Decision: The bot's working directory lives at `/home/logan/projects/trans/watranscribe-bot/`
for Logan's local convenience, but is a fully independent git repo (own `git init`, own commit
history) and is excluded from the parent `trans/` repo via `.gitignore` (`watranscribe-bot/`).

Reasons: Reconciles "keep it in one place on disk" with D-005's isolation requirement — the
repo/deploy/secret boundary is unchanged, only the local folder location moved.

## D-007: No automatic external summarization

Status: Accepted (deferred). Stage 0 returns the raw transcript only. If summarization is added
later, it needs its own explicit privacy decision (see the handoff doc's Section 5.5/Phase 4) —
it is not a default extension of the transcription feature.

## D-008: Private allowlisted beta first, sandbox test number for Stage 0

Status: Accepted. No production/dedicated phone number, no App Review, no public onboarding
until Stage 0 proves the flow feels worth continuing.

## D-009: One worker, concurrency one, SQLite only if a durable queue is actually needed

Status: Accepted as the target design for Stage 1. Not yet built — Stage 0 hasn't reached the
point of needing a queue at all.

## D-010: No analytics, hosted error tracking, or third-party crash reporting

Status: Accepted. Would risk capturing transcript/payload content off-box.

## D-011: Dedicated subdomain (`bot.flyboybyte.com`) for the webhook, not a path under `transcribe.flyboybyte.com`

Date: 2026-08-06
Status: Accepted

Decision: When deployed, the webhook gets its own subdomain, own nginx server block, and own
certbot cert — not a reverse-proxied path under the existing production domain.

Reasons: Keeps D-005's isolation consistent at the DNS/nginx layer, not just the process/secret
layer. Avoids ever needing to edit the config of a domain that's currently serving real
production traffic just to add a bot route.

## D-012: Project parked, no time pressure to resume

Date: 2026-08-06
Status: Superseded by D-013

Decision: Pause all work here. Code is scaffolded but untested against real Meta/WhatsApp
traffic; nothing is deployed. Parking is a successful, deliberate outcome, not a stall.

Reasons: Logan is a college student and automotive technician with limited, uneven available
time; the project doesn't need to be rushed to a live state before that time exists. See
`PROJECT_STATE.md` and `RESUME_CHECKLIST.md` for exact resume steps.

## D-013: Project fully shelved, not just parked

Date: 2026-08-08
Status: Accepted

Decision: Move from "parked, resume when there's time" to "fully shelved, no active plan to
resume." Code and docs are kept, not deleted.

Reasons: The thing D-012 was waiting on time for — a working WhatsApp-voice-note-to-transcript
flow — got built and confirmed working a different way in the meantime: the PWA Web Share Target
plus an Android TWA (`trans/watranscribe-twa/`), neither of which routes anything through Meta as
a data processor, neither of which needed Meta App Review. That was this bot's core justification,
and it stopped being unique to this approach. See `trans/DECISIONS.md` D-006/D-009/D-012 for the
full reasoning across the whole project, not just this file. If resuming later, re-check whether
that reasoning still holds before restarting — don't just pick up where D-012 left off assuming
nothing changed.
