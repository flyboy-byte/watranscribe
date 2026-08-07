# watranscribe-bot — plan & status

**Status (2026-07-28):** Stage 0 scaffold built and verified locally
(signature validation, webhook handshake, payload routing — all with
mocked external calls; see agent report in session history / README for
detail). **Blocked on the user's side**: Meta is holding account changes
(including WhatsApp app/product creation) because it flagged an unrecognized
device — the user switched from their usual laptop to a phone mid-flow,
which reset Meta's device-trust signal. Not a UI/flow problem after all
(the earlier "Other" → "Business" mismatch was a red herring from testing
on an unfamiliar device). Fix is just time + consistency: keep using the
same (laptop) browser/device Meta already trusts, avoid VPNs, and it should
clear on its own (hours to a couple days).

This repo now lives at `/home/logan/projects/trans/watranscribe-bot/` on
disk (moved in from a standalone sibling directory on 2026-07-28) but is
**deliberately kept as its own git repo**, gitignored from the parent
`trans/` repo — the isolation rationale (separate deploy unit, separate
secrets, no shared blast radius with the production Flask app or the other
VPS projects) still applies; only the local folder location changed. Git
repo was just initialized here (`git init`) — not yet pushed to GitHub.

## Next steps once unblocked

1. User finishes Meta app creation (WhatsApp product added), gets: App
   Secret, temporary access token, test phone number ID, and adds their own
   phone as a registered recipient (up to 5 allowed on the test number).
2. User invents a `WHATSAPP_VERIFY_TOKEN` (any random string).
3. Fill in `.env` from `.env.example` with all 5 vars (4 WhatsApp + 1
   Deepgram key).
4. Get a public HTTPS URL for the webhook by deploying to the VPS: own
   systemd `--user` unit, own port, own subdomain — **`bot.flyboybyte.com`**
   (decided 2026-08-06), not a path under `transcribe.flyboybyte.com`. New
   nginx server block + its own certbot cert, zero edits to the existing
   production site's config. ngrok was considered and rejected (exposes the
   personal laptop instead of the already-isolated VPS deploy target).
5. Register the webhook URL + verify token with Meta (WhatsApp →
   Configuration in the app dashboard), subscribe to the `messages` field.
6. Send a real voice note from the registered test phone to the test
   number, confirm a transcript comes back.
7. Init git, push to a new private GitHub repo (matching the `trans/`
   convention: `gh repo create watranscribe-bot --private --source=.
   --remote=origin --push`).

## Full roadmap (unchanged from the approved plan)

<!-- Copied verbatim from /home/logan/.claude/plans/the-project-is-in-hashed-perlis.md
     at the time this repo was scaffolded — update both if the plan changes. -->

### Context

WAtranscribe (`/home/logan/projects/trans/`) just went through a privacy
pivot: no database, no history, everything ephemeral (~6h session lifetime,
cron-purged). The user wanted to explore branching this into an "open
source meta bot" — very early-stage, platform and purpose both
intentionally undecided. The one concrete signal is WhatsApp. The user's
explicit, driving concern is **security** — not hypothetically, but because
this VPS (`flyboybyte.com`, 51.81.80.126) already runs 4 projects side by
side, including a **budget/finance tracker** and a **stock trading hobby
experiment**. A new internet-facing bot component is a new attack surface
on a box where a compromise could plausibly reach financially-adjacent
services, not just this transcription toy. That risk profile shapes every
architecture choice below, not just a checklist item at the end.

### 1. Concrete low-risk starting point

Build a **WhatsApp sandbox proof-of-concept**: a small bot that receives a
voice note via the WhatsApp Business Cloud API test number, transcribes it,
and replies with text. Skip summarization at first. No production traffic,
no real phone number, no App Review needed — Meta's test/sandbox number
supports this for up to 5 developer-added recipient numbers, for free.

**Integration approach: extract/vendor shared logic, do not call the live
Flask app's HTTP API.** Reasons: an HTTP-API approach makes the bot a new
network-facing client of the production Flask app — a new inbound attack
surface on the same box, requiring a new auth scheme, rate limiting, and
cost caps before the bot's purpose is even decided. A shared
library/vendored code means the bot calls Deepgram directly with its own
keys, in its own process — zero new inbound network path into the existing
transcribe app, no shared session store or blast radius. It also extends
the "don't retain other people's audio" ethos: the bot handles audio
in-memory/temp-file only, independent of the Flask app's session store.

### 2. What "WhatsApp bot" concretely requires

- **Webhook**: HTTPS endpoint Meta POSTs incoming messages to. One-time GET
  verification handshake (challenge/response with a verify token you
  choose) registers the URL.
- **Signature validation**: every webhook POST carries
  `X-Hub-Signature-256` — HMAC-SHA256 of the raw body keyed with your App
  Secret. Must validate on every request or anyone who finds the URL can
  inject fake messages.
- **24-hour customer service window**: once a user messages you, free-form
  replies are allowed for 24h from their last message; outside that,
  only pre-approved template messages work. Low-friction for this bot
  since replies happen inside the window.
- **App Review**: the test number caps at 5 pre-registered recipients.
  Messaging arbitrary WhatsApp users requires Meta App Review — business
  verification, use-case description, a screencast — days to weeks. Real
  gate between spike and product.
- **Costs**: per-conversation (24h windows) pricing, varies by
  category/country, has changed historically — check current Meta pricing
  before going beyond the free sandbox.

### 3. Security concerns — resolve before real usage, not before the PoC

- **Bot↔backend auth**: only relevant if the HTTP-API path is ever chosen
  instead of vendoring — not needed under the recommended architecture.
- **Isolation from the other 3+ projects on this VPS**: own systemd
  `--user` unit, own port, own `.env`/secrets — no sharing with `budget`,
  the trading experiment, or WAtranscribe itself. Explicit pass at deploy
  time confirming no shared file permissions, no shared systemd `User=`
  escalation path, no accidentally-reused API keys.
- **Rate limiting / abuse prevention**: per-WhatsApp-sender limits at the
  bot layer — first line of defense since the bot is directly
  internet-facing to WhatsApp users.
- **Cost controls**: Deepgram is usage-based with no built-in spend cap.
  Provider-side billing alerts/hard caps, plus an app-side daily volume
  ceiling as an independent circuit breaker.
- **Input validation**: extension/size allowlist, plus audio *duration*
  caps (no human eyeballing uploads here), reject non-audio before it
  reaches Deepgram.
- **No retention**: audio/transcripts exist only long enough to produce one
  reply — no session store, no disk persistence, no logs containing raw
  transcript text.

### 4. "Meta bot" scoping options

- **(a) WhatsApp-native transcribe+summarize** — same flow as the website,
  over WhatsApp. Lowest scope, fastest demo, reuses the most logic.
- **(b) Multi-tool assistant bot** — transcription is one capability among
  several; open-ended, no validated second capability yet.
- **(c) Orchestrator/router across independent backend "skills"** — most
  literal "meta" reading; premature with only one real skill existing.

**Recommendation: prototype (a) first** (this repo). Doesn't foreclose
(b)/(c) later.

### 5. Repo / architecture recommendation

New repo (this one), not a subdirectory of `trans/`. Stage 0 vendors
`deepgram_client.py` (adapted, config passed as args, not Flask
`app.config`) rather than building a shared package yet — only promote to
a real installable package if both projects clearly keep needing it. Own
`.env`, own systemd `--user` unit on its own port (5759 is taken by
`trans/` — check `ss -tlnp` again before picking one), following
`trans/deploy/DEPLOY.md`'s conventions but as a fully separate unit/port
from every other project on the box.

### 6. Staged roadmap

- **Stage 0 — Spike (current)**: sandbox test number, vendored code, a
  webhook that receives a voice note and replies with the raw transcript.
  Only auth requirement is Meta's mandatory webhook signature check — no
  rate limiting yet, ngrok or similar fine for the public URL during dev.
- **Stage 1 — Harden for real usage**: only once Stage 0 feels worth
  continuing and a real number is wanted — Meta App Review; promote to a
  shared package if justified; per-sender rate limiting; daily cost
  ceiling; billing alerts; strict audio duration/size caps; confirm zero
  retention; write a deploy doc with an explicit isolation check against
  the budget/trading apps on the same box.
- **Stage 2 — Scope/monetization/multi-platform**: deliberately deferred
  until Stage 1 produces real usage data.

### Verification / decision checkpoints

- End of Stage 0: manually message the sandbox bot from a real phone,
  confirm transcript comes back correctly, confirm no audio/transcript
  persists anywhere in the bot's process/disk after the reply is sent.
- Before Stage 1: explicit written review of what's shared vs. isolated
  between this bot and the other 3+ projects on the VPS.
- Before Stage 2: real usage/cost data from Stage 1 informs any
  scope-broadening decision.
