# WAtranscribe-bot Project State

Last updated: 2026-08-06
Updated by: Claude (session), at Logan's request to park the project

## Current status
**Parked** — no active work planned until Logan has more free time (post-college-return).

## What works
- Existing website (`trans/`, `transcribe.flyboybyte.com`): fully functional, unaffected by any of this bot work.
- Bot webhook code: scaffolded and verified locally with **mocked** external calls only —
  signature validation (`X-Hub-Signature-256`), GET verification handshake, payload routing.
  Never exercised against a real Meta webhook or real Deepgram call.
- Meta test number: claimed (Step 1 of Meta's setup flow — "Completed" as of last check).
- Meta webhook: **not** registered/verified with Meta — no callback URL has ever been configured.
- Phone number registration (Step 2, "Register your WhatsApp phone number"): **not confirmed complete**
  — this was the last open task before parking.
- Real end-to-end test (send a voice note, get a transcript back): **never attempted.**

## Deployment
- Server: none — nothing has been deployed anywhere. No systemd unit exists for this bot.
- Repo location: `/home/logan/projects/trans/watranscribe-bot/` (own git repo, gitignored from
  the parent `trans/` repo — see `DECISIONS.md` D-006).
- Branch: `master`, first commit made as part of this parking checkpoint (previously zero commits).
- Reverse proxy / process manager: N/A — not deployed.
- Planned (not built): dedicated subdomain `bot.flyboybyte.com`, own nginx server block, own
  certbot cert, own systemd `--user` unit on its own port (see `DECISIONS.md` D-011).

## Meta identifiers (NO SECRETS)
- App ID: _(fill in — not captured during this session)_
- WABA ID: _(fill in — not captured during this session)_
- Phone Number ID: _(already in `.env` as `WHATSAPP_PHONE_NUMBER_ID` — not a secret, but left
  out of this file deliberately; copy it in yourself if useful)_
- Graph API version: _(not yet pinned anywhere in code — must be set in `app/config.py` before
  resuming; check current default at implementation time, do not assume an old version)_
- Callback URL: none registered yet.

## Secrets
Stored at: `/home/logan/projects/trans/watranscribe-bot/.env` (gitignored, confirmed via
`git check-ignore -v .env`). Never committed to git — verified: repo had zero commits until
this parking checkpoint, and `.env` was never staged.

Rotation date: 2026-08-06. A WhatsApp access token was pasted in plaintext in chat earlier the
same day; Logan confirmed it was rotated in Meta's dashboard before parking. No action needed
on resume.

## Known issues
- Token exposure above — needs explicit confirmation/rotation.
- Graph API version is not pinned in `app/config.py` yet.
- No automated tests were ever run against a real Meta account (all fixtures/mocks).

## Privacy status
Design intent unchanged from `PLAN.md`/`DECISIONS.md`: zero retention, vendored transcription
logic (no new inbound path into the production Flask app), signature-validated webhook only.
None of this has been exercised against real traffic yet, so there is nothing to audit for actual
privacy behavior — only the design has been reviewed, not a running system.

## Next three tasks (in order, on resume)
1. Confirm/rotate the exposed Meta access token (see Secrets section above).
2. Finish "Register your WhatsApp phone number" in Meta's dashboard (Step 2) using the existing
   test number — no new/real business number is needed for this.
3. Deploy to the VPS: new systemd `--user` unit, new port, `bot.flyboybyte.com` subdomain +
   nginx server block + certbot cert (see `DECISIONS.md` D-011), then register the webhook URL
   with Meta and send one real test voice note end-to-end.

## Exact resume command/process
See `RESUME_CHECKLIST.md`.

## Rollback
Nothing is deployed, so there is nothing to roll back. If a partial VPS deploy is ever started
and needs undoing later: stop/disable the systemd unit, remove the nginx server block, and
`certbot delete` the `bot.flyboybyte.com` cert. Not applicable at the current (parked) state.
